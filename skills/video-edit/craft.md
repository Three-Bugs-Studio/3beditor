# Editing craft → 3beditor

The basics every editor learns in Premiere Pro and After Effects (QuạHD's beginner Premiere series and After Effects #1), mapped to what our engine does. Use it to explain choices to customers in editor language, and to say honestly what isn't supported yet.

| Editor technique | What it's for | In 3beditor |
|---|---|---|
| **Project and sequence settings** (Full HD, 30 fps, square pixels) | every clip conforms to one frame size and rate | EDL `size` + `fps`. Every clip is scaled, cropped and conformed. Use 1080×1920 for TikTok/Reels/Shorts and 1920×1080 for YouTube |
| **Cut and trim on the timeline** | keep the best part of each clip | `clips[].in/out`. Cut on still moments, and with music cut on its beats (see the gym rules in SKILL.md) |
| **Layers** (top layer covers lower ones) | titles and logos over footage | captions sit above the footage. **Image or logo layers aren't supported yet**, so use a `color:` card or caption text instead |
| **Unlink video and audio** | keep the sound running under a picture cut | `mute: true` on clips plus the source as `music`, i.e. one continuous audio bed |
| **Speed up / slow down** | slow motion on the key moment, fast-forward the boring part | `clips[].speed` (0.25–4). Slow motion invents in-between frames, which looks best from 60 fps footage |
| **Volume** | balance music against voice and ambience | `music.volume`. Pre-mix several beds into one WAV (e.g. ambience at 15%). There's no per-clip volume yet |
| **Transitions** (cross dissolve, dip to black, TikTok whips) | soften a scene change, mark a time jump, or hit a beat | 16-transition library: `cut`, cinematic (`fade`, `dip_black`, `dip_white`, `blur`, `fade_grays`, `smooth_left`, `circle_open`) and TikTok (`whip_left/right/up/down`, `zoom_punch`, `flash`, `glitch`, `swipe_up`). Set a default `transition`, override per clip, preview with `board.py transitions --clip ...`. Plus `fade_in`/`fade_out` from black |
| **Sequence frame rate** | the motion feel | `fps`: 24 film, 30 social, 60 smooth. Slow motion from 60 fps footage uses real frames |
| **Effect Controls keyframes** (scale and position over time) | slow push-in, Ken Burns, pop-in | **only static** `zoom` for now (punch-in per clip). Animated push-in isn't supported yet |
| **Effects** (Lumetri basic correction, then a creative look) | fix exposure first, then give the video a mood | `color`: brightness, contrast, saturation and warmth first, then `teal_orange`, `crush`, `vignette` and `grain` for the look |
| **Text tool, font, stroke, drop shadow** | readable titles | `caption_style`: `font` (installed family) or `font_file` (any .ttf/.otf, e.g. a Việt hóa font), `outline` (stroke px), `shadow`, `blur` (glow), `spacing`, `italic`, `box`. Keep text out of faces: top for titles, centre for big words |
| **Vietnamese fonts ("Lỗi Font Chữ")** | most display fonts are English-only, so ạ ế ữ break and apps silently swap fonts | the render **stops** and names the missing letters. `python fonts.py list --vietnamese` shows the installed fonts that work, and `fonts.py check FONT "text"` checks one. Fix: use the font's "Việt hóa" version (search "<font name> Việt hóa"), passed as `font_file` |
| **Masks, PSD/AI layer animation** (logo flying in) | branded intros and outros | not supported. Make it in a motion tool (or with the Remotion skills) and add the MP4 as a clip |
| **Render / export** | the final file | `render.py` writes H.264 + AAC at −14 LUFS. `--preview` gives a fast 1/3-size check before the full render |

## Rules of thumb these lessons share

1. **Organise first.** Keep one working folder per project (we use `<temp>/3beditor/<project>`, outside the customer's folders), so nothing goes missing.
2. **Learn by turning one knob at a time.** When a look is off, change one `color` value, re-preview and compare. Don't change five at once.
3. **Correction before creativity.** Get exposure and white balance right (brightness, warmth), then add the stylised look.
4. **Sound carries the cut.** A cut feels smooth when the audio keeps flowing under it and the cut lands on a beat.

## SubText caption recipes (the VietCong666 style, QuạHD lesson 4)

Short-form captions that follow the speech. Get word times from `analyze.py CLIP --transcript` (`speech.words`) and put them in each caption's `words`.

| Form | Recipe |
|---|---|
| 1. Basic, key words coloured | white text, black `outline` 8-10, `highlight: ["key", "words"]`, `highlight_color` red `#FF3B30` or yellow `#FFD400` |
| 2. Word by word, left to right | `reveal: "word"` (+ `animation: "pop"`). The layout stays fixed and each word appears as it's spoken |
| 3. Big text in the middle | `position: "center"`, `size` 90-120, one short line per caption |
| 4. Growing from the centre | `reveal: "build"`. The line grows and re-centres word by word |
| 5. Meme PNGs popping in | not supported (image layers) |
| 6. Zoom text | `animation: "zoom"` (slow grow over the line) or `"pop"` (quick punch) |
| TikTok karaoke | `reveal: "karaoke"`: the whole line shows and the spoken word lights up in `highlight_color` |

Readable on a phone: 2-4 words per caption, at least 70 px at 1080×1920, stroke 6 or more over busy footage, and never more than 2 lines.

## Effects with restraint (what separates a clean, professional edit)

1. **Hard cut is the default.** Most cuts in good edits are invisible hard cuts on a still moment or a beat.
2. **Every effect has a reason the viewer can feel:**
   - a hit transition (flash, zoom punch) on the music's real drop;
   - a whip that continues motion already in the shot;
   - a fade or dip to mark a new place or a jump in time;
   - slow motion on the one moment that matters.
3. **Never on a same-angle cut.** Rep-to-rep from one camera, an effect looks random. Match the pose and cut hard.
4. **Budget:** about one effect per 4-6 cuts, at most two kinds per video, and stay inside one family (TikTok hits or cinematic soft, not both).
5. **Analyze, then choose:** `fx_plan.py` measures each cut and explains its suggestion. Show that to the customer instead of a menu of effects.
6. **Numbers from real top reels** (ghost-editor's study of 6 top reels): 113 of 119 transitions were hard cuts, the median shot was about 3 s, and there were 0.4-0.9 audible sound effects per 10 s.

## Sound effects (`sfx` in the EDL)

Built-in CC0 sounds: `boom`, `clang`, `whoosh`, `riser`, `glitch` (`sfx/CREDITS.md`). They follow the same restraint as transitions:

- **Only with a reason:** `boom` on the PR rep or the final reveal, `clang` when plates or a bar actually hit the floor, `whoosh` or `glitch` only under a whip or glitch transition (starting about 0.15 s before the cut), `riser` for the 2 s before the heaviest set.
- **At most about one per 10 s,** never the same sound twice in a video, and none at all is a fine answer.
- **Never on top of a spoken word.** Put it in a pause (check `speech.words`).
- **Level:** `volume_db` -8 for `boom` and `clang`, -12 for `whoosh` and `glitch`, -14 for `riser`. The render's loudness pass levels the whole mix, so never raise the final volume to make a sound louder; lower the music instead.

## Lessons borrowed from ghost-editor

- **Talking clips (coach tips, PR stories):** transcribe everything and choose from the words, never by scrubbing. Of several tries at one sentence, keep the fluent, later one. Cut each take from 0.10-0.15 s before its first word to 0.20-0.30 s after its last, and trim pauses over 0.8 s.
- **Between two takes of the same sentence from one camera,** hide the jump with a hard cut plus a small zoom change (1.0 → 1.15), not a dissolve. At most about three punch-ins per video.
- **Text stays out of the app's buttons:** the render keeps bottom captions above TikTok's caption area and away from the right-hand button column. Keep big titles near the top or centre, never over the face.
- **The loop point:** TikTok and Reels loop the video. A `fade_out` to black flashes on every loop, so leave it out for short looping reels unless a dark ending is the point.
- **Check true peak:** `analyze.py --target` also fails if the true peak is above -1 dBTP, which clips after the app re-encodes the upload.
