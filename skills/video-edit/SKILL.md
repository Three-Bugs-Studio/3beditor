---
name: video-edit
description: "Edit the user's footage into a finished video that matches a style, either from a reference video or a preset (gym-montage, gym-cinematic, tiktok-fast, vlog, cinematic, podcast-clip). Covers cutting, reframing to 9:16/16:9/1:1, captions from speech, colour, music, loudness, then a check of the result against the style. Use for 'edit my clips like this video', 'make a reel from these', 'cut this into a TikTok', 'add captions and music'."
---

# Video edit

Footage + style → `edl.json` (the edit plan) → preview → render → measure → fix.

Scripts are in `../../scripts/` relative to this skill's base directory. Run `python <scripts>/render.py --help` for the full EDL format. `craft.md` next to this file maps everyday Premiere and After Effects techniques to the EDL and lists what isn't supported yet.

## Rules

- Never modify or overwrite the user's files. Put everything in a `3beditor_work/` folder next to their footage.
- Use absolute paths in `edl.json`.
- Get the user's OK on the preview before the full render.
- At most 2 fix rounds after the full render, then report what still differs.

## Steps

1. **Check the machine.** Run `python <scripts>/doctor.py`. If `ok` is false, give the fix lines and stop.
2. **Get the style.**
   - Reference video or link (TikTok, YouTube, Facebook): follow the `video-style` skill to produce `ref_style/style.json` with `visual_notes`.
   - Preset name: use `../../styles/<name>.json`.
   - Neither: ask which platform the video is for and pick the matching preset.
3. **Understand the footage.** For each clip run `python <scripts>/analyze.py CLIP --out <work>/clips/<name> --transcript` (leave out `--transcript` for clips without speech). Read every `contact.png`. Note the good moments, bad frames and what is said when.
4. **Plan `edl.json`**, mapping style to EDL:
   | Style field | EDL decision |
   |---|---|
   | `format.aspect` | `size`: 9:16 → `[1080,1920]`, 16:9 → `[1920,1080]`, 1:1 → `[1080,1080]`. Clips are cover-cropped to fit |
   | `format.letterboxed: true` | `"fit": "contain"`: the whole clip sits on black bars, like the reference |
   | `visual_notes.text_overlays` with a fixed title | one caption from 0 to the end, `"position": "top"` |
   | `pacing.avg_shot_s`, `avg_shot_by_third_s`, `first_cut_s` | clip lengths. Keep the hook as fast as the reference |
   | `music.cut_on_beat_ratio` > 0.5 and the user gave music | run `analyze.py` on the music file, then put cut points on its `music.beats_s` |
   | `speech.words` | cut on word `end` times, never mid-word. Keep sentences whole |
   | `color` (style vs. footage average) | `color.saturation` ≈ style_sat / footage_sat (0.5–2), `brightness` ≈ (style − footage) / 255, `warmth` ≈ (style − footage) / 20, clamped −1..1 |
   | big moments the viewer should feel (the PR rep, plates hitting the floor) | at most one `sfx` per ~10 s, only with a reason. Built-ins and levels are in `craft.md` ("Sound effects") |
   | `visual_notes.captions` | `captions` built from transcript words, grouped `words_per_caption` at a time, with start = first word start and end = last word end (copy each word's time into `words` for reveal). `caption_style` comes from position, case, colour, box, stroke and motion (`reveal`, `animation`, `highlight`). See the SubText recipes in `craft.md` |
   | caption font | the customer's font, or one that looks like the reference. For Vietnamese, only fonts from `python <scripts>/fonts.py list --vietnamese` or a Việt hóa `font_file`. The render refuses fonts with missing letters |
   | `pacing.transitions` + `visual_notes.transitions` | start with **hard cuts everywhere**, then run `python <scripts>/fx_plan.py <edl> --style <style>`. It adds an effect only where one is motivated: a hit (`flash`/`zoom_punch`) on a real energy rise, a whip that follows real motion, a soft `fade`/`dip_black` on a scene or time change. Same-angle cuts stay hard cuts. Never add effects for variety; at most about 1 per 4-6 cuts and 2 kinds per video |
   | `format.fps` / style `edit.fps` | `fps`: 24 for film looks, 30 for social, 60 only when the footage is 60 fps |
   | end card or title in the reference | add a `color:` card clip, with its caption set to `"position": "center"` |
   | `visual_notes.framing` punch-ins | `zoom: 1.1–1.25` on some clips |
   | `audio.integrated_lufs` | `loudness_lufs` (default −14) |
   | `visual_notes.story` + `shots[].role` | the clip order: follow the same line (hook → proof → payoff) with the user's own moments. A reference that opens on the payoff opens on the user's best rep |
   | `visual_notes.shots[].overlay_text` | text captions at the same points, rewritten for the user's story. Never copy the reference's words |
   | `visual_notes.sfx` | `sfx` at the matching moment in the user's video, using the closest built-in sound. The sound rules in `craft.md` still apply |

   Respect a length the user asked for, even if that means fewer shots.
   Gym footage: cut each set down to its best 1-3 reps (the contact sheet and the clip's own cuts show where they are), and end on the heaviest rep or PR.
   **One camera angle (a single set filmed on a phone):** fast cuts at random times look jumpy. The lifter teleports, because the reference's fast cuts went between *different* scenes. Instead:
   - Cut only at the same point in a rep, usually the still moment at the bottom or lockout, so each cut reads as a skip forward in time. Find those moments from motion over time (e.g. ffmpeg `tblend=all_mode=difference,signalstats` on the bar area: low motion = the still points). Then check the frames on both sides of every cut.
   - Don't switch zoom on and off between shots. Use one zoom for the whole video, or none.
   - Keep the sound continuous: set `mute: true` on every clip and use the source video itself as `music` (with `volume: 1`). Choose `music.start` so the cuts fall on its beats (`analyze.py` gives `music.beats_s`).
   - Shots of one rep each, about 1.5-2 s, then a longer final grind. Slow motion and speed ramps aren't supported yet, so tell the user if the reference uses them.
   Restraint: the reference's count of effects is a ceiling, not a target. Fewer, well-placed effects read as professional, while many effects (or an effect on a same-angle cut) read as amateur.
   Transitions on beat-locked cuts: a transition overlaps its two clips, so keep its **middle** on the beat (`fx_plan.py --apply` does this). Extend the outgoing clip's `out` by half the transition (× its `speed`) and start the incoming clip's `in` half a transition earlier (× its `speed`). The timeline then keeps its length, and `analyze.py --cuts-from` reports the mid-transition times.
   Music: if the reference uses a trending song, leave `music` out and tell the user to add that sound in the TikTok, Reels or Shorts app (it stays licensed there). Keep their own audio, or set `mute: true` on clips.
5. **Preview.** Run `python <scripts>/render.py <work>/edl.json --preview`, then `python <scripts>/analyze.py <work>/out_preview.mp4 --out <work>/preview`. Show the user the preview contact sheet and a short plan (shots, length, captions, music) and ask for their OK or changes.
6. **Render and check.** Run `python <scripts>/render.py <work>/edl.json`, then `python <scripts>/analyze.py <work>/out.mp4 --out <work>/final --target <style.json> --cuts-from <work>/edl.json`. Always pass `--cuts-from`: fades between similar shots can't be detected reliably, but the EDL knows the exact cuts. Exit code 2 means a mismatch: read `match.checks` and adjust:
   - `pacing.*` too slow: shorten or split clips. Too fast: lengthen them.
   - `color.*` off: move the matching `color` value by the difference. **Exception:** when the reference and the footage are different kinds of content (a bright graphics or UI ad vs. camera or game footage, or day vs. night), don't chase `brightness`. Forcing it washes out the footage. Report it as an intended difference instead.
   - `audio.integrated_lufs` off: check that `loudness_lufs` is set and the music isn't clipping.
   - `audio.true_peak_dbtp` above -1: lower the music `volume` or the loudest `sfx` `volume_db`, never the loudness target.
   Re-render, at most 2 rounds.
7. **Report:** the output path, its length, a short table of target vs. actual for each check, and anything you couldn't match and why. Offer tweaks ("faster hook?", "different music volume?").
