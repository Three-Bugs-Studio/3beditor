"""Transition library: every type renders, per-cut choice, exact timing, and real-frame slow motion."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze  # noqa: E402
import render  # noqa: E402
from test_render import media, probe, write_edl  # noqa: E402,F401  (pytest fixture)


def video_frames(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v",
                          "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout
    return int(out.strip())


def test_every_transition_renders_and_keeps_planned_length(media):
    kinds = [k for k in render.TRANSITIONS if k != "cut"]
    clips = [{"src": "a.mp4" if i % 2 else "b.mp4", "in": 0, "out": 0.8} for i in range(len(kinds) + 1)]
    for c, kind in zip(clips[1:], kinds):
        c["transition"] = {"type": kind}
    r = render.render(write_edl(media, captions=[], size=[180, 320], clips=clips))
    planned = 0.8 * len(clips) - sum(render.TRANSITIONS[k][1] for k in kinds)
    assert abs(r["duration_s"] - planned) < 0.02 * len(kinds)  # each transition snaps to whole frames
    assert video_frames(r["output"]) == round(r["duration_s"] * 25)  # count real frames: audio alone can fake length


def test_mixed_cuts_stay_frame_exact(media):
    clips = [{"src": "a.mp4", "in": 0, "out": 1}, {"src": "b.mp4", "in": 0, "out": 1},
             {"src": "a.mp4", "in": 1, "out": 2, "transition": {"type": "flash"}}, {"src": "b.mp4", "in": 1, "out": 2}]
    edl = write_edl(media, captions=[], clips=clips)
    loaded = render.load(edl)
    assert [round(s, 2) for s, _ in render.timeline(loaded)] == [0, 1, 1.8, 2.8]  # the flash overlaps 0.2 s; cuts don't
    cuts, kinds = analyze.edl_cuts(edl)
    assert cuts == [1.0, 1.9, 2.8] and kinds == {"hard": 2, "animated": 1}
    r = render.render(edl)
    assert video_frames(r["output"]) == 95  # 3.8 s x 25 fps


def test_odd_lengths_at_24fps_keep_every_frame(media):
    # lengths that aren't whole frames used to drift and end the video early at a 1-frame cut overlap
    clips = [{"src": "a.mp4", "in": 0, "out": 1.472}, {"src": "b.mp4", "in": 0, "out": 1.497},
             {"src": "a.mp4", "in": 1.2, "out": 2.672, "transition": {"type": "whip_left"}},
             {"src": "b.mp4", "in": 1.1, "out": 2.597}, {"src": "a.mp4", "in": 2.0, "out": 3.447,
                                                         "transition": {"type": "zoom_punch"}}]
    edl = write_edl(media, captions=[], fps=24, clips=clips)
    total = render.timeline(render.load(edl))[-1][1]
    assert video_frames(render.render(edl)["output"]) == round(total * 24)


def test_per_clip_transition_overrides_default_and_bad_ones_fail(media):
    edl = write_edl(media, captions=[], transition={"type": "fade"},
                    clips=[{"src": "a.mp4", "in": 0, "out": 1}, {"src": "b.mp4", "in": 0, "out": 1},
                           {"src": "a.mp4", "in": 1, "out": 2, "transition": {"type": "whip_left", "duration": 0.2}}])
    tins = [c["tin"] for c in render.load(edl)["clips"]]
    assert tins[1] == {"type": "fade", "duration": 0.4} and tins[2] == {"type": "whip_left", "duration": 0.2}
    with pytest.raises(render.EDLError, match="unknown transition"):
        render.load(write_edl(media, clips=[{"src": "a.mp4", "in": 0, "out": 1},
                                            {"src": "b.mp4", "in": 0, "out": 1, "transition": {"type": "spin360"}}]))
    with pytest.raises(render.EDLError, match="fps"):
        render.load(write_edl(media, fps=500))


def test_slow_motion_uses_real_frames_from_60fps_footage(media):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=s=320x240:d=2:r=60", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(media / "hfr.mp4")], check=True)
    slow = [{"src": "hfr.mp4", "in": 0, "out": 1, "speed": 0.5}]
    cmd = " ".join(render.render(write_edl(media, captions=[], fps=30, clips=slow), dry_run=True)["command"])
    assert "minterpolate" not in cmd  # 60 fps x 0.5 = 30 real frames per second: nothing to invent
    cmd = " ".join(render.render(write_edl(media, captions=[], fps=30,
                                           clips=[{"src": "a.mp4", "in": 0, "out": 1, "speed": 0.5}]),
                                 dry_run=True)["command"])
    assert "minterpolate" in cmd  # 25 fps footage needs in-between frames
