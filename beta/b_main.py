from __future__ import annotations
# ---------------------------------------------

from pathlib import Path
from datetime import datetime
import re, subprocess, json 
import time
import pyautogui

from editing_b import beta_make_edits
from script_b import generate_script2
from voice_b import compile_audio, showtime
from captions_b import beta_captions
from thumbnail_b import render_black_topleft
from upload_b import upload_youtube2  # v2 for channel-specific upload
from first_sentence_b import first_sentence

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

DESCRIPTION = "\n".join([
    "Daily stories to help with life's emotional damage 🗣🔥🔥",
    "#Shorts"  # NEW (optional, for discovery)
])
HASHTAGS = "#aita  #redditconfessions  #relationshipstories #redditfamilydrama #redditreadings #betrayal #relationshipdrama #Shorts" 
TAGS = ["redditfamilydrama", "reddit", "redditrelationship", "shorts"]  
SCHEDULE_AT_LOCAL = None
MODE = "private"  # switch to "public" when ready


#=========#=========#=========#=========#=========#=========#SCRIPT===#=========#=========#=========#=========#=========#=========#=========#=========#=========#========

print("Generating script...")
text = '''
Ever watch a hundred electricians drink a bar dry in two hours?

I used to run Christmas parties at a golf club.
Some nights were quiet. Some were chaos.
This one was a big electrical company after a day on the course.

Problem: no bar package set. No limit. No rules.
We pause service and check with their managers.
The CEO strolls in—gold watch, Range Rover at the door—and waves it off.
Open bar. Everything.

I double-check: any cap, any exclusions?
He shrugs. Open the whole bar.

So we start pouring.
Shots line the counter.
Top-shelf whiskey gets drowned in coke.
Half-finished $50 drinks pile up on tables like decoration.

Two hours in, the till says ~$20,000.
We ask if we should stop.
He starts to panic. Sends everyone home.
Then he says it isn’t right and he won’t pay.

But we’ve got the order, the receipts, the timestamps.
He looks wrecked—realizing he approved a free-for-all for a hundred thirsty coworkers.

We close the doors, clear the battlefield of untouched cocktails, and lock the tab.
Next day, new rule: no open bar without a signed limit—ever again.
'''
text = clean_script_text(text)
thumbnail_sentence = first_sentence(text)
display_time = showtime(thumbnail_sentence)

TITLE = thumbnail_sentence


#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========

# Thumbnail
thumbnail_box_path = render_black_topleft(
    image_path="/Users/marcus/Downloads/Shorts_thumbv2w.png",
    text=thumbnail_sentence,
    box=(40, 235, 1200, 200),              # (x, y, w, h) — the white card area
    out_dir="/Users/marcus/Downloads/shorts_thumbnails_storage",
    font_size=70,                         # target “X size”
    min_font=48,
    line_spacing=1.42,
    letter_spacing_px=0,                   # normal spacing
    space_extra_px=4,                     # widen spaces a bit
    bold_px=1.55,                             # thickness (0=normal, try 2–4 for bold)
    # font_path=None,                      # leave None to auto-find Arial
)

# TTS
wav_bytes, duration_sec = compile_audio(text)

# Save audio
INBOX = Path("/Users/marcus/Movies/FilmoraInbox/reddit1_pipeline")
INBOX.mkdir(parents=True, exist_ok=True)
file_path  = INBOX / f"voice_{datetime.now():%Y%m%d_%H%M%S}.wav"
file_path.write_bytes(wav_bytes)
target_dir_audio  = file_path.parent.as_posix()
target_name_audio = file_path.name

# Build video in Filmora (CHANGE MEDIA)
export_title = beta_make_edits(9, duration_sec, target_dir_audio, target_name_audio)
combined_no_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_clipstore/{export_title}.mp4"

#Captions with thumbnail
combined_yes_captions_path = beta_captions(
    combined_no_captions_path,
    intro_card_src=thumbnail_box_path,
    intro_secs=display_time - 0.3,
    intro_fade=0.1,
    intro_scale=0.80,
    intro_crop_bottom=0.25,
    intro_offset_x=0,
    intro_offset_y=0,
    intro_round_px=45
)


# --- NEW: verify the final render qualifies as a Short ---
w, h, dur = assert_is_short_and_vertical(combined_yes_captions_path, max_seconds=180)  # keep 60 if you prefer stricter
print(f"Final render: {w}x{h}, {dur:.2f}s -> OK for Shorts.")

res = input("Upload to yt?")
# --- Upload (uncomment when ready) ---
if res == 'y':
    upload_youtube2(
        VIDEO_PATH = combined_yes_captions_path,
        THUMB_PATH = None,
        TITLE = TITLE,
        DESCRIPTION = DESCRIPTION,
        HASHTAGS = HASHTAGS,
        TAGS = TAGS,
        MODE = MODE,
        SCHEDULE_AT_LOCAL = SCHEDULE_AT_LOCAL,
        channel_api_json="whatreallyhappened.json"
    )
    print("SENT WOOSH")
else:
    print("Skipped upload.")
