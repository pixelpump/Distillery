import hashlib
import io
import os
import re
import sys
import errno
import numpy as np
import soundfile as sf


def safe_print(message: str, file=sys.stderr):
    """Print to stderr, suppressing broken pipe errors."""
    try:
        print(message, file=file, flush=True)
    except (BrokenPipeError, IOError) as e:
        if e.errno != errno.EPIPE:
            raise

# When running inside a PyInstaller bundle, __file__ is in a read-only temp dir.
# Use a writable location under the user's home directory for the audio cache.
if getattr(sys, '_MEIPASS', None):
    AUDIO_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".distillery", "audio_cache")
else:
    AUDIO_CACHE_DIR = os.path.join(os.path.dirname(__file__), "audio_cache")

KOKORO_REPO_ID = "hexgrad/Kokoro-82M"
KOKORO_SIZE_MB = 313


def is_model_installed() -> bool:
    """Check if Kokoro model weights exist in the HuggingFace cache without importing kokoro."""
    try:
        from huggingface_hub import scan_cache_dir
        info = scan_cache_dir()
        for repo in info.repos:
            if repo.repo_id == KOKORO_REPO_ID and repo.size_on_disk > 10_000_000:
                return True
        return False
    except Exception:
        return False


def download_model(progress_cb=None):
    """Download Kokoro model weights with progress reporting.
    
    progress_cb: callable(downloaded_mb: float, total_mb: float) called periodically.
    """
    from huggingface_hub import snapshot_download
    from tqdm import tqdm

    class _ProgressTqdm(tqdm):
        """Custom tqdm class that forwards progress to our callback."""
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("unit", "B")
            kwargs.setdefault("unit_scale", True)
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            super().update(n)
            if progress_cb and self.total:
                downloaded_mb = self.n / (1024 * 1024)
                total_mb = self.total / (1024 * 1024)
                progress_cb(downloaded_mb, total_mb)

    safe_print("[Distillery] Downloading Kokoro model weights...")
    snapshot_download(
        KOKORO_REPO_ID,
        tqdm_class=_ProgressTqdm,
    )
    safe_print("[Distillery] Kokoro model download complete.")


def _cache_path(url_hash: str) -> str:
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    return os.path.join(AUDIO_CACHE_DIR, f"{url_hash}.mp3")


def is_cached(url_hash: str) -> bool:
    return os.path.isfile(_cache_path(url_hash))


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


SPLIT_PATTERN = r"\n+"


def count_segments(text: str) -> int:
    """Count how many non-empty segments the pipeline will produce."""
    parts = re.split(SPLIT_PATTERN, text)
    return max(1, sum(1 for p in parts if p.strip()))


def generate_audio(text: str, url_hash: str, progress_cb=None) -> str:
    """Generate audio. If progress_cb provided, called with (done, total) after each chunk."""
    cache_file = _cache_path(url_hash)
    if os.path.isfile(cache_file):
        if progress_cb:
            progress_cb(1, 1)
        return cache_file

    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="a")
    total = count_segments(text)

    audio_chunks = []
    done = 0
    for _, _, audio in pipeline(text, voice="af_heart", speed=1.0, split_pattern=SPLIT_PATTERN):
        if audio is not None and len(audio) > 0:
            audio_chunks.append(audio)
            done += 1
            if progress_cb:
                progress_cb(done, total)

    if not audio_chunks:
        raise RuntimeError("TTS pipeline produced no audio output.")

    combined = np.concatenate(audio_chunks)

    buf = io.BytesIO()
    sf.write(buf, combined, samplerate=24000, format="MP3")
    buf.seek(0)

    with open(cache_file, "wb") as f:
        f.write(buf.read())

    return cache_file
