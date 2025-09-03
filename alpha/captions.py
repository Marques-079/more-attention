# === CONFIG ==============================================================
from pathlib import Path
INPUT_VIDEO       = Path.home() / "Downloads" / "My Video-1.mp4"
MODEL_NAME        = "small.en"       # tiny/base/small/medium/large-v3; *.en faster for English
FONT_SIZE         = 220              # hyperparameter: caption size
CENTER_X, CENTER_Y= 960, 540         # center for 1920x1080; change for other resolutions
UPPERCASE         = True             # ALL CAPS for captions

# Timing hyperparams
MIN_CAPTION_SEC   = 0.30             # minimum on-screen time per caption (readability)
CUT_AHEAD_SEC     = 0.00             # end each caption slightly before next starts (one-at-a-time)
TAIL_HOLD_SEC     = 1.20             # NEW: extra hold after caption, capped to avoid overlap with next

# Grouping hyperparams (control words/characters per caption)
MAX_WORDS_PER_CAP = 1                # e.g., 1 = one word per card; set 2, 3, ... to show more
MAX_CHARS_PER_CAP = None             # e.g., 18; or None to ignore char limit
MAX_GAP_SEC       = 1.20             # start a new caption if silence/gap exceeds this

# Font: drop your .ttf/.otf here (no system install needed)
CUSTOM_FONT_DIR   = Path.home() / "Documents" / "mrbeast_caps" / "fonts"

# Animation hyperparameters
# ANIM choices: "none", "fade", "pop", "zoom", "bounce", "slide_up", "slide_down",
#               "slide_left", "slide_right", "rotate", "inflate", "inflate_soft"
ANIM              = "inflate"
ANIM_IN_MS        = 20000   # main appear time (ms) for transform/move
ANIM_OUT_MS       = 50      # fade-out tail (used by 'fade'; others ignore)
# ========================================================================

import subprocess, shutil, platform, re, sys
from datetime import timedelta
from faster_whisper import WhisperModel
from tqdm.auto import tqdm

# ---------- load Whisper with a supported compute_type ----------
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

# ---------- font: use any .ttf/.otf in CUSTOM_FONT_DIR ----------
def pick_custom_font(font_dir: Path):
    font_dir.mkdir(parents=True, exist_ok=True)
    candidates = list(font_dir.glob("*.ttf")) + list(font_dir.glob("*.otf"))
    if not candidates:
        print("\n[FONT SETUP REQUIRED]")
        print("1) Download any .ttf or .otf font.")
        print(f"2) Place it here: {font_dir}")
        print("3) Re-run this cell.")
        raise SystemExit("[exit] No font found yet.")
    font_file = candidates[0]
    family = None
    try:
        from fontTools.ttLib import TTFont  # optional (pip install fonttools)
        tt = TTFont(font_file)
        names = {n.nameID: n.toUnicode() for n in tt["name"].names if n.toUnicode()}
        family = names.get(1) or names.get(4)
    except Exception:
        family = font_file.stem
    print("[font] Using file:", font_file)
    print("[font] Font family set to:", family)
    return font_file, family

# ---------- ASS header (centered, white text, thick black outline) ----------
ASS_HEADER_TMPL = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
; White text (Primary), THICK black outline, subtle shadow for separation.
Style: Beast,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,12,2,5,60,60,60,1

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

def anim_tag(cx: int, cy: int, name: str, in_ms: int, out_ms: int) -> str:
    name = (name or "none").lower()
    if name == "none":
        return r"{\an5\pos(" + f"{cx},{cy}" + r")}"
    if name == "fade":
        return r"{\an5\pos(" + f"{cx},{cy}" + r")\fad(" + f"{in_ms},{out_ms}" + r")}"
    if name == "pop":
        return r"{\an5\pos(" + f"{cx},{cy}" + r")\fscx80\fscy80\t(0," + f"{in_ms}" + r",\fscx100\fscy100)}"
    if name == "zoom":
        return r"{\an5\pos(" + f"{cx},{cy}" + r")\fscx60\fscy60\t(0," + f"{in_ms}" + r",\fscx100\fscy100)}"
    if name == "bounce":
        return (r"{\an5\move(" + f"{cx},{cy-40},{cx},{cy},0,{in_ms}" + r")"
                r"\fscx120\fscy120\t(0,120,\fscx95\fscy95)\t(120," + f"{in_ms}" + r",\fscx100\fscy100)}")
    if name == "slide_up":
        return r"{\an5\move(" + f"{cx},{cy+60},{cx},{cy},0,{in_ms}" + r")}"
    if name == "slide_down":
        return r"{\an5\move(" + f"{cx},{cy-60},{cx},{cy},0,{in_ms}" + r")}"
    if name == "slide_left":
        return r"{\an5\move(" + f"{cx-140},{cy},{cx},{cy},0,{in_ms}" + r")}"
    if name == "slide_right":
        return r"{\an5\move(" + f"{cx+140},{cy},{cx},{cy},0,{in_ms}" + r")}"
    if name == "rotate":
        return r"{\an5\pos(" + f"{cx},{cy}" + r")\frz-12\t(0," + f"{in_ms}" + r",\frz0)}"
    if name == "inflate":
        # clean blow-up: scale 80% -> 100%, no move/overshoot
        return r"{\an5\pos(" + f"{cx},{cy}" + r")\fscx80\fscy80\t(0," + f"{in_ms}" + r",\fscx100\fscy100)}"
    if name == "inflate_soft":
        # blow-up with slight blur fade for smoother edges
        return (r"{\an5\pos(" + f"{cx},{cy}" + r")\fscx80\fscy80\blur2\alpha&H20&"
                r"\t(0," + f"{in_ms}" + r",\fscx100\fscy100\blur0\alpha&H00&)}")
    return r"{\an5\pos(" + f"{cx},{cy}" + r")}"

# ---------- Group words into captions (by count/chars and pauses) ----------
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
                                center_xy=(960,540),
                                uppercase=True,
                                min_caption=0.30,
                                cut_ahead=0.00,
                                tail_hold=1.20,
                                anim="none",
                                in_ms=220,
                                out_ms=100):
    """
    Build ASS Dialogue lines from grouped captions.
    - Ensures one-at-a-time (by capping end at next_start - cut_ahead)
    - Extends each caption by up to `tail_hold` seconds into silence,
      but never overlaps the next caption.
    """
    cx, cy = center_xy
    events = []
    n = len(lines)
    for i, ln in enumerate(lines):
        t0 = float(ln[0]["start"])
        natural_end = float(ln[-1]["end"])
        # base end: at least natural end or min_caption
        t1 = max(natural_end, t0 + min_caption)

        if i + 1 < n:
            next_start = float(lines[i+1][0]["start"])
            # available gap after this caption (minus safety cut)
            gap_after = max(0.0, next_start - natural_end - cut_ahead)
            # extend by up to tail_hold, but not beyond the next caption
            t1 = min(max(t1, natural_end + min(tail_hold, gap_after)), next_start - cut_ahead)
        else:
            # last caption: freely extend by tail_hold
            t1 = natural_end + tail_hold
            # still honor min_caption
            t1 = max(t1, t0 + min_caption)

        if t1 <= t0:
            t1 = t0 + 0.05

        text = " ".join([w["text"] for w in ln]).strip()
        if uppercase:
            text = text.upper()
        ov = anim_tag(cx, cy, anim, in_ms, out_ms)
        events.append(f"Dialogue: 0,{_fmt_time(t0)},{_fmt_time(t1)},Beast,,0,0,0,,{ov}{text}")
    return events


# ============= CALLABLE FUNCTION: wraps entire pipeline ======================
from pathlib import Path
from tqdm.auto import tqdm
import re, shutil, platform, subprocess

# add these at the top of your file (with your other imports)
import tempfile, os
from pathlib import Path
import re, shutil, platform, subprocess
from tqdm.auto import tqdm

def build_mrbeast_captions(input_mp4: str | Path,
                           output_dir: str | Path = Path.home() / "Downloads",
                           output_name: str | None = None,
                           keep_ass: bool = False) -> Path:
    """
    Full pipeline; writes only the final MP4 by default.
    Set keep_ass=True if you want to keep the .ass file.
    """
    steps = ["Validate input", "Load Whisper", "Transcribe", "Build ASS", "Write ASS", "FFmpeg burn"]
    with tqdm(total=len(steps), desc="MrBeast Caption Pipeline", unit="step") as pbar:
        # 1) Validate input
        video_path = Path(input_mp4).expanduser().resolve()
        assert video_path.exists(), f"Video not found: {video_path}"
        print("[info] video:", video_path)
        pbar.update(1)

        # 2) Load Whisper
        print("[info] loading Whisper model …")
        model = load_whisper_auto(MODEL_NAME)
        pbar.update(1)

        # 3) Transcribe
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
        pbar.update(1)

        # 4) Build ASS text (unchanged)
        font_file, FONT_NAME = pick_custom_font(CUSTOM_FONT_DIR)
        ASS_HEADER = ASS_HEADER_TMPL.format(font=FONT_NAME, size=FONT_SIZE)
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
            center_xy=(CENTER_X, CENTER_Y),
            uppercase=UPPERCASE,
            min_caption=MIN_CAPTION_SEC,
            cut_ahead=CUT_AHEAD_SEC,
            tail_hold=TAIL_HOLD_SEC,
            anim=ANIM,
            in_ms=ANIM_IN_MS,
            out_ms=ANIM_OUT_MS
        )
        ass_text = ASS_HEADER + "\n".join(ass_events)
        pbar.update(1)

        # 5) Resolve output paths
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = re.sub(r'[^A-Za-z0-9_.-]+', '_', video_path.stem)
        stem = output_name if output_name else safe_stem

        # Write ASS either permanently or to a temp file
        if keep_ass:
            ass_path = output_dir / f"{stem}_auto.ass"
            ass_path.write_text(ass_text, encoding="utf-8")
            print("[info] wrote ASS:", ass_path)
        else:
            fd, tmp = tempfile.mkstemp(prefix=f"{stem}_", suffix=".ass")
            os.close(fd)
            ass_path = Path(tmp)
            ass_path.write_text(ass_text, encoding="utf-8")
            print("[info] using temporary ASS:", ass_path.name)
        print("[check] FONT =", FONT_NAME, "| SIZE =", FONT_SIZE, "| ANIM =", ANIM)
        pbar.update(1)

        # 6) Burn with FFmpeg
        if not shutil.which("ffmpeg"):
            raise SystemExit("FFmpeg not found on PATH. Install it and rerun.")

        fontsdir_arg = f":fontsdir={CUSTOM_FONT_DIR.as_posix()}"
        out_video = output_dir / f"{stem}.mp4"  # or keep your old suffix pattern
        vcodec = "h264_videotoolbox" if platform.system() == "Darwin" else "libx264"
        vf_arg = f"ass={ass_path.as_posix()}{fontsdir_arg}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf_arg,
            "-c:v", vcodec, "-preset", "veryfast", "-crf", "18",
            "-c:a", "copy",
            str(out_video)
        ]
        print("[info] running FFmpeg with filter:", vf_arg)
        try:
            subprocess.run(cmd, check=True)
            print("[done] saved:", out_video)
        finally:
            if not keep_ass:
                try:
                    ass_path.unlink()
                except FileNotFoundError:
                    pass
        pbar.update(1)

        return out_video

