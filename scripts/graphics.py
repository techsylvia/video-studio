"""Pillow helpers: caption and headline cards, image cards. Each returns a full-frame RGBA image."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def hex_rgba(value: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    v = value.lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), int(round(alpha * 255)))


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_card(size: tuple[int, int], text: str, font_path: str, font_size: int, color: str,
              y_center: float, max_width: float = 0.82, stroke_color: str | None = None,
              stroke_width: int = 0, box_color: str | None = None, box_opacity: float = 0.0,
              uppercase: bool = False, line_gap: float = 0.18) -> Image.Image:
    """Centered, wrapped text on a transparent frame. y_center is 0-1 of frame height."""
    W, H = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    if uppercase:
        text = text.upper()
    lines = wrap(draw, text, font, int(W * max_width))
    asc, desc = font.getmetrics()
    lh = asc + desc
    gap = int(font_size * line_gap)
    block_h = len(lines) * lh + (len(lines) - 1) * gap
    top = int(H * y_center - block_h / 2)
    widths = [draw.textlength(l, font=font) for l in lines]
    if box_color and box_opacity > 0:
        pad_x, pad_y = int(font_size * 0.45), int(font_size * 0.3)
        bw = int(max(widths)) + 2 * pad_x
        x0 = (W - bw) // 2
        draw.rounded_rectangle([x0, top - pad_y, x0 + bw, top + block_h + pad_y],
                               radius=int(font_size * 0.35), fill=hex_rgba(box_color, box_opacity))
    y = top
    for l, w in zip(lines, widths):
        draw.text(((W - w) / 2, y), l, font=font, fill=hex_rgba(color),
                  stroke_width=stroke_width, stroke_fill=hex_rgba(stroke_color) if stroke_color else None)
        y += lh + gap
    return img


def image_card(size: tuple[int, int], image_path: Path, width: float = 0.78, x: str | float = "center",
               y: float = 0.16, radius: int = 28, shadow: bool = True) -> Image.Image:
    """A screenshot or picture as a floating rounded card. width/x/y are 0-1 of the frame."""
    W, H = size
    frame = Image.new("RGBA", size, (0, 0, 0, 0))
    pic = Image.open(image_path).convert("RGBA")
    tw = int(W * width)
    th = int(pic.height * tw / pic.width)
    pic = pic.resize((tw, th), Image.LANCZOS)
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tw - 1, th - 1], radius=radius, fill=255)
    px = (W - tw) // 2 if x == "center" else int(W * float(x))
    py = int(H * y)
    if shadow:
        sh = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([px + 6, py + 14, px + tw + 6, py + th + 14],
                                             radius=radius, fill=(0, 0, 0, 110))
        frame = Image.alpha_composite(frame, sh.filter(ImageFilter.GaussianBlur(18)))
    frame.paste(pic, (px, py), mask)
    return frame
