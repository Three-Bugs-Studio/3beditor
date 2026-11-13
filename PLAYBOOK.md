# 3beditor playbook

**English** · [Tiếng Việt](PLAYBOOK_vi.md)

A simple guide to making your first video. No editing experience needed: you talk to Claude, and it does the editing.

---

## On your phone (no computer needed)

Nothing is installed on the phone and no folders are made. Everything runs inside the Claude app, and you only download the finished video.

1. **Add the skill (once, on a computer or in a browser):** download `3beditor-skill.zip` from the [Releases](https://github.com/Three-Bugs-Studio/3beditor/releases/latest) page. Open [claude.ai](https://claude.ai) → **Settings** → **Customize** → **Skills** → **+ Add** → **Upload skill**, and pick the file.
2. **On your phone:** open the Claude app, tap **+** to send your clips, and type `edit my gym video from these clips`.
3. Pick a style by number, approve the storyboard, and download the video.

Note: the phone version is still experimental. Keep clips short (under about 1 minute each). The app can't watch TikTok links, so send the video file instead.

---

## 1. Set it up on a computer (one time, about 5 minutes)

You need **Claude Code** ([get it here](https://claude.com/claude-code)) on a computer.

**Step 1. Install the two free tools 3beditor uses.** Open the Terminal (on Windows: press the Windows key, type `Terminal`, press Enter) and paste the line for your computer:

| Computer | Paste this |
|---|---|
| Windows | `winget install Gyan.FFmpeg Python.Python.3.12` |
| Mac | `brew install ffmpeg python` |

Close the Terminal and open it again when it finishes.

**Step 2. Add 3beditor to Claude Code.** In Claude Code, type these two lines, one at a time:

```
/plugin marketplace add Three-Bugs-Studio/3beditor
```
```
/plugin install 3beditor@3bstudio
```

Restart Claude Code.

**Step 3. Check it works.** Type: `check my 3beditor setup`. Claude tells you if anything is missing and how to fix it.

---

## 2. Make your first video

1. Put your clips in one folder, for example `D:\gym-clips`.
2. In Claude Code, type:
   ```
   /video D:\gym-clips
   ```
3. Answer Claude's few questions: where you'll post it (TikTok, Reels, YouTube), how long, any title text.
4. **Pick a look.** Claude shows your own clip in every style, numbered. Reply with a number.
5. **Check the storyboard.** You see one picture per shot. Reply `OK`, or a number to change that shot.
6. Wait a minute or two. Your video is saved next to your clips as `<name>_3beditor.mp4`. No extra folders are made.

Your original clips are never changed.

---

## 3. Things you can say

You can talk to Claude in plain words, in English or Vietnamese:

| You want | Say |
|---|---|
| A video from your clips | `make a 30-second TikTok from D:\gym-clips` |
| The look of a video you like | `edit my clips like this https://www.tiktok.com/@someone/video/123` |
| A ready-made look | `/edit-like gym-cinematic D:\gym-clips` |
| A plan before you film | `plan my gym video before I film it` |
| A video from photos | `make a 20-second reel from these photos` |
| Small changes | `make the start faster`, `bigger captions`, `less music`, `no effects` |
| Keep a look for next time | `save this style as my-style` |

**Ready-made looks:** Gym Montage · Gym Cinematic · TikTok Fast · Vlog · Cinematic · Podcast Clip.

---

## 4. Filming tips for gym videos

- **Prop your phone or use a tripod.** A steady shot looks professional.
- **Film at 60 fps** if you want slow motion on the big rep.
- **Film from 2-3 angles:** the whole body, the side, and a close-up (grip, chalk, face on the last rep).
- **Start recording 2 seconds before the set, stop 2 seconds after.**
- **Same spot and same light** for every set.

---

## 5. Before you post

- **Music:** save the video without music, then add a trending sound inside TikTok, Reels or Shorts. It stays licensed there and helps your video get seen. Only use your own song file if you have the rights to it.
- Captions are already placed clear of the app's buttons.
- Sound is already set to the right loudness for phones.

---

## 6. If something goes wrong

| Problem | Fix |
|---|---|
| Claude says FFmpeg or Python is missing | Do step 1 again, then close and reopen the Terminal and Claude Code |
| `/video` isn't found | Do step 2 again and restart Claude Code |
| A TikTok link won't play | Sign in to TikTok in Claude's browser, or send the video file instead |
| Vietnamese letters look broken | Pick another font from Claude's list, or a "Việt hóa" font |
| You don't like the result | Just say what to change: `faster`, `warmer colour`, `remove shot 3` |

**Get the newest version:** type `/plugin marketplace update 3bstudio`, then restart Claude Code.

---

## Need help?

Ask a question or report a problem on [GitHub Issues](https://github.com/Three-Bugs-Studio/3beditor/issues).

3beditor is free. If it helps you, you can [support the maker](https://github.com/sponsors/DongDuong2001).
