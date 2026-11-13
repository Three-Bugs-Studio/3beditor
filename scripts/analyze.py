"""Measure a video's style so Claude can "watch" it.

usage: python analyze.py VIDEO [--out DIR] [--threshold 0.3] [--transcript] [--target style.json] [--cuts-from edl.json]
Writes DIR/style.json and DIR/contact.png. Never modifies VIDEO.
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

SCHEMA = 1
SHEET_COLS, SHEET_ROWS = 4, 4


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p


def probe(video):
    data = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)]).stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"
              and not s.get("disposition", {}).get("attached_pic")), None)  # MP3 cover art is not a video
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    if v is None:
        if not has_audio:
            sys.exit(f"no video or audio stream in {video}")
        # a music file: only its length, loudness and beats are measured
        return {"duration_s": round(float(data["format"]["duration"]), 3), "width": None, "height": None,
                "aspect": None, "fps": None, "has_audio": True}
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
    w, h = int(v["width"]), int(v["height"])
    return {
        "duration_s": round(float(data["format"]["duration"]), 3),
        "width": w,
        "height": h,
        "aspect": "9:16" if h > w * 1.5 else "16:9" if w > h * 1.5 else "1:1" if abs(w - h) < 0.1 * w else f"{w}:{h}",
        "fps": round(int(num) / int(den), 3) if int(den) else None,
        "has_audio": any(s["codec_type"] == "audio" for s in data["streams"]),
    }


def ffmpeg_print(video, vf):
    """Run a filter graph that prints per-frame metadata to stdout."""
    return run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an",
                "-vf", f"{vf},metadata=print:file=-", "-f", "null", "-"]).stdout


SOFT_FPS = 5      # sampling rate for animated transitions (slides, blurs) that change too slowly per frame
MERGE_S = 0.5     # scene changes closer than this are one transition


def _scores(video, vf):
    out = ffmpeg_print(video, vf)
    return list(zip((float(t) for t in re.findall(r"pts_time:([\d.]+)", out)),
                    (float(x) for x in re.findall(r"scene_score=([\d.]+)", out))))


def scene_cuts(video, threshold):
    """Return (cut times, transition kinds). Two passes: every frame for hard cuts,
    5 fps for animated transitions whose change is spread over many frames."""
    hard = _scores(video, f"scale=320:-2,select='gt(scene,{threshold})'")  # 320px proxy: same cuts, much faster
    soft = _scores(video, f"fps={SOFT_FPS},scale=320:-2,select='gt(scene,{threshold * 0.8})'")
    events = sorted([(t, sc, "hard") for t, sc in hard] + [(t, sc, "animated") for t, sc in soft])
    clusters = []
    for e in events:
        if clusters and e[0] - clusters[-1][-1][0] <= MERGE_S:
            clusters[-1].append(e)
        else:
            clusters.append([e])
    cuts, kinds = [], {"hard": 0, "animated": 0}
    for c in clusters:
        pick = max(c, key=lambda e: (e[2] == "hard", e[1]))  # prefer the exact hard-cut frame
        cuts.append(round(pick[0], 3))
        kinds[pick[2]] += 1
    return cuts, kinds


def pacing(cuts, duration):
    cuts = sorted({c for c in cuts if 0 < c < duration})
    bounds = [0.0] + cuts + [duration]
    shots = [round(b - a, 3) for a, b in zip(bounds, bounds[1:])]

    def avg_in(lo, hi):
        part = [s for a, s in zip(bounds, shots) if a < hi and a + s > lo]  # shots overlapping this third
        return round(statistics.mean(part), 3) if part else None

    third = duration / 3
    return {
        "shot_count": len(shots),
        "cuts_per_min": round(len(cuts) / duration * 60, 2) if duration else 0,
        "avg_shot_s": round(statistics.mean(shots), 3),
        "median_shot_s": round(statistics.median(shots), 3),
        "min_shot_s": min(shots),
        "max_shot_s": max(shots),
        "first_cut_s": cuts[0] if cuts else None,  # how fast the hook moves
        "avg_shot_by_third_s": [avg_in(0, third), avg_in(third, 2 * third), avg_in(2 * third, duration)],
        "cuts_s": cuts,
        "shots_s": shots,
    }


def color(video):
    out = ffmpeg_print(video, "fps=2,scale=160:-2,signalstats")
    keys = {"YAVG": "brightness", "SATAVG": "saturation", "UAVG": "u", "VAVG": "v"}
    samples = {k: [float(x) for x in re.findall(rf"lavfi\.signalstats\.{k}=([\d.]+)", out)] for k in keys}
    if not samples["YAVG"]:
        return None
    m = {name: statistics.mean(samples[k]) for k, name in keys.items()}
    # values are 8-bit (0-255); 128 is neutral for u/v
    warmth = round((m["v"] - 128) - (m["u"] - 128), 1)
    return {
        "brightness_0_255": round(m["brightness"], 1),
        "brightness_spread": round(statistics.pstdev(samples["YAVG"]), 1),
        "saturation_0_255": round(m["saturation"], 1),
        "warmth": warmth,
        "tint": "warm" if warmth > 4 else "cool" if warmth < -4 else "neutral",
    }


def loudness(video):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn", "-af", "ebur128=peak=true",
               "-f", "null", "-"]).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    lra = re.findall(r"LRA:\s+([\d.]+) LU", err)
    tp = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", err)
    return {"integrated_lufs": float(i[-1]) if i else None, "range_lu": float(lra[-1]) if lra else None,
            "true_peak_dbtp": float(tp[-1]) if tp and tp[-1] != "-inf" else None}


def contact_sheet(video, duration, path):
    n = SHEET_COLS * SHEET_ROWS
    times = [round(duration * (i + 0.5) / n, 2) for i in range(n)]
    # fps=n/duration samples n evenly spaced frames; tile stitches them left-to-right, top-to-bottom
    run(["ffmpeg", "-hide_banner", "-y", "-i", str(video), "-an",
         "-vf", f"fps={n}/{duration},scale=320:-2,tile={SHEET_COLS}x{SHEET_ROWS}",
         "-frames:v", "1", str(path)])
    return times


def _has_librosa():
    try:
        import librosa  # noqa: F401
        return True
    except ImportError:
        return False


def beats(video, cuts, tmp_dir):
    """Music tempo and how many cuts land on a beat. None if librosa is not installed."""
    try:
        import librosa
    except ImportError:
        return None
    wav = Path(tmp_dir) / "_beats.wav"
    run(["ffmpeg", "-hide_banner", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "22050", str(wav)])
    try:
        y, sr = librosa.load(str(wav), sr=22050)
        tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
    finally:
        wav.unlink(missing_ok=True)
    times = [round(float(t), 3) for t in librosa.frames_to_time(frames, sr=sr)]
    on_beat = [c for c in cuts if times and min(abs(c - t) for t in times) <= 0.1]
    return {
        "bpm": round(float(getattr(tempo, "item", lambda: tempo)()), 1),
        "beats_s": times,
        "cut_on_beat_ratio": round(len(on_beat) / len(cuts), 2) if cuts else None,
    }


def transcript(video, model_size="base"):
    """Word-level speech transcript. None if faster-whisper is not installed."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    import numpy as np  # installed with faster-whisper
    # decode with our ffmpeg, not faster-whisper's PyAV path, which breaks across PyAV versions
    pcm = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1",
                          "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segs, info = model.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, vad_filter=True)
    words = [{"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)}
             for seg in segs for w in (seg.words or [])]
    spoken = sum(w["end"] - w["start"] for w in words)
    return {
        "language": info.language,
        "text": " ".join(w["w"] for w in words),
        "words_per_min": round(len(words) / spoken * 60, 1) if spoken else 0,
        "words": words,
    }


# metric path, tolerance, relative? -> used by compare()
CHECKS = [
    ("format.aspect", None, False),
    ("pacing.avg_shot_s", 0.25, True),
    ("pacing.cuts_per_min", 0.25, True),
    ("color.brightness_0_255", 15, False),
    ("color.saturation_0_255", 15, False),
    ("color.warmth", 6, False),
    ("audio.integrated_lufs", 2, False),
]


def _get(d, path):
    for k in path.split("."):
        d = d.get(k) if isinstance(d, dict) else None
    return d


def compare(actual, target):
    """Diff a measured style against a target style/preset. Metrics missing on either side are skipped."""
    checks = []
    for path, tol, rel in CHECKS:
        a, t = _get(actual, path), _get(target, path)
        if a is None or t is None:
            continue
        if tol is None:
            ok = a == t
        else:
            ok = abs(a - t) <= (tol * abs(t) if rel else tol)
        checks.append({"metric": path, "target": t, "actual": a, "ok": ok,
                       **({} if tol is None else {"diff": round(a - t, 2)})})
    tp = _get(actual, "audio.true_peak_dbtp")
    if tp is not None:  # delivery limit, not a style: peaks above -1 dBTP clip after the app re-encodes the upload
        checks.append({"metric": "audio.true_peak_dbtp", "target": "<= -1.0", "actual": tp, "ok": tp <= -1.0})
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def edl_cuts(edl_path):
    """Exact cut times of a video rendered from an EDL (detection misses fades between similar shots)."""
    sys.path.insert(0, str(Path(__file__).parent))
    import render
    edl = render.load(edl_path)
    plan, clips, fps = render.frame_plan(edl), edl["clips"], float(edl.get("fps", 30))
    cuts = [round((plan[i][0] + plan[i][2] / 2) / fps, 3) for i in range(1, len(clips))]  # middle of each transition
    hard = sum(c["tin"]["type"] == "cut" for c in clips[1:])
    return cuts, {"hard": hard, "animated": len(cuts) - hard}


def analyze(video, out_dir, threshold=0.3, with_transcript=False, model_size="base", cuts_from=None):
    video, out_dir = Path(video), Path(out_dir)
    if not video.is_file():
        sys.exit(f"not a file: {video}")
    out_dir.mkdir(parents=True, exist_ok=True)
    info = probe(video)
    if info["width"] is None:  # music file
        cuts = edl_cuts(cuts_from)[0] if cuts_from else []
        style = {"schema": SCHEMA, "source": video.name, "format": info, "pacing": None, "color": None,
                 "audio": loudness(video), "music": beats(video, cuts, out_dir), "speech": None,
                 "contact_sheet": None, "visual_notes": None,
                 "not_measured": [] if _has_librosa() else ["music beats (pip install librosa)"]}
        (out_dir / "style.json").write_text(json.dumps(style, indent=2), encoding="utf-8")
        return style
    sheet = out_dir / "contact.png"
    cuts, kinds = edl_cuts(cuts_from) if cuts_from else scene_cuts(video, threshold)
    pace = {**pacing(cuts, info["duration_s"]), "transitions": kinds}
    music = beats(video, pace["cuts_s"], out_dir) if info["has_audio"] else None
    speech = transcript(video, model_size) if with_transcript and info["has_audio"] else None
    not_measured = []
    if info["has_audio"] and music is None:
        not_measured.append("music beats (pip install librosa)")
    if with_transcript and info["has_audio"] and speech is None:
        not_measured.append("transcript (pip install faster-whisper)")
    style = {
        "schema": SCHEMA,
        "source": video.name,
        "format": info,
        "pacing": pace,
        "color": color(video),
        "audio": loudness(video) if info["has_audio"] else None,
        "music": music,
        "speech": speech,
        "contact_sheet": {"file": sheet.name, "grid": f"{SHEET_COLS}x{SHEET_ROWS}",
                          "times_s": contact_sheet(video, info["duration_s"], sheet)},
        # filled in by Claude after viewing contact.png: captions, transitions, framing, mood
        "visual_notes": None,
        "not_measured": not_measured,
    }
    (out_dir / "style.json").write_text(json.dumps(style, indent=2), encoding="utf-8")
    return style


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which cannot print Vietnamese
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", default=None, help="output folder (default: <video name>_style next to the video)")
    ap.add_argument("--threshold", type=float, default=0.3, help="scene-change sensitivity 0-1; lower finds more cuts")
    ap.add_argument("--transcript", action="store_true", help="add a word-level transcript (needs faster-whisper)")
    ap.add_argument("--model", default="base", help="whisper model size: tiny, base, small, medium")
    ap.add_argument("--target", help="a style.json or preset to compare this video against")
    ap.add_argument("--cuts-from", help="edl.json this video was rendered from: use its exact cuts instead of detecting")
    a = ap.parse_args()
    out = a.out or Path(a.video).with_name(Path(a.video).stem + "_style")
    s = analyze(a.video, out, a.threshold, a.transcript, a.model, a.cuts_from)
    summary = {k: s[k] for k in ("format", "color", "audio")}
    if s["pacing"]:
        summary["pacing"] = {k: v for k, v in s["pacing"].items() if k not in ("cuts_s", "shots_s")}
    if s["music"]:
        summary["music"] = {k: s["music"][k] for k in ("bpm", "cut_on_beat_ratio")}
    if s["speech"]:
        summary["speech"] = {k: s["speech"][k] for k in ("language", "words_per_min", "text")}
    if a.target:
        summary["match"] = compare(s, json.loads(Path(a.target).read_text(encoding="utf-8")))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"wrote {Path(out) / 'style.json'}" + (f" and {Path(out) / 'contact.png'}" if s["contact_sheet"] else ""))
    if a.target and not summary["match"]["ok"]:
        sys.exit(2)  # style mismatch: caller should adjust the edit and re-render
