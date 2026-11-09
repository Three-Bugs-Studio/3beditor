"""Fonts for captions: which fonts are installed, and does a font have every character the captions need.

usage:
  python fonts.py list [--vietnamese]        installed font families (only those with full Vietnamese support)
  python fonts.py check FONT "caption text"  FONT is a family name or a .ttf/.otf/.ttc file; lists missing characters

Most popular display fonts are English-only: Vietnamese letters (ạ ế ữ ...) are missing, and video apps then
silently swap in another font, so the text looks broken. Use a "Việt hóa" version of the font instead.
"""
import argparse
import functools
import json
import os
import platform
import struct
import sys
from pathlib import Path

VIETNAMESE = set("ăâđêôơưĂÂĐÊÔƠƯàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ"
                 "ÀÁẢÃẠẰẮẲẴẶẦẤẨẪẬÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ")
FONT_EXT = {".ttf", ".otf", ".ttc"}


def font_dirs():
    home = Path.home()
    if platform.system() == "Windows":
        return [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
                Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")) / "Microsoft/Windows/Fonts"]
    if platform.system() == "Darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"), home / "Library/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), home / ".fonts", home / ".local/share/fonts"]


def _tables(data, off):
    n = struct.unpack_from(">H", data, off + 4)[0]
    return {data[off + 12 + 16 * i: off + 16 + 16 * i].decode("latin-1"):
            struct.unpack_from(">II", data, off + 20 + 16 * i) for i in range(n)}  # tag -> (offset, length)


def _names(data, off):
    count, strings = struct.unpack_from(">HH", data, off + 2)
    best = {}
    for i in range(count):
        pid, eid, lang, nid, ln, so = struct.unpack_from(">HHHHHH", data, off + 6 + 12 * i)
        if nid not in (1, 4) or (pid, eid) not in ((3, 1), (3, 0), (0, 3), (0, 4), (1, 0)):
            continue
        raw = data[off + strings + so: off + strings + so + ln]
        text = raw.decode("utf-16-be" if pid in (0, 3) else "latin-1", "replace")
        rank = (pid == 3 and lang == 0x409) * 2 + (pid == 3)  # prefer Windows English names
        if nid not in best or rank > best[nid][0]:
            best[nid] = (rank, text)
    return best.get(1, (0, ""))[1], best.get(4, (0, ""))[1]


def _cmap(data, off):
    count = struct.unpack_from(">H", data, off + 2)[0]
    subs = {}
    for i in range(count):
        pid, eid, so = struct.unpack_from(">HHI", data, off + 4 + 8 * i)
        subs[(pid, eid)] = off + so
    for key in ((3, 10), (0, 4), (0, 6), (3, 1), (0, 3), (0, 1), (0, 0)):
        if key not in subs:
            continue
        s, fmt = subs[key], struct.unpack_from(">H", data, subs[key])[0]
        chars = set()
        if fmt == 4:
            seg2 = struct.unpack_from(">H", data, s + 6)[0]
            ends, starts = s + 14, s + 16 + seg2
            for k in range(seg2 // 2):
                a, b = struct.unpack_from(">H", data, starts + 2 * k)[0], struct.unpack_from(">H", data, ends + 2 * k)[0]
                chars.update(range(a, b + 1))  # shortcut: ignores glyph-id 0 mappings inside a range, fine for coverage
            return chars
        if fmt == 12:
            n = struct.unpack_from(">I", data, s + 12)[0]
            for k in range(n):
                a, b, _ = struct.unpack_from(">III", data, s + 16 + 12 * k)
                chars.update(range(a, b + 1))
            return chars
    return set()


def read_font(path):
    """[{family, full_name, chars}] for a .ttf/.otf, or one entry per face in a .ttc collection."""
    data = Path(path).read_bytes()
    offsets = [0]
    if data[:4] == b"ttcf":
        n = struct.unpack_from(">I", data, 8)[0]
        offsets = list(struct.unpack_from(f">{n}I", data, 12))
    faces = []
    for off in offsets:
        t = _tables(data, off)
        if "name" not in t or "cmap" not in t:
            continue
        family, full = _names(data, t["name"][0])
        faces.append({"family": family, "full_name": full, "chars": _cmap(data, t["cmap"][0]), "path": str(path)})
    return faces


@functools.lru_cache(maxsize=1)  # one font scan per run: gallery and storyboard render many times
def installed():
    seen = {}
    for d in font_dirs():
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.suffix.lower() in FONT_EXT:
                try:
                    for f in read_font(p):
                        seen.setdefault(f["family"].lower(), f)
                except (OSError, struct.error, UnicodeDecodeError):
                    continue  # unreadable or exotic font file: skip it
    return seen


def resolve(font):
    """A font file path, or the installed face whose family (or full name) matches. None if not found."""
    p = Path(font)
    if p.suffix.lower() in FONT_EXT and p.is_file():
        faces = read_font(p)
        return faces[0] if faces else None
    want = font.lower()
    fonts = installed()
    return fonts.get(want) or next((f for f in fonts.values() if f["full_name"].lower() == want), None)


def missing(face, text):
    return sorted({ch for ch in text if not ch.isspace() and ord(ch) not in face["chars"]})


def vietnamese_ok(face):
    return not missing(face, "".join(VIETNAMESE))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which cannot print Vietnamese
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--vietnamese", action="store_true")
    ck = sub.add_parser("check")
    ck.add_argument("font")
    ck.add_argument("text")
    a = ap.parse_args()
    if a.cmd == "list":
        fams = sorted(f["family"] for f in installed().values() if not a.vietnamese or vietnamese_ok(f))
        print(json.dumps(fams, ensure_ascii=False, indent=1))
    else:
        face = resolve(a.font)
        if not face:
            sys.exit(f"font not found: {a.font}")
        miss = missing(face, a.text)
        print(json.dumps({"font": face["family"], "file": face["path"], "missing": miss,
                          "vietnamese": vietnamese_ok(face)}, ensure_ascii=False, indent=1))
        sys.exit(1 if miss else 0)
