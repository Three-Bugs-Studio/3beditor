---
name: video-studio
description: "The all-in-one video maker: the customer brings their clips, picks a preset style from a gallery of their own footage (or brings a reference video or TikTok/YouTube link for a freestyle look), approves a storyboard, and gets the finished video. Use for any open request like 'make a video from my clips', 'edit my gym video', 'turn this into a reel', '/video', or when unsure which 3beditor skill fits. Vietnamese requests too: 'dựng video', 'làm video từ clip', 'edit video gym', 'làm reel', 'làm video TikTok'."
---

# Video studio

**Language:** speak Vietnamese by default: plain, friendly tiếng Việt with no editing jargon. Switch to English only when the customer writes in English. Files the customer keeps (plans, reports) follow the same rule.

One guided flow. The customer approves four cheap things (style, setup card, plan, storyboard) before anything slow is rendered. Speak plainly, in the customer's language, and keep each check-in short.

Scripts are in `../../scripts/` relative to this skill's base directory. The detailed editing rules live in the `video-edit` skill (its mapping table and gym rules) and the `video-style` skill (references and links). Follow them where this flow points to them.

## 0. Intake

Run `python <scripts>/doctor.py` first; if `ok` is false, give the fix lines and stop.

If the customer has **no footage yet** (or wants an AI-generated video), run the `video-plan` skill first: story, assets and shot list. Come back here once the clips exist, and use their `plan.md` as the plan check.

Ask only what's missing, in one message:
- the clips (files or a folder)
- where it will be posted (TikTok/Reels/Shorts → 9:16, YouTube → 16:9) and roughly how long
- music: their own file, or "add a sound in the app later" (recommended for public posts, since it stays licensed)
- any text: title, name, call to action, and the **font** if they have one (a .ttf/.otf file is fine). For Vietnamese text, check it with `python <scripts>/fonts.py check FONT "their text"`. If letters are missing, suggest the font's "Việt hóa" version or a font from `fonts.py list --vietnamese`

Keep working files out of the customer's folders: use `<temp>/3beditor/<project>` as `<work>`, where `<temp>` is `python -c "import tempfile; print(tempfile.gettempdir())"`. The only file that lands in their folder is the finished video, saved next to their clips as `<name>_3beditor.mp4` (or where they ask), never overwriting a file. Never change their files.

## 1. Style: preset or freestyle

- **Preset.** Run `python <scripts>/board.py gallery <best clip> --out <work>/board`, with `--size 1920x1080` for 16:9. Show `gallery.png`: their own frame in every preset, numbered. Also show the list from `python <scripts>/board.py styles` with each style's name and `best_for`. They pick a number. The preset JSON's `edit` block holds the EDL settings (colour, captions, transition, fades) and its `pacing`/`visual_notes` describe the rhythm.
- **Freestyle.** They upload a video or paste a TikTok/YouTube/Facebook link. Follow the `video-style` skill to make `<work>/ref_style/style.json`, then summarise the look in 3-4 lines and confirm.
- **Saved style.** If they liked a freestyle result, offer to save it into `../../styles/<name>.json` (add `name`, `description`, `best_for` and an `edit` block) so it appears in the gallery next time.

## 2. Setup card: font, transitions, fps, caption motion

Fill in the defaults from the chosen style (its `edit` block and `transition_mix`), then show one short numbered card. The customer changes any line by number and can see every option before choosing:

1. **Font.** Run `python <scripts>/board.py fonts --text "<their title>" --clip <clip> --out <work>/setup` and show `fonts.png`: **their own words** in the best installed fonts that have every letter, heaviest first. They pick a number, name an installed font, or send their own .ttf/.otf (a "Việt hóa" font for Vietnamese). Check a font they name with `python <scripts>/fonts.py check FONT "<all their text>"`. If letters are missing, say which ones and suggest the Việt hóa version or a board font.
2. **Transitions: analyze first, then add only what's motivated.** Professional edits are mostly clean hard cuts, and every effect needs a reason the customer can hear or see. Never sprinkle effects for variety.
   - First build the hard-cut plan (step 4's EDL with no transitions). Then run `python <scripts>/fx_plan.py <work>/edl.json --style <style>`. It measures every cut: same camera angle, real motion direction, the music's biggest energy rise, and scene or time changes. It suggests an effect only where one is motivated, within the style's budget, with a plain reason for each cut.
   - Show the result as a short table: `cut · time · suggestion · reason`. "0 effects" is a good answer for one-angle footage with gentle music. The look then comes from grade, speed and cutting on the beat.
   - If they want to preview the options, run `python <scripts>/board.py transitions --clip <A> --clip2 <B> --out <work>/setup` and send `transitions_reel.mp4` (their own clips, each transition named).
   - If they ask for an effect the analysis didn't suggest, add it, but say briefly why it may look random (e.g. "same camera angle on both sides"). Keep to at most 2 kinds of effect per video.
   - Apply with `fx_plan.py ... --apply <work>/edl_fx.json`. Run it on the hard-cut plan: it gives each transition half a transition from each clip, so its middle stays on the original cut and beat.
3. **FPS.**
   - **24:** film look, for cinematic styles.
   - **30:** the TikTok/Reels/Shorts standard.
   - **60:** extra smooth, for sports and fast motion.

   Check the footage's own fps (`format.fps` from `analyze.py`): 60 out from 30 in adds nothing. For slow motion, 60 fps footage gives real frames; from 30 fps the in-between frames are invented, which can smear on fast moves. Say which applies.
4. **Caption motion:** none, `pop`, `fade` or `zoom`, and reveal `word`, `build` or `karaoke`. Also highlight colour and stroke. Name them by the SubText recipes in the `video-edit` skill's `craft.md`.

Save the card as `<work>/setup.json` and apply it to the EDL (`caption_style`, `transition` and per-clip transitions, `fps`). Wait for OK.

## 3. Plan check

Analyze each clip (`analyze.py CLIP --out <work>/clips/<name>`, with `--transcript` when there's speech) and look at every contact sheet. Then show a short numbered plan:
- the story in one line (e.g. "setup in slow motion → 5 fast reps → slow-mo final rep on the drop")
- length, format, music, and the text on screen
- anything the style does that the footage can't (e.g. black bars only suit landscape footage)

Wait for OK or changes.

## 4. Storyboard check

Write `<work>/edl.json` using the `video-edit` rules: its mapping table, the gym and single-camera rules, beat-locked cuts, and continuous audio. Then run `python <scripts>/board.py storyboard <work>/edl.json --out <work>/board`.

Show `storyboard.png`: one graded, captioned key frame per shot, labelled `n · start-end · speed · transition`. Ask for thumbs up or down **by panel number** ("swap 3 for a later rep", "make 7 longer"). Change only those panels and re-show the board until they approve.

## 5. Build

Render with `python <scripts>/render.py <work>/edl.json`, then check:
- `analyze.py <out> --out <work>/final --target <style.json> --cuts-from <work>/edl.json`, with at most 2 fix rounds, following `video-edit` step 6
- frames on both sides of every cut: same pose, nothing jumping
- with music: cuts on its beats, and the payoff on the drop

## 6. Delivery

Export to the folder they named, without overwriting existing files: add `_v2`, `_v3` and so on. Then report:
- the file path and length
- a short target-vs-actual table
- what was intentionally different, and anything not yet supported (camera stabilisation, auto speed ramps)
- 1-2 offered tweaks

If the music isn't licensed for posting, say so plainly.
