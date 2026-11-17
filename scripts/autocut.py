"""./studio autocut CLIP [CLIP ...] --reel NAME — first-pass cut list that removes long pauses.

Uses the word timestamps from ./studio transcribe (runs it if a transcript is missing),
keeps speech, trims gaps longer than brand pacing.max_gap and pads each cut so breaths
and word endings are not chopped. It does NOT judge takes: review the printed segments,
remove false starts and duplicates, then render.
"""
from __future__ import annotations

import argparse
import json

from common import REELS, ROOT, load_brand, next_free, probe, resolve


def islands(words: list[dict], max_gap: float) -> list[list[dict]]:
    groups, cur = [], []
    for w in words:
        if cur and w["start"] - cur[-1]["end"] > max_gap:
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--reel", required=True, help="reel name, e.g. budget-tips")
    ap.add_argument("--max-gap", type=float, help="seconds of silence to cut (default from brand)")
    args = ap.parse_args()

    pacing = load_brand().get("pacing", {})
    max_gap = args.max_gap or float(pacing.get("max_gap", 0.45))
    pad = float(pacing.get("pad", 0.12))
    min_clip = float(pacing.get("min_clip", 0.6))
    reel_dir = REELS / args.reel
    clips_out = []
    for c in args.clips:
        src = resolve(c)
        rel = str(src.relative_to(ROOT)) if src.is_relative_to(ROOT) else str(src)
        tfile = reel_dir / f"{src.stem}.transcript.json"
        if not tfile.exists():
            from transcribe import transcribe_file
            print(f"Transcribing {rel} ...")
            transcribe_file(src, args.reel)
        words = [w for w in json.loads(tfile.read_text())["words"] if w["word"]]
        dur = probe(src)["duration"]
        print(f"\n{rel}")
        for g in islands(words, max_gap):
            cin, cout = max(0.0, g[0]["start"] - pad), min(dur, g[-1]["end"] + pad)
            if clips_out and clips_out[-1]["source"] == rel and cin <= clips_out[-1]["out"]:
                clips_out[-1]["out"] = round(cout, 3)
                clips_out[-1]["text"] += " " + " ".join(w["word"] for w in g)
            elif cout - cin >= min_clip:
                clips_out.append({"source": rel, "in": round(cin, 3), "out": round(cout, 3),
                                  "text": " ".join(w["word"] for w in g)})
    total = 0.0
    for i, c in enumerate(clips_out):
        print(f"  [{i:02d}] {c['source']}  {c['in']:7.2f}-{c['out']:7.2f}  {c['text'][:90]}")
        total += c["out"] - c["in"]
    cut = {"name": args.reel, "output": f"exports/{args.reel}.mp4", "clips": clips_out,
           "captions": {"enabled": True}, "graphics": []}
    reel_dir.mkdir(parents=True, exist_ok=True)
    path = next_free(reel_dir / "cutlist.json")
    path.write_text(json.dumps(cut, indent=2, ensure_ascii=False))
    print(f"\n{len(clips_out)} segments, {total:.1f}s -> {path.relative_to(ROOT)}")
    print("Review: delete false starts/duplicates, check the ending is complete, then ./studio render", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
