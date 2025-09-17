# Content background

TL;DR. End-to-end system that turns a short idea into a fully produced YouTube video: script → thumbnail → voiceover → edited video with burned-in subtitles → scheduled post. It’s reproducible, observable, and cheap enough to run daily.

I was bored in the holidays and saw how all these faceless channels, ranging from documentries, reddit stories, ASMR content all garner in millions of views on the daily. 
Why not make our own pipeline to automate this process! To generate a video all youll need is to input the idea into the alpha_ideas.txt file and hit run. The pipeline handles the rest from scriping, voice generation, editing, subtittles and posting. 

Next steps : If I retouch this project the next step would be to expand the abilties of the generation pipeline, expand its reach to use non-stock footage. ( whileabiding to youtube transformative content policies) <br>

<p align="center">
  <img src="https://github.com/Marques-079/more-attention/blob/32d1287549eb9170fbe5875a924d2211ef6e6a25/app/Minmap%20attention.png"
       width="1000"  alt="gif1">
</p>

---

The only cost you will incur is on script generation using gpt-5 or gpt-5 nano. Per video depending on lenght the total cost will amount to 0.08 cents or >0.01 respectively ($NZD)

Opensource software really came in clutch for this project using Kokoros 82 million paramters text-to-speech (TTS) and OpenAI's faster-whisper model for captions. 
These workarounds LEGALLY generate results comparable to paid software like ElevenLabs and Filmora's in house autocaptions (costs money for tokens) 

---
# Editing warmup with an Example video 

P.S. Sorry for bad quality but I had to quantize the heck out of the screen recording 💀 
<p align="left">
  <img src="https://github.com/Marques-079/more-attention/blob/72f80ae79793b5626e3ff5acf8b8a2745e5362c9/app/ezgif.com-optimize.gif"
       width="1000"  alt="gif1">
</p>

---

Idea sources ─┬─> Script (OpenAI JSON schema)
              ├─> Voice (Kokoro TTS)
              ├─> Thumbnail (template engine)
              └─> Edit & Export (Filmora automation)
                           └─> Subtitles (ASR + burn-in)
                                   └─> YouTube API (upload/schedule)


• Script (OpenAI JSON schema) : 
    Tech : OpenAI w/ JSON schema (Pydantic), prompt versions pinned
    Implementation : LLM returns validated JSON (title, beats, VO, thumb text, metadata); auto-repair on parse errors
    Cost : > 0.01 cents - 0.08 cents (NZD)
    
• Voice (Kokoro TTS): 
    Tech : Kokoro TTS, SSML, WAV concat, LUFS normalization
    Implementation : Paragraph chunks → synthesize → normalize to ~-16 LUFS → join → runs/<id>/audio.wav
    Cost : Free (Apache-2.0 licensing)
    
• Thumbnail (template engine) : 
    Tech : Pillow (dynamic text fitting), safe margins, extraction from script
    Implementation : Apply template + binary-search font size → export high-DPI PNG → optional A/B variants
    Cost : Free (MIT licensing)
    
• Edit & Export (Filmora automation) : 
    Tech : Filmora 14 via AppleScript; ffmpeg fallback
    Implementation : Import VO + assets → place to VO timestamps → apply captions/style → export MP4 (9:16 or 16:9)
    Cost : $40 dollars p/a
    
    
• Subtitles (ASR + burn-in): 
    Tech : LLM script timings or Whisper ASR check; SRT/VTT; ffmpeg burn over
    Implementation : Generate SRT → style → burn-in to final MP4; also keep sidecar captions
    Cost : Free (MIT licensing)

• YouTube API (upload/schedule): 
    Tech : Google API client, OAuth per channel
    Implementation : Upload video + thumbnail → set title/desc/tags/visibility → schedule in local TZ
    Cost : Free (Apache-2.0 licensing)

Total fixed cost: $40
Total variable costs : Dependant of video
                                   

---

# Results using Stock Footage and Fake Script

<p align="left">
  <img src="https://github.com/Marques-079/more-attention/blob/30703779f257f6bc6a5a8035c3871deca44fc132/app/Demo1-moreatt1-ezgif.com-video-to-gif-converter.gif"
       width="1000"  alt="gif1">
</p>

---

# Final note 

As LLMs and video generation models such as Veo3 improve, I believe we will see an even greater amount of fully AI generated content. Although as of now, its quality does not come even close to human edited content, but rapid model and tooling advances will soon make it competitive and in some domains, practically indistinguishable; this raising new questions about attribution and trust.




