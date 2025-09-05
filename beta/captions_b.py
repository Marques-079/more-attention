# === CONFIG ==============================================================

from pathlib import Path
import tempfile

# Where to save the rendered video:
OUTPUT_DIR = Path.home() / "Downloads" / "reddit1_filmora_captioned"

# Filename pattern (placeholders: {stem}=input filename stem, {ts}=timestamp, {anim}=ANIM)
FILENAME_TEMPLATE = "exported_{ts}.mp4"

MODEL_NAME        = "small.en"       # tiny/base/small/medium/large-v3; *.en faster for English

# Caption look
FONT_SIZE         = 210
UPPERCASE         = True

# Outline controls
BORDER_PX         = 12.0
SHADOW_PX         = 2.0
BLUR_PX           = 0.0
STABILIZE_OUTLINE = True

# Timing hyperparams
MIN_CAPTION_SEC   = 0.30
CUT_AHEAD_SEC     = 0.00
TAIL_HOLD_SEC     = 1.20

# Grouping hyperparams
MAX_WORDS_PER_CAP = 1
MAX_CHARS_PER_CAP = None
MAX_GAP_SEC       = 1.20

# Animation
ANIM              = "inflate"
ANIM_IN_MS        = 20000
ANIM_OUT_MS       = 50

# Fonts
CUSTOM_FONT_DIR   = Path.home() / "Documents" / "mrbeast_caps" / "fonts"

# Rendering safety
AUTO_PLAYRES      = True             # match ASS PlayRes to actual video resolution
YUV444_RENDER     = True             # render subs in 4:4:4 to stabilize edges, then downsample

# --- NEW: Reddit intro card overlay --------------------------------------
INTRO_CARD_SRC     = Path("/Users/marcus/Downloads/Thumb_shorts_white")   # file OR folder; None disables
INTRO_ENABLED      = True
INTRO_SECS         = 3.0
INTRO_FADE         = 0.30
INTRO_SCALE        = 0.92
INTRO_CROP_BOTTOM  = 0.12
INTRO_OFFSET_X     = 0
INTRO_OFFSET_Y     = 0
INTRO_ROUND_PX     = 40   
# ========================================================================

import os, subprocess, shutil, platform, re, sys
from datetime import timedelta
from faster_whisper import WhisperModel
from datetime import datetime

def timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    return datetime.now().strftime(fmt)

def sanitize_stem(stem: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', stem).strip('_')

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

# ---------- probe video resolution ----------
def probe_resolution(video_path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height","-of","csv=s=x:p=0", str(video_path)
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        w, h = map(int, out.split("x"))
        print(f"[info] probed resolution: {w}x{h}")
        return w, h
    except Exception:
        print("[warn] ffprobe failed, falling back to 1920x1080")
        return 1920, 1080

CENTER_X, CENTER_Y = None, None

# ---------- load Whisper ----------
import platform as _pf
def load_whisper_auto(model_name: str):
    osname = _pf.system()
    candidates = (["float16", "int8", "float32"] if osname == "Darwin"
                  else ["int8_float16", "int8", "float16", "float32"])
    last = None
    for ct in candidates:
        try:
            print(f"[info] trying compute_type={ct} …")
            return WhisperModel(model_name, compute_type=ct, device="auto")
        except ValueError as e:
            print(f"[skip] {e}")
            last = e
    raise last

# ---------- font ----------
def pick_custom_font(font_dir: Path):
    font_dir.mkdir(parents=True, exist_ok=True)
    candidates = list(font_dir.glob("*.ttf")) + list(font_dir.glob("*.otf"))
    if not candidates:
        print("\n[FONT SETUP REQUIRED]")
        print("1) Download any .ttf or .otf font.")
        print(f"2) Place it here: {font_dir}")
        print("3) Re-run.")
        raise SystemExit("[exit] No font found yet.")
    font_file = candidates[0]
    family = None
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(font_file)
        names = {n.nameID: n.toUnicode() for n in tt["name"].names if n.toUnicode()}
        family = names.get(1) or names.get(4)
    except Exception:
        family = font_file.stem
    print("[font] Using file:", font_file)
    print("[font] Font family set to:", family)
    return font_file, family

# ---------- ASS header ----------
ASS_HEADER_TMPL = """[Script Info]
ScriptType: v4.00+
PlayResX: {play_w}
PlayResY: {play_h}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
; White text (Primary), THICK black outline, subtle shadow for separation.
Style: Beast,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{border},{shadow},5,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def _fmt_time(t: float) -> str:
    td = timedelta(seconds=max(0.0, t))
    cs = int(round(td.total_seconds() * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def _scale_spec_for_anim(name: str):
    name = (name or "none").lower()
    if name in ("inflate", "inflate_soft", "pop"):
        return 80, 100
    if name == "zoom":
        return 60, 100
    return 100, 100

def _fmt_float(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")

def anim_tag(cx: int, cy: int, name: str, in_ms: int, out_ms: int,
             border_px: float, stabilize_outline: bool, blur_px: float) -> str:
    cx, cy = int(round(cx)), int(round(cy))
    s0, s1 = _scale_spec_for_anim(name)
    if stabilize_outline and (s0 != s1):
        bord0 = border_px * (s0 / 100.0)
        bord1 = border_px * (s1 / 100.0)
        bord_tag0 = rf"\bord{_fmt_float(bord0)}"
        bord_anim = rf"\t(0,{in_ms},\bord{_fmt_float(bord1)})"
    else:
        bord_tag0 = rf"\bord{_fmt_float(border_px)}"
        bord_anim = ""
    blur_tag = (rf"\blur{_fmt_float(blur_px)}" if blur_px and blur_px > 0 else "")
    name = (name or "none").lower()
    if name == "none":
        return rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}}}"
    if name == "fade":
        return rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}\fad({in_ms},{out_ms})}}"
    if name == "pop":
        return rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}\fscx80\fscy80\t(0,{in_ms},\fscx100\fscy100){bord_anim}}}"
    if name == "zoom":
        return rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}\fscx60\fscy60\t(0,{in_ms},\fscx100\fscy100){bord_anim}}}"
    if name == "bounce":
        return (rf"{{\an5\move({cx},{cy-40},{cx},{cy},0,{in_ms}){bord_tag0}{blur_tag}"
                rf"\fscx120\fscy120\t(0,120,\fscx95\fscy95)\t(120,{in_ms},\fscx100\fscy100){bord_anim}}}")
    if name == "slide_up":
        return rf"{{\an5\move({cx},{cy+60},{cx},{cy},0,{in_ms}){bord_tag0}{blur_tag}}}"
    if name == "slide_down":
        return rf"{{\an5\move({cx},{cy-60},{cx},{cy},0,{in_ms}){bord_tag0}{blur_tag}}}"
    if name == "slide_left":
        return rf"{{\an5\move({cx-140},{cy},{cx},{cy},0,{in_ms}){bord_tag0}{blur_tag}}}"
    if name == "slide_right":
        return rf"{{\an5\move({cx+140},{cy},{cx},{cy},0,{in_ms}){bord_tag0}{blur_tag}}}"
    if name == "rotate":
        return rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}\frz-12\t(0,{in_ms},\frz0)}}"
    if name == "inflate":
        return rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}\fscx80\fscy80\t(0,{in_ms},\fscx100\fscy100){bord_anim}}}"
    if name == "inflate_soft":
        return (rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}\fscx80\fscy80\alpha&H20&\blur2"
                rf"\t(0,{in_ms},\fscx100\fscy100\alpha&H00&\blur0){bord_anim}}}")
    return rf"{{\an5\pos({cx},{cy}){bord_tag0}{blur_tag}}}"

# ---------- Group words into captions ----------
def clean_token(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^\s+|\s+$", "", s)
    return re.sub(r"^\W+|\W+$", "", s)

def group_words_to_captions(words,
                            max_words=1,
                            max_chars=None,
                            max_gap_s=0.6):
    lines, cur = [], []
    last_end = None
    for w in words:
        token = clean_token(w["text"])
        if not token:
            continue
        gap = (w["start"] - last_end) if last_end is not None else 0.0

        join_len = len((" ".join([x["text"] for x in cur] + [token])).strip())
        need_new = False
        if last_end is not None and gap > max_gap_s:
            need_new = True
        if cur and len(cur) >= max_words:
            need_new = True
        if (not need_new) and (max_chars is not None) and (join_len > max_chars):
            need_new = True

        if need_new and cur:
            lines.append(cur)
            cur = []

        cur.append({"start": float(w["start"]), "end": float(w["end"]), "text": token})
        last_end = float(w["end"])

    if cur:
        lines.append(cur)
    return lines

def build_center_caption_events(lines,
                                play_w: int, play_h: int,
                                uppercase=True,
                                min_caption=0.30,
                                cut_ahead=0.00,
                                tail_hold=1.20,
                                anim="none",
                                in_ms=220,
                                out_ms=100,
                                border_px=12.0,
                                stabilize_outline=True,
                                blur_px=0.0):
    cx = int(round(play_w / 2))
    cy = int(round(play_h / 2))
    events = []
    n = len(lines)
    for i, ln in enumerate(lines):
        t0 = float(ln[0]["start"])
        natural_end = float(ln[-1]["end"])
        t1 = max(natural_end, t0 + min_caption)

        if i + 1 < n:
            next_start = float(lines[i+1][0]["start"])
            gap_after = max(0.0, next_start - natural_end - cut_ahead)
            t1 = min(max(t1, natural_end + min(tail_hold, gap_after)), next_start - cut_ahead)
        else:
            t1 = max(natural_end + tail_hold, t0 + min_caption)

        if t1 <= t0:
            t1 = t0 + 0.05

        text = " ".join([w["text"] for w in ln]).strip()
        if uppercase:
            text = text.upper()

        ov = anim_tag(cx, cy, anim, in_ms, out_ms, border_px, stabilize_outline, blur_px)
        events.append(f"Dialogue: 0,{_fmt_time(t0)},{_fmt_time(t1)},Beast,,0,0,0,,{ov}{text}")
    return events

# ---------- resolve an intro image (file OR folder) -------------
def resolve_intro_image(src: Path | None) -> Path | None:
    if not src:
        print("[debug] resolve_intro_image: src=None")
        return None
    src = Path(src).expanduser()
    print(f"[debug] resolve_intro_image: candidate='{src}' exists={src.exists()} is_dir={src.is_dir()}")
    if src.exists():
        if src.is_file():
            return src
        # folder: pick first image
        allowed = {".png",".jpg",".jpeg",".webp",".bmp"}
        imgs = [f for f in sorted(src.iterdir()) if f.is_file() and f.suffix.lower() in allowed]
        return imgs[0] if imgs else None
    return None

# ---------- MAIN ----------------------------------------------------------
def beta_captions(INPUT_VIDEO: str | Path,
                  intro_card_src: Path | None = INTRO_CARD_SRC,
                  intro_enabled: bool = INTRO_ENABLED,
                  intro_secs: float = INTRO_SECS,
                  intro_fade: float = INTRO_FADE,
                  intro_scale: float = INTRO_SCALE,
                  intro_crop_bottom: float = INTRO_CROP_BOTTOM,
                  intro_offset_x: int = INTRO_OFFSET_X,
                  intro_offset_y: int = INTRO_OFFSET_Y,
                  intro_round_px: int = INTRO_ROUND_PX) -> str:

    video_path = Path(INPUT_VIDEO).expanduser().resolve()
    assert video_path.exists(), f"Video not found: {video_path}"
    print("[info] video:", video_path)

    PLAY_W, PLAY_H = probe_resolution(video_path) if AUTO_PLAYRES else (1920, 1080)
    if CENTER_X is None or CENTER_Y is None:
        cx, cy = PLAY_W // 2, PLAY_H // 2
    else:
        cx, cy = CENTER_X, CENTER_Y
    print(f"[info] PlayRes set to: {PLAY_W}x{PLAY_H} | Center=({cx},{cy})")

    print("[info] loading Whisper model …")
    model = load_whisper_auto(MODEL_NAME)

    print("[info] transcribing (word timestamps) …")
    segments, _ = model.transcribe(str(video_path), vad_filter=True, word_timestamps=True)

    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                tok = (w.word or "").strip()
                if tok:
                    words.append({"start": float(w.start), "end": float(w.end), "text": tok})

    print(f"[info] words captured: {len(words)}")

    # ---------- Build ASS ----------
    _, FONT_NAME = pick_custom_font(CUSTOM_FONT_DIR)
    ASS_HEADER = ASS_HEADER_TMPL.format(
        play_w=PLAY_W, play_h=PLAY_H, font=FONT_NAME, size=FONT_SIZE,
        border=_fmt_float(BORDER_PX), shadow=_fmt_float(SHADOW_PX)
    )

    caption_lines = group_words_to_captions(
        words,
        max_words=MAX_WORDS_PER_CAP,
        max_chars=MAX_CHARS_PER_CAP,
        max_gap_s=MAX_GAP_SEC
    )
    print(f"[info] caption groups built: {len(caption_lines)} "
          f"(max_words={MAX_WORDS_PER_CAP}, max_chars={MAX_CHARS_PER_CAP}, max_gap_s={MAX_GAP_SEC})")

    ass_events = build_center_caption_events(
        caption_lines,
        play_w=PLAY_W, play_h=PLAY_H,
        uppercase=UPPERCASE,
        min_caption=MIN_CAPTION_SEC,
        cut_ahead=CUT_AHEAD_SEC,
        tail_hold=TAIL_HOLD_SEC,
        anim=ANIM,
        in_ms=ANIM_IN_MS,
        out_ms=ANIM_OUT_MS,
        border_px=BORDER_PX,
        stabilize_outline=STABILIZE_OUTLINE,
        blur_px=BLUR_PX
    )
    ass_text = ASS_HEADER + "\n".join(ass_events)

    # ---------- Output path ----------
    out_dir = ensure_dir(Path(OUTPUT_DIR))
    ts = timestamp()
    out_name = FILENAME_TEMPLATE.format(stem=sanitize_stem(video_path.stem), ts=ts, anim=ANIM)
    out_video = (out_dir / out_name).resolve()
    out_tmp = out_video.with_suffix(".tmp.mp4")
    print("[info] OUTPUT_DIR:", out_dir)
    print("[info] Output file:", out_video)

    if not shutil.which("ffmpeg"):
        raise SystemExit("FFmpeg not found on PATH. Install it and rerun.")

    fontsdir_arg = f":fontsdir={CUSTOM_FONT_DIR.as_posix()}"

    tmp_path = None
    try:
        # write ASS to temp file
        with tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False, encoding="utf-8") as tmp:
            tmp.write(ass_text)
            tmp.flush()
            tmp_path = Path(tmp.name)

        vcodec = "h264_videotoolbox" if platform.system() == "Darwin" else "libx264"

        intro_img = resolve_intro_image(intro_card_src) if intro_enabled else None
        print(f"[debug] intro_enabled={intro_enabled} intro_secs={intro_secs} intro_fade={intro_fade}")
        print(f"[debug] resolved intro image: {intro_img}")

        if intro_img and intro_secs > 0:
            # subtitles chain for base video
            base_chain = (f"format=yuv444p,ass={tmp_path.as_posix()}{fontsdir_arg}"
                        if YUV444_RENDER else
                        f"ass={tmp_path.as_posix()}{fontsdir_arg}")

            fade_d     = max(0.0, min(float(intro_fade), float(intro_secs)))
            crop_keep  = max(0.0, min(1.0, 1.0 - float(intro_crop_bottom)))
            scale_frac = max(0.05, min(2.0, float(intro_scale)))
            scaled_w   = int(round(PLAY_W * scale_frac))
            if scaled_w % 2: scaled_w -= 1
            if scaled_w < 2: scaled_w = 2

            enable_expr = f"between(t\\,0\\,{intro_secs})"  # escape commas

            round_px = max(0, int(intro_round_px))
            print(f"[debug] overlay params: crop_keep={crop_keep} scale_frac={scale_frac} "
                f"scaled_w={scaled_w} fade_d={fade_d} offsets=({intro_offset_x},{intro_offset_y}) "
                f"round_px={round_px}")

            # Build the card-processing chain; if rounding requested, compute an alpha mask via geq()
            if round_px > 0:
                # alpha expression: 255 inside rounded-rect, 0 outside
                aexpr = (
                    f"if(lte(hypot("
                    f"if(lt(X,{round_px}),{round_px}-X,if(lt(W-X,{round_px}),{round_px}-(W-X),0)),"
                    f"if(lt(Y,{round_px}),{round_px}-Y,if(lt(H-Y,{round_px}),{round_px}-(H-Y),0))"
                    f"),{round_px}),255,0)"
                )
                card_chain = (
                    f"[cardc]scale={scaled_w}:-1[card_s];"
                    f"[card_s]format=rgba,"
                    f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{aexpr}'[card_r];"
                    f"[card_r]fade=t=out:st={intro_secs - fade_d}:d={fade_d}:alpha=1[cardf];"
                )
            else:
                card_chain = (
                    f"[cardc]scale={scaled_w}:-1[cards];"
                    f"[cards]fade=t=out:st={intro_secs - fade_d}:d={fade_d}:alpha=1[cardf];"
                )

            fc = (
                f"[0:v]{base_chain}[base];"
                f"[1:v]format=rgba,crop=iw:ih*{crop_keep}:0:0[cardc];"
                f"{card_chain}"
                f"[base][cardf]overlay="
                f"x=(main_w-overlay_w)/2+{int(intro_offset_x)}:"
                f"y=(main_h-overlay_h)/2+{int(intro_offset_y)}:"
                f"enable='{enable_expr}'[v];"
                f"[v]format=yuv420p[vout]"
            )
            print("[debug] filter_complex >>>\n" + fc + "\n<<< end filter_complex")


            cmd = [
                "ffmpeg","-y","-hide_banner","-loglevel","info",
                "-i", str(video_path),
                "-loop","1","-t", f"{intro_secs + 0.5}","-i", str(intro_img),
                "-filter_complex", fc,
                "-map","[vout]","-map","0:a?",
                "-c:v", vcodec, "-preset","veryfast","-crf","18",
                "-c:a","copy",
                "-movflags","+faststart",
                str(out_tmp)
            ]
        else:
            vf_arg = (f"format=yuv444p,ass={tmp_path.as_posix()}{fontsdir_arg},format=yuv420p"
                      if YUV444_RENDER else
                      f"ass={tmp_path.as_posix()}{fontsdir_arg}")
            cmd = [
                "ffmpeg","-y","-hide_banner","-loglevel","info",
                "-i", str(video_path),
                "-vf", vf_arg,
                "-c:v", vcodec, "-preset","veryfast","-crf","18",
                "-c:a","copy",
                "-movflags","+faststart",
                str(out_tmp)
            ]

        print("[info] ffmpeg cmd:", " ".join(cmd))
        run = subprocess.run(cmd, check=False, text=True, capture_output=True)
        if run.returncode != 0:
            # show head/tail to diagnose
            err = run.stderr or ""
            head = "\n".join(err.splitlines()[:20])
            tail = "\n".join(err.splitlines()[-20:])
            print("\n[ffmpeg stderr — head]\n" + head + "\n")
            print("[ffmpeg stderr — tail]\n" + tail + "\n")
            print("[ffmpeg stderr — end]")
            raise RuntimeError(f"ffmpeg failed (code {run.returncode})")

        out_tmp.replace(out_video)
        print("[done] saved:", out_video)

    finally:
        if tmp_path and tmp_path.exists():
            try: tmp_path.unlink()
            except Exception as e: print(f"[warn] could not delete temp ASS: {e}")
        if out_tmp.exists():
            try: out_tmp.unlink()
            except Exception: pass

    if not out_video.exists():
        raise FileNotFoundError(f"Expected output not found: {out_video}")
    return out_video.as_posix()
