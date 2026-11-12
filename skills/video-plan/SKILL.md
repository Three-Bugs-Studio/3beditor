---
name: video-plan
description: "Plan a video before filming or generating it: story beats, a shot list with camera angles, and a reference asset set (characters, outfits, locations from 3 angles) with prompts for AI image/video tools (Nano Banana, Seedream/Seedance, GPT image, Topview), or a shoot plan for filming on a phone. Use when the customer has no footage yet, says 'plan my video', 'what should I film', 'help me make an AI video', 'storyboard my idea', or before 'generate video' in any AI tool. Vietnamese requests too: 'lên kế hoạch video', 'nên quay gì', 'làm video AI', 'lên kịch bản phân cảnh'."
---

# Video plan

**Language:** speak Vietnamese by default: plain, friendly tiếng Việt with no editing jargon. Switch to English only when the customer writes in English. Files the customer keeps (plans, reports) follow the same rule.

**The idea:** consistent characters, locations and camera angles come from preparation, not from the AI model or the camera. Don't press "generate" (or record) until these 3 steps are approved. A mistake caught here costs a minute; caught after generating or filming, it costs a redo.

Work in `3beditor_work/plan/` (or `plan/` in the current folder). Write everything there as files the customer keeps. Speak plainly in the customer's language.

## Step 1. Story and storyboard (the most important step, don't rush it)

Ask only what's missing: the goal, the platform (TikTok/Reels/Shorts → 9:16, YouTube → 16:9), length, who the main character is, and the feeling at the end.

Write `plan.md`:
- **Character:** personality and state of mind in 2-3 lines. These decide where they live, what they wear and how the camera sees them.
- **Beats table:** `# | time | what happens | emotion | shot size and angle | sound`. One row every 1.5-4 s (short-form). Keep the first 2 s a hook, put silence or a breath before the payoff, and make the payoff the loudest moment.
- **Contrast through the camera:** when the story has two sides (before/after, two life paths, struggle/victory), give each side its own angle, light and colour, so the viewer feels the difference without words.
- **Who checks what:** the AI will produce the images and clips, and the customer (with you) checks every one against this plan.

**From a reference video:** if the customer has one, run `video-style` first. Start the beats table from its `visual_notes.shots` (same roles and timing, the customer's own content) and the shoot plan from `visual_notes.filming`.

Show the beats table and wait for approval. Change only the rows the customer names.

## Step 2. Reference asset set (the "visual guide")

Everything later is generated from these images, so fix errors here.

Write `assets.md` with one block per asset: what it is, why it's in the story, and a ready-to-paste prompt.
- **Character sheet:** front, 3/4 and side, plus a full-body and a face close-up. If the character appears at different ages or in different lives, keep the same face features (eyes, nose, hair colour, skin) in every version and change only age, outfit and styling. Say so in every prompt.
- **Outfits and props** that show the character's life: what a gym member, an office worker or an artist would actually wear and carry. The AI can suggest options from the plan, but the customer decides the taste.
- **Locations from at least 3 angles each** (wide establishing, reverse, detail corner), so the space is clear and stays the same in every shot. Fix a wrong room now.
- **Tool tips (as of late 2026, check before relying on them):** for character and asset images, Nano Banana Pro gives the strongest consistency. Nano Banana 2.x or Seedream are cheaper and good. GPT image models work well for locations and backgrounds.

Keep every prompt self-contained: subject, look, lens and shot size, light, background, aspect ratio, and "same character as reference image N" where it applies.

## Step 3. Shots: decide the camera like a director

Write `shots.json`, one object per beat:
```json
{"beat": 3, "duration_s": 2.5, "shot": "medium, low angle", "lens": "35mm",
 "camera_move": "slow push-in", "start_frame": "assets: girl_adult_artist, apartment_B_wide",
 "action": "...", "prompt": "...", "transition_in": "cut on beat"}
```
- **Control the camera.** Don't leave the angle to chance. If the AI tool has a 3D scene or camera builder (Topview's 3D builder, for example), describe the set from `plan.md` (or have an assistant write that description), let it build the space, then place and keyframe the camera. Preset camera paths are fine for quick filler shots; story shots deserve a hand-set path.
- **Copying a reference shot's camera move:** use the tool's depth/motion extraction on the reference clip and apply your character and location. Warn the customer that small details from the reference can leak into the result.
- **Fixing a nearly perfect shot:** if the action is right but the background or a detail is wrong, use the tool's clip edit or swap (e.g. Seedance clip edit) to replace just that element. Don't regenerate the whole shot.
- **Filming it yourself (gym and real footage),** add a shoot plan to `plan.md`:
  - **Tripod or propped phone, locked off.** Handheld drift makes jump cuts look jumpy.
  - **60 fps** for anything that will be slow motion (30 fps slow motion needs invented frames).
  - **3 angles per exercise:** wide (whole body and bar), medium (from the side), detail (grip, chalk, plates, face on the last rep).
  - Start recording 2 s before the set and stop 2 s after.
  - Same light and same spot for every set, unless the contrast is intentional.

Show the shot list as a table, wait for approval, then hand over: "generate or film these, then run `/video` with the clips and I'll edit them to the plan." The `video-studio` flow takes over from there, and `plan.md` becomes its storyboard.

## Delivery checklist (before the customer generates or films)

- every beat has a shot, every shot names its assets, every prompt states the aspect ratio
- the character's face features are written identically in every character prompt
- every location has 3 angles
- the hook is 2 s or less, and the payoff has a breath before it
