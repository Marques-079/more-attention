#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from pathlib import Path

# ---------- CONFIG ----------
TEMPLATES = {
    0: "/Users/marcus/Downloads/WRH_white.png",
    1: "/Users/marcus/Downloads/WRH_black.png",
}
OUT_DIR = Path("/Users/marcus/Downloads/video_thumbnails_reddit1")

# Text box: x=40, y=260, width=1200, height=450
BOX_X, BOX_Y, BOX_W, BOX_H = 40, 260, 1200, 360
# ---------------------------

def load_arial_font(font_size: int, weight: str = "regular"):
    weight = (weight or "regular").lower()
    if weight == "bold":
        candidates = [
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Arial Bold.ttf",
        ]
    else:
        candidates = [
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Arial Unicode.ttf",
        ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, font_size)
    return ImageFont.load_default()

# ---- robust measurements (support older Pillow too) ----
def _bbox(draw, text, font, thickness_px: int):
    try:
        return draw.textbbox((0, 0), text, font=font, stroke_width=thickness_px)
    except TypeError:
        b = draw.textbbox((0, 0), text, font=font)
        return (b[0], b[1], b[2] + 2*thickness_px, b[3] + thickness_px)

def _text_width(draw, text, font, thickness_px: int) -> int:
    b = _bbox(draw, text, font, thickness_px)
    return b[2] - b[0]

def _line_height(draw, text, font, thickness_px: int) -> int:
    b = _bbox(draw, text, font, thickness_px)
    return b[3] - b[1]
# -------------------------------------------------------

def measure_text_height(lines, font, line_spacing_px, draw, thickness_px: int = 0) -> int:
    heights = [_line_height(draw, line, font, thickness_px) for line in lines]
    return (sum(heights) + line_spacing_px * (len(lines) - 1)) if heights else 0

def wrap_to_fit(words, draw, font, max_width, max_height, line_spacing_px, thickness_px: int):
    """Greedily add full words while re-wrapping; stop right before height overflows."""
    used = 0
    lines = []
    for i in range(1, len(words) + 1):
        wrapped, current = [], []
        for w in words[:i]:
            test = (" ".join(current + [w])).strip()
            if _text_width(draw, test, font, thickness_px) <= max_width:
                current.append(w)
            else:
                if current:
                    wrapped.append(" ".join(current))
                # if a single word is wider than the line, char-split it
                if _text_width(draw, w, font, thickness_px) > max_width:
                    piece = ""
                    for ch in w:
                        if _text_width(draw, piece + ch, font, thickness_px) <= max_width:
                            piece += ch
                        else:
                            if piece:
                                wrapped.append(piece)
                            piece = ch
                    current = [piece] if piece else []
                else:
                    current = [w]
        if current:
            wrapped.append(" ".join(current))

        h = measure_text_height(wrapped, font, line_spacing_px, draw, thickness_px)
        if h <= max_height:
            lines = wrapped
            used = i
        else:
            break
    return lines, used

def _apply_ellipsis(lines, draw, font, max_width, thickness_px: int, ellipsis="…"):
    """Append ellipsis to last line, trimming by words (then chars) so it fits."""
    if not lines:
        return lines
    last = lines[-1]
    # quick fit
    if _text_width(draw, last + ellipsis, font, thickness_px) <= max_width:
        lines[-1] = last + ellipsis
        return lines

    # word-level backoff
    tokens = last.split(" ")
    while len(tokens) > 1:
        tokens.pop()  # drop last word
        candidate = " ".join(tokens)
        if _text_width(draw, candidate + ellipsis, font, thickness_px) <= max_width:
            lines[-1] = candidate + ellipsis
            return lines

    # single long word: char-level trim
    base = tokens[0] if tokens else last
    trimmed = ""
    for ch in base:
        if _text_width(draw, trimmed + ch + ellipsis, font, thickness_px) <= max_width:
            trimmed += ch
        else:
            break
    if trimmed:
        lines[-1] = trimmed + ellipsis
    else:
        # fallback: ellipsis alone if it fits
        if _text_width(draw, ellipsis, font, thickness_px) <= max_width:
            lines[-1] = ellipsis
        # else leave as-is (shouldn’t happen with reasonable sizes)
    return lines

def generate_thumbnail(
    template_choice: int,
    script_text: str,
    font_size: int = 72,
    font_color: tuple = (0, 0, 0),
    line_spacing_px: int = 6,
    font_weight: str = "regular",    # "regular" | "bold"
    thickness_px: int = 0,           # extra thickness via same-color stroke
    use_ellipsis: bool = True
) -> Path:
    if template_choice not in TEMPLATES:
        raise ValueError("template_choice must be 0 (white) or 1 (black)")
    template_path = Path(TEMPLATES[template_choice])
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    if template_choice == 1 and font_color == (0, 0, 0):
        font_color = (255, 255, 255)

    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = load_arial_font(font_size, weight=font_weight)

    words = script_text.strip().split()
    lines, used_words = wrap_to_fit(
        words, draw, font,
        max_width=BOX_W,
        max_height=BOX_H,
        line_spacing_px=line_spacing_px,
        thickness_px=thickness_px
    )

    # If we didn't consume all words, smart-crop and add ellipsis to the last line
    if use_ellipsis and used_words < len(words) and lines:
        lines = _apply_ellipsis(lines, draw, font, BOX_W, thickness_px)

    # draw lines
    cursor_y = BOX_Y
    for line in lines:
        try:
            draw.text((BOX_X, cursor_y), line, font=font,
                      fill=font_color, stroke_width=thickness_px, stroke_fill=font_color)
        except TypeError:  # very old Pillow: no stroke args
            draw.text((BOX_X, cursor_y), line, font=font, fill=font_color)
        cursor_y += _line_height(draw, line, font, thickness_px) + line_spacing_px

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = "WRH_white" if template_choice == 0 else "WRH_black"
    out_path = OUT_DIR / f"{base}_{stamp}.png"
    img.save(out_path)
    print(f"Saved thumbnail: {out_path}")
    print(f"Words used: {used_words}/{len(words)}  (ellipsis added: {use_ellipsis and used_words < len(words)})")
    return out_path

