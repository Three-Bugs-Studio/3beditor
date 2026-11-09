"""Beat detection. Skipped when librosa is not installed."""
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("librosa")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze  # noqa: E402


def test_cuts_on_120bpm_clicks(tmp_path):
    clip = tmp_path / "beat.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for c in ("red", "blue", "green", "white"):
        cmd += ["-f", "lavfi", "-i", f"color={c}:s=320x240:d=2:r=25"]
    cmd += ["-f", "lavfi", "-i", r"aevalsrc=sin(2*PI*1000*t)*lt(mod(t\,0.5)\,0.04):d=8",
            "-filter_complex", "[0][1][2][3]concat=n=4:v=1:a=0[v]", "-map", "[v]", "-map", "4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(clip)]
    subprocess.run(cmd, check=True)
    m = analyze.analyze(clip, tmp_path / "out")["music"]
    assert 110 < m["bpm"] < 130, m["bpm"]
    assert m["cut_on_beat_ratio"] == 1.0
