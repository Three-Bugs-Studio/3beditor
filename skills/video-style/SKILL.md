---
name: video-style
description: "Watch a reference video (a file, or a TikTok/YouTube/Facebook link) and analyze its editing style (cut pacing, colour, captions, transitions, music beat, loudness) into a reusable style.json. Use when the user shares a reference video or pastes a video link and says 'analyze this style', 'what style is this', 'make mine look like this', or wants to save a style for later. Vietnamese requests too: 'phân tích phong cách video này', 'video này dựng kiểu gì', 'làm giống video này'."
---

# Video style

**Language:** speak Vietnamese by default: plain, friendly tiếng Việt with no editing jargon. Switch to English only when the customer writes in English. Files the customer keeps (plans, reports) follow the same rule.

Turns a reference video into `style.json`: measured numbers plus your notes from looking at its frames. `video-edit` uses that file as the target.

Scripts live in `../../scripts/` relative to this skill's base directory. Run them with `python` (use `python3` if `python` is missing).

## Steps

1. **Check the machine.** Run `python <scripts>/doctor.py`. If `"ok": false`, show the user the `fix` lines in plain words and stop. The optional libraries only add beats and a transcript, so mention them but don't block on them.
2. **Get the reference.**
   - **A link** (TikTok, YouTube, Facebook, Instagram): watch it in the browser (step 3a). Never download it, and never install or use tools that get around a site's bot checks or logins.
   - **A file** (saved video or screen recording): measure it with the script (step 3b).
3a. **Watch a link in the browser.** Use the built-in browser (`Claude_Browser` tools) or Claude in Chrome, whichever this session has.
   1. Open the link and wait 3-4 s. If the page asks to sign in or blocks the video, ask the user to sign in in that browser, or to send a file instead.
   2. Read `../../scripts/watch.js` and run its text with the browser's JavaScript tool as `await ` + the file's text. It streams the video like a normal viewer (no download) and returns style JSON. It also draws a 4x4 contact sheet over the page.
   3. In the **same batch** (the page may redraw), take a screenshot to see the contact sheet.
   4. Save the returned JSON as `<work>/ref_style/style.json`.
   5. If it returns `error`: with "no playable video", press play once and rerun. With "site blocks reading frames", ask the user for the file.
   - Browser watching measures pictures only: `audio`, `music` and `speech` stay `null`. Ask the user what the sound is (trending song? voice-over?), and use `loudness_lufs: -14` (TikTok/Reels/Shorts standard) when editing.
   - Shots are only split on sudden cuts. Slow fades or slides count as one shot, so check the sheet.
   - `format.letterboxed: true` means the clip sits in black bars inside the frame, and `content_box`/`content_aspect` give the real picture. That's a deliberate look worth copying.
3b. **Measure a file.** Run `python <scripts>/analyze.py REF.mp4 --out <work>/ref_style`. Add `--transcript` when the reference has speech captions, so you can see caption pace against the speech. Then read `<work>/ref_style/contact.png`, a 4x4 grid of 16 frames in time order (left to right, top to bottom; times are in `contact_sheet.times_s`). For a closer look at one moment: `ffmpeg -ss T -i REF.mp4 -frames:v 1 frame.png`.
4. **Look closely.** Check the measured numbers against what you see, and note what numbers can't capture: text overlays, caption style, speed ramps (slow motion on the rep), zooms, shake, flashes, black bars.
5. **Write `visual_notes`** into `style.json` (edit the JSON, keep every measured field):
   ```json
   "visual_notes": {
     "captions": {"present": true, "position": "center|bottom|top", "case": "upper|sentence",
                  "words_per_caption": 3, "color": "#FFFFFF", "box": false, "font_feel": "bold sans, black outline"},
     "transitions": "hard cuts, mostly on the beat",
     "framing": "tight face, punch-in zoom every 2-3 shots, b-roll cutaways",
     "text_overlays": "hook title in first 2 s",
     "mood": "energetic",
     "story": {"summary": "a 3-month glow-up ending on a 140 kg deadlift PR",
               "hook": "0-1.5 s: the PR lockout first, then 'how it started'",
               "highlights": [{"at_s": 6.2, "what": "boom + freeze on the lockout", "why": "the payoff lands on the drop"}]},
     "shots": [{"at_s": 0.0, "role": "hook", "seen": "PR lockout, side view", "framing": "medium, low angle",
                "camera": "tripod, locked off", "overlay_text": "3 months ago I couldn't pull 60 kg", "sound": "music drop"}],
     "filming": {"setup": "phone on a tripod, 2 angles (side and front)", "light": "gym ceiling light, warm, no extra light",
                 "grade": "warm, a little faded"},
     "sfx": [{"at_s": 6.2, "kind": "boom", "on": "bar locks out"}]
   }
   ```
   - `shots`: one row per shot in `pacing.shots_s`. `role` is what the shot does in the story: `hook`, `context`, `proof`, `turn`, `payoff` or `cta`. Joined up, the roles are the reference's story line.
   - `seen` and `overlay_text` hold only what you can see in the frames. Put guesses (light, camera, gear) in `framing`, `camera` and `filming`, and add "(guess)" when you aren't sure. Never invent a certain answer.
   - `filming` is only for real camera footage. Skip it for screen recordings, animation or AI clips.
   - `sfx` lists the sound hits you notice and the moment each one lands on. It stays empty for browser links, which measure pictures only.
   Use `pacing.transitions` (`hard` cuts vs. `animated` slides or fades), `music.cut_on_beat_ratio` (above 0.5 means it cuts on the beat), `pacing.avg_shot_by_third_s` (a faster first third means a fast hook) and `speech.words_per_min` to back up what you see.
6. **Explain it** to the user in plain words, in their language, in this order:
   - one line on what the video is and why it works ("a PR reel that shows the payoff first, then the journey");
   - the hook (first 2-3 s) and the story line from `shots[].role`, with the 2-4 `highlights`;
   - pace, look, captions and sound in 4-6 lines. Avoid jargon such as LUFS: say "loud and punchy, like TikTok" instead;
   - for real footage, how to film it: setup, angles and light from `filming`;
   - what you're unsure about.
   Suggest they keep the story line and tell it with their own moments, not copy the video.
7. **Offer to save it** as a reusable preset: copy it to `../../styles/<name>.json` and tell the user they can now say "edit my clips in <name> style".

## Built-in presets

`../../styles/` has `gym-montage`, `gym-cinematic`, `tiktok-fast`, `vlog`, `cinematic` and `podcast-clip`. They use the same keys, so they can stand in for a reference video.

## Limits to tell the user about

- Colour is measured as averages (brightness, saturation, warm/cool). The match will be close, not an exact grade.
- You can describe a caption font but can't identify it exactly. You'll pick the closest one installed.
