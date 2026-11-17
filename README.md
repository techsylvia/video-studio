# Video-Studio

**Your own AI video editor, running on your Mac.** Turn raw talking clips and B-roll into vertical
reels with your voice, captions and graphics. Set it up once, then edit by asking for what you want
in Claude Code or Codex.

Made by Sylvia ([@sylviadonchev](https://instagram.com/sylviadonchev)) for creators and busy mums
who do everything themselves.

- **Private by design.** Transcription and rendering happen on your computer. Your footage is never
  uploaded to a transcription or rendering service, and never committed to GitHub.
- **Works with Claude Code and Codex.** Rules live in `AGENTS.md`; Claude Code reads them through
  `CLAUDE.md`. Claude Code users also get a one-word shortcut: `/edit-reel`.
- **Safe with your originals.** Files in `raw/` are never changed, and every render is saved as a new
  version (`_v2`, `_v3` ...) with the cut list that made it.

## Get started (Mac)

1. **Download this kit.** On this page click the green **Code** button → **Download ZIP**. Unzip it,
   rename the folder to `Video-Studio` and put it somewhere you keep projects.
2. **Open it in your AI editor.**
   - *Claude Code:* open the Claude desktop app → **Code** tab → **Local** → **Select folder** →
     `Video-Studio`. Use **Manual** permission mode for setup so Claude asks before every command.
     Needs a paid Claude plan (Pro, Max, Team or Enterprise).
   - *Codex:* open the Codex app and select the `Video-Studio` folder.
3. **Paste the setup prompt** from [`START-HERE.md`](START-HERE.md) (also in the PDF guides:
   [Claude Code](guides/Build-Your-AI-Video-Editor-in-Claude-Code.pdf) ·
   [Codex](guides/Build-Your-AI-Video-Editor-in-Codex.pdf)). The AI checks your Mac, asks
   before installing anything (FFmpeg, a small Python environment, a local speech model), runs a
   test reel and tells you what works.
4. **Make your first reel.** Export a clip from Photos (File › Export › Export Unmodified Original)
   into `raw/`, then ask for an edit, or in Claude Code type `/edit-reel` and the clip name.

## What's inside

| Path | What it does |
|---|---|
| `AGENTS.md` | The editor's rules: safety, workflow, your style defaults |
| `CLAUDE.md` | Loads `AGENTS.md` for Claude Code, plus Claude-specific notes |
| `.claude/skills/edit-reel/` | The `/edit-reel` skill for Claude Code |
| `prompts/edit-reel.md` | The full edit brief (used by both tools) |
| `brand/brand.json` | Your colours, fonts, caption style and pacing (the AI asks once, then saves) |
| `studio` | One launcher for every action (`./studio help`) |
| `guides/` | The illustrated setup guides as PDFs (Claude Code and Codex) |
| `scripts/` | doctor, setup, probe, transcribe, autocut, render, compare, smoke-test |
| `raw/` `reels/` `exports/` `references/` | Your footage, edit records, renders and reference files (kept off GitHub) |

```
./studio doctor          check your Mac (installs nothing)
./studio setup           create .venv + install Pillow and local speech-to-text
./studio smoke-test      render test + speech test, no personal footage
./studio transcribe raw/CLIP.MOV --reel NAME
./studio autocut raw/A.MOV raw/B.MOV --reel NAME
./studio render reels/NAME/cutlist.json [--draft]
./studio compare raw/CLIP.MOV exports/NAME.mp4
```

**Under the hood:** FFmpeg for cutting and encoding; mlx-whisper on Apple Silicon (faster-whisper
on other machines) for word-level captions; Pillow for captions, headlines and screenshot cards.
SDR exports are 1080×1920 H.264 + AAC. iPhone HDR footage stays HDR (10-bit HEVC) unless you ask
for SDR.

## Optional extras

Only after the core editor works, and only if you want them:

- **Face-tracked effects** — [`/effects`](https://github.com/Vibha-Ramprakash/claude-video-effects)
  by Vibha Ramprakash (MIT). Built for Claude Code; review it before installing.
- **Reference videos** — [`/watch`](https://github.com/bradautomates/claude-video) by Brad Automates
  (MIT), plus yt-dlp, for videos you're authorised to use. Keep its transcription local for your own
  footage.
- **HTML motion graphics** — Node + HyperFrames, after a local render test.

## Licence

MIT — see [LICENSE](LICENSE). The optional extras above have their own licences.
