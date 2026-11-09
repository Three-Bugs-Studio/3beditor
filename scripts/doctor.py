"""Check what 3beditor needs on this machine. Prints JSON; exit 1 if a required tool is missing."""
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys

INSTALL = {
    "ffmpeg": {"Windows": "winget install Gyan.FFmpeg", "Darwin": "brew install ffmpeg", "Linux": "sudo apt install ffmpeg"},
    "librosa": "pip install librosa",
    "faster_whisper": "pip install faster-whisper",
}


def tool_version(name):
    path = shutil.which(name)
    if not path:
        return None
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"  # present but would not run: say unknown, not missing
    m = re.search(r"version (\S+)", out)
    return m.group(1) if m else "unknown"


def check():
    os_name = platform.system()
    py_ok = sys.version_info >= (3, 10)
    report = {"os": os_name, "python": platform.python_version(), "required": {}, "optional": {}, "fix": []}
    report["required"]["python>=3.10"] = py_ok
    if not py_ok:
        report["fix"].append("Install Python 3.10 or newer from python.org")
    for tool in ("ffmpeg", "ffprobe"):
        v = tool_version(tool)
        report["required"][tool] = v or False
        if not v:
            report["fix"].append(INSTALL["ffmpeg"].get(os_name, "Install FFmpeg from ffmpeg.org"))
    m = re.match(r"n?(\d+)\.", str(report["required"]["ffmpeg"]))
    if m and int(m.group(1)) < 7:  # tested on 7.1 and 9.0; older builds lack some transitions. Git builds ("N-...") pass
        report["required"]["ffmpeg>=7"] = False
        report["fix"].append(f"Update FFmpeg to version 7 or newer ({INSTALL['ffmpeg'].get(os_name, 'ffmpeg.org')})")
    for mod, use in (("librosa", "music beat detection"), ("faster_whisper", "speech transcript")):
        found = importlib.util.find_spec(mod) is not None
        report["optional"][mod] = {"installed": found, "used_for": use}
        if not found:
            report["fix"].append(f"(optional, {use}) {INSTALL[mod]}")
    report["fix"] = list(dict.fromkeys(report["fix"]))
    report["ok"] = py_ok and all(report["required"].values())
    return report


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which cannot print Vietnamese
    r = check()
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["ok"] else 1)
