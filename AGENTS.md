# Video-Studio — instructions for the AI editor

This folder is a local video editor for a content creator. You (Claude Code, Codex or another
coding agent) run the scripts here to turn raw talking clips and B-roll into vertical reels with
the creator's voice, captions and graphics. The creator is usually not technical: keep replies
short and friendly, do the work for them, and explain choices in plain words.

## Folders

| Folder | What goes there |
|---|---|
| `raw/` | Source copies exported from Photos. **Read-only for you: never edit, move or overwrite.** |
| `reels/<name>/` | Transcripts, cut lists, check frames and edit records for one reel |
| `exports/` | Rendered MP4 drafts and finals. Renders never overwrite; new versions get `_v2`, `_v3` |
| `references/` | Example reels, approved screenshots, logos, music the creator can use |
| `brand/` | `brand.json` (colours, fonts, caption style, pacing) and `fonts/` |
| `scripts/` | The toolkit. Run it through `./studio` |

## Commands

```
./studio doctor                         check the computer (installs nothing)
./studio setup                          create .venv, install Pillow + local speech-to-text
./studio smoke-test                     render test + speech test, no personal footage
./studio probe raw/CLIP.MOV             orientation, size, fps, colour (SDR/HDR), audio
./studio transcribe raw/CLIP.MOV --reel NAME
./studio autocut raw/A.MOV raw/B.MOV --reel NAME    first-pass cut list without long pauses
./studio render reels/NAME/cutlist.json [--draft]  render + automatic checks
./studio compare raw/CLIP.MOV exports/NAME.mp4      side-by-side colour check
```

If `./studio` says "permission denied" (it can happen after unzipping a download), run
`chmod +x studio scripts/setup.sh` once, or call it as `bash studio ...`.

The cut list format is shown in `scripts/cutlist.example.json`: clips with `source`, `in`, `out`
(seconds on the source timeline), optional `graphics` (`headline` or `image`, with `start`/`end`
on the output timeline), optional `voiceover` (`file`, `in`, `clip_audio_volume`) when B-roll is
cut to a recording, optional `music` (`file`, `volume`) and `audio.cleanup`. Captions come from the transcripts
in `reels/<name>/` automatically.

## Safety rules

- Ask before installing anything or expanding access. Explain what and why first.
  Keep installs inside this project (`.venv`) where practical.
- Everything stays on this computer: local transcription and rendering only. Never send the
  creator's footage or audio to an external transcription, rendering or AI service.
- Never overwrite or modify files in `raw/`. Keep the original and every edit decision
  (the renderer saves the cut list used next to each version).
- Do not publish, post or upload anything. Do not open or inspect the Photos library database.
- Use only screenshots, music and fonts the creator supplied or approved.

## Brand settings

Read `brand/brand.json` before editing. If `"configured": false`, ask the creator once for their
colours, caption font, caption style and pacing, save the answers there, and set it to `true`.
After that, reuse them without asking again.

## Editing workflow

When the creator asks for a reel (or types `/edit-reel`), follow `prompts/edit-reel.md`.
In short: probe and transcribe every take, review all takes before cutting, group by topic,
tell duplicates, false starts and continuations apart, show a cut plan, then render a draft,
check it, and report. Never publish.

## Style rules (the creator's defaults)

**Voice stays in the edit.** Keep speech audible unless the brief explicitly asks for silence.
Shorten dead air without chopping breaths or words. Use gentle cleanup (`audio.cleanup`) only
when it improves clarity; compare with the source and avoid raising room noise. Keep music low
under narration and use tracks the creator can use.

**Use motion to explain.** Try a process diagram, draw-on arrow, floating screenshot card or
short editorial headline where it adds meaning. Use real screenshots supplied or approved for
the project. Keep overlays clear of faces and platform controls (top ~12% and bottom ~25% of
the frame). If a graphic won't fit, simplify or omit it.

**Protect skin tone and source footage.** No automatic warming, cooling, whitening or beauty
treatment. Face-only smoothing is opt-in and should be subtle. Name any substitute honestly.
Check the original against the render (`./studio compare`), especially for phone HDR. HDR
sources export as HDR; only convert to SDR (`--tonemap-sdr`) when the creator asks.

## Checking a render

`./studio render` verifies size, duration, audio and a full decode, and saves start/middle/end
frames in `reels/<name>/checks/`. Then look at those frames yourself (captions readable? graphics
off the face? colour like the source?), check the transcript of the first and last lines, and
tell the creator what to check by eye and ear. A cut waiting for narration is still a draft.

## Optional extras (only after the core works, and only with the creator's OK)

- Face-tracked effects: Vibha Ramprakash's `/effects` skill
  (github.com/Vibha-Ramprakash/claude-video-effects, MIT). Review it before installing.
- Reference videos: Brad Automates' `/watch` (github.com/bradautomates/claude-video, MIT) and
  yt-dlp, for videos the creator is authorised to use. For personal footage keep transcription
  local; do not use its cloud options.
- HTML motion graphics: Node + HyperFrames, after a local render test. If browser rendering is
  blocked, keep captions and graphics on the working FFmpeg/Pillow path.
