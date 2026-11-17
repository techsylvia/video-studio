#!/usr/bin/env bash
# ./studio setup — create the project Python environment (.venv) and install
# Pillow plus a local speech-to-text backend. Run it only after the creator
# has approved these installs. It does not install ffmpeg (see ./studio doctor).
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && \
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
      PY="$candidate"; break
    fi
  done
fi
if [ -z "$PY" ]; then
  echo "Python 3.10+ not found. On a Mac: brew install python@3.12" >&2
  exit 1
fi

if [ ! -d .venv ]; then
  echo "Creating .venv with $("$PY" --version)"
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet "Pillow>=10"

if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
  echo "Apple Silicon: installing mlx-whisper (falls back to faster-whisper if it fails)"
  .venv/bin/python -m pip install --quiet mlx-whisper || \
    .venv/bin/python -m pip install --quiet faster-whisper
else
  echo "Installing faster-whisper (CPU int8)"
  .venv/bin/python -m pip install --quiet faster-whisper
fi

echo "Done. Speech model weights download on first transcription and are cached after that."
echo "Next: ./studio doctor, then ./studio smoke-test"
