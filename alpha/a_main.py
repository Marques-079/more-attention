from pathlib import Path
from datetime import datetime
import re

from editing import make_edits
from script import get_script
from voice import compile_audio
from captions import build_mrbeast_captions
from thumbnail import generate_thumbnail
from upload_yt import upload_youtube

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


#MOC SCRIPT CALL
# with open("/Users/marcus/Documents/GitHub/more-attention/app/scripts/gen_scripts/1text.txt", "r", encoding="utf-8") as f:
#   text = f.read()

text = '''
Throwaway because my IRL circle knows my main, and this is the kind of thing you don’t get to unsay once it’s out there.. Ages for context: me 36F, ex-husband 38M (let’s call him "Mark"), former friend 36F ("Lena"). And no, I don’t need legal advice; the divorce papers are signed and collecting dust in a folder I can’t quite bring myself to shred. What I need, apparently, is to figure out when the floor disappeared from under me — and whether I’m the only one who heard the thud.. I am... exhausted. Like, bone-deep, burnt-toast exhausted. If there were a trophy for being the default adult, I’d have it in three sizes and dusted weekly: I paid the bills, I took care of his mother when she got sick, I planned birthdays and remember every allergy and appointment and sent cards to his coworkers when they had babies. I did what needed to be done. And, stupidly, I kept thinking: that’s what love is, right? The sweat and the lists and the load-bearing beams no one notices unless they fail.. This is the problem with being the load-bearing beam. Everyone leans on you. And then they call you rigid.. I met Mark through Lena. Let that sink in — I met my now-ex through my then-best friend. Fresh out of college, tiny apartment, sticky floors from the last tenants, our lives were cardboard boxes and borrowed mugs. Lena was my person — we shared clothes, shame, and microwave meals. She had a laugh that made strangers look up with a half-smile. Mark was in her circle; he was the "music guy" at house parties, always with a playlist and a good story. We clicked. He brought me a cup of coffee at a backyard barbecue in a chipped mug and we bantered about nothing important and it felt — inevitable.. From the beginning, Lena was... there. Front row. Facilitator. Cheerleader. She loved the way he and I bantered; she’d clap her hands and say, "Oh my GOD, you two," in a tone I interpreted as amusement. In the photos from those early days (back when we actually printed photos), you can see it: I’m leaning into Mark, his arm around my waist, and over my shoulder there’s Lena with that wide grin, eyes on him, not the camera. I thought it meant she was happy for me. That’s what I thought about everything with her — that she was happy for me.. We dated, we moved in together, we got a dog, we went to IKEA three times in one sweaty weekend and didn’t kill each other. We got married. Lena was my maid of honor. She planned the bachelorette and cried during her speech and made a scrapbook with captions written in her loopy handwriting. She also insisted on helping Mark write his vows — because "you know he struggles with words, babe; you’re the writer." I thought it was sweet. I was touched that she knew him so well, that she knew me so well, that she wanted to translate love across our style. But I am starting to suspect that wasn’t what she was translating.

'''
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

export_title = make_edits(3, duration_sec, target_dir_audio, target_name_audio) #Number indicates what background to use

#print(export_title)

combined_no_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_clipstore/{export_title}.mp4"

out = build_mrbeast_captions(combined_no_captions_path, output_dir="/Users/marcus/Downloads/reddit1_filmora_captioned", output_name=f"exported_{export_title}", keep_ass = False)
combined_yes_captions_path = f"/Users/marcus/Downloads/reddit1_filmora_captioned/exported_{export_title}.mp4"

thumbnail_script = "YAPYAP need to fix" #NEED TO OPTIMISE THIS SO WE GET GOOD CONTENT HERE 

thumbnail_path = generate_thumbnail(template_choice=1, script_text=thumbnail_script, font_size=46, line_spacing_px=5, font_weight="bold", thickness_px=0.5, use_ellipsis=True)

print(f"This is thumbnail path {thumbnail_path}, This is video path {combined_yes_captions_path}")







#upload_youtube(combined_yes_captions_path, thumbnail_path, TITLE, DESCRIPTION, HASHTAGS, TAGS, MODE, SCHEDULE_AT_LOCAL)

#TODO 
'''
Finalised prompts for script generation and idea gathering prawn?

Many channels -> niches? 

shorts pipeline too
'''

'''
Need to format script, remove /n and swap commas for '-'
'''