"""./studio render reels/<reel>/cutlist.json [--draft] — cut, caption and export a vertical reel.

- Never overwrites: a second render becomes <name>_v2.mp4, and the cut list used is saved
  next to the transcripts as a record of the edit decisions.
- SDR sources export as H.264 + AAC (default 1080x1920). HDR sources (HLG/PQ) export as
  10-bit HEVC with the source's HDR transfer kept; nothing is forced to SDR unless asked.
- Captions and graphics are drawn with Pillow and overlaid by FFmpeg, so libass/drawtext
  are not required.
- After rendering it verifies size, duration, audio and a full decode, and saves check frames.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import (EXPORTS, HDR_TRANSFERS, REELS, ROOT, die, find_font, load_brand, next_free,
                    probe, resolve, run, tool)

try:
    from graphics import image_card, text_card
except ImportError:  # Pillow missing
    image_card = text_card = None


# ------------------------------------------------------------------ captions
def chunk_words(words: list[dict], per: int, max_chars: int) -> list[dict]:
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        text = " ".join(x["word"] for x in cur)
        ends_sentence = w["word"].endswith((".", "?", "!", ","))
        if len(cur) >= per or len(text) >= max_chars or ends_sentence:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = [{"start": c[0]["start"], "end": c[-1]["end"],
            "text": " ".join(x["word"] for x in c).strip()} for c in chunks]
    # close tiny gaps so captions don't flicker; enforce a minimum on-screen time
    for i, c in enumerate(out):
        nxt = out[i + 1]["start"] if i + 1 < len(out) else None
        if nxt is not None and nxt - c["end"] < 0.3:
            c["end"] = nxt
        if c["end"] - c["start"] < 0.4:
            c["end"] = c["start"] + 0.4 if nxt is None else min(c["start"] + 0.4, nxt)
    return out


def captions_for(cut: dict, clips: list[dict], reel_dir: Path, brand: dict) -> list[dict]:
    cap = {**brand.get("captions", {}), **(cut.get("captions") or {})}
    if not cap.get("enabled", True):
        return []
    if cap.get("items"):  # captions written directly on the output timeline
        return cap["items"]
    mapping = cap.get("transcripts", {})
    words_out = []
    for c in clips:
        tpath = mapping.get(c["source"])
        tfile = resolve(tpath) if tpath else reel_dir / (Path(c["source"]).stem + ".transcript.json")
        if not tfile.exists():
            print(f"  note: no transcript for {c['source']} ({tfile.name}); no captions for that clip")
            continue
        for w in json.loads(tfile.read_text())["words"]:
            if w["start"] >= c["in"] - 0.05 and w["end"] <= c["out"] + 0.05 and w["word"]:
                s = max(c["in"], w["start"]) - c["in"] + c["offset"]
                e = min(c["out"], w["end"]) - c["in"] + c["offset"]
                words_out.append({"start": s, "end": max(e, s + 0.05), "word": w["word"]})
    return chunk_words(words_out, int(cap.get("words_per_caption", 4)), int(cap.get("max_chars", 26)))


def caption_track(items: list[dict], total: float, size: tuple[int, int], brand: dict,
                  cut: dict, tmp: Path) -> Path | None:
    """Render caption PNGs and an ffconcat list that plays them on the output timeline."""
    if not items:
        return None
    cap = {**brand.get("captions", {}), **(cut.get("captions") or {})}
    font = find_font(cap.get("font") or brand.get("fonts", {}).get("captions"))
    blank = tmp / "blank.png"
    from PIL import Image
    Image.new("RGBA", size, (0, 0, 0, 0)).save(blank)
    entries, t = [], 0.0
    for i, it in enumerate(sorted(items, key=lambda x: x["start"])):
        s, e = max(it["start"], t), min(it["end"], total)
        if e <= s:
            continue
        if s > t:
            entries.append((blank, s - t))
        png = tmp / f"cap_{i:04d}.png"
        text_card(size, it["text"], font, int(cap.get("font_size", 66)), cap.get("color", "#FFFFFF"),
                  float(cap.get("y", 0.70)), float(cap.get("max_width", 0.82)),
                  cap.get("stroke_color"), int(cap.get("stroke_width", 0)),
                  cap.get("box_color") if cap.get("box") else None, float(cap.get("box_opacity", 0)),
                  bool(cap.get("uppercase", False))).save(png)
        entries.append((png, e - s))
        t = e
    if total > t:
        entries.append((blank, total - t))
    lst = tmp / "captions.ffconcat"
    q = lambda p: str(p).replace("'", "'\\''")  # noqa: E731
    body = ["ffconcat version 1.0"]
    for p, d in entries:
        body += [f"file '{q(p)}'", f"duration {d:.3f}"]
    body.append(f"file '{q(entries[-1][0])}'")
    lst.write_text("\n".join(body) + "\n")
    return lst


def graphic_pngs(cut: dict, size: tuple[int, int], brand: dict, tmp: Path) -> list[dict]:
    out = []
    head = brand.get("headlines", {})
    for i, g in enumerate(cut.get("graphics", []) or []):
        png = tmp / f"gfx_{i:02d}.png"
        if g.get("type", "headline") == "headline":
            font = find_font(g.get("font") or brand.get("fonts", {}).get("headlines"))
            text_card(size, g["text"], font, int(g.get("font_size", head.get("font_size", 72))),
                      g.get("color", head.get("color", "#F6F1E9")), float(g.get("y", head.get("y", 0.13))),
                      float(g.get("max_width", 0.84)), None, 0,
                      g.get("box_color", head.get("box_color", "#20272C")),
                      float(g.get("box_opacity", head.get("box_opacity", 0.6)))).save(png)
        elif g["type"] == "image":
            src = resolve(g["image"])
            if not src.exists():
                die(f"graphic image not found: {g['image']}")
            image_card(size, src, float(g.get("width", 0.78)), g.get("x", "center"),
                       float(g.get("y", 0.16))).save(png)
        else:
            die(f"unknown graphic type {g['type']!r} (use headline or image)")
        out.append({"png": png, "start": float(g["start"]), "end": float(g["end"])})
    return out


# ------------------------------------------------------------------ render
def build_and_run(cut: dict, cut_path: Path, draft: bool, tonemap_sdr: bool) -> Path:
    brand = load_brand()
    exp = {**brand.get("export", {}), **(cut.get("export") or {})}
    W, H = int(exp.get("width", 1080)), int(exp.get("height", 1920))
    name = cut.get("name") or cut_path.parent.name
    reel_dir = REELS / name
    reel_dir.mkdir(parents=True, exist_ok=True)

    clips, offset = [], 0.0
    for c in cut["clips"]:
        src = resolve(c["source"])
        if not src.exists():
            die(f"clip not found: {c['source']}")
        info = probe(src)
        if not info["video"]:
            die(f"{c['source']} has no video stream")
        cin = float(c.get("in", 0))
        cout = float(c.get("out", info["duration"]))
        if cout <= cin:
            die(f"{c['source']}: out ({cout}) must be after in ({cin})")
        clips.append({**c, "src": src, "info": info, "in": cin, "out": cout,
                      "dur": cout - cin, "offset": offset})
        offset += cout - cin
    total = offset

    hdr_flags = [c["info"]["video"]["hdr"] for c in clips]
    hdr = any(hdr_flags) and not tonemap_sdr
    if any(hdr_flags) and not all(hdr_flags) and not tonemap_sdr:
        print("  warning: mixing HDR and SDR clips; exporting HDR. Compare colour carefully, "
              "or re-run with --tonemap-sdr if the creator asks for an SDR export.")
    first_v = clips[0]["info"]["video"]
    fps = float(exp.get("fps") or brand.get("pacing", {}).get("fps") or round(first_v["fps"]) or 30)
    pix = "yuv420p10le" if hdr else "yuv420p"

    ffmpeg = tool("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-v", "error", "-y"]
    for c in clips:
        cmd += ["-ss", f"{c['in']:.3f}", "-t", f"{c['dur']:.3f}", "-i", str(c["src"])]
    n_in = len(clips)

    tmp = Path(tempfile.mkdtemp(prefix="studio_"))
    items = captions_for(cut, clips, reel_dir, brand)
    if items and text_card is None:
        die("Pillow is not installed; run ./studio setup")
    cap_list = caption_track(items, total, (W, H), brand, cut, tmp)
    gfx = graphic_pngs(cut, (W, H), brand, tmp) if cut.get("graphics") else []
    if cap_list:
        cmd += ["-f", "concat", "-safe", "0", "-i", str(cap_list)]
        cap_idx = n_in
        n_in += 1
    gfx_idx = []
    for g in gfx:
        cmd += ["-loop", "1", "-framerate", f"{fps:g}", "-t", f"{total:.3f}", "-i", str(g["png"])]
        gfx_idx.append(n_in)
        n_in += 1
    vo = cut.get("voiceover")
    if vo:
        vpath = resolve(vo["file"])
        if not vpath.exists():
            die(f"voiceover not found: {vo['file']}")
        cmd += ["-ss", f"{float(vo.get('in', 0)):.3f}", "-i", str(vpath)]
        vo_idx = n_in
        n_in += 1
    music = cut.get("music")
    if music:
        mpath = resolve(music["file"])
        if not mpath.exists():
            die(f"music not found: {music['file']}")
        cmd += ["-stream_loop", "-1", "-i", str(mpath)]
        music_idx = n_in
        n_in += 1

    if tonemap_sdr and any(hdr_flags):
        filters = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        if " zscale " not in filters or " tonemap " not in filters:
            die("--tonemap-sdr needs ffmpeg built with zscale (libzimg). Keep the HDR export, or install "
                "an ffmpeg build that includes zscale.")
    tone = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,") if tonemap_sdr and any(hdr_flags) else ""
    cleanup = (cut.get("audio") or {}).get("cleanup", False)
    f, concat_in = [], []
    for k, c in enumerate(clips):
        d = c["dur"]
        tm = tone if c["info"]["video"]["hdr"] else ""
        f.append(f"[{k}:v]setpts=PTS-STARTPTS,{tm}scale={W}:{H}:force_original_aspect_ratio=increase:"
                 f"flags=lanczos,crop={W}:{H},setsar=1,fps={fps:g},tpad=stop_mode=clone:stop_duration=1,"
                 f"trim=duration={d:.3f},format={pix}[v{k}]")
        if c["info"]["audio"]:
            clean = "highpass=f=70,afftdn=nr=6," if cleanup else ""
            f.append(f"[{k}:a]asetpts=PTS-STARTPTS,{clean}aresample=48000,"
                     f"aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={d:.3f}[a{k}]")
        else:
            f.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={d:.3f}[a{k}]")
        concat_in.append(f"[v{k}][a{k}]")
    f.append(f"{''.join(concat_in)}concat=n={len(clips)}:v=1:a=1[base][abase]")
    vlabel, ov = "base", "yuv420p10" if hdr else "yuv420"
    if cap_list:
        f.append(f"[{cap_idx}:v]format=rgba,fps={fps:g},setpts=PTS-STARTPTS[caps]")
        f.append(f"[{vlabel}][caps]overlay=0:0:format={ov}:eof_action=pass[vc]")
        vlabel = "vc"
    for j, (g, idx) in enumerate(zip(gfx, gfx_idx)):
        s, e = g["start"], g["end"]
        fd = min(0.25, (e - s) / 3)
        f.append(f"[{idx}:v]format=rgba,fade=t=in:st={s:.3f}:d={fd:.3f}:alpha=1,"
                 f"fade=t=out:st={e - fd:.3f}:d={fd:.3f}:alpha=1[g{j}]")
        f.append(f"[{vlabel}][g{j}]overlay=0:0:format={ov}:enable='between(t,{s:.3f},{e:.3f})'[vg{j}]")
        vlabel = f"vg{j}"
    f.append(f"[{vlabel}]format={pix}[vout]")
    alabel = "abase"
    if vo:
        # The picture is cut to the recording: the voiceover is the main audio track.
        f.append(f"[{vo_idx}:a]asetpts=PTS-STARTPTS,aresample=48000,"
                 f"aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={total:.3f}[vo]")
        clip_vol = float(vo.get("clip_audio_volume", 0))
        if clip_vol > 0:
            f.append(f"[abase]volume={clip_vol}[abq]")
            f.append("[vo][abq]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[avo]")
            alabel = "avo"
        else:
            f.append("[abase]anullsink")
            alabel = "vo"
    if music:
        vol = float(music.get("volume", brand.get("music", {}).get("volume", 0.12)))
        f.append(f"[{music_idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"volume={vol},atrim=duration={total:.3f}[mus]")
        f.append(f"[{alabel}][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[amix]")
        alabel = "amix"

    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", f"[{alabel}]"]
    crf = 23 if draft else int(exp.get("crf", 18))
    preset = "veryfast" if draft else "medium"
    if hdr:
        trc = first_v["color_transfer"] if first_v["color_transfer"] in HDR_TRANSFERS else "arib-std-b67"
        cmd += ["-c:v", "libx265", "-preset", preset, "-crf", str(crf + 2), "-pix_fmt", pix, "-tag:v", "hvc1",
                "-color_primaries", "bt2020", "-color_trc", trc, "-colorspace", "bt2020nc",
                "-x265-params", f"log-level=error:colorprim=bt2020:transfer={trc}:colormatrix=bt2020nc"]
    else:
        cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", pix, "-profile:v", "high"]
        if tonemap_sdr or first_v["color_primaries"] == "bt709":
            cmd += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.3f}"]

    out = next_free(resolve(cut.get("output") or f"exports/{name}.mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd.append(str(out))
    print(f"Rendering {len(clips)} clip(s), {total:.2f}s, {'HDR HEVC 10-bit' if hdr else 'SDR H.264'}, "
          f"{len(items)} captions, {len(gfx)} graphics -> {out.relative_to(ROOT)}")
    try:
        run(cmd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    record = {**cut, "rendered_to": str(out.relative_to(ROOT)), "duration": round(total, 3),
              "mode": "hdr" if hdr else "sdr", "captions_used": items}
    (reel_dir / f"{out.stem}.cutlist.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return out, total, (W, H), reel_dir


# ------------------------------------------------------------------ verify
def verify(out: Path, expect_dur: float, expect_audio: bool, size: tuple[int, int], frames_dir: Path) -> dict:
    info = probe(out)
    v, a = info["video"], info["audio"]
    dec = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(out), "-f", "null", "-"],
                         capture_output=True, text=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    grabs = []
    for label, t in (("start", min(0.5, info["duration"] / 4)), ("middle", info["duration"] / 2),
                     ("end", max(0, info["duration"] - 0.5))):
        p = frames_dir / f"{out.stem}_{label}.jpg"
        subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(out),
                        "-frames:v", "1", "-q:v", "3", str(p)], capture_output=True)
        if p.exists():
            grabs.append(str(p.relative_to(ROOT)))
    checks = {
        "size": bool(v) and v["display_size"] == list(size),
        "duration": abs(info["duration"] - expect_dur) < 0.25,
        "audio": (a is not None) if expect_audio else True,
        "full_decode": dec.returncode == 0 and not dec.stderr.strip(),
    }
    return {"file": str(out.relative_to(ROOT)), "checks": checks, "ok": all(checks.values()),
            "duration": round(info["duration"], 3),
            "size": v["display_size"] if v else None, "hdr": v["hdr"] if v else None,
            "decode_errors": dec.stderr.strip()[:500], "frames": grabs}


def print_report(rep: dict) -> None:
    print(f"\n{rep['file']}  {rep['size'][0]}x{rep['size'][1]}  {rep['duration']}s  "
          f"{'HDR' if rep['hdr'] else 'SDR'}")
    for k, ok in rep["checks"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {k}")
    if rep["decode_errors"]:
        print("  decode errors:", rep["decode_errors"])
    print("  check frames:", ", ".join(rep["frames"]))
    print("  Still to do by eye/ear: play it with sound, check the first and last words, captions, "
          "graphics vs face, colour vs source.")


def render_cutlist(cut_path: Path, draft: bool = False, tonemap_sdr: bool = False) -> dict:
    cut = json.loads(cut_path.read_text())
    out, total, size, reel_dir = build_and_run(cut, cut_path, draft, tonemap_sdr)
    rep = verify(out, total, True, size, reel_dir / "checks")
    print_report(rep)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlist", help="path to a cut list JSON, e.g. reels/my-reel/cutlist.json")
    ap.add_argument("--draft", action="store_true", help="faster, lower quality preview render")
    ap.add_argument("--tonemap-sdr", action="store_true",
                    help="convert HDR clips to SDR (only when the creator asks; needs zscale in ffmpeg)")
    a = ap.parse_args()
    try:
        report = render_cutlist(resolve(a.cutlist), a.draft, a.tonemap_sdr)
    except RuntimeError as err:
        die(str(err))
    sys.exit(0 if report["ok"] else 2)
