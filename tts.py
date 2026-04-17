import hashlib
import io
import os
import numpy as np
import soundfile as sf

AUDIO_CACHE_DIR = os.path.join(os.path.dirname(__file__), "audio_cache")


def _cache_path(url_hash: str) -> str:
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    return os.path.join(AUDIO_CACHE_DIR, f"{url_hash}.mp3")


def is_cached(url_hash: str) -> bool:
    return os.path.isfile(_cache_path(url_hash))


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def generate_audio(text: str, url_hash: str) -> str:
    cache_file = _cache_path(url_hash)
    if os.path.isfile(cache_file):
        return cache_file

    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="a")

    audio_chunks = []
    for _, _, audio in pipeline(text, voice="af_heart", speed=1.0, split_pattern=r"\n+"):
        if audio is not None and len(audio) > 0:
            audio_chunks.append(audio)

    if not audio_chunks:
        raise RuntimeError("TTS pipeline produced no audio output.")

    combined = np.concatenate(audio_chunks)

    buf = io.BytesIO()
    sf.write(buf, combined, samplerate=24000, format="MP3")
    buf.seek(0)

    with open(cache_file, "wb") as f:
        f.write(buf.read())

    return cache_file
