"""Picture boards a customer approves before the full render.

usage:
  python board.py styles                                 list the preset styles (JSON)
  python board.py gallery CLIP [--at 5.0] --out DIR      the customer's own frame in every preset style -> DIR/gallery.png
  python board.py storyboard EDL.json --out DIR          one key frame per shot, graded and captioned -> DIR/storyboard.png
  python board.py transitions                            list the transition library (JSON)
  python board.py transitions --clip A [--clip2 B] --out DIR   reel of every transition on the customer's clips
                                                         -> DIR/transitions_reel.mp4 + DIR/transitions.png
  python board.py fonts --text "Về đích" [--clip C] [--fonts "A,B"] --out DIR   their words in each font -> DIR/fonts.png
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import render  # noqa: E402

STYLES = Path(__file__).resolve().parent.parent / "styles"
COLS = 3


def list_styles():
    out = []
    for p in sorted(STYLES.glob("*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        out.append({"id": p.stem, "name": s.get("name", p.stem), "description": s.get("description", ""),
                    "best_for": s.get("best_for", "")})
    return out


def ff(args, cwd=None):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError(p.stderr[-2000:])


def frame_at(video, t, png):
    ff(["-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1", str(png)])


def tile(frames, labels, out_png):
    """Grid of frames (time order, left to right) with a numbered label on each panel."""
    work = Path(out_png).parent
    for i, f in enumerate(frames):
        Path(f).replace(work / f"_panel_{i:03d}.png")
    rows = -(-len(frames) // COLS)
    ff(["-i", "_panel_%03d.png", "-vf", f"tile={COLS}x{rows}:padding=6:color=0x111111", "-frames:v", "1", "_grid.png"],
       cwd=work)
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                                    "-of", "csv=p=0", str(work / "_panel_000.png")], capture_output=True, text=True)
               .stdout.strip().split(","))
    # tile padding sits only between panels, not around the edge
    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {COLS * w + (COLS - 1) * 6}",
           f"PlayResY: {rows * h + (rows - 1) * 6}", "", "[V4+ Styles]",
           "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,"
           "StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
           f"Style: L,Arial,{max(14, w // 16)},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,4,0,7,0,0,0,1",
           "", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    for i, text in enumerate(labels):
        x, y = (i % COLS) * (w + 6) + 8, (i // COLS) * (h + 6) + 8
        ass.append(f"Dialogue: 0,0:00:00.00,0:00:05.00,L,,0,0,0,,{{\\pos({x},{y})}}{text}")
    (work / "_labels.ass").write_text("\n".join(ass) + "\n", encoding="utf-8-sig")
    ff(["-i", "_grid.png", "-vf", "subtitles=_labels.ass", "-frames:v", "1", Path(out_png).name], cwd=work)
    for f in work.glob("_*"):
        f.unlink()
    return str(out_png)


def gallery(clip, out_dir, at=None, size=(1080, 1920)):
    clip, out_dir = Path(clip).resolve(), Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if at is None:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(clip)], capture_output=True, text=True).stdout)
        at = dur * 0.4
    frames, labels, styles = [], [], list_styles()
    with tempfile.TemporaryDirectory() as tmp:
        for i, st in enumerate(styles):
            edit = {k: v for k, v in json.loads((STYLES / f"{st['id']}.json").read_text(encoding="utf-8"))
                    .get("edit", {}).items() if k not in ("fade_in", "fade_out", "transition")}  # fades would blacken a still
            edl = {**edit, "output": f"s{i}.mp4", "size": list(size), "fps": 30,
                   "clips": [{"src": str(clip), "in": at, "out": at + 0.6}],
                   "captions": [{"text": st["name"], "start": 0, "end": 0.6}]}
            p = Path(tmp) / f"s{i}.json"
            p.write_text(json.dumps(edl), encoding="utf-8")
            r = render.render(p, preview=True)
            frames.append(out_dir / f"_g{i}.png")
            frame_at(r["output"], 0.3, frames[-1])
            labels.append(str(i + 1))
        return {"gallery": tile(frames, labels, out_dir / "gallery.png"), "styles": styles, "frame_at_s": at}


def storyboard(edl_path, out_dir):
    edl_path, out_dir = Path(edl_path).resolve(), Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    edl = render.load(edl_path)
    preview = render.render(edl_path, preview=True)["output"]
    raw = json.loads(edl_path.read_text(encoding="utf-8"))
    panels, frames, labels = [], [], []
    for i, (c, (start, end)) in enumerate(zip(edl["clips"], render.timeline(edl))):
        mid = (start + end) / 2
        caps = [x["text"] for x in raw.get("captions") or [] if float(x["start"]) <= mid < float(x["end"])]
        speed = "" if c["speed"] == 1 else f" · {'slow' if c['speed'] < 1 else 'fast'} {c['speed']}x"
        speed += "" if not i or c["tin"]["type"] == "cut" else f" · {c['tin']['type']}"
        panels.append({"panel": i + 1, "out_start_s": round(start, 2), "out_end_s": round(end, 2), "src": c["src"],
                       "in": c["start"], "speed": c["speed"], "zoom": c["zoom"],
                       "transition_in": c["tin"]["type"], "captions": caps})
        labels.append(f"{i + 1} · {start:.1f}-{end:.1f}s{speed}")
        frames.append(out_dir / f"_s{i}.png")
        frame_at(preview, mid, frames[-1])
    Path(preview).unlink(missing_ok=True)
    (out_dir / "storyboard.json").write_text(json.dumps(panels, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"storyboard": tile(frames, labels, out_dir / "storyboard.png"), "panels": panels}


def duration(video):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(video)], capture_output=True, text=True).stdout)


def list_transitions():
    return [{"number": i + 1, "id": k, "group": g, "what": what, "seconds": d}
            for i, (k, (_, d, _, g, what)) in enumerate(render.TRANSITIONS.items())]


def transitions(clip_a, out_dir, clip_b=None, size=(540, 960), seg=1.3):
    """A reel of the customer's own clips with every transition, named on screen, plus a board of mid-transition frames."""
    clip_a, out_dir = Path(clip_a).resolve(), Path(out_dir).resolve()
    clip_b = Path(clip_b).resolve() if clip_b else clip_a
    out_dir.mkdir(parents=True, exist_ok=True)
    da, db = duration(clip_a), duration(clip_b)
    if min(da, db) < seg + 0.5:
        raise RuntimeError(f"clips must be at least {seg + 0.5:.1f} s long")
    cat = list_transitions()[1:]  # every type except the plain cut
    clips = []
    for k in range(len(cat) + 1):  # alternate A and B, walking through each clip so shots differ
        src, dur = (clip_a, da) if k % 2 == 0 else (clip_b, db)
        t = (k * 1.7) % (dur - seg - 0.2)
        clips.append({"src": str(src), "in": round(t, 2), "out": round(t + seg, 2),
                      **({"transition": {"type": cat[k - 1]["id"]}} if k else {})})
    edl = {"output": "transitions_reel.mp4", "size": list(size), "fps": 30, "clips": clips, "loudness_lufs": -14,
           "caption_style": {"position": "bottom", "size": size[0] // 13, "outline": 5, "uppercase": True}}
    p = out_dir / "transitions_reel.json"
    p.write_text(json.dumps(edl), encoding="utf-8")
    spans = render.timeline(render.load(p))
    # each name shows from its transition until the next one starts, so two names never overlap
    edl["captions"] = [{"text": f"{c['number']} {c['id'].replace('_', ' ')}", "start": round(spans[i + 1][0], 2),
                        "end": round(spans[i + 2][0] if i + 2 < len(spans) else spans[-1][1], 2)}
                       for i, c in enumerate(cat)]
    p.write_text(json.dumps(edl), encoding="utf-8")
    reel = render.render(p)["output"]
    loaded = render.load(p)
    frames, labels = [], []
    for i, c in enumerate(cat):
        start = render.timeline(loaded)[i + 1][0]
        frames.append(out_dir / f"_t{i}.png")
        frame_at(reel, start + loaded["clips"][i + 1]["tin"]["duration"] / 2, frames[-1])  # the middle of the effect
        labels.append(f"{c['number']} {c['id']}")
    p.unlink()
    return {"reel": reel, "board": tile(frames, labels, out_dir / "transitions.png"), "transitions": cat}


def font_board(text, out_dir, clip=None, families=None, size=(540, 960), limit=9):
    """The customer's own words in each candidate font (Vietnamese-safe by default), over their footage."""
    import fonts
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if families:
        faces = [fonts.resolve(f) for f in families]
        bad = [f for f, face in zip(families, faces) if not face]
        if bad:
            raise RuntimeError(f"not installed: {', '.join(bad)}")
    else:  # installed fonts that have every letter of the text, heaviest weights first (they read best on video)
        weight = ("black", "heavy", "extrabold", "bold", "semibold", "medium", "light", "thin")
        skip = ("math", "symbol", "mono", "code", "consolas", "courier", "emoji", "wingding", "webding", "marlett",
                "mdl2", "assets", "holo")
        faces = sorted((f for f in fonts.installed().values()
                        if not fonts.missing(f, text) and not any(s in f["family"].lower() for s in skip)),
                       key=lambda f: next((i if i < 6 else i + 1 for i, w in enumerate(weight)  # regular sits at 6
                                           if w in f["family"].lower()), 6))[:limit]
    bg = ({"src": str(Path(clip).resolve()), "in": duration(clip) * 0.4, "out": duration(clip) * 0.4 + 0.3}
          if clip else {"src": "color:0x1A1A1A", "duration": 0.3})
    frames, labels, out = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        for i, face in enumerate(faces):
            miss = fonts.missing(face, text)
            edl = {"output": f"f{i}.mp4", "size": list(size), "fps": 30, "clips": [bg],
                   "captions": [{"text": text, "start": 0, "end": 0.3}],
                   "caption_style": {"font_file": face["path"], "position": "center", "size": size[0] // 9,
                                     "outline": 6, "shadow": 2}}
            p = Path(tmp) / f"f{i}.json"
            p.write_text(json.dumps(edl), encoding="utf-8")
            if miss:  # the customer named a font that can't write their text: show why instead of a broken sample
                out.append({"number": i + 1, "family": face["family"], "missing": miss})
                continue
            frames.append(out_dir / f"_f{i}.png")
            frame_at(render.render(p)["output"], 0.1, frames[-1])
            labels.append(f"{i + 1} {face['family']}")
            out.append({"number": i + 1, "family": face["family"], "file": face["path"]})
        board = tile(frames, labels, out_dir / "fonts.png") if frames else None
    return {"board": board, "fonts": out}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which cannot print Vietnamese
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("styles")
    g = sub.add_parser("gallery")
    g.add_argument("clip")
    g.add_argument("--at", type=float, help="time in the clip to show (default 40%% in)")
    g.add_argument("--out", required=True)
    g.add_argument("--size", default="1080x1920", help="output frame, e.g. 1080x1920 or 1920x1080")
    s = sub.add_parser("storyboard")
    s.add_argument("edl")
    s.add_argument("--out", required=True)
    t = sub.add_parser("transitions")
    t.add_argument("--clip", help="customer clip; without it, just list the transitions")
    t.add_argument("--clip2", help="second clip to cut to (default: the same clip, other moments)")
    t.add_argument("--out")
    f = sub.add_parser("fonts")
    f.add_argument("--text", required=True, help="the customer's own title or caption")
    f.add_argument("--clip", help="footage to show behind the text")
    f.add_argument("--fonts", help="comma-separated families to compare (default: best Vietnamese-safe ones)")
    f.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        if a.cmd == "styles":
            r = list_styles()
        elif a.cmd == "gallery":
            r = gallery(a.clip, a.out, a.at, tuple(int(x) for x in a.size.split("x")))
        elif a.cmd == "transitions":
            r = transitions(a.clip, a.out or ".", a.clip2) if a.clip else list_transitions()
        elif a.cmd == "fonts":
            r = font_board(a.text, a.out, a.clip, a.fonts.split(",") if a.fonts else None)
        else:
            r = storyboard(a.edl, a.out)
    except (render.EDLError, RuntimeError) as e:
        sys.exit(str(e))
    print(json.dumps(r, indent=2, ensure_ascii=False))
