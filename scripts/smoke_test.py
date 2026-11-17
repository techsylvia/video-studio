"""./studio smoke-test — prove the core editor works without touching personal footage.

1. Render test: builds a synthetic 1080x1920 clip with a tone, cuts it, adds captions and a
   headline, then checks size, duration, audio, a full decode and that captions are visible.
2. Speech test: makes a short spoken sample (macOS `say`, or espeak-ng on Linux, or your own
   references/speech-sample.* recording) and checks the transcript's words and timestamps.
   A tone alone does not test speech recognition.
Results go to reels/_smoke/.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

from common import REELS, REFERENCES, ROOT, run, tool

SMOKE = REELS / "_smoke"
PHRASE = "This is my video studio test. One, two, three, four, five."
results: dict[str, dict] = {}


def render_test() -> None:
    try:
        from PIL import Image, ImageChops, ImageStat
        from render import render_cutlist
    except ImportError as e:
        results["render"] = {"status": "FAIL", "detail": f"missing package: {e}. Run ./studio setup"}
        return
    src = SMOKE / "synthetic_source.mp4"
    run([tool("ffmpeg"), "-v", "error", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=4",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src)])
    for old in SMOKE.glob("smoke_test*.mp4"):
        old.unlink()
    cut = {
        "name": "_smoke",
        "output": "reels/_smoke/smoke_test.mp4",
        "clips": [{"source": "reels/_smoke/synthetic_source.mp4", "in": 0.5, "out": 3.5}],
        "captions": {"items": [{"start": 0.0, "end": 1.5, "text": "Smoke test caption"},
                               {"start": 1.5, "end": 3.0, "text": "Video-Studio works"}]},
        "graphics": [{"type": "headline", "text": "SMOKE TEST", "start": 0.2, "end": 2.8}],
    }
    cut_path = SMOKE / "cutlist.json"
    cut_path.write_text(json.dumps(cut, indent=2))
    rep = render_cutlist(cut_path, draft=True)

    # Is the caption actually visible? Compare the caption band with the same band in the source.
    out = ROOT / rep["file"]
    a, b = SMOKE / "frame_render.png", SMOKE / "frame_source.png"
    run([tool("ffmpeg"), "-v", "error", "-y", "-ss", "0.75", "-i", str(out), "-frames:v", "1", str(a)])
    run([tool("ffmpeg"), "-v", "error", "-y", "-ss", "1.25", "-i", str(src), "-frames:v", "1", str(b)])
    ra, rb = Image.open(a).convert("L"), Image.open(b).convert("L")
    band = lambda y0, y1: (0, int(1920 * y0), 1080, int(1920 * y1))  # noqa: E731
    cap_diff = ImageStat.Stat(ImageChops.difference(ra.crop(band(0.66, 0.74)), rb.crop(band(0.66, 0.74)))).mean[0]
    ref_diff = ImageStat.Stat(ImageChops.difference(ra.crop(band(0.42, 0.50)), rb.crop(band(0.42, 0.50)))).mean[0]
    caption_ok = cap_diff > max(4.0, ref_diff * 3)
    rep["checks"]["caption_visible"] = caption_ok
    ok = rep["ok"] and caption_ok
    results["render"] = {"status": "PASS" if ok else "FAIL", "file": rep["file"], "checks": rep["checks"],
                         "frames": rep["frames"] + [str(a.relative_to(ROOT))]}


def speech_test() -> None:
    from transcribe import available_backend, transcribe_file
    if not available_backend():
        results["speech"] = {"status": "SKIPPED", "detail": "no speech-to-text backend; run ./studio setup"}
        return
    expected = None
    sample = None
    if shutil.which("say"):
        sample = SMOKE / "speech_sample.aiff"
        subprocess.run(["say", "-o", str(sample), PHRASE], check=True)
        expected = PHRASE
    elif shutil.which("espeak-ng") or shutil.which("espeak"):
        sample = SMOKE / "speech_sample.wav"
        subprocess.run([shutil.which("espeak-ng") or shutil.which("espeak"), "-w", str(sample), PHRASE], check=True)
        expected = PHRASE
    else:
        found = sorted(REFERENCES.glob("speech-sample.*"))
        sample = found[0] if found else None
    if not sample:
        results["speech"] = {"status": "SKIPPED",
                             "detail": "no 'say'/espeak; record a short non-private sentence to references/speech-sample.m4a"}
        return
    tfile = transcribe_file(sample, "_smoke", language="en" if expected else None)
    data = json.loads(tfile.read_text())
    words = data["words"]
    from common import probe
    dur = probe(sample)["duration"]
    times_ok = bool(words) and all(0 <= w["start"] <= w["end"] <= dur + 0.5 for w in words) and \
        all(words[i]["start"] <= words[i + 1]["start"] for i in range(len(words) - 1))
    norm = lambda s: re.findall(r"[a-z]+", s.lower())  # noqa: E731
    got = " ".join(w["word"] for w in words)
    if expected:
        exp = norm(expected)
        heard = set(norm(got))
        match = sum(1 for w in exp if w in heard) / len(exp)
        ok = times_ok and match >= 0.6
        detail = f"heard: \"{got}\" — {match:.0%} of expected words, timestamps {'ok' if times_ok else 'BAD'}"
    else:
        ok = times_ok
        detail = f"heard: \"{got}\" — check this matches what you said; timestamps {'ok' if times_ok else 'BAD'}"
    results["speech"] = {"status": "PASS" if ok else "FAIL", "backend": data["backend"], "model": data["model"],
                         "detail": detail, "transcript": str(tfile.relative_to(ROOT))}


if __name__ == "__main__":
    SMOKE.mkdir(parents=True, exist_ok=True)
    try:
        render_test()
    except Exception as e:  # report, don't crash, so the speech test still runs
        results["render"] = {"status": "FAIL", "detail": str(e)[:800]}
    try:
        speech_test()
    except Exception as e:
        results["speech"] = {"status": "FAIL", "detail": f"{str(e)[:600]} (if this is a network error, the "
                             "speech model could not be downloaded: check the connection, approve the "
                             "download and run the smoke test again)"}
    (SMOKE / "report.json").write_text(json.dumps(results, indent=2))
    print("\nSmoke test results")
    for name, r in results.items():
        print(f"  [{r['status']}] {name}" + (f" — {r.get('detail')}" if r.get("detail") else ""))
        if r.get("file"):
            print(f"         test MP4: {ROOT / r['file']}")
    print(f"  report: {(SMOKE / 'report.json').relative_to(ROOT)}")
    sys.exit(0 if all(r["status"] == "PASS" for r in results.values()) else 1)
