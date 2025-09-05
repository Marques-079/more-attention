print("0")
from kokoro import KPipeline
print("1")
from IPython.display import display, Audio
print
import soundfile as sf
print("3")
import io
print("4")
import numpy as np
print("5")


print("Defining functions...")
def compile_audio(text):
    pipeline = KPipeline(lang_code='a')   # 'a' = American English
    voice   = "am_adam"
    speed   = 1.05
    rate    = 24000

    # Stream chunks directly into an in-memory WAV (FLOAT = highest quality)
    buf = io.BytesIO()
    with sf.SoundFile(buf, mode="w", samplerate=rate, channels=1,
                      format="WAV", subtype="FLOAT") as f:
        for i, (gs, ps, audio) in enumerate(pipeline(text, voice=voice, speed=speed)):
            display(Audio(audio, rate=rate, autoplay=(i == 0)))
            f.write(np.asarray(audio, dtype="float32"))

    buf.seek(0)
    duration_sec = sf.info(buf).duration
    wav_bytes = buf.getvalue()
    print("Audio compiled")
    return wav_bytes, duration_sec
