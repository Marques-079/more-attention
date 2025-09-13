from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageColor

def _ts(fmt="%Y%m%d_%H%M%S"):
    return datetime.now().strftime(fmt)

def _ensure_dir(p: str | Path) -> Path:
    p = Path(p); p.mkdir(parents=True, exist_ok=True); return p

def _find_arial() -> Path | None:
    for p in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
    ]:
        if Path(p).exists(): return Path(p)
    return None

def _to_rgba(color, alpha_scale: float) -> tuple[int, int, int, int]:
    """Return RGBA with alpha scaled by alpha_scale (0..1)."""
    if isinstance(color, tuple):
        if len(color) == 4:
            r, g, b, a = color
        else:
            r, g, b = color
            a = 255
    else:
        r, g, b, a = ImageColor.getcolor(str(color), "RGBA")
    a = int(round(max(0.0, min(1.0, alpha_scale)) * a))
    return (r, g, b, a)

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
    bold_px: float = 0.0,                 # <<< float accepted
    padding_px: int = 8,
    font_path: str | Path | None = None,  # None => auto-find Arial
    color=(0, 0, 0),
) -> str:
    """
    Draws plain black Arial from the TOP-LEFT of `box`, word-wrapped.
    `letter_spacing_px` applies between letters inside words (can be negative).
    `space_extra_px` adds extra pixels to spaces (word gaps).
    `bold_px` supports floats (e.g., 1.55). The integer part is a normal stroke;
    the fractional part blends a 1px larger ring with proportional alpha.
    Returns saved PNG path.
    """
    image_path = Path(image_path); assert image_path.exists(), f"Image not found: {image_path}"
    out_dir = _ensure_dir(out_dir)

    if font_path is None:
        font_path = _find_arial()
        if not font_path:
            raise FileNotFoundError("Arial.ttf not found. Pass `font_path` to a valid .ttf.")
    font_path = Path(font_path); assert font_path.exists(), f"Font not found: {font_path}"

    # ---- normalize numeric params where Pillow needs ints ----
    # Box & paddings
    x, y, bw, bh = map(int, box)
    padding_i        = int(padding_px)
    max_w = max(1, bw - 2 * padding_i)
    max_h = max(1, bh - 2 * padding_i)
    # Spacing (integers for pixel advances)
    letter_spacing_i = int(letter_spacing_px)
    space_extra_i    = int(space_extra_px)
    # Font sizes
    font_size_i      = int(font_size)
    min_font_i       = int(min_font)
    # Stroke decomposition
    bold_val         = max(0.0, float(bold_px))
    bold_base        = int(bold_val)                              # integer stroke
    bold_frac        = float(bold_val - bold_base)                # 0.. <1
    bold_meas        = bold_base + (1 if bold_frac > 1e-6 else 0) # used for bbox so nothing clips

    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    # Overlay for fractional ring only (to avoid darkening text fill)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    o_draw  = ImageDraw.Draw(overlay)

    # ---------- measurement helpers ----------
    def char_bbox(s: str, fnt: ImageFont.FreeTypeFont):
        return draw.textbbox((0, 0), s, font=fnt, stroke_width=bold_meas)

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
                    w += max(0, space_extra_i)
                else:
                    if nxt != ' ':
                        w += letter_spacing_i
        return max(0, w)

    def line_height(fnt: ImageFont.FreeTypeFont) -> int:
        b = char_bbox("Hg", fnt)
        raw = max(1, b[3] - b[1])
        return int(round(raw * float(line_spacing)))

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
    size = max(min_font_i, font_size_i)
    fnt = ImageFont.truetype(str(font_path), size)
    lines = wrap_words(fnt, text, max_w)
    W, H = block_dims(fnt, lines)

    while (W > max_w or H > max_h) and size > min_font_i:
        size -= 2
        fnt = ImageFont.truetype(str(font_path), size)
        lines = wrap_words(fnt, text, max_w)
        W, H = block_dims(fnt, lines)

    # ---------- draw top-left ----------
    tx = x + padding_i
    ty = y + padding_i
    lh = line_height(fnt)

    # Precompute overlay stroke color with fractional alpha
    overlay_stroke = _to_rgba(color, bold_frac) if bold_frac > 1e-6 else None

    for ln in lines:
        cx = tx
        for i, ch in enumerate(ln):
            # 1) Base draw with integer stroke (no transparency)
            draw.text(
                (cx, ty),
                ch,
                font=fnt,
                fill=color,
                stroke_width=bold_base,
                stroke_fill=color,
            )
            # 2) Fractional ring (alpha-blended 1px thicker stroke) on overlay
            if overlay_stroke is not None:
                # Render only stroke on overlay; fill fully transparent to avoid darkening glyph body
                o_draw.text(
                    (cx, ty),
                    ch,
                    font=fnt,
                    fill=(0, 0, 0, 0),
                    stroke_width=bold_base + 1,
                    stroke_fill=overlay_stroke,
                )

            cw, _ = char_size(ch, fnt)
            advance = cw
            if i < len(ln) - 1:
                nxt = ln[i + 1]
                if ch == ' ':
                    advance += max(0, space_extra_i)
                else:
                    if nxt != ' ':
                        advance += letter_spacing_i
            cx += advance
        ty += lh

    # Composite overlay (fractional strokes) on top
    if overlay_stroke is not None:
        img = Image.alpha_composite(img, overlay)

    out_path = out_dir / f"thumb_black_tl_{_ts()}.png"
    img.save(out_path, "PNG", optimize=True)
    return str(out_path)
