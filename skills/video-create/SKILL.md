---
name: video-create
description: "Create a short video from scratch, with no footage or only a few photos: script, text cards, images, captions and music, rendered to 9:16, 16:9 or 1:1. Use for 'make a video about X', 'turn these photos into a reel', 'make a promo/announcement video', 'slideshow with music'. Vietnamese requests too: 'làm video về X', 'làm reel từ ảnh', 'làm video quảng cáo', 'slideshow có nhạc'."
---

# Video create

**Language:** speak Vietnamese by default: plain, friendly tiếng Việt with no editing jargon. Switch to English only when the customer writes in English. Files the customer keeps (plans, reports) follow the same rule.

Brief → script → shot list → `edl.json` → preview → render. Uses the same scripts as `video-edit` (`../../scripts/`, relative to this skill's base directory).

## Steps

1. **Check the machine.** Run `python <scripts>/doctor.py`.
2. **Brief.** Ask only what's missing: platform (sets the aspect ratio), length, message, any photos, clips, logo or music, and a style (preset or reference video, as in `video-style`).
3. **Script.** Write a script of 1 line per shot. Keep the first line a hook of 2 seconds or less. Show it to the user and adjust.
4. **Shot list → `edl.json`:**
   - User photos → `{"src": "photo.jpg", "duration": d}`. They are cover-cropped; add `zoom: 1.1` for some movement.
   - No visual → `{"src": "color:#101010", "duration": d}`, with the line as a caption on top.
   - Script lines → `captions`, timed to each shot. Large, centred text works for text-only cards (`caption_style.position: "center"`, `size` 90–120).
   - Music → `music`, with `loudness_lufs: -14`.
   - Take pacing, colour and caption look from the chosen style, the same way as in `video-edit`.
5. **Preview, OK, render, check.** Same as steps 5 and 6 of `video-edit`.

## When to go further

The renderer does cuts, cards, captions, colour and music. For animated motion graphics (moving text, charts, logo animations), check whether the Remotion skills are installed and Node.js is available. If they are, build that part with them and add the rendered MP4 as a clip in `edl.json`. Note that Remotion needs a paid licence for larger companies. Otherwise, say plainly that animated graphics aren't supported yet.
