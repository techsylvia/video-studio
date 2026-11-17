# Start here

You have the Video-Studio folder open in Claude Code (desktop app → **Code** tab → **This computer**) or in
Codex. No personal footage is needed for setup.

## 1. Paste this setup prompt

```
This folder is my Video-Studio starter kit. Read AGENTS.md and START-HERE.md, then set it up
on this computer. Use this computer's actual paths.

First run ./studio doctor and tell me what you need to install and why. Ask before installing
anything or expanding access. Keep installs inside this project where practical. Use local
transcription and rendering only; don't send my footage to external services.

Then run ./studio smoke-test. If something fails, use the fallbacks in AGENTS.md and report
what actually passed. Ask me once for my brand colours, caption font, caption style and pacing,
and save them in brand/brand.json.

Do not edit my personal footage yet. Finish with the exact path to the test MP4 and a checklist
of what works, what needs my input, and how to start my first edit.
```

## 2. What the AI will ask to install

- **FFmpeg** (cutting and encoding), usually with Homebrew: `brew install ffmpeg`.
  If Homebrew is missing, it will ask you to install it from brew.sh first.
- **A project Python environment** (`.venv`) with Pillow and a local speech-to-text model
  (mlx-whisper on Apple Silicon). The speech model downloads once, then works offline.

Say yes only to what you're comfortable with. Everything stays inside this folder except FFmpeg.

## 3. Your first edit

1. In Photos, select a short talking clip with a complete closing line.
   **File › Export › Export Unmodified Original** → save into `raw/`.
2. Ask: *"Edit the clips I identify in raw/ into a vertical talking reel"* and name the clip,
   or in Claude Code type `/edit-reel IMG_1234`.
3. The AI shows you a cut plan, renders a draft into `exports/` and tells you what to check.
4. Play it with sound. Ask for changes in plain words: *"remove the opening quote, keep my full
   ending, move the diagram away from my face."* Each change saves a new version.
5. Happy with it? In Photos choose **File › Import** and pick the MP4 from `exports/`.

## If something gets stuck

Ask the AI for the failing step, the exact error and the simplest working fallback. A setup is only
done when there is a playable test MP4 you can open.
