"""Analyze every cut of an edit plan and suggest a transition only where something motivates it.

usage: python fx_plan.py EDL.json [--style gym-cinematic] [--apply OUT.json]

Professional edits are mostly clean hard cuts. A transition needs a reason in the footage or music:
  - the beat drop (music at least 1.5x louder for 2 s) -> one hit transition (flash / zoom punch)
  - real motion in the same direction on both sides of the cut -> a whip that follows it
  - a change of scene or a jump in time            -> a soft cinematic transition (fade / dip)
  - same camera angle on both sides                -> hard cut, an effect would look random
Then an effects budget keeps it clean: about one effect per N cuts and at most two kinds.
--apply writes a new EDL with the plan, keeping each transition's middle where the cut was.
"""
import argparse
import array
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import render  # noqa: E402

STYLES = Path(__file__).resolve().parent.parent / "styles"
N = 32  # analysis frames are 32x32 grey: enough to compare scenes and see motion, fast in plain Python
HITS = ("flash", "zoom_punch")
SOFT = ("fade", "dip_black", "blur", "fade_grays", "smooth_left", "dip_white", "circle_open")
WHIP = {"left": "whip_left", "right": "whip_right", "up": "whip_up", "down": "whip_down"}


def grey(clip, t):
    if clip["src"].startswith("color:"):
        src = ["-f", "lavfi", "-i", f"color=c={clip['src'][6:]}:s={N}x{N}"]
    else:
        src = ["-ss", f"{max(0.0, t):.3f}", "-i", str(clip["path"])]
    out = subprocess.run(["ffmpeg", "-v", "error", *src, "-frames:v", "1", "-vf", f"scale={N}:{N},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return out if len(out) == N * N else None


def similarity(a, b):
    """Histogram overlap 0..1: about 0.8 or more is the same scene and angle."""
    ha, hb = [0] * 16, [0] * 16
    for x in a:
        ha[x >> 4] += 1
    for x in b:
        hb[x >> 4] += 1
    return sum(min(p, q) for p, q in zip(ha, hb)) / (N * N)


def motion(a, b, r=4):
    """(dx, dy) the picture moved from frame a to frame b, or (0, 0) if no clear shift explains the change."""
    def sad(dx, dy):
        tot = cnt = 0
        for y in range(max(0, dy), min(N, N + dy)):
            row_b, row_a = y * N, (y - dy) * N
            for x in range(max(0, dx), min(N, N + dx)):
                tot += abs(b[row_b + x] - a[row_a + x - dx])
                cnt += 1
        return tot / cnt
    still = sad(0, 0)
    best = min(((sad(dx, dy), dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)), key=lambda s: s[0])
    return (best[1], best[2]) if still > 4 and best[0] < still / 1.3 else (0, 0)


def direction(m):
    dx, dy = m
    if math.hypot(dx, dy) < 2:
        return None
    return ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")


def music_energy(edl, total):
    """RMS loudness of the music bed every 0.1 s on the output timeline, or None without music."""
    m = edl.get("music")
    if not m:
        return None
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(float(m.get("start", 0))), "-t", f"{total:.3f}",
                          "-i", str(m["path"]), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    s = array.array("h", pcm)
    return [math.sqrt(sum(x * x for x in s[i:i + 800]) / 800) for i in range(0, len(s) - 799, 800)]


def jump(energy, t, w=20):  # 2 s either side: a section change, not one kick drum
    if not energy:
        return 1.0
    i = int(t * 10)
    before, after = energy[max(0, i - w):i], energy[i:i + w]
    return (sum(after) / len(after)) / max(1.0, sum(before) / len(before)) if before and after else 1.0


def plan(edl_path, style=None):
    edl_path = Path(edl_path)
    raw, edl = json.loads(edl_path.read_text(encoding="utf-8")), render.load(edl_path)
    mix = {"accents": ["flash"], "accent_every_n_cuts": 4}
    if style:
        sp = Path(style) if Path(style).is_file() else STYLES / f"{style}.json"
        mix = json.loads(sp.read_text(encoding="utf-8")).get("transition_mix", mix)
    accents, every = mix["accents"], int(mix.get("accent_every_n_cuts", 4))
    clips, spans = edl["clips"], render.timeline(edl)
    energy = music_energy(edl, spans[-1][1])
    cuts = []
    for i in range(1, len(clips)):
        p, c, rp, rc = clips[i - 1], clips[i], raw["clips"][i - 1], raw["clips"][i]
        p_out = p["start"] + p["dur"] * p["speed"]
        a_end, a_pre = grey(p, p_out - 0.04), grey(p, p_out - 0.04 - 0.12 * p["speed"])
        b_start, b_post = grey(c, c["start"]), grey(c, c["start"] + 0.12 * c["speed"])
        sim = similarity(a_end, b_start) if a_end and b_start else 0.0
        m_out = direction(motion(a_pre, a_end)) if a_pre and a_end else None
        m_in = direction(motion(b_start, b_post)) if b_start and b_post else None
        # skipping reps inside one take is normal; a time jump is another file or a gap of over 30 s
        time_jump = p["src"] != c["src"] or abs(c["start"] - p_out) > 30
        cut_t = spans[i][0] + c["tin"]["duration"] / 2  # middle of any existing transition
        cuts.append({"cut": i, "time_s": round(cut_t, 2), "into_clip": i + 1, "same_angle": sim >= 0.8,
                     "similarity": round(sim, 2), "motion_out": m_out, "motion_in": m_in, "time_jump": time_jump,
                     "energy_jump": round(jump(energy, cut_t), 2),
                     "short": min(p["dur"], c["dur"]) < 0.6, "was": rc.get("transition", {}).get("type")})
    # candidates by priority: the drop, then real motion, then a scene/time change
    drop = max(cuts, key=lambda k: k["energy_jump"]) if cuts else None
    for k in cuts:
        k["suggest"], k["reason"], k["priority"] = "cut", "", 0
        hit = next((a for a in accents if a in HITS), None)
        whips = any(a.startswith("whip") for a in accents)
        soft = next((a for a in accents if a in SOFT), None)
        if k["short"]:
            k["reason"] = "shot under 0.6 s: no room for an effect"
        elif k is drop and k["energy_jump"] >= 1.5 and hit:
            k.update(suggest=hit, priority=3, reason=f"the music's biggest hit (energy x{k['energy_jump']})")
        elif k["same_angle"] and not k["time_jump"]:
            k["reason"] = "same camera angle: a hard cut stays seamless, an effect would look random"
        elif whips and k["motion_out"] and k["motion_out"] == k["motion_in"]:
            k.update(suggest=WHIP[k["motion_out"]], priority=2,
                     reason=f"both shots move {k['motion_out']}: the whip follows that motion")
        elif soft and (k["time_jump"] or k["similarity"] < 0.5):
            k.update(suggest=soft, priority=1, reason="new scene or a jump in time: a soft transition marks it")
        else:
            k["reason"] = "nothing in the footage or music asks for an effect"
    budget = max(1, len(cuts) // every)
    chosen = sorted((k for k in cuts if k["priority"]), key=lambda k: (-k["priority"], -k["energy_jump"]))
    kinds, kept = set(), 0
    for k in chosen:
        family = "whip" if k["suggest"].startswith("whip") else k["suggest"]
        if kept >= budget or (family not in kinds and len(kinds) >= 2):
            k.update(suggest="cut", reason=k["reason"] + "; dropped to keep the edit clean (effects budget)")
            continue
        kinds.add(family)
        kept += 1
    for k in cuts:
        del k["priority"]
    return {"cuts": cuts, "effects": kept, "budget": budget, "music": energy is not None}


def apply(edl_path, result, out_path):
    """Write the plan into a new EDL. A transition overlaps its clips, so each side gives half of it,
    which keeps its middle exactly where the hard cut was (and on the beat)."""
    raw = json.loads(Path(edl_path).read_text(encoding="utf-8"))
    for k in result["cuts"]:
        prev, cur = raw["clips"][k["cut"] - 1], raw["clips"][k["cut"]]
        cur["transition"] = {"type": k["suggest"]}
        if k["suggest"] != "cut" and "in" in cur and "out" in prev:
            half = render.TRANSITIONS[k["suggest"]][1] / 2
            if cur["in"] - half * cur.get("speed", 1) >= 0:
                prev["out"] = round(prev["out"] + half * prev.get("speed", 1), 3)
                cur["in"] = round(cur["in"] - half * cur.get("speed", 1), 3)
    raw.setdefault("output", "out.mp4")
    Path(out_path).write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which cannot print Vietnamese
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("--style", help="preset id or style.json whose transition_mix lists the allowed effects")
    ap.add_argument("--apply", help="write a new EDL with the suggested transitions")
    a = ap.parse_args()
    try:
        r = plan(a.edl, a.style)
    except render.EDLError as e:
        sys.exit(str(e))
    if a.apply:
        apply(a.edl, r, a.apply)
        r["written"] = a.apply
    print(json.dumps(r, indent=2, ensure_ascii=False))
