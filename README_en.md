# 3beditor: edit videos by talking to Claude

[Tiếng Việt](README.md) · **English**

A free Claude Code plugin that turns your clips into a finished short video for TikTok, Reels or Shorts. Pick a style (or show it a video you like), approve a storyboard, and get an MP4. It edits like a professional: clean hard cuts on the beat, and effects only where the footage or the music gives a reason.

Made with gym and training videos in mind, but it works for any footage. It speaks English and Vietnamese (captions are checked for every Vietnamese letter).

**New here? Read the easy guide: [Playbook](PLAYBOOK.md) · [Hướng dẫn tiếng Việt](PLAYBOOK_vi.md)**

## Install (2 minutes)

1. **FFmpeg 7+** and **Python 3.10+**:

   | System | FFmpeg |
   |---|---|
   | Windows | `winget install Gyan.FFmpeg` |
   | macOS | `brew install ffmpeg` |
   | Ubuntu/Debian | `sudo apt install ffmpeg` |

2. **In Claude Code:**
   ```
   /plugin marketplace add Three-Bugs-Studio/3beditor
   /plugin install 3beditor@3bstudio
   ```
   Restart Claude Code. To update later: `/plugin marketplace update 3bstudio`.

3. *Optional:* captions from speech and beat detection:
   ```bash
   pip install faster-whisper librosa
   ```

Not sure it's set up? Ask Claude "check my 3beditor setup". It runs a check and tells you exactly what's missing.

## Make a video

```
/video ./my-clips
```

Claude walks you through it, and you approve each step before anything slow happens:

1. **A few questions:** where you'll post it, how long, your title, music.
2. **Style:** a gallery of **your own clip in every preset look**, numbered. Or bring your own: a video file, or a TikTok/YouTube link (Claude watches it in its browser, with no download).
3. **Setup card** (optional): font (your own words shown in each font), transitions and fps (24 film, 30 social, 60 smooth).
4. **Storyboard:** one key frame per shot. Reply "OK" or a panel number to change.
5. **Your video:** rendered, measured against the style, and saved next to your clips.

Other ways in:
- `/edit-like https://www.tiktok.com/@someone/video/123 ./clips`: edit your clips in that video's style
- `/edit-like gym-cinematic ./clips`: use a preset directly
- "Plan my gym video before I film it": a shot list, plus prompts for AI video tools
- "Make a 20-second reel from these photos"

**Preset styles:** Gym Montage · Gym Cinematic · TikTok Fast · Vlog · Cinematic · Podcast Clip. Analyse any video and ask Claude to save it as your own style.

## What it can do

- **Cutting:** the best reps, cuts on still moments and on the music's beats, slow motion (real frames from 60 fps footage), fades from black, and reframing to 9:16 / 16:9 / 1:1.
- **Look:** colour grading, from natural to a film look (teal/orange, deep blacks, vignette, grain).
- **Text:** captions in any font, including your own `.ttf`/`.otf` files. Vietnamese is checked letter by letter, so there are no broken fonts. Stroke, shadow and glow; highlighted key words; pop, fade and zoom; word-by-word and karaoke (TikTok "SubText" styles).
- **Transitions:** 15 cinematic and TikTok transitions (whips, zoom punch, flash, glitch, fades, dips…), each chosen per cut, **only where the analysis finds a reason**.
- **Sound:** continuous audio under the cuts, music mixing, five free sound effects (boom, clang, whoosh, riser, glitch) used only where they mean something, and loudness for phones (−14 LUFS, peaks under −1 dBTP).
- **Safe for the apps:** captions stay clear of the TikTok/Reels buttons and caption area.
- **Checks:** every result is measured (pacing, colour, loudness, beat sync, frame-accurate timing) against the chosen style.

Your original files are never changed, and no extra folders are made: only the finished `<name>_3beditor.mp4` is saved next to your clips.

**About music:** for public posts, export without music and add a trending sound inside TikTok, Reels or Shorts, so it stays licensed. Only use a song file you have the rights to.

## How it works (for developers)

| Script | Job |
|---|---|
| `scripts/doctor.py` | checks FFmpeg (7+) and Python, and says how to fix what's missing |
| `scripts/analyze.py` | video → `style.json` (cuts, pacing, colour, loudness, beats, transcript) + a contact sheet. `--target` compares against a style |
| `scripts/watch.js` | runs in Claude's browser on a TikTok/YouTube page: the same style numbers from the frames, no download |
| `scripts/board.py` | picture boards to choose from: style `gallery`, `storyboard`, `transitions` reel, `fonts` |
| `scripts/fx_plan.py` | analyses every cut and suggests a transition only where one is motivated, within an effects budget |
| `scripts/fonts.py` | installed fonts with full Vietnamese support, and missing-letter checks |
| `scripts/render.py` | renders an `edl.json` with FFmpeg: clips, speed, reframing, transitions, grade, captions, music, loudness |

Skills: `video-studio` (the guided flow), `video-edit`, `video-style`, `video-plan`, `video-create`. Design notes are in `RESEARCH.md`.

Only Python's standard library and FFmpeg are needed. Tested on Windows (FFmpeg 9.0) and Linux (FFmpeg 7.1):

```bash
python -m pytest -q tests
```

`mobile/build_zip.py` packages everything as one skill ZIP for the Claude app (experimental: it needs FFmpeg in the app's sandbox).

## Thanks

Sound effects and several editing rules (safe areas, take picking, sound restraint) come from [ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT). The sounds are CC0, see `sfx/CREDITS.md`. The shot-by-shot reference breakdown (story line, hook, how it was filmed) follows ideas from [rea-video](https://github.com/JuneYaooo/rea-video) (Apache-2.0).

## Contributing

Fork it, change it, send a pull request: see [CONTRIBUTING.md](CONTRIBUTING.md). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

Like 3beditor? [Sponsor @DongDuong2001](https://github.com/sponsors/DongDuong2001) to keep it free.

## License

MIT. Free to use, change and share, as long as you keep the copyright notice.
Made by Duong Phu Dong ([@DongDuong2001](https://github.com/DongDuong2001)) at Three Bugs Studio.
