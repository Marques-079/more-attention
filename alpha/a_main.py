from pathlib import Path
from datetime import datetime
import re

from editing import make_edits
from script import get_script
from voice import compile_audio
from captions import build_mrbeast_captions
from thumbnail import generate_thumbnail
from upload_yt import upload_youtube

# ======  TITLE / DESCRIPTION / HASHTAGS HERE ===#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========
TITLE = "What Really Happened — AITA #42"
DESCRIPTION = (
    "In today’s episode, we break down a wild AITA post and what actually happened.\n"
    "Chapters:\n"
    "00:00 Intro\n"
    "00:25 The post\n"
    "03:10 Reactions\n"
    "04:55 Verdict"
)
HASHTAGS = "#AITA #Reddit #WhatReallyHappened #Shorts"  # Hashtags go in title/description text
TAGS = ["AITA", "Reddit", "storytime", "analysis"]      # Non-public tags array
SCHEDULE_AT_LOCAL = None #"2025-09-04 19:30"
# Choose a mode: "instant" | "scheduled" | "private"
MODE = "private"

#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========#=========

def clean_script_text(text: str, *, replace_commas=True, preserve_numeric_commas=True) -> str:
    s = re.sub(r'\s*[\r\n]+\s*', ' ', text)
    s = re.sub(r'[ \t\u00A0]+', ' ', s)

    # 3) Replace commas with dashes (add spaces around dash for TTS clarity)
    if replace_commas:
        if preserve_numeric_commas:
            # Replace commas NOT between digits
            s = re.sub(r'(?<!\d)\s*,\s*(?!\d)', ' - ', s)
        else:
            s = re.sub(r'\s*,\s*', ' - ', s)
        s = re.sub(r'\s*-\s*', ' - ', s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s
print('Operating now...')

#MOC SCRIPT CALL
with open("/Users/marcus/Documents/GitHub/more-attention/app/scripts/gen_scripts/2text.txt", "r", encoding="utf-8") as f:
  text = f.read()

# text = '''
# Throwaway because my IRL circle knows my main, and this is the kind of thing you don’t get to unsay once. I am up at 2am coding this project what the lock in?!, aight still got to configure the prompting also YIKES'''

text = clean_script_text(text)

#Convert text to speech (audio wav + duration seconds)
wav_bytes, duration_sec = compile_audio(text)

#Save clip to path
INBOX = Path("/Users/marcus/Movies/FilmoraInbox/reddit1_pipeline") 
INBOX.mkdir(parents=True, exist_ok=True)

file_path  = INBOX / f"voice_{datetime.now():%Y%m%d_%H%M%S}.wav"
file_path.write_bytes(wav_bytes)

target_dir_audio  = file_path.parent.as_posix()  # e.g. "/Users/marcus/Movies/FilmoraInbox/my_project"
target_name_audio = file_path.name               # e.g. "voice_20250902_141530.wav"

#print(target_name_audio)

export_title = make_edits(1, duration_sec, target_dir_audio, target_name_audio) #Number indicates what background to use

#print(export_title)

combined_no_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_clipstore/{export_title}.mp4"

out = build_mrbeast_captions(combined_no_captions_path, output_dir="/Users/marcus/Downloads/reddit1_filmora_captioned", output_name=f"exported_{export_title}", keep_ass = False)
combined_yes_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_captioned/exported_{export_title}.mp4"

thumbnail_script = "1212 lesgoo" #NEED TO OPTIMISE THIS SO WE GET GOOD CONTENT HERE 

thumbnail_path = generate_thumbnail(template_choice=1, script_text=thumbnail_script, font_size=46, line_spacing_px=5, font_weight="bold", thickness_px=0.5, use_ellipsis=True)

print(f"This is thumbnail path {thumbnail_path}, This is video path {combined_yes_captions_path}")


post_youtube = input("Do you want to post this to Youtube using API?")
if post_youtube.lower() == "y":
    upload_youtube(combined_yes_captions_path, thumbnail_path, TITLE, DESCRIPTION, HASHTAGS, TAGS, MODE, SCHEDULE_AT_LOCAL)
else:
    print("Not uploading to YouTube.")
    pass


#TODO 
'''
Finalised prompts for script generation and idea gathering prawn?

Many channels -> niches? 

shorts pipeline too
'''
