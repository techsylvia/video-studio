"""./studio compare SOURCE RENDER [--source-at S] [--render-at R] — side-by-side colour check.

Saves reels/_compare/<render>_vs_<source>.jpg and prints both files' colour tags.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from common import REELS, ROOT, probe, resolve, tool

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("source")
ap.add_argument("render")
ap.add_argument("--source-at", type=float, default=1.0, help="seconds into the source")
ap.add_argument("--render-at", type=float, default=1.0, help="seconds into the render")
a = ap.parse_args()

src, ren = resolve(a.source), resolve(a.render)
out_dir = REELS / "_compare"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"{ren.stem}_vs_{src.stem}.jpg"
# Both frames are scaled to the same height; no colour conversion is applied, so what you see
# is what each file holds (HDR frames may look flat in a JPEG — compare on the phone too).
fc = ("[0:v]scale=-2:960:flags=lanczos,setsar=1[a];[1:v]scale=-2:960:flags=lanczos,setsar=1[b];"
      "[a][b]hstack=inputs=2")
subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-ss", str(a.source_at), "-i", str(src),
                "-ss", str(a.render_at), "-i", str(ren), "-filter_complex", fc, "-frames:v", "1",
                "-q:v", "3", str(out)], check=True)
for label, p in (("source", src), ("render", ren)):
    v = probe(p)["video"]
    print(f"{label:7s} {Path(p).name}: {v['color_primaries']} / {v['color_transfer']} / "
          f"{v['color_space']}  {v['pix_fmt']}  {'HDR' if v['hdr'] else 'SDR'}")
print("side by side ->", out.relative_to(ROOT))
