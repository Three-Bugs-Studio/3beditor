"""render.py end to end on synthetic media, plus EDL validation and the style-compare loop."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze  # noqa: E402
import render  # noqa: E402


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture
def media(tmp_path):
    # 16:9 clip with a tone, 16:9 clip with no audio, an image, a music bed
    ff("-f", "lavfi", "-i", "testsrc2=s=640x360:d=5:r=25", "-f", "lavfi", "-i", "sine=f=440:d=5",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(tmp_path / "a.mp4"))
    ff("-f", "lavfi", "-i", "testsrc=s=640x360:d=5:r=25", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       str(tmp_path / "b.mp4"))
    ff("-f", "lavfi", "-i", "color=c=orange:s=400x400", "-frames:v", "1", str(tmp_path / "card.png"))
    ff("-f", "lavfi", "-i", "sine=f=220:d=3", str(tmp_path / "music.wav"))
    return tmp_path


def write_edl(d, **over):
    edl = {
        "output": "out.mp4", "size": [360, 640], "fps": 25,
        "clips": [{"src": "a.mp4", "in": 1, "out": 3, "zoom": 1.2},
                  {"src": "b.mp4", "in": 0, "out": 1.5},
                  {"src": "card.png", "duration": 1},
                  {"src": "color:black", "duration": 0.5}],
        "color": {"saturation": 1.3, "warmth": 0.5},
        "captions": [{"text": "hello world", "start": 0.2, "end": 1.8}],
        "caption_style": {"position": "center", "uppercase": True, "box": True, "size": 40},
        "music": {"src": "music.wav", "volume": 0.4},
        "loudness_lufs": -14,
        **over,
    }
    p = d / "edl.json"
    p.write_text(json.dumps(edl), encoding="utf-8")
    return p


def probe(p):
    return json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(p)],
                                     capture_output=True, text=True, check=True).stdout)


def test_cut_render(media):
    r = render.render(write_edl(media))
    info = probe(r["output"])
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (v["width"], v["height"]) == (360, 640)
    assert any(s["codec_type"] == "audio" for s in info["streams"])  # music looped under silent clips
    assert abs(float(info["format"]["duration"]) - 5.0) < 0.15  # 2 + 1.5 + 1 + 0.5
    s = analyze.analyze(r["output"], media / "check")
    assert s["pacing"]["shot_count"] >= 3
    assert abs(s["audio"]["integrated_lufs"] + 14) < 2


def test_fade_shortens_timeline(media):
    r = render.render(write_edl(media, transition={"type": "fade", "duration": 0.25}))
    assert abs(r["duration_s"] - (5.0 - 3 * 0.25)) < 3 / 25  # snapped to whole frames: within a frame per transition
    assert abs(float(probe(r["output"])["format"]["duration"]) - r["duration_s"]) < 0.15


def test_preview_is_small(media):
    r = render.render(write_edl(media), preview=True)
    v = next(s for s in probe(r["output"])["streams"] if s["codec_type"] == "video")
    assert r["output"].endswith("out_preview.mp4") and v["width"] == 120


@pytest.mark.parametrize("bad, msg", [
    ({"clips": []}, "clips"),
    ({"clips": [{"src": "nope.mp4", "in": 0, "out": 1}]}, "not found"),
    ({"clips": [{"src": "a.mp4", "in": 2, "out": 1}]}, "greater"),
    ({"clips": [{"src": "card.png"}]}, "duration"),
    ({"output": "a.mp4"}, "overwrite"),
    ({"transition": {"type": "wipe"}}, "transition"),
    ({"transition": {"type": "fade", "duration": 0.6}}, "shorter"),
    ({"caption_style": {"color": "white"}}, "RRGGBB"),
])
def test_bad_edl_rejected(media, bad, msg):
    with pytest.raises(render.EDLError, match=msg):
        render.load(write_edl(media, **bad))


def test_compare_flags_mismatch():
    actual = {"format": {"aspect": "9:16"}, "pacing": {"avg_shot_s": 3.0, "cuts_per_min": 20},
              "color": {"warmth": 0}, "audio": {"integrated_lufs": -14.5}}
    target = {"format": {"aspect": "9:16"}, "pacing": {"avg_shot_s": 1.5, "cuts_per_min": 21},
              "audio": {"integrated_lufs": -14}}
    m = analyze.compare(actual, target)
    by = {c["metric"]: c["ok"] for c in m["checks"]}
    assert by == {"format.aspect": True, "pacing.avg_shot_s": False, "pacing.cuts_per_min": True,
                  "audio.integrated_lufs": True}  # warmth skipped: target has no colour
    assert m["ok"] is False


def test_cuts_from_edl_and_caption_override(media, tmp_path):
    edl = write_edl(media, transition={"type": "fade", "duration": 0.25},
                    captions=[{"text": "end", "start": 4, "end": 4.2, "position": "center"}])
    cuts, kinds = analyze.edl_cuts(edl)
    # clips 2, 1.5, 1, 0.5 s with 0.25 s fades: fade midpoints
    assert all(abs(a - b) <= 0.04 for a, b in zip(cuts, [1.875, 3.125, 3.875]))  # whole frames at 25 fps
    assert kinds == {"hard": 0, "animated": 3}
    loaded = render.load(edl)
    render.write_ass(loaded, tmp_path / "c.ass")
    assert r"{\an5}END" in (tmp_path / "c.ass").read_text(encoding="utf-8-sig")


def test_contain_letterboxes(media):
    r = render.render(write_edl(media, fit="contain", captions=[], clips=[{"src": "a.mp4", "in": 0, "out": 1}]))
    s = analyze.analyze(r["output"], media / "lb")
    assert s["color"]["brightness_0_255"] < 60  # 16:9 strip inside 9:16: mostly black bars
    with pytest.raises(render.EDLError, match="fit"):
        render.load(write_edl(media, fit="stretch"))


def test_watch_js_parses():
    import shutil
    if not shutil.which("node"):
        pytest.skip("node not installed")
    subprocess.run(["node", "--check", str(Path(render.__file__).with_name("watch.js"))], check=True)


def test_slow_motion_fades_and_film_look(media):
    edl = write_edl(media, captions=[], fade_in=0.5, fade_out=0.5,
                    color={"teal_orange": 0.6, "crush": 0.5, "vignette": True, "grain": 0.3},
                    clips=[{"src": "a.mp4", "in": 0, "out": 1, "speed": 0.5},
                           {"src": "b.mp4", "in": 0, "out": 2, "speed": 2}])
    r = render.render(edl)
    assert abs(r["duration_s"] - 3.0) < 0.01  # 1 s at half speed + 2 s at double speed
    assert abs(float(probe(r["output"])["format"]["duration"]) - 3.0) < 0.15
    first = subprocess.run(["ffmpeg", "-v", "error", "-i", r["output"], "-vf", "signalstats,metadata=print:file=-",
                            "-frames:v", "1", "-f", "null", "-"], capture_output=True, text=True).stdout
    assert float(first.split("YAVG=")[1].split()[0]) < 30  # starts from black
    with pytest.raises(render.EDLError, match="speed"):
        render.load(write_edl(media, clips=[{"src": "a.mp4", "in": 0, "out": 1, "speed": 10}]))


def test_sfx_mixed_and_captions_in_safe_area(media):
    # silent clip + one boom at 1.0 s: the render must be silent before the hit and loud after it
    p = write_edl(media, clips=[{"src": "b.mp4", "in": 0, "out": 3}], music=None, loudness_lufs=None,
                  captions=[{"text": "PR", "start": 0, "end": 2}], caption_style={"position": "bottom"},
                  sfx=[{"src": "boom", "at": 1.0, "volume_db": -6}])
    out = render.render(p)["output"]
    def peak(ss, t):
        err = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(ss), "-t", str(t), "-i", out, "-af", "volumedetect",
                              "-f", "null", "-"], capture_output=True, text=True).stderr
        return float(err.split("max_volume:")[1].split("dB")[0])
    assert peak(0, 0.8) < -60 and peak(1.0, 1.0) > -20
    edl = render.load(p)
    ass = media / "c.ass"
    render.write_ass(edl, ass)
    line = next(x for x in ass.read_text(encoding="utf-8-sig").splitlines() if x.startswith("Dialogue"))
    assert line.split(",")[7] == str(int(640 * 0.25))  # bottom captions sit above TikTok's caption text
    with pytest.raises(render.EDLError, match="built-in sound"):
        render.load(write_edl(media, sfx=[{"src": "nope", "at": 1}]))


def test_true_peak_is_a_delivery_check():
    hot = {"audio": {"true_peak_dbtp": -0.2}}
    assert not analyze.compare(hot, {})["ok"]
    assert analyze.compare({"audio": {"true_peak_dbtp": -1.6}}, {})["ok"]


def test_loudness_second_pass_hits_target(tmp_path):
    # a clip far louder than the target: the correction brings it within 0.5 LU and keeps the peak under -1
    clip = tmp_path / "loud.mp4"
    ff("-f", "lavfi", "-i", "color=c=gray:s=160x90:d=4:r=25", "-f", "lavfi", "-i", "aevalsrc=0.9*sin(2*PI*1000*t):d=4",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(clip))
    before, _ = render.measure_loudness(clip)
    assert before > -10
    gain = render.fix_loudness(clip, -14)
    after, peak = render.measure_loudness(clip)
    assert gain < 0 and abs(after - -14) <= 0.5 and peak <= -1
    assert render.fix_loudness(clip, -14) == 0.0  # already on target: file left alone
