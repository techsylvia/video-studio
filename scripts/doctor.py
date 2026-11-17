"""./studio doctor — check this computer and report what is ready and what is missing.

Read-only: it installs nothing.
"""
from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys

from common import ROOT, find_font

OK, MISSING, NOTE = "OK     ", "MISSING", "NOTE   "
problems: list[str] = []


def line(status: str, label: str, detail: str = "") -> None:
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))


def out(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


print("Video-Studio doctor\n")

# --- computer ---
system = platform.system()
machine = platform.machine()
print("Computer")
if system == "Darwin":
    chip = out(["sysctl", "-n", "machdep.cpu.brand_string"]) or machine
    line(OK, "macOS", f"{platform.mac_ver()[0]} on {chip} ({machine})")
else:
    line(NOTE, system, f"{platform.release()} ({machine}). This kit is Mac-first but works on Linux too.")
apple_silicon = system == "Darwin" and machine == "arm64"
free_gb = shutil.disk_usage(ROOT).free / 1e9
if free_gb < 10:
    line(MISSING, "Free disk space", f"{free_gb:.0f} GB free; video needs room — aim for 20 GB+")
    problems.append("Free up disk space")
else:
    line(OK, "Free disk space", f"{free_gb:.0f} GB free")

# --- core tools ---
print("\nCore tools")
for name in ("ffmpeg", "ffprobe"):
    path = shutil.which(name)
    if path:
        ver = out([name, "-hide_banner", "-version"]).splitlines()[:1]
        line(OK, name, (ver[0] if ver else path))
    else:
        hint = "brew install ffmpeg" if system == "Darwin" else "install ffmpeg with your package manager"
        line(MISSING, name, hint)
        problems.append(f"Install {name} ({hint})")
if shutil.which("ffmpeg"):
    encoders = out(["ffmpeg", "-hide_banner", "-encoders"])
    for enc, why in (("libx264", "H.264 export (SDR)"), ("libx265", "HEVC 10-bit export (HDR)")):
        if enc in encoders:
            line(OK, enc, why)
        else:
            line(NOTE if enc == "libx265" else MISSING, enc, f"needed for {why}")
            if enc == "libx264":
                problems.append("Your ffmpeg has no libx264 encoder; reinstall ffmpeg")

py_ok = sys.version_info >= (3, 10)
line(OK if py_ok else MISSING, "Python", platform.python_version() + ("" if py_ok else " — need 3.10 or newer"))
if not py_ok:
    problems.append("Install Python 3.10+")

venv = ROOT / ".venv"
in_venv = sys.prefix != sys.base_prefix
line(OK if venv.exists() else MISSING, "Project environment (.venv)",
     "present" if venv.exists() else "run ./studio setup after approving the installs")
if not venv.exists():
    problems.append("Run ./studio setup")

# --- python packages ---
print("\nPython packages" + ("" if in_venv else " (checked outside .venv)"))
has = lambda m: importlib.util.find_spec(m) is not None  # noqa: E731
line(OK if has("PIL") else MISSING, "Pillow", "captions and graphics")
if not has("PIL"):
    problems.append("Pillow is missing (./studio setup installs it)")
if apple_silicon:
    ok = has("mlx_whisper")
    line(OK if ok else MISSING, "mlx-whisper", "local speech-to-text on Apple Silicon")
    if not ok and has("faster_whisper"):
        line(NOTE, "faster-whisper", "installed and will be used as the fallback")
    elif not ok:
        problems.append("No speech-to-text backend (./studio setup installs mlx-whisper)")
else:
    ok = has("faster_whisper")
    line(OK if ok else MISSING, "faster-whisper", "local speech-to-text (CPU int8)")
    if not ok:
        problems.append("No speech-to-text backend (./studio setup installs faster-whisper)")

# --- extras ---
print("\nExtras")
try:
    line(OK, "Caption font", find_font())
except SystemExit:
    line(MISSING, "Caption font", "put a .ttf or .otf in brand/fonts/")
    problems.append("Add a caption font to brand/fonts/")
say = shutil.which("say")
line(OK if say else NOTE, "Speech sample for smoke test",
     "macOS 'say' available" if say else "no 'say' command; put a short recording at references/speech-sample.m4a")
line(OK if shutil.which("node") else NOTE, "Node.js", "only needed for optional HTML motion graphics")

print()
if problems:
    print("Needs attention:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)
print("Everything needed for the core editor is ready. Next: ./studio smoke-test")
