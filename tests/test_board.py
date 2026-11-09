"""Style gallery and storyboard: the boards a customer approves before the full render."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import board  # noqa: E402
from test_render import media, write_edl  # noqa: E402,F401  (pytest fixture)


def size(png):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(png)], capture_output=True, text=True).stdout
    return tuple(map(int, out.strip().split(",")))


def test_every_preset_has_gallery_fields():
    styles = board.list_styles()
    assert len(styles) >= 6
    for s in styles:
        spec = json.loads((board.STYLES / f"{s['id']}.json").read_text(encoding="utf-8"))
        assert s["name"] and s["description"] and s["best_for"], s["id"]
        assert "color" in spec["edit"] and "caption_style" in spec["edit"], s["id"]


def test_gallery_one_panel_per_style(media, tmp_path):
    r = board.gallery(media / "a.mp4", tmp_path / "g", at=1.0, size=(360, 640))
    w, h = size(r["gallery"])
    rows = -(-len(r["styles"]) // board.COLS)
    assert (w, h) == (board.COLS * 120 + (board.COLS - 1) * 6, rows * 212 + (rows - 1) * 6)  # preview = 1/3 size panels
    assert not list((tmp_path / "g").glob("_*"))  # temp panels cleaned up


def test_storyboard_panels_match_shots(media):
    edl = write_edl(media, transition={"type": "fade", "duration": 0.25},
                    captions=[{"text": "hello world", "start": 1.5, "end": 2.5}],
                    clips=[{"src": "a.mp4", "in": 0, "out": 2, "speed": 0.5},
                           {"src": "b.mp4", "in": 0, "out": 1.5},
                           {"src": "card.png", "duration": 1}])
    r = board.storyboard(edl, media / "sb")
    p = r["panels"]
    assert [x["panel"] for x in p] == [1, 2, 3]
    assert p[0]["out_end_s"] == 4.0 and abs(p[1]["out_start_s"] - 3.75) <= 0.04  # slow-mo doubles; fades overlap
    assert p[0]["captions"] == ["hello world"]
    assert Path(r["storyboard"]).is_file() and (media / "sb" / "storyboard.json").is_file()
    assert not list(media.glob("out_preview.mp4"))  # storyboard's preview render is removed


def test_transition_reel_names_every_transition(media, tmp_path):
    r = board.transitions(media / "a.mp4", tmp_path / "t", clip_b=media / "b.mp4", size=(180, 320), seg=1.0)
    assert len(r["transitions"]) == len(board.render.TRANSITIONS) - 1  # all but the plain cut
    assert Path(r["reel"]).is_file() and Path(r["board"]).is_file()
    assert [t["id"] for t in board.list_transitions()][0] == "cut"


def test_font_board_shows_only_fonts_that_can_write_the_text(tmp_path):
    r = board.font_board("Về đích", tmp_path / "f", size=(180, 320), limit=3)
    assert r["fonts"] and all("missing" not in f for f in r["fonts"])
    assert Path(r["board"]).is_file()
