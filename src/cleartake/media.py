"""Everything that touches ffmpeg: probing, decoding, encoding and muxing."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 48_000
AUDIO_FORMATS = {"wav", "flac", "mp3", "m4a"}
MEDIA_SUFFIXES = {
    ".wav",
    ".flac",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".m4v",
    ".avi",
}
_ENCODERS = {
    "wav": ["-c:a", "pcm_s24le"],
    "flac": ["-c:a", "flac"],
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
}


class MediaError(RuntimeError):
    """ffmpeg or ffprobe could not read or write a file."""


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    has_video: bool
    has_audio: bool
    sample_rate: int
    channels: int


def require_ffmpeg() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise MediaError(f"{' and '.join(missing)} not found on PATH. Install ffmpeg first.")


def _run(cmd: list[str], data: bytes | None = None) -> bytes:
    proc = subprocess.run(cmd, input=data, capture_output=True)
    if proc.returncode:
        tail = proc.stderr.decode(errors="replace").strip().splitlines()[-3:]
        raise MediaError(" ".join(tail) or f"{cmd[0]} failed")
    return proc.stdout


def probe(path: Path) -> MediaInfo:
    require_ffmpeg()
    out = _run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    data = json.loads(out)
    streams = data.get("streams", [])
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    # Cover art in an mp3 shows up as a video stream; it is not a picture to keep.
    video = any(
        s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0
        for s in streams
    )
    if audio is None:
        raise MediaError(f"{path.name} has no audio stream")
    duration = float(data.get("format", {}).get("duration") or audio.get("duration") or 0)
    return MediaInfo(
        duration=duration,
        has_video=video,
        has_audio=True,
        sample_rate=int(audio.get("sample_rate") or SAMPLE_RATE),
        channels=int(audio.get("channels") or 1),
    )


def decode(path: Path, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Return the first audio stream as mono float32 at the given rate."""
    raw = _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "-",
        ]
    )
    return np.frombuffer(raw, dtype=np.float32).copy()


def encode(audio: np.ndarray, out: Path, fmt: str, sample_rate: int = SAMPLE_RATE) -> None:
    if fmt not in AUDIO_FORMATS:
        raise MediaError(f"unsupported audio format {fmt!r}, choose one of {sorted(AUDIO_FORMATS)}")
    pcm = np.clip(audio, -1.0, 1.0).astype(np.float32).tobytes()
    _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "f32le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            "-",
            *_ENCODERS[fmt],
            str(out),
        ],
        pcm,
    )


def mux_video(video: Path, audio_wav: Path, out: Path) -> None:
    """Keep the first picture stream as it is and swap in the enhanced audio. Other streams are dropped."""
    audio_codec = ["-c:a", "pcm_s24le"] if out.suffix.lower() == ".mov" else ["-c:a", "aac", "-b:a", "192k"]
    _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            *audio_codec,
            "-map_metadata",
            "0",
            str(out),
        ]
    )


def video_fingerprint(path: Path) -> str:
    """MD5 of the first video stream's packets, to prove the picture was not re-encoded."""
    out = _run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "md5", "-"])
    return out.decode().strip()


def write_preview(audio: np.ndarray, out: Path, sample_rate: int = SAMPLE_RATE) -> None:
    """A browser friendly 16 bit wav used by the A and B player."""
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            "-",
            "-c:a",
            "pcm_s16le",
            str(out),
        ],
        pcm,
    )
