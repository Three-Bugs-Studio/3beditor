---
name: 3beditor
description: "Make a finished short video from the customer's clips, right in the Claude app (also on a phone): pick a style, approve a storyboard, get an MP4 to post on TikTok, Reels or Shorts. Use for 'edit my gym video', 'make a reel from these clips', 'turn this into a TikTok', or any video upload with an editing request."
---

# 3beditor (Claude app and phone)

The customer is probably on a **phone**: keep every message short, ask one thing at a time, offer numbered choices, and show pictures (boards) rather than long text. Speak their language (Vietnamese or English).

Everything this skill needs is inside its folder: `scripts/`, `styles/` and `references/`. Run the scripts with `python3 <this folder>/scripts/...`. Uploaded files are in `/mnt/user-data/uploads/`. Put every result the customer should download in `/mnt/user-data/outputs/`. Work in `/tmp/3be/`.

## 0. Check the room (always first, a few seconds)

Run `python3 scripts/doctor.py`. If `ok` is false (FFmpeg missing), tell the customer plainly that video editing isn't available in this app environment yet, and stop. Then check the uploads folder for videos (`.mp4 .mov .m4v .webm`). If there are none, ask them to attach their clips with the + button. Links can't be watched here, so ask for the video file of a reference instead.

## 1. Quick start (the phone flow, 3 taps)

1. **Style.** Run `python3 scripts/board.py gallery <best clip> --out /tmp/3be/board` and show `gallery.png` (their own frame in every preset, numbered), plus the one-line list from `board.py styles`. They reply with a number.
2. **Text and length.** Ask one short question: "Title on the video? (or skip) · Length: 15 / 30 / 60 s?"
3. **Storyboard.** Build the edit (rules in `references/edit.md`), then run `python3 scripts/board.py storyboard /tmp/3be/edl.json --out /tmp/3be/board` and show `storyboard.png`. "Reply OK, or a panel number to change."

Then render, check and deliver (step 3). Defaults come from the chosen style: font, transitions, fps and caption motion. Offer the **setup card** (step 2) only if they ask to customise ("đổi font", "change transition", "60fps").

## 2. Setup card (only when asked)

- **Font:** `board.py fonts --text "<their title>" --clip <clip> --out /tmp/3be/setup` shows their words in each font that has every letter. Pick by number.
- **Transitions:** analyze first with `python3 scripts/fx_plan.py /tmp/3be/edl.json --style <style>` and show the cut-by-cut table with its reasons. Mostly hard cuts; effects only where motivated (`references/craft.md`).
- **FPS:** 24 film, 30 social, 60 smooth (only matters with 60 fps footage).
- **Caption motion:** pop, fade or zoom, and word, build or karaoke reveal.

## 3. Render, check, deliver

1. `python3 scripts/render.py /tmp/3be/edl.json` (use `--preview` first if the clip is long, since the app's time is limited).
2. `python3 scripts/analyze.py <out> --out /tmp/3be/final --target <style.json> --cuts-from /tmp/3be/edl.json`, with at most 1 fix round.
3. Copy the MP4 to `/mnt/user-data/outputs/` with a clear name (e.g. `back_day_reel.mp4`) and give the download link.
4. Two lines only: what was done, plus one offer ("faster cuts?", "change the title?"). Add the music note: post without music and add a trending sound inside TikTok/Reels so it stays licensed.

## Limits to say when they matter

- Long or 4K clips may hit the app's time limit. Suggest clips under about 1 minute each, or trimming first.
- There's no camera stabilisation, and links can't be watched in the app (send the file instead).
- Keep edits clean: mostly hard cuts, effects only where the footage or music gives a reason.
