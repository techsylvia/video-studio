"""./studio transcribe FILE [--reel NAME] — local speech-to-text with word timestamps.

Writes reels/<reel>/<clip>.transcript.json (words + segments on the SOURCE timeline),
plus .srt and .txt next to it. Audio never leaves this computer.
Backends: mlx-whisper on Apple Silicon, faster-whisper (CPU int8) everywhere else.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import tempfile
from pathlib import Path

from common import REELS, die, resolve, run, tool

MLX_DEFAULT = "mlx-community/whisper-large-v3-turbo"
FASTER_DEFAULT = "small"


def available_backend() -> str | None:
    has = lambda m: importlib.util.find_spec(m) is not None  # noqa: E731
    if platform.system() == "Darwin" and platform.machine() == "arm64" and has("mlx_whisper"):
        return "mlx"
    if has("faster_whisper"):
        return "faster"
    if has("mlx_whisper"):
        return "mlx"
    return None


def pick_backend(requested: str | None) -> str:
    backend = requested or available_backend()
    if not backend:
        die("No speech-to-text backend installed. Run ./studio setup (after approving the install).")
    return backend


def transcribe_audio(wav: Path, backend: str, model: str | None, language: str | None) -> dict:
    words, segments = [], []
    if backend == "mlx":
        import mlx_whisper  # type: ignore
        model = model or MLX_DEFAULT
        result = mlx_whisper.transcribe(str(wav), path_or_hf_repo=model,
                                        word_timestamps=True, language=language)
        for seg in result.get("segments", []):
            segments.append({"start": float(seg["start"]), "end": float(seg["end"]),
                             "text": seg["text"].strip()})
            for w in seg.get("words", []) or []:
                words.append({"start": float(w["start"]), "end": float(w["end"]),
                              "word": w["word"].strip(), "p": round(float(w.get("probability", 0)), 3)})
        lang = result.get("language")
    elif backend == "faster":
        from faster_whisper import WhisperModel  # type: ignore
        model = model or FASTER_DEFAULT
        fw = WhisperModel(model, device="cpu", compute_type="int8")
        segs, info = fw.transcribe(str(wav), word_timestamps=True, language=language)
        for seg in segs:
            segments.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
            for w in seg.words or []:
                words.append({"start": float(w.start), "end": float(w.end),
                              "word": w.word.strip(), "p": round(float(w.probability), 3)})
        lang = info.language
    else:
        die(f"Unknown backend {backend!r} (use mlx or faster)")
    return {"backend": backend, "model": model, "language": lang, "words": words, "segments": segments}


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_outputs(data: dict, base: Path) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".transcript.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    srt = []
    for i, seg in enumerate(data["segments"], 1):
        srt.append(f"{i}\n{srt_time(seg['start'])} --> {srt_time(seg['end'])}\n{seg['text']}\n")
    base.with_suffix(".srt").write_text("\n".join(srt))
    base.with_suffix(".txt").write_text(
        "\n".join(f"[{s['start']:7.2f} - {s['end']:7.2f}] {s['text']}" for s in data["segments"]) + "\n")


def transcribe_file(src: Path, reel: str, backend: str | None = None, model: str | None = None,
                    language: str | None = None) -> Path:
    if not src.exists():
        die(f"{src} not found")
    backend = pick_backend(backend)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        run([tool("ffmpeg"), "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1",
             "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])
        data = transcribe_audio(wav, backend, model, language)
    data["source"] = str(src)
    base = REELS / reel / src.stem
    write_outputs(data, base)
    return base.with_suffix(".transcript.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="clips to transcribe, e.g. raw/IMG_0001.MOV")
    ap.add_argument("--reel", help="reel folder name under reels/ (default: each clip's name)")
    ap.add_argument("--backend", choices=["mlx", "faster"])
    ap.add_argument("--model", help=f"model (default {MLX_DEFAULT} on mlx, {FASTER_DEFAULT} on faster)")
    ap.add_argument("--language", help="e.g. en, de, es; default: auto-detect")
    args = ap.parse_args()
    for f in args.files:
        src = resolve(f)
        out = transcribe_file(src, args.reel or src.stem, args.backend, args.model, args.language)
        data = json.loads(out.read_text())
        print(f"{src.name}: {len(data['words'])} words, language {data['language']}, "
              f"backend {data['backend']} -> {out.relative_to(out.parents[2])}")
