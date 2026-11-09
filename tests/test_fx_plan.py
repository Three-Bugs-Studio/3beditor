"""fx_plan: effects only where the footage or music gives a reason, within a budget."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fx_plan  # noqa: E402


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("fx")
    enc = ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    ff("-f", "lavfi", "-i", "testsrc2=s=320x240:d=6:r=25", *enc, str(d / "same.mp4"))  # one camera angle
    ff("-f", "lavfi", "-i", "color=c=0x202020:s=320x240:d=6:r=25", *enc, str(d / "dark.mp4"))  # another scene
    for name, src in (("pan1", "testsrc2=s=1600x240:d=4:r=25"), ("pan2", "smptehdbars=s=1600x240:d=4:r=25")):
        # the camera pans right, so the picture moves left
        ff("-f", "lavfi", "-i", src, "-vf", "crop=320:240:'t*250':0", *enc, str(d / f"{name}.mp4"))
    # quiet for 3 s, then loud: a drop at 3 s
    ff("-f", "lavfi", "-i", "sine=f=220:d=3", "-f", "lavfi", "-i", "sine=f=220:d=3", "-filter_complex",
       "[0]volume=0.05[a];[1]volume=0.9[b];[a][b]concat=n=2:v=0:a=1", str(d / "drop.wav"))
    return d


def edl(d, clips, **extra):
    p = d / f"e{abs(hash(json.dumps(clips)))}.json"
    p.write_text(json.dumps({"output": "o.mp4", "size": [180, 320], "clips": clips, **extra}), encoding="utf-8")
    return p


def test_same_angle_cuts_stay_hard_cuts(clips):
    r = fx_plan.plan(edl(clips, [{"src": "same.mp4", "in": 0, "out": 1.5}, {"src": "same.mp4", "in": 2, "out": 3.5},
                                 {"src": "same.mp4", "in": 4, "out": 5.5}]), "tiktok-fast")
    assert [k["suggest"] for k in r["cuts"]] == ["cut", "cut"] and r["effects"] == 0
    assert all(k["same_angle"] for k in r["cuts"])


def test_new_scene_gets_a_soft_transition_only_in_cinematic_styles(clips):
    e = edl(clips, [{"src": "same.mp4", "in": 0, "out": 2}, {"src": "dark.mp4", "in": 0, "out": 2}])
    assert fx_plan.plan(e, "cinematic")["cuts"][0]["suggest"] == "dip_black"
    assert fx_plan.plan(e, "podcast-clip")["cuts"][0]["suggest"] == "cut"  # its style has no soft transitions


def test_one_hit_on_the_drop(clips):
    cl = [{"src": "same.mp4", "in": 0, "out": 1.5, "mute": True}, {"src": "dark.mp4", "in": 0, "out": 1.5, "mute": True},
          {"src": "same.mp4", "in": 3, "out": 4.5, "mute": True}, {"src": "dark.mp4", "in": 2, "out": 3.5, "mute": True}]
    r = fx_plan.plan(edl(clips, cl, music={"src": "drop.wav", "volume": 1}), "tiktok-fast")
    hits = [k for k in r["cuts"] if k["suggest"] in fx_plan.HITS]
    assert len(hits) == 1 and hits[0]["time_s"] == 3.0


def test_whip_follows_real_motion(clips):
    r = fx_plan.plan(edl(clips, [{"src": "pan1.mp4", "in": 0.5, "out": 2}, {"src": "pan2.mp4", "in": 0.5, "out": 2}]),
                     "tiktok-fast")
    k = r["cuts"][0]
    assert (k["motion_out"], k["motion_in"], k["suggest"]) == ("left", "left", "whip_left")


def test_budget_keeps_it_clean(clips):
    cl = [{"src": "same.mp4" if i % 2 else "dark.mp4", "in": 0, "out": 1.2} for i in range(9)]  # 8 scene changes
    r = fx_plan.plan(edl(clips, cl), "cinematic")
    assert r["effects"] == r["budget"] == 2  # cinematic: one effect per 3 cuts at most
    assert sum(k["suggest"] != "cut" for k in r["cuts"]) == 2


def test_apply_keeps_transition_middle_on_the_cut(clips, tmp_path):
    e = edl(clips, [{"src": "same.mp4", "in": 0, "out": 2}, {"src": "dark.mp4", "in": 1, "out": 3}])
    r = fx_plan.plan(e, "cinematic")
    fx_plan.apply(e, r, tmp_path / "out.json")
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert out["clips"][1]["transition"] == {"type": "dip_black"}
    assert out["clips"][0]["out"] == 2.3 and out["clips"][1]["in"] == 0.7  # dip_black is 0.6 s: 0.3 s each side
