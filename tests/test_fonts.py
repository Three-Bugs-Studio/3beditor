"""Fonts and caption effects: glyph checks (Vietnamese), font files, highlight, animation, word reveal."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fonts  # noqa: E402
import render  # noqa: E402
from test_render import media, probe, write_edl  # noqa: E402,F401  (pytest fixture)

ST = {"uppercase": False, "color": "#FFFFFF", "highlight_color": "#FFE600", "animation": "none", "reveal": "none",
      "blur": 0}


def default_face():
    face = render.pick_font({}, Path("."))
    assert face, "no default font installed"
    return face


def test_glyph_check_finds_missing_characters():
    face = default_face()
    assert fonts.missing(face, "Gym 🔥") == ["🔥"]  # text fonts have no emoji
    assert fonts.missing(face, "  \n") == []


def test_font_file_is_read_and_used(media):
    face = default_face()
    r = render.render(write_edl(media, caption_style={"font_file": face["path"], "outline": 8, "shadow": 3},
                                clips=[{"src": "a.mp4", "in": 0, "out": 1}]))
    assert Path(r["output"]).is_file()


def test_unknown_font_and_missing_glyphs_stop_the_render(media):
    with pytest.raises(render.EDLError, match="not installed"):
        render.load(write_edl(media, caption_style={"font": "No Such Font 123"}))
    with pytest.raises(render.EDLError, match="Việt hóa"):
        render.load(write_edl(media, captions=[{"text": "PR 🔥", "start": 0, "end": 1}]))
    with pytest.raises(render.EDLError, match="reveal"):
        render.load(write_edl(media, caption_style={"reveal": "typewriter"}))


def test_highlight_words_get_the_highlight_colour():
    [(_, _, text)] = render.caption_events({"text": "Em đẹp quá", "start": 0, "end": 1, "highlight": ["ĐẸP"]}, ST)
    assert text == r"Em {\c&H00E6FF&}đẹp{\c&HFFFFFF&} quá"


def test_word_reveal_keeps_layout_and_uses_word_times():
    ev = render.caption_events({"text": "Em đẹp quá", "start": 1, "end": 2.5,
                                "words": [{"start": 1}, {"start": 1.4}, {"start": 2}]}, {**ST, "reveal": "word"})
    assert [(a, b) for a, b, _ in ev] == [(1, 1.4), (1.4, 2), (2, 2.5)]
    assert ev[0][2] == r"Em {\alpha&HFF&}đẹp quá"  # later words hidden, not removed
    assert ev[2][2] == "Em đẹp quá"


def test_build_and_karaoke():
    c = {"text": "gọi cho\nanh", "start": 0, "end": 3}
    build = [t for _, _, t in render.caption_events(c, {**ST, "reveal": "build"})]
    assert build == ["gọi", "gọi cho", r"gọi cho\Nanh"]
    kara = [t for _, _, t in render.caption_events(c, {**ST, "reveal": "karaoke"})]
    assert kara[1] == r"gọi {\c&H00E6FF&}cho{\c&HFFFFFF&}\Nanh"


def test_pop_animation_on_newest_word():
    ev = render.caption_events({"text": "a b", "start": 0, "end": 1}, {**ST, "reveal": "build", "animation": "pop"})
    assert ev[1][2] == "a " + render.POP + r"b{\fscx100\fscy100}"
