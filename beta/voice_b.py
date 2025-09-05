from kokoro import KPipeline
from IPython.display import display, Audio
import soundfile as sf
import io
import numpy as np

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


def showtime(text: str) -> float:
    """
    Return the spoken duration (seconds) for `text` using Kokoro
    with the same config as compile_audio: lang 'a', voice 'am_adam',
    speed 1.05, rate 24000. Does not save or play audio.
    """
    pipeline = KPipeline(lang_code='a')   # American English
    voice    = "am_adam"
    speed    = 1.05
    rate     = 24000

    total_samples = 0
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        a = np.asarray(audio, dtype=np.float32)
        total_samples += a.shape[0]

    duration_sec = total_samples / float(rate)
    return duration_sec