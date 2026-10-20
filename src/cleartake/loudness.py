"""EBU R128 loudness measurement and a gain plus limiter finish, all through ffmpeg."""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass

import numpy as np

from .media import SAMPLE_RATE

PRESETS = {
    "podcast": (-16.0, -1.5),
    "youtube": (-14.0, -1.5),
    "broadcast": (-23.0, -1.0),
}


@dataclass(frozen=True)
class Loudness:
    integrated: float
    true_peak: float
    lra: float

    def as_dict(self) -> dict:
        return {k: round(v, 1) for k, v in asdict(self).items()}


def _ffmpeg_audio(audio: np.ndarray, graph: str, sample_rate: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-f",
            "f32le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            "-",
            "-af",
            graph,
            "-f",
            "null",
            "-",
        ],
        input=audio.astype(np.float32).tobytes(),
        capture_output=True,
    )


def measure(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> Loudness:
    if audio.size == 0 or not np.any(audio):
        return Loudness(-70.0, -70.0, 0.0)
    text = _ffmpeg_audio(audio, "ebur128=peak=true", sample_rate).stderr.decode(errors="replace")
    summary = text[text.rfind("Summary:") :]

    def grab(label: str, unit: str) -> float:
        match = re.search(rf"{label}:\s+(-?[\d.]+|-inf)\s+{unit}", summary)
        if not match:
            raise RuntimeError("could not read the ffmpeg loudness summary")
        return -70.0 if match.group(1) == "-inf" else float(match.group(1))

    return Loudness(grab("I", "LUFS"), grab("Peak", "dBFS"), grab("LRA", "LU"))


def apply_preset(audio: np.ndarray, preset: str, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Gain to the target, then a true-peak ceiling. The result is measured again by the caller."""
    target, ceiling = PRESETS[preset]
    before = measure(audio, sample_rate)
    if before.integrated <= -69.0:
        return audio
    out = audio * (10 ** ((target - before.integrated) / 20))
    for _ in range(4):
        out = _limit(out, ceiling - 0.2, sample_rate)
        now = measure(out, sample_rate)
        if now.true_peak <= ceiling + 0.05 and abs(now.integrated - target) <= 0.5:
            break
        # Limiting costs a little loudness: push the level back up, then limit again.
        out = out * (10 ** ((target - now.integrated) / 20))
    return _limit(out, ceiling - 0.2, sample_rate)


def _limit(audio: np.ndarray, ceiling_db: float, sample_rate: int) -> np.ndarray:
    limit = 10 ** (ceiling_db / 20)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "f32le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            "-",
            "-af",
            f"alimiter=limit={limit:.5f}:attack=3:release=60:level=0:asc=0",
            "-f",
            "f32le",
            "-",
        ],
        input=audio.astype(np.float32).tobytes(),
        capture_output=True,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()
