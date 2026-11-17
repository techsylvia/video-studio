"""./studio probe FILE [FILE ...] — show orientation, size, frame rate, colour and audio."""
from __future__ import annotations

import argparse
import json

from common import probe, resolve

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("files", nargs="+")
ap.add_argument("--json", action="store_true", help="print raw JSON")
args = ap.parse_args()

for f in args.files:
    info = probe(resolve(f))
    if args.json:
        print(json.dumps(info, indent=2))
        continue
    v, a = info["video"], info["audio"]
    print(info["file"])
    print(f"  duration    {info['duration']:.2f}s")
    if v:
        print(f"  video       {v['codec']}  {v['display_size'][0]}x{v['display_size'][1]} "
              f"{v['orientation']}  (coded {v['coded_size'][0]}x{v['coded_size'][1]}, rotation {v['rotation']})")
        print(f"  frame rate  {v['fps']}")
        print(f"  colour      {v['color_primaries']} / {v['color_transfer']} / {v['color_space']}  "
              f"range {v['color_range']}  {v['pix_fmt']}  {'HDR' if v['hdr'] else 'SDR'}")
    else:
        print("  video       none")
    print(f"  audio       {a['codec']} {a['channels']}ch {a['sample_rate']} Hz" if a else "  audio       none")
