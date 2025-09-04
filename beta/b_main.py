from __future__ import annotations
# ---------------------------------------------

from pathlib import Path
from datetime import datetime
import re, subprocess, json  # NEW: subprocess, json for ffprobe
import time
import pyautogui

from editing_b import beta_make_edits
from script_b import generate_script2
from voice_b import compile_audio
from captions_b import beta_captions
from thumbnail_b import generate_thumbnail
from upload_b import upload_youtube2  # v2 for channel-specific upload

# --- helper: verify "Shorts rules" on the final rendered file ---
def assert_is_short_and_vertical(video_path: str, *, max_seconds: int = 180) -> tuple[int, int, float]:
    """
    Ensures the uploaded file will be classified as a Short:
    - duration <= 180s (YouTube now supports up to 3 minutes for Shorts)
    - portrait or square aspect (h >= w)
    Returns (width, height, duration_seconds)
    """
    # Requires ffprobe in PATH
    out = subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height:format=duration",
        "-of","json", video_path
    ])
    info = json.loads(out.decode("utf-8"))
    w = int(info["streams"][0]["width"])
    h = int(info["streams"][0]["height"])
    dur = float(info["format"]["duration"])

    if dur > max_seconds:
        raise ValueError(f"Video is {dur:.2f}s. Shorts must be <= {max_seconds}s.")
    if h < w:
        raise ValueError(f"Video is {w}x{h} (landscape). Shorts must be square or vertical.")
    return w, h, dur

def clean_script_text(text: str, *, replace_commas=True, preserve_numeric_commas=True) -> str:
    s = re.sub(r'\s*[\r\n]+\s*', ' ', text)
    s = re.sub(r'[ \t\u00A0]+', ' ', s)
    if replace_commas:
        if preserve_numeric_commas:
            s = re.sub(r'(?<!\d)\s*,\s*(?!\d)', ' - ', s)
        else:
            s = re.sub(r'\s*,\s*', ' - ', s)
        s = re.sub(r'\s*-\s*', ' - ', s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s

print('Operating now...')

TITLE = "[FULL STORY] My Roommate Tried To Ruin My Life, So I Planned A Payback She’ll Never Forget.."
DESCRIPTION = "\n".join([
    "Daily stories to help with life's emotional damage 🗣🔥🔥",
    "",
    "We write original first person dramas inspired by real life.",
    "We adapt, condense, and sometimes combine elements for pacing. Names and timelines changed.",
    "Hit play and enjoy.",
    "",  # keep a blank line before hashtags
    "#Shorts"  # NEW (optional, for discovery)
])
HASHTAGS = "#aita  #reddit #redditstoriesfullstory   #redditconfessions  #relationshipstories   #redditfamilydrama #redditreadings #betrayal #relationshipdrama #Shorts"  # NEW
TAGS = ["redditfamilydrama", "reddit", "redditrelationship", "shorts"]  # NEW
SCHEDULE_AT_LOCAL = None
MODE = "private"  # switch to "public" when ready




text = '''
Throwaway because my IRL circle knows my main, and this is the kind of thing you don’t get to unsay once.
'''
text = clean_script_text(text)

# TTS
wav_bytes, duration_sec = compile_audio(text)

# Save audio
INBOX = Path("/Users/marcus/Movies/FilmoraInbox/reddit1_pipeline")
INBOX.mkdir(parents=True, exist_ok=True)
file_path  = INBOX / f"voice_{datetime.now():%Y%m%d_%H%M%S}.wav"
file_path.write_bytes(wav_bytes)
target_dir_audio  = file_path.parent.as_posix()
target_name_audio = file_path.name

# Build video in Filmora
export_title = beta_make_edits(1, duration_sec, target_dir_audio, target_name_audio)
combined_no_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_clipstore/{export_title}.mp4"

# Captions pass
out = beta_captions(combined_no_captions_path)
combined_yes_captions_path = out









# Thumbnail
thumbnail_script = text[:1000]
thumbnail_path = generate_thumbnail(
    template_choice=0, script_text=thumbnail_script,
    font_size=46, line_spacing_px=6, font_weight="bold",
    thickness_px=0.5, use_ellipsis=True
)

# --- NEW: verify the final render qualifies as a Short ---
w, h, dur = assert_is_short_and_vertical(combined_yes_captions_path, max_seconds=180)  # keep 60 if you prefer stricter
print(f"Final render: {w}x{h}, {dur:.2f}s -> OK for Shorts.")

# --- Upload (uncomment when ready) ---
upload_youtube2(
    combined_yes_captions_path,
    thumbnail_path,
    TITLE,
    DESCRIPTION,
    HASHTAGS,
    TAGS,
    MODE,
    SCHEDULE_AT_LOCAL,
    channel_api_json="whatreallyhappened.json"
)
print(f"This is thumbnail path {thumbnail_path}, This is video path {combined_yes_captions_path}")
