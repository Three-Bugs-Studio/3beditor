"""Render an edit decision list (edl.json) to a video with FFmpeg.

usage: python render.py EDL.json [--preview] [--dry-run]

Paths inside the EDL are relative to the EDL file. Inputs are never overwritten.
See SCHEMA below for every field.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fonts  # noqa: E402

SCHEMA = """
{
  "output": "out.mp4",                       required
  "size": [1080, 1920], "fps": 30,           default 1080x1920 @ 30
  "fit": "cover",                            default for every clip; clips can override
  "clips": [                                 required, in timeline order
    {"src": "a.mp4", "in": 1.0, "out": 3.5,  video: trim in/out seconds
     "zoom": 1.1, "mute": false,             optional punch-in, drop clip audio
     "fit": "contain",                       optional: "cover" (crop to fill, default) or "contain" (black bars)
     "speed": 0.5},                          optional: 0.5 = slow motion (frames interpolated), 2 = fast
    {"src": "card.png", "duration": 2},      image held for N seconds
    {"src": "color:black", "duration": 1}    solid colour card
  ],
  "transition": {"type": "cut", "duration": 0.3},   default between clips; a clip's own "transition" (the
                                             transition INTO that clip) wins. Types (python board.py transitions):
                                             cut | cinematic: fade, dip_black, dip_white, blur, fade_grays,
                                             smooth_left, circle_open | tiktok: whip_left/right/up/down,
                                             zoom_punch, flash, glitch, swipe_up
  "fps": 30,                                 24 cinematic, 30 social, 60 smooth; slow motion from 60 fps footage
                                             uses real frames, otherwise in-between frames are invented
  "fade_in": 0.5, "fade_out": 0.8,           optional fade from/to black (and silence), seconds
  "color": {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "warmth": 0.0},
                                             brightness -1..1, warmth -1 (cool)..1 (warm)
  "color": {..., "teal_orange": 0.6, "crush": 0.5, "vignette": true, "grain": 0.3},
                                             optional film look: teal shadows + warm highlights, deeper blacks (0..1)
  "captions": [{"text": "Em đẹp quá", "start": 0.0, "end": 1.2,   output-timeline seconds
                "position": "center",                       optional, overrides caption_style
                "highlight": ["đẹp"],                       words drawn in highlight_color
                "words": [{"start": 0.0}, {"start": 0.4}, {"start": 0.8}]}],  optional word times for reveal
  "caption_style": {"position": "bottom" | "center" | "top", "size": 72,
                    "color": "#FFFFFF", "outline_color": "#000000", "box": false,
                    "uppercase": false, "bold": true, "italic": false,
                    "font": "Arial",                        an installed family (python fonts.py list --vietnamese)
                    "font_file": "fonts/MyFont-VH.ttf",     or a font file, e.g. a "Việt hóa" font; wins over font
                    "outline": 4, "shadow": 0, "blur": 0,   stroke width, drop shadow, glow softness (px)
                    "spacing": 0,                           letter spacing (px)
                    "highlight_color": "#FFE600",
                    "animation": "none" | "pop" | "fade" | "zoom",
                    "reveal": "none" | "word" | "build" | "karaoke"},
                    word: words appear left to right, layout fixed; build: the line grows and re-centres;
                    karaoke: the whole line shows and the spoken word lights up in highlight_color.
                    Every caption character must exist in the font, or the render stops (no silent font swap).
  "music": {"src": "song.mp3", "volume": 0.3, "start": 0.0},
  "loudness_lufs": -14
}
"""
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
ALIGN = {"bottom": 2, "center": 5, "top": 8}  # ASS numpad alignment


class EDLError(ValueError):
    pass


# name: (ffmpeg xfade transition, default seconds, effect switched on only during the transition, group, what it is)
TRANSITIONS = {
    "cut": (None, 0, None, "basic", "hard cut"),
    "fade": ("fade", 0.4, None, "cinematic", "cross dissolve"),
    "dip_black": ("fadeblack", 0.6, None, "cinematic", "dip to black"),
    "dip_white": ("fadewhite", 0.5, None, "cinematic", "soft dip to white"),
    "blur": ("fade", 0.5, "gblur=sigma=18", "cinematic", "dreamy blur dissolve"),
    "fade_grays": ("fadegrays", 0.6, None, "cinematic", "fade through black and white"),
    "smooth_left": ("smoothleft", 0.5, None, "cinematic", "soft sliding wipe"),
    "circle_open": ("circleopen", 0.5, None, "cinematic", "iris opens on the next shot"),
    "whip_left": ("slideleft", 0.25, "dblur=angle=0:radius=60", "tiktok", "whip pan to the left"),
    "whip_right": ("slideright", 0.25, "dblur=angle=0:radius=60", "tiktok", "whip pan to the right"),
    "whip_up": ("slideup", 0.25, "dblur=angle=90:radius=60", "tiktok", "whip pan up"),
    "whip_down": ("slidedown", 0.25, "dblur=angle=90:radius=60", "tiktok", "whip pan down"),
    "zoom_punch": ("zoomin", 0.3, "gblur=sigma=10", "tiktok", "zoom punch into the next shot"),
    "flash": ("fadewhite", 0.2, None, "tiktok", "white flash, great on a beat drop"),
    "glitch": ("pixelize", 0.25, "rgbashift=rh=14:bh=-14:gv=6", "tiktok", "digital glitch"),
    "swipe_up": ("coverup", 0.3, None, "tiktok", "next shot swipes up over this one"),
}


def probe_media(path):
    """(has an audio stream, video frames per second or 0)"""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,avg_frame_rate",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    audio, fps = False, 0.0
    for row in out.split():
        kind, _, rate = row.partition(",")
        audio |= kind == "audio"
        if kind == "video" and "/" in rate and rate.split("/")[1] not in ("", "0"):
            fps = fps or int(rate.split("/")[0]) / int(rate.split("/")[1])
    return audio, fps


def has_audio(path):
    return probe_media(path)[0]


def transition_spec(spec, where):
    kind = spec.get("type", "cut")
    if kind not in TRANSITIONS:
        raise EDLError(f"{where}: unknown transition '{kind}'. Choose from: {', '.join(TRANSITIONS)}")
    dur = 0.0 if kind == "cut" else float(spec.get("duration", TRANSITIONS[kind][1]))
    if kind != "cut" and dur <= 0:
        raise EDLError(f"{where}: transition duration must be positive")
    return {"type": kind, "duration": dur}


def frame_plan(edl):
    """[(start frame, length in frames, transition overlap in frames)] per clip. Whole frames on purpose:
    fractional lengths drift a little per trim, and a 1-frame cut overlap then misses and ends the video early.
    Boundaries are rounded from the exact timeline, so no cut is ever more than half a frame off its plan."""
    fps, plan, t = float(edl.get("fps", 30)), [], 0.0
    frames = lambda s: int(s * fps + 0.5)  # round half up (Python's round() sends 12.5 to 12)
    for i, c in enumerate(edl["clips"]):
        start = t - (c["tin"]["duration"] if i else 0)
        a, b = frames(start), max(frames(start + c["dur"]), frames(start) + 1)
        ov = max(1, frames(t) - a) if i and c["tin"]["type"] != "cut" else 0
        plan.append((a, b - a, ov))
        t = start + c["dur"]
    return plan


def timeline(edl):
    """(start, end) seconds of every clip on the output timeline; a transition overlaps the end of the clip before it."""
    fps = float(edl.get("fps", 30))
    return [(s / fps, (s + n) / fps) for s, n, _ in frame_plan(edl)]


def load(edl_path):
    edl_path = Path(edl_path)
    try:
        edl = json.loads(edl_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise EDLError(f"cannot read {edl_path}: {e}")
    base = edl_path.parent
    if not edl.get("output"):
        raise EDLError("'output' is required")
    if not edl.get("clips"):
        raise EDLError("'clips' must be a non-empty list")
    out = (base / edl["output"]).resolve()
    default_tr = transition_spec(edl.get("transition") or {"type": "cut"}, "transition")
    fps = float(edl.get("fps", 30))
    if not 1 <= fps <= 120:
        raise EDLError("fps must be between 1 and 120 (24 cinematic, 30 social, 60 smooth)")
    clips = []
    for i, c in enumerate(edl["clips"]):
        src = c.get("src")
        if not src:
            raise EDLError(f"clip {i}: 'src' is required")
        if src.startswith("color:"):
            kind, path = "color", None
        else:
            path = (base / src).resolve()
            if not path.is_file():
                raise EDLError(f"clip {i}: file not found: {path}")
            if path == out:
                raise EDLError("output would overwrite an input")
            kind = "image" if path.suffix.lower() in IMAGE_EXT else "video"
        if kind == "video":
            start, end = float(c.get("in", 0)), c.get("out")
            if end is None or float(end) <= start:
                raise EDLError(f"clip {i}: needs 'out' greater than 'in'")
            speed = float(c.get("speed", 1))
            if not 0.25 <= speed <= 4:
                raise EDLError(f"clip {i}: speed must be between 0.25 and 4")
            dur = (float(end) - start) / speed
        else:
            speed = 1.0
            start, dur = 0.0, float(c.get("duration", 0))
            if dur <= 0:
                raise EDLError(f"clip {i}: needs a positive 'duration'")
        zoom = float(c.get("zoom", 1))
        if zoom < 1:
            raise EDLError(f"clip {i}: zoom must be >= 1")
        fit = c.get("fit", edl.get("fit", "cover"))
        if fit not in ("cover", "contain"):
            raise EDLError(f"clip {i}: fit must be 'cover' or 'contain'")
        audio, src_fps = probe_media(path) if kind == "video" else (False, 0.0)
        tin = transition_spec(c["transition"], f"clip {i}") if c.get("transition") and i else (
            default_tr if i else {"type": "cut", "duration": 0.0})  # transition INTO this clip
        clips.append({"kind": kind, "path": path, "src": src, "start": start, "dur": dur, "zoom": zoom, "fit": fit,
                      "speed": speed, "src_fps": src_fps, "tin": tin, "audio": audio and not c.get("mute")})
    for i in range(1, len(clips)):
        if clips[i]["tin"]["duration"] >= min(clips[i - 1]["dur"], clips[i]["dur"]):
            raise EDLError(f"clip {i}: transition must be shorter than the clips on both sides")
    music = edl.get("music")
    if music:
        mp = (base / music["src"]).resolve()
        if not mp.is_file():
            raise EDLError(f"music file not found: {mp}")
        if mp == out:
            raise EDLError("output would overwrite an input")
        music = {**music, "path": mp}
    for j, cap in enumerate(edl.get("captions") or []):
        if not cap.get("text") or float(cap["end"]) <= float(cap["start"]):
            raise EDLError(f"caption {j}: needs text and end > start")
    st = edl.get("caption_style") or {}
    if st.get("animation", "none") not in ("none", "pop", "fade", "zoom"):
        raise EDLError("caption_style.animation must be none, pop, fade or zoom")
    if st.get("reveal", "none") not in ("none", "word", "build", "karaoke"):
        raise EDLError("caption_style.reveal must be none, word, build or karaoke")
    font = None
    if edl.get("captions"):
        font = pick_font(st, base)
        text = "".join(c["text"] for c in edl["captions"])
        miss = fonts.missing(font, text.upper() if st.get("uppercase") else text)
        if miss:
            raise EDLError(f"font '{font['family']}' has no glyph for: {' '.join(miss)}. "
                           "Use a 'Việt hóa' version of the font, or one from: python fonts.py list --vietnamese")
    for key in ("color", "outline_color", "highlight_color"):
        val = (edl.get("caption_style") or {}).get(key)
        if val is not None and not re.fullmatch(r"#[0-9A-Fa-f]{6}", val):
            raise EDLError(f"caption_style.{key} must be #RRGGBB, got {val!r}")
    w, h = edl.get("size") or [1080, 1920]
    return {**edl, "out": out, "clips": clips, "music": music, "font": font,
            "chain": any(c["tin"]["type"] != "cut" for c in clips),
            "w": int(w) // 2 * 2, "h": int(h) // 2 * 2, "fps": edl.get("fps", 30)}


DEFAULT_FONTS = ("Arial", "Liberation Sans", "DejaVu Sans", "Noto Sans", "Helvetica")
BR = ""  # line-break marker inside a caption's word list (a private-use char, never in real text)
POP = r"{\fscx125\fscy125\t(0,120,\fscx100\fscy100)}"


def pick_font(st, base):
    if st.get("font_file"):
        path = (base / st["font_file"]).resolve()
        face = fonts.resolve(str(path)) if path.is_file() else None
        if not face:
            raise EDLError(f"caption_style.font_file not found or unreadable: {path}")
        return {**face, "file": True}
    if st.get("font"):
        face = fonts.resolve(st["font"])
        if not face:
            raise EDLError(f"font '{st['font']}' is not installed. Install it, set font_file, "
                           "or pick one from: python fonts.py list --vietnamese")
        return {**face, "file": False}
    for name in DEFAULT_FONTS:
        face = fonts.resolve(name)
        if face:
            return {**face, "file": False}
    raise EDLError("no default font found: set caption_style.font or font_file")


def ass_color(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()  # ASS is BGR


def ass_tag_color(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def _norm(word):
    return "".join(ch for ch in word.casefold() if ch.isalnum())


def caption_events(c, st):
    """(start, end, ASS text) lines for one caption: highlighted words, animation and word-by-word reveal."""
    text = c["text"].upper() if st["uppercase"] else c["text"]
    tokens = text.replace("{", "(").replace("}", ")").replace("\n", f" {BR} ").split()
    hl = {_norm(w) for w in c.get("highlight", [])}
    base_c, hl_c = ass_tag_color(st["color"]), ass_tag_color(st["highlight_color"])

    def line(toks, hide_from=None, lit=None, newest=None):
        out, k, first = [], 0, True
        for tk in toks:
            if tk == BR:
                out.append(r"\N")
                first = True
                continue
            word = f"{{\\c{hl_c}}}{tk}{{\\c{base_c}}}" if lit == k or (lit is None and _norm(tk) in hl) else tk
            if newest == k and st["animation"] == "pop":
                word = POP + word + r"{\fscx100\fscy100}"
            if hide_from == k:  # everything from here on is invisible but still takes its place in the layout
                word = r"{\alpha&HFF&}" + word
            out.append(("" if first else " ") + word)
            first, k = False, k + 1
        return "".join(out)

    prefix = r"{\an%d}" % ALIGN[c["position"]] if c.get("position") in ALIGN else ""
    if float(st["blur"]):
        prefix += r"{\blur%s}" % st["blur"]
    start, end, reveal = float(c["start"]), float(c["end"]), st["reveal"]
    n = sum(tk != BR for tk in tokens)
    if reveal == "none" or n < 2:
        anim = {"pop": POP, "fade": r"{\fad(120,120)}", "zoom": r"{\t(\fscx115\fscy115)}"}.get(st["animation"], "")
        return [(start, end, prefix + anim + line(tokens))]
    given = c.get("words") or []
    times = ([float(w["start"]) for w in given] if len(given) == n
             else [start + (end - start) * k / n for k in range(n)])
    events = []
    for k in range(n):
        t0, t1 = max(start, times[k]), (times[k + 1] if k + 1 < n else end)
        if t1 <= t0:
            continue
        if reveal == "karaoke":
            body = line(tokens, lit=k)
        elif reveal == "word":
            body = line(tokens, hide_from=k + 1, newest=k)
        else:  # build: only the words so far, so a centred line re-centres as it grows
            toks, seen = [], 0
            for tk in tokens:
                if seen > k:
                    break
                toks.append(tk)
                seen += tk != BR
            body = line(toks, newest=k)
        events.append((t0, t1, prefix + body))
    return events


def ass_time(t):
    t = max(0.0, float(t))
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def write_ass(edl, path):
    st = {"position": "bottom", "size": 72, "color": "#FFFFFF", "outline_color": "#000000", "box": False,
          "uppercase": False, "bold": True, "italic": False, "outline": 4, "shadow": 0, "blur": 0, "spacing": 0,
          "highlight_color": "#FFE600", "animation": "none", "reveal": "none", **(edl.get("caption_style") or {})}
    margin = int(edl["h"] * 0.12)
    family = edl["font"]["family"] if edl.get("font") else "Arial"
    style = (f"Style: Default,{family},{st['size']},{ass_color(st['color'])},&H000000FF,"
             f"{ass_color(st['outline_color'])},&H80000000,{-1 if st['bold'] else 0},{-1 if st['italic'] else 0},"
             f"0,0,100,100,{st['spacing']},0,{3 if st['box'] else 1},{st['outline']},{st['shadow']},"
             f"{ALIGN.get(st['position'], 2)},60,60,{margin},1")
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {edl['w']}", f"PlayResY: {edl['h']}", "",
             "[V4+ Styles]",
             "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
             "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,"
             "MarginV,Encoding", style, "", "[Events]",
             "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    for c in edl["captions"]:
        for t0, t1, text in caption_events(c, st):
            lines.append(f"Dialogue: 0,{ass_time(t0)},{ass_time(t1)},Default,,0,0,0,,{text}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def color_filter(c):
    if not c:
        return None
    b, ct, s, warm = (float(c.get(k, d)) for k, d in
                      (("brightness", 0), ("contrast", 1), ("saturation", 1), ("warmth", 0)))
    parts = []
    if (b, ct, s) != (0, 1, 1):
        parts.append(f"eq=brightness={b}:contrast={ct}:saturation={s}")
    if warm:
        k = max(-1.0, min(1.0, warm)) * 0.15  # shortcut: warmth is a global red/blue shift, upgrade to a LUT for exact grades
        parts.append(f"colorbalance=rs={k}:bs={-k}:rm={k / 2}:bm={-k / 2}")
    to, crush, grain = (max(0.0, min(1.0, float(c.get(k, 0)))) for k in ("teal_orange", "crush", "grain"))
    if to:  # film look: cool teal shadows, warm skin-tone highlights
        parts.append(f"colorbalance=rs={-0.12 * to:.3f}:bs={0.12 * to:.3f}:rh={0.10 * to:.3f}:bh={-0.10 * to:.3f}")
    if crush:  # deeper blacks, slightly soft whites
        parts.append(f"curves=master='0/0 0.25/{0.25 - 0.12 * crush:.3f} 0.75/0.75 1/{1 - 0.04 * crush:.3f}'")
    if c.get("vignette"):
        parts.append("vignette=PI/4.5")
    if grain:
        parts.append(f"noise=alls={round(14 * grain)}:allf=t")
    return ",".join(parts) or None


def build(edl, preview=False):
    w, h, fps = edl["w"], edl["h"], edl["fps"]
    if preview:
        w, h = w // 3 // 2 * 2, h // 3 // 2 * 2
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    fg, n = [], 0
    vlabels, alabels = [], []
    clips, fps_f, plan = edl["clips"], float(fps), frame_plan(edl)
    for i, c in enumerate(clips):
        # in a transition chain a hard cut is a 1-frame overlap: give the outgoing clip that frame so timing stays exact
        nf = plan[i][1] + (1 if edl["chain"] and i + 1 < len(clips) and clips[i + 1]["tin"]["type"] == "cut" else 0)
        d = nf / fps_f
        if c["kind"] == "video":
            cmd += ["-ss", f"{c['start']}", "-t", f"{d * c['speed'] + 0.1:.3f}", "-i", str(c["path"])]
        elif c["kind"] == "image":
            cmd += ["-loop", "1", "-t", f"{d}", "-i", str(c["path"])]
        else:
            cmd += ["-f", "lavfi", "-t", f"{d}", "-i", f"color=c={c['src'][6:]}:s={w}x{h}:r={fps}"]
        vin = n
        n += 1
        zw, zh = int(w * c["zoom"]) // 2 * 2, int(h * c["zoom"]) // 2 * 2
        if c["fit"] == "contain":  # letterbox: whole picture on black bars, a common look in gym reposts
            frame = (f"scale={zw}:{zh}:force_original_aspect_ratio=decrease,crop='min(iw,{w})':'min(ih,{h})',"
                     f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black")
        else:  # cover: fill the frame then centre-crop, so 16:9 footage reframes to 9:16 without bars
            frame = f"scale={zw}:{zh}:force_original_aspect_ratio=increase,crop={w}:{h}"
        retime = ""
        if c["speed"] != 1:
            retime = f"setpts=(PTS-STARTPTS)/{c['speed']},"
            # slow motion needs fps x speed real frames per second; invent the in-between ones only if the source lacks them
            if c["speed"] < 1 and not preview and c["src_fps"] * c["speed"] < float(fps) * 0.95:
                retime += f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1,"
        fg.append(f"[{vin}:v]{retime}{frame},"
                  f"setsar=1,fps={fps},format=yuv420p,tpad=stop_mode=clone:stop_duration={d},trim=end_frame={nf},"
                  f"setpts=PTS-STARTPTS,fps={fps}[v{i}]")  # re-state the rate: FFmpeg 7's xfade rejects 'unknown'
        if c["audio"]:
            tempo, sp = [], c["speed"]
            while sp < 0.5 or sp > 2:  # atempo takes 0.5-2 per stage
                tempo.append(0.5 if sp < 0.5 else 2.0)
                sp /= tempo[-1]
            tempo = "".join(f"atempo={x}," for x in tempo + ([sp] if sp != 1 else []))
            fg.append(f"[{vin}:a]{tempo}aformat=sample_rates=48000:channel_layouts=stereo,"
                      f"atrim=duration={d},apad=whole_dur={d},asetpts=PTS-STARTPTS[a{i}]")
        else:
            cmd += ["-f", "lavfi", "-t", f"{d}", "-i", "anullsrc=r=48000:cl=stereo"]
            fg.append(f"[{n}:a]asetpts=PTS-STARTPTS[a{i}]")
            n += 1
        vlabels.append(f"[v{i}]")
        alabels.append(f"[a{i}]")

    spans, windows = timeline(edl), []
    if edl["chain"]:
        v, a = vlabels[0], alabels[0]
        for i in range(1, len(vlabels)):
            kind = clips[i]["tin"]["type"]
            td = (plan[i][2] or 1) / fps_f  # a hard cut in the chain is one overlapping frame
            xf, _, effect, _, _ = TRANSITIONS[kind]
            start = plan[i][0] / fps_f
            fg.append(f"{v}{vlabels[i]}xfade=transition={xf or 'fade'}:duration={td:.6f}:offset={start:.6f}[vx{i}]")
            fg.append(f"{a}{alabels[i]}acrossfade=d={td:.6f}[ax{i}]")
            v, a = f"[vx{i}]", f"[ax{i}]"
            if effect:  # switched on only while this transition plays
                windows.append(f"{effect}:enable='between(t,{start:.3f},{start + td:.3f})'")
    else:
        k = len(vlabels)
        fg.append("".join(x for pair in zip(vlabels, alabels) for x in pair) + f"concat=n={k}:v=1:a=1[vc][ac]")
        v, a = "[vc]", "[ac]"
    total = spans[-1][1]

    post = windows + [f for f in (color_filter(edl.get("color")),) if f]
    if edl.get("captions"):
        post.append("subtitles=captions.ass" + (":fontsdir=fonts" if (edl.get("font") or {}).get("file") else ""))  # relative name: ffmpeg runs in workdir, avoids Windows path escaping
    fi, fo = float(edl.get("fade_in", 0)), float(edl.get("fade_out", 0))
    if fi:
        post.append(f"fade=t=in:st=0:d={fi}")
    if fo:
        post.append(f"fade=t=out:st={max(0, total - fo):.3f}:d={fo}")
    fg.append(f"{v}{','.join(post) or 'null'}[vout]")

    m = edl.get("music")
    if m:
        cmd += ["-ss", f"{float(m.get('start', 0))}", "-stream_loop", "-1", "-i", str(m["path"])]
        fg.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={float(m.get('volume', 0.3))},"
                  f"atrim=duration={total:.3f}[mus]")
        # shortcut: music sits under speech at a fixed volume, no ducking; add sidechaincompress if voices get buried
        fg.append(f"{a}[mus]amix=inputs=2:duration=first:normalize=0[amix]")
        a = "[amix]"
        n += 1
    if fi or fo:
        fades = ([f"afade=t=in:st=0:d={fi}"] if fi else []) + ([f"afade=t=out:st={max(0, total - fo):.3f}:d={fo}"] if fo else [])
        fg.append(f"{a}{','.join(fades)}[afd]")
        a = "[afd]"
    lufs = edl.get("loudness_lufs")
    fg.append(f"{a}{f'loudnorm=I={float(lufs)}:TP=-1.5:LRA=11' if lufs is not None else 'anull'},"
              f"aresample=48000[aout]")

    cmd += ["-filter_complex", ";".join(fg), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast" if preview else "medium", "-crf", "28" if preview else "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    return cmd, total


def render(edl_path, preview=False, dry_run=False):
    edl = load(edl_path)
    out = edl["out"]
    if preview:
        out = out.with_name(out.stem + "_preview" + out.suffix)
    with tempfile.TemporaryDirectory() as work:
        if edl.get("captions"):
            write_ass(edl, Path(work) / "captions.ass")
            if edl["font"]["file"]:  # the customer's font file: libass loads it from this folder, no install needed
                (Path(work) / "fonts").mkdir()
                shutil.copy(edl["font"]["path"], Path(work) / "fonts")
        cmd, total = build(edl, preview)
        cmd.append(str(out))
        if dry_run:
            return {"command": cmd, "duration_s": round(total, 3), "output": str(out)}
        out.parent.mkdir(parents=True, exist_ok=True)
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{p.stderr[-3000:]}")
    return {"output": str(out), "duration_s": round(total, 3), "preview": preview}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which cannot print Vietnamese
    ap = argparse.ArgumentParser(description=__doc__ + SCHEMA, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("--preview", action="store_true", help="fast 1/3-size render to <output>_preview.mp4")
    ap.add_argument("--dry-run", action="store_true", help="print the ffmpeg command without running it")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found: run scripts/doctor.py")
    try:
        print(json.dumps(render(a.edl, a.preview, a.dry_run), indent=2))
    except (EDLError, RuntimeError) as e:
        sys.exit(str(e))
