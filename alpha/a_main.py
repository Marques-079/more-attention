from pathlib import Path
from datetime import datetime

from editing import make_edits
from script import get_script
from voice import compile_audio
from captions import build_mrbeast_captions
from thumbnail import generate_thumbnail


#MOC SCRIPT CALL
# with open("/Users/marcus/Documents/GitHub/more-attention/app/scripts/gen_scripts/1text.txt", "r", encoding="utf-8") as f:
#   text = f.read()

text = '''
Throwaway because my IRL circle knows my main - and this is the kind of thing you don’t get to unsay once it’s out there. Ages for context: me 36F - ex-husband 38M (let’s call him "Mark"), former friend 36F ("Lena"). And no - I don’t need legal advice; the divorce papers are signed and collecting dust in a folder I can’t quite bring myself to shred. What I need - apparently-  is to figure out when the floor disappeared from under me — and whether I’m the only one who heard the thud.

'''

#Convert text to speech (audio wav + duration seconds)
wav_bytes, duration_sec = compile_audio(text)

#Save clip to path
INBOX = Path("/Users/marcus/Movies/FilmoraInbox/reddit1_pipeline") 
INBOX.mkdir(parents=True, exist_ok=True)

file_path  = INBOX / f"voice_{datetime.now():%Y%m%d_%H%M%S}.wav"
file_path.write_bytes(wav_bytes)

target_dir_audio  = file_path.parent.as_posix()  # e.g. "/Users/marcus/Movies/FilmoraInbox/my_project"
target_name_audio = file_path.name               # e.g. "voice_20250902_141530.wav"

print(target_name_audio)

export_title = make_edits(1, duration_sec, target_dir_audio, target_name_audio) #Number indicates what background to use
print(export_title)

combined_no_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_clipstore/{export_title}.mp4"

out = build_mrbeast_captions(combined_no_captions_path, output_dir="/Users/marcus/Downloads/reddit1_filmora_captioned", output_name=f"exported_{export_title}", keep_ass = False)
combined_yes_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_captioned/exported_{export_title}.mp4"

thumbnail_script = ""

generate_thumbnail(template_choice=1, script_text=thumbnail_script, font_size=46, line_spacing_px=5, font_weight="bold", thickness_px=0.5, use_ellipsis=True)

#TODO 
'''
Generate thumbnail + templating
Finalised prompts for script generation and idea gathering prawn?
Setup Yt api and auto positings -> Many channels -> niches? 
shorts pipeline too
Setup automation for script generation -> voice -> video -> upload
'''