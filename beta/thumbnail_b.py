from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

def _ts(fmt="%Y%m%d_%H%M%S"): 
    return datetime.now().strftime(fmt)

def _ensure_dir(p: str | Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def _find_arial() -> Path | None:
    # Common macOS / Windows locations
    for p in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
    ]:
        if Path(p).exists(): return Path(p)
    return None

def render_black_topleft(
    image_path: str | Path,
    text: str,
    box: tuple[int, int, int, int],      # (x, y, w, h)
    out_dir: str | Path = "/Users/marcus/Downloads/shorts_thumbnails_storage",
    font_size: int = 160,                 # will shrink-to-fit
    min_font: int = 24,
    line_spacing: float = 1.08,
    letter_spacing_px: int = 0,           # can be negative (tighten letters)
    space_extra_px: int = 0,              # added to spaces between words
    bold_px: int = 0,                     # thickness via stroke
    padding_px: int = 8,
    font_path: str | Path | None = None,  # None => auto-find Arial
    color=(0, 0, 0),
) -> str:
    """
    Draws plain black Arial from the TOP-LEFT of `box`, word-wrapped.
    `letter_spacing_px` applies between letters inside words (can be negative).
    `space_extra_px` adds extra pixels to spaces (word gaps).
    Returns saved PNG path.
    """
    image_path = Path(image_path); assert image_path.exists(), f"Image not found: {image_path}"
    out_dir = _ensure_dir(out_dir)

    if font_path is None:
        font_path = _find_arial()
        if not font_path:
            raise FileNotFoundError("Arial.ttf not found. Pass `font_path` to a valid .ttf.")
    font_path = Path(font_path); assert font_path.exists(), f"Font not found: {font_path}"

    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    x, y, bw, bh = box
    max_w = max(1, bw - 2 * padding_px)
    max_h = max(1, bh - 2 * padding_px)

    # ---------- measurement helpers ----------
    def char_bbox(s: str, fnt: ImageFont.FreeTypeFont):
        return draw.textbbox((0, 0), s, font=fnt, stroke_width=bold_px)

    def char_size(ch: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
        b = char_bbox(ch, fnt)
        return b[2] - b[0], b[3] - b[1]

    def string_width(s: str, fnt: ImageFont.FreeTypeFont) -> int:
        if not s: return 0
        w = 0
        for i, ch in enumerate(s):
            cw, _ = char_size(ch, fnt)
            w += cw
            if i < len(s) - 1:
                nxt = s[i + 1]
                if ch == ' ':
                    # widen spaces themselves
                    w += max(0, space_extra_px)
                else:
                    # letter spacing only if the next thing isn't a space
                    if nxt != ' ':
                        w += letter_spacing_px
        return max(0, w)

    def line_height(fnt: ImageFont.FreeTypeFont) -> int:
        b = char_bbox("Hg", fnt)
        raw = max(1, b[3] - b[1])
        return int(round(raw * line_spacing))

    def wrap_words(fnt: ImageFont.FreeTypeFont, s: str, maxw: int) -> list[str]:
        words = s.split()
        lines, cur = [], ""
        for w in words:
            cand = (cur + " " + w).strip() if cur else w
            if string_width(cand, fnt) <= maxw:
                cur = cand
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return lines

    def block_dims(fnt: ImageFont.FreeTypeFont, lines: list[str]) -> tuple[int, int]:
        lh = line_height(fnt)
        H = len(lines) * lh
        W = 0
        for ln in lines:
            W = max(W, string_width(ln, fnt))
        return W, H

    # ---------- fit loop ----------
    size = max(min_font, int(font_size))
    fnt = ImageFont.truetype(str(font_path), size)
    lines = wrap_words(fnt, text, max_w)
    W, H = block_dims(fnt, lines)

    while (W > max_w or H > max_h) and size > min_font:
        size -= 2
        fnt = ImageFont.truetype(str(font_path), size)
        lines = wrap_words(fnt, text, max_w)
        W, H = block_dims(fnt, lines)

    # ---------- draw top-left ----------
    tx = x + padding_px
    ty = y + padding_px
    lh = line_height(fnt)

    for ln in lines:
        cx = tx
        for i, ch in enumerate(ln):
            draw.text(
                (cx, ty),
                ch,
                font=fnt,
                fill=color,
                stroke_width=max(0, bold_px),
                stroke_fill=color,
            )
            cw, _ = char_size(ch, fnt)
            advance = cw
            if i < len(ln) - 1:
                nxt = ln[i + 1]
                if ch == ' ':
                    advance += max(0, space_extra_px)
                else:
                    if nxt != ' ':
                        advance += letter_spacing_px
            cx += advance
        ty += lh

    out_path = out_dir / f"thumb_black_tl_{_ts()}.png"
    img.save(out_path, "PNG", optimize=True)
    return str(out_path)
