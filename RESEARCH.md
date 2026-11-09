# 3beditor: research and plugin design

Goal: one Claude plugin a customer installs once. They give it a **reference video** ("make it like this") and **their footage**, and get back an edited video in that style. It can also create videos from scratch.

## 1. What already exists (Nov 2026)

| Project | License | What it has | What it lacks |
|---|---|---|---|
| [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) | MIT | 42 stdlib-Python FFmpeg tools, a SKILL.md, an MCP server, and a Claude plugin manifest. Scene and beat detection, contact sheets, captions, loudness, LUTs, FCPXML/EDL export | No way to match a reference style. Claude has to judge everything itself |
| [OpenMontage](https://github.com/calesthio/OpenMontage) | **AGPLv3** | A full agentic pipeline: pacing, scene and keyframe analysis of a reference, approval gates, self-review after render | Heavy (Python + Node + Remotion + many API keys). The AGPL licence makes it risky to fork into a paid product |
| [mcp-video](https://pypi.org/project/mcp-video/) (KyaniteLabs) | open source | MCP server with 80–90 tools, including scene detection and storyboards | Only primitives. No style profile |
| [Remotion skills](https://www.remotion.dev/docs/ai/skills) | Remotion licence | Good at motion graphics and caption code ("create from scratch") | Not an editor of real footage. **Companies above a small headcount need a paid licence**, so check this before pushing it on customers |

**Gap = our product:** none of them measure a reference video's style as numbers, apply those numbers to new footage, and then **re-measure the output to check it matches**. Everything else above can be borrowed as patterns.

## 2. How Claude "watches" a video

Claude cannot take in a video file. It can read **images and text**. So "watching" means turning the video into those:

| Style trait | How it is measured | Tool |
|---|---|---|
| Cut pacing (shot lengths, cuts per minute) | Scene-change detection | `ffmpeg -vf select='gt(scene,0.3)'` or PySceneDetect |
| Cuts on the beat | Beat times compared with cut times | librosa beat tracking |
| Transitions (hard cut, fade, whip) | How the scene score changes across neighbouring frames, plus Claude viewing frames around each cut | ffmpeg + contact sheet |
| Colour look | Mean brightness, saturation and hue, plus a histogram per shot | ffmpeg `signalstats` |
| Captions (position, case, words per line, font feel) | Claude views sampled frames. Caption text comes from the transcript | contact sheet + faster-whisper |
| Framing (punch-in zooms, aspect ratio, b-roll ratio) | ffprobe, plus Claude viewing frames | ffprobe + contact sheet |
| Audio (loudness, music vs voice, tempo) | EBU R128 loudness, BPM | ffmpeg `ebur128`, librosa |
| Hook (first 3 s) and pacing curve | Shot lengths over time | derived from the scene list |

The output is **`style.json`**, a small, editable style profile. Customers can save profiles and reuse them ("my TikTok style").

## 3. Pipeline

```
reference.mp4 ─► analyze ─► style.json ◄─┐
                                         │ diff and fix (max 2 loops)
footage/*    ─► analyze ─► shots + transcript ─► Claude plans edl.json ─► render ─► output.mp4
                                                                                      │
                                                                     re-analyze ──────┘
```

1. **analyze**: one script returns JSON plus a contact-sheet PNG. The same script runs on the reference, the footage and the output.
2. **plan**: Claude writes `edl.json` (the edit decision list: clips, in and out points, captions, colour adjustments, music). This is the customer approval gate: show the storyboard contact sheet before rendering.
3. **render**: FFmpeg only (filter graph built from the EDL). Remotion is optional, only for "create from scratch" and motion graphics.
4. **verify**: re-analyze the output, diff it against `style.json` (for example "avg shot 2.1 s vs target 1.4 s"), and fix. **This loop is the selling point.**

Ideas borrowed from ffmpeg-skill: `--dry-run`, never overwrite inputs, a `doctor` command that checks ffmpeg and Python, and an export to FCPXML/EDL so pro customers can finish in Premiere, Resolve or Final Cut.

## 4. Plugin layout (smallest that does the job)

```
3beditor/
  .claude-plugin/plugin.json
  .claude-plugin/marketplace.json   # customers: /plugin marketplace add <your-repo>
  skills/
    video-style/SKILL.md     # analyze a reference into style.json
    video-edit/SKILL.md      # footage + style.json → edl → render → verify
    video-create/SKILL.md    # from scratch (script → shots → render), optional Remotion
  commands/
    edit-like.md             # /edit-like <reference> <footage folder>, the one-command entry
  scripts/
    analyze.py  render.py  doctor.py
  styles/                    # a few built-in profiles (vlog, tiktok-fast, cinematic, podcast-clip)
```

Dependencies: **FFmpeg + Python 3.10 + faster-whisper (MIT) + librosa (ISC)**. No API keys are needed for the core flow. MCP server: skip it for v1. Skills plus scripts are enough in Claude Code and Claude Desktop. Add MCP only if you target clients that cannot run scripts.

## 5. Making it easy for customers

- One command, `/edit-like ref.mp4 ./clips`, plus plain-language skills ("make my clips look like this video").
- `doctor.py` runs first and gives install steps per OS (winget, brew, apt) when ffmpeg is missing. This is the #1 support issue.
- Built-in style presets, so customers without a reference can still get a result.
- A storyboard preview before the slow render step.

## 6. Risks

- **Reference links (decided):** Claude watches links in a browser with `scripts/watch.js`, like a viewer, with no download. Downloaders (yt-dlp) need TikTok's bot checks bypassed, so they are out. Browser watching gets pictures only (no loudness, beats or speech), and needs the built-in browser or Claude in Chrome. Works on TikTok and YouTube Shorts (tested Nov 2026). Facebook and Instagram are untested.
- **Colour matching** with simple stats (eq/colorbalance) gets close, not exact. Upgrade path: generate a 3D LUT from paired frames.
- **Caption font:** Claude can describe it ("bold sans, yellow, centred, all-caps") but cannot name the exact font. Map descriptions to a bundled set of open fonts.
- **Long footage:** transcription and analysis are slow on CPU. Use proxies (downscale to 360p for analysis).
- **Claude.ai web (cloud sandbox):** whether ffmpeg and audio libraries are available there is unverified. Target Claude Code and Desktop first.

## 7. Suggested MVP order

1. `doctor.py` + `analyze.py` → `style.json` + contact sheet (prove we can "watch").
2. `video-style` skill + 2 presets.
3. `render.py` from `edl.json` (cuts, captions, colour, music, loudness).
4. `video-edit` skill with the verify loop + `/edit-like`.
5. `video-create` and Remotion last.
