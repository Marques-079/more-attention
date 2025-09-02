from pathlib import Path
from datetime import datetime

from editing import make_edits
from script import get_script
from voice import compile_audio



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

export_title = make_edits(4, duration_sec, target_dir_audio, target_name_audio) #Number indicates what background to use
print(export_title)


