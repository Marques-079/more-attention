# alpha/voice.py
print('Hi from alpha/voice.py')

import os, glob, io, time
import numpy as np
import soundfile as sf

try:
    from IPython.display import Audio, display  # optional
    _HAS_IPY = True
except Exception:
    _HAS_IPY = False
    class Audio:  # tiny stub so imports never fail
        def __init__(self, *_a, **_k): ...
    def display(*_a, **_k): ...

from kokoro_onnx import Kokoro, SAMPLE_RATE

# ----- asset discovery -----
def _resolve_kokoro_assets():
    print("[kokoro] resolving asset paths…", flush=True)
    m = os.getenv("KOKORO_MODEL")
    v = os.getenv("KOKORO_VOICES")

    def pick(patterns):
        base = os.path.expanduser("~/.cache/kokoro_assets")
        for pat in patterns:
            hits = sorted(glob.glob(os.path.join(base, pat)))
            if hits:
                return hits[-1]
        return None

    if not m or not os.path.exists(m):
        print("[kokoro] env KOKORO_MODEL not set or missing; searching ~/.cache/kokoro_assets/*.onnx", flush=True)
        m = pick(["*.onnx"])
    if not v or not os.path.exists(v):
        print("[kokoro] env KOKORO_VOICES not set or missing; searching ~/.cache/kokoro_assets/*voices*.* / voices.* / *.bin / *.json", flush=True)
        v = pick(["*voices*.*", "voices.*", "*.bin", "*.json"])

    if not (m and os.path.exists(m) and v and os.path.exists(v)):
        raise FileNotFoundError(
            "Kokoro assets not found.\n"
            "Set KOKORO_MODEL and KOKORO_VOICES env vars, "
            "or put files in ~/.cache/kokoro_assets/"
        )

    print(f"[kokoro] using model:  {m}", flush=True)
    print(f"[kokoro] using voices: {v}", flush=True)
    return m, v

MODEL_PATH, VOICES_PATH = _resolve_kokoro_assets()
print("[kokoro] initializing TTS engine…", flush=True)
_TTS = Kokoro(MODEL_PATH, VOICES_PATH)
print("[kokoro] TTS engine initialized.", flush=True)

def _to_mono_float32(y):
    if isinstance(y, (list, tuple)) and len(y) > 0:
        y = y[0]
    a = np.asarray(y, dtype=np.float32)
    if a.ndim == 2 and a.shape[0] in (1, 2):  # (channels, samples)
        a = np.mean(a, axis=0).astype(np.float32)
    return a

def compile_audio(text: str, voice: str = "am_adam", speed: float = 1.05, rate: int = SAMPLE_RATE):
    print(f"[kokoro] synth start | voice={voice} speed={speed} sr={rate} text_len={len(text)}", flush=True)
    t0 = time.perf_counter()
    y = _TTS.create(text, voice=voice, speed=speed)  # ndarray or (L,R)
    t1 = time.perf_counter()
    try:
        y_shape = np.asarray(y).shape
    except Exception:
        y_shape = "<unknown>"
    print(f"[kokoro] synth done in {(t1 - t0)*1000:.0f} ms | raw_shape={y_shape}", flush=True)

    audio = _to_mono_float32(y)
    print(f"[kokoro] converted to mono float32 | samples={audio.shape[0]}", flush=True)

    if _HAS_IPY:
        try:
            print("[kokoro] IPython detected → previewing audio inline…", flush=True)
            display(Audio(audio, rate=rate, autoplay=True))
        except Exception as e:
            print(f"[kokoro] IPython preview skipped: {e}", flush=True)

    buf = io.BytesIO()
    print("[kokoro] writing WAV to in-memory buffer…", flush=True)
    with sf.SoundFile(buf, mode="w", samplerate=rate, channels=1, format="WAV", subtype="FLOAT") as f:
        f.write(audio)
    byte_len = buf.getbuffer().nbytes
    buf.seek(0)
    dur = sf.info(buf).duration
    print(f"[kokoro] done | duration={dur:.2f}s bytes={byte_len}", flush=True)
    return buf.getvalue(), dur
