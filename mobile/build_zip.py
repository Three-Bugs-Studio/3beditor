"""Package 3beditor as one self-contained skill ZIP for the Claude app (web, desktop and phone).

usage: python mobile/build_zip.py   ->  dist/3beditor-skill.zip
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "3beditor-skill.zip"
FILES = {  # zip path: source
    "3beditor/SKILL.md": ROOT / "mobile" / "SKILL.md",
    "3beditor/references/edit.md": ROOT / "skills" / "video-edit" / "SKILL.md",
    "3beditor/references/craft.md": ROOT / "skills" / "video-edit" / "craft.md",
    "3beditor/references/style.md": ROOT / "skills" / "video-style" / "SKILL.md",
    "3beditor/references/plan.md": ROOT / "skills" / "video-plan" / "SKILL.md",
}
FILES.update({f"3beditor/scripts/{p.name}": p for p in (ROOT / "scripts").glob("*.py")})
FILES.update({f"3beditor/styles/{p.name}": p for p in (ROOT / "styles").glob("*.json")})
FILES.update({f"3beditor/sfx/{p.name}": p for p in (ROOT / "sfx").iterdir()})


def build():
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in sorted(FILES.items()):
            if src.suffix == ".wav":
                z.write(src, arc)
                continue
            text = src.read_text(encoding="utf-8")
            if arc.startswith("3beditor/references/"):  # desktop skills point at ../../scripts; here it's scripts/
                text = text.replace("../../scripts/", "scripts/").replace("../../styles/", "styles/")
            z.writestr(arc, text)
    return OUT


if __name__ == "__main__":
    out = build()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert "3beditor/SKILL.md" in names and "3beditor/scripts/render.py" in names
    print(f"{out} ({out.stat().st_size // 1024} KB, {len(names)} files)")
