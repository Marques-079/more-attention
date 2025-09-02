from pathlib import Path
from datetime import datetime

from editing import make_edits
from script import get_script
from voice import compile_audio



#MOC SCRIPT CALL
# with open("/Users/marcus/Documents/GitHub/more-attention/app/scripts/gen_scripts/1text.txt", "r", encoding="utf-8") as f:
#   text = f.read()

text = "Its a great day to win isn't is Sir?"

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

make_edits(1, duration_sec, target_dir_audio, target_name_audio) #Number indicates what background to use


