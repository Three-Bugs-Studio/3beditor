---
description: Edit your footage to match a reference video's style (or a preset like tiktok-fast)
argument-hint: <reference video, link or preset name> <footage file or folder> [notes, e.g. "30 seconds, use song.mp3"]
---

Use the `video-edit` skill.

- The first argument is the style: a video file or a TikTok/YouTube/Facebook link means watch and analyze it with the `video-style` skill first; a name means use the preset in the plugin's `styles/` folder (gym-montage, gym-cinematic, tiktok-fast, vlog, cinematic, podcast-clip).
- The second argument is the footage: one file, or a folder (use every video and image in it).
- Treat anything after that as the user's notes (length, music, captions on or off).

If an argument is missing, ask for it in one short question.

Arguments: $ARGUMENTS
