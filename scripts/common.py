"""Shared helpers for the Video-Studio scripts. Standard library only."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
REELS = ROOT / "reels"
EXPORTS = ROOT / "exports"
REFERENCES = ROOT / "references"
BRAND_FILE = ROOT / "brand" / "brand.json"
FONTS_DIR = ROOT / "brand" / "fonts"

HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        die(f"{name} was not found. Run ./studio doctor to see what is missing.")
    return path


def run(cmd: list[str], quiet: bool = True) -> subprocess.CompletedProcess:
    """Run a command and raise with its stderr if it fails."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        tail = "\n".join(res.stderr.strip().splitlines()[-25:])
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd[:6])} ...\n{tail}")
    if not quiet and res.stdout:
        print(res.stdout)
    return res


def ffprobe_json(path: Path) -> dict:
    res = run([tool("ffprobe"), "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", str(path)])
    return json.loads(res.stdout)


def _fraction(value: str | None) -> float:
    if not value or value in ("0/0", "N/A"):
        return 0.0
    if "/" in value:
        num, den = value.split("/", 1)
        return float(num) / float(den) if float(den) else 0.0
    return float(value)


def _rotation(stream: dict) -> int:
    for side in stream.get("side_data_list", []) or []:
        if "rotation" in side:
            return int(round(float(side["rotation"])))
    rotate = (stream.get("tags") or {}).get("rotate")
    return int(rotate) if rotate else 0


def probe(path: Path) -> dict:
    """Summarise what matters for editing: orientation, size, fps, colour, audio."""
    data = ffprobe_json(path)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"
                  and not (s.get("disposition") or {}).get("attached_pic")), None)
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    info: dict = {"file": str(path), "duration": float(data["format"].get("duration", 0) or 0)}
    if video:
        rot = _rotation(video)
        w, h = int(video.get("width", 0)), int(video.get("height", 0))
        dw, dh = (h, w) if abs(rot) % 180 == 90 else (w, h)
        transfer = video.get("color_transfer") or "unknown"
        info["video"] = {
            "codec": video.get("codec_name"),
            "coded_size": [w, h],
            "rotation": rot,
            "display_size": [dw, dh],
            "orientation": "portrait" if dh > dw else ("landscape" if dw > dh else "square"),
            "fps": round(_fraction(video.get("avg_frame_rate")) or _fraction(video.get("r_frame_rate")), 3),
            "pix_fmt": video.get("pix_fmt"),
            "color_primaries": video.get("color_primaries") or "unknown",
            "color_transfer": transfer,
            "color_space": video.get("color_space") or "unknown",
            "color_range": video.get("color_range") or "unknown",
            "hdr": transfer in HDR_TRANSFERS,
        }
    else:
        info["video"] = None
    if audio:
        info["audio"] = {
            "codec": audio.get("codec_name"),
            "channels": audio.get("channels"),
            "sample_rate": int(audio.get("sample_rate", 0) or 0),
        }
    else:
        info["audio"] = None
    return info


def load_brand() -> dict:
    if not BRAND_FILE.exists():
        die("brand/brand.json is missing.")
    return json.loads(BRAND_FILE.read_text())


def resolve(path_str: str) -> Path:
    """Resolve a path from a cut list: relative paths are relative to the project root."""
    p = Path(path_str).expanduser()
    return p if p.is_absolute() else (ROOT / p)


def next_free(path: Path) -> Path:
    """Never overwrite: my-reel.mp4 -> my-reel_v2.mp4 -> my-reel_v3.mp4 ..."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    base = stem.rsplit("_v", 1)[0] if "_v" in stem and stem.rsplit("_v", 1)[1].isdigit() else stem
    n = 2
    while True:
        candidate = path.with_name(f"{base}_v{n}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def find_font(preferred: str | None = None) -> str:
    """Return a TrueType/OpenType font path for captions and headlines."""
    candidates: list[Path] = []
    if preferred:
        candidates.append(resolve(preferred))
    candidates += sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf"))
    candidates += [Path(p) for p in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    )]
    for c in candidates:
        if c.exists():
            return str(c)
    die("No usable font found. Put a .ttf or .otf file in brand/fonts/.")
    return ""
