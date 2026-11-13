"""Builds a 6 s clip with known cuts at 2 s and 4 s, then checks analyze.py measures them."""
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze  # noqa: E402
import doctor  # noqa: E402


def make_clip(path):
    colors = ["red", "blue", "green"]
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for c in colors:
        cmd += ["-f", "lavfi", "-i", f"color={c}:s=320x240:d=2:r=25"]
    cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=6",
            "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0[v]", "-map", "[v]", "-map", "3",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)]
    subprocess.run(cmd, check=True)


def test_doctor_finds_ffmpeg():
    r = doctor.check()
    assert r["ok"], r["fix"]


def test_analyze_measures_known_clip(tmp_path):
    clip = tmp_path / "clip.mp4"
    make_clip(clip)
    before = hashlib.sha256(clip.read_bytes()).hexdigest()

    s = analyze.analyze(clip, tmp_path / "out")

    assert abs(s["format"]["duration_s"] - 6) < 0.2
    assert s["format"]["aspect"] == "1:1" or s["format"]["width"] == 320
    p = s["pacing"]
    assert p["shot_count"] == 3, p
    assert [round(c) for c in p["cuts_s"]] == [2, 4], p["cuts_s"]
    assert abs(p["avg_shot_s"] - 2) < 0.2
    assert s["color"]["saturation_0_255"] > 50  # pure colours are highly saturated
    assert s["audio"]["integrated_lufs"] is not None
    assert (tmp_path / "out" / "contact.png").stat().st_size > 0
    assert (tmp_path / "out" / "style.json").is_file()
    assert hashlib.sha256(clip.read_bytes()).hexdigest() == before  # input untouched


def test_animated_slide_transition_detected(tmp_path):
    # 60 fps slide between two similar frames: per-frame change is small, the 5 fps pass must catch it
    clip = tmp_path / "slide.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "testsrc2=s=320x568:d=3:r=60",
                    "-f", "lavfi", "-i", "color=c=0x0B3B2C:s=320x568:d=3:r=60",
                    "-filter_complex", "[0][1]xfade=transition=slideleft:duration=0.6:offset=1.5,format=yuv420p",
                    "-c:v", "libx264", str(clip)], check=True)
    cuts, kinds = analyze.scene_cuts(clip, 0.3)
    assert len(cuts) == 1 and 1.4 <= cuts[0] <= 2.2, cuts


def test_music_file_without_video(tmp_path):
    # an MP3 has no picture: analyze.py must still give its length and loudness instead of stopping
    song = tmp_path / "song.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=4",
                    str(song)], check=True)
    s = analyze.analyze(song, tmp_path / "out")
    assert s["format"]["has_audio"] and s["format"]["width"] is None
    assert abs(s["format"]["duration_s"] - 4) < 0.1
    assert s["audio"]["integrated_lufs"] is not None
    assert s["pacing"] is None and s["contact_sheet"] is None
    assert (tmp_path / "out" / "style.json").is_file()
