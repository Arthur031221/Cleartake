import subprocess

import numpy as np
import pytest

from cleartake import engines
from cleartake.media import SAMPLE_RATE


class FakeEngine(engines.Engine):
    """Stands in for the neural models: attenuates everything, so results are predictable."""

    info = engines.EngineInfo("fake", "FAKE_MODEL", SAMPLE_RATE, "test engine")

    def enhance(self, audio):
        return audio * 0.5


def speechlike(seconds=4.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    envelope = (np.sin(2 * np.pi * 2.5 * t) > 0).astype(np.float32) * 0.5 + 0.1
    tone = np.sin(2 * np.pi * 180 * t) + 0.5 * np.sin(2 * np.pi * 540 * t)
    return (0.2 * envelope * tone + 0.01 * rng.standard_normal(t.size)).astype(np.float32)


@pytest.fixture
def audio():
    return speechlike()


@pytest.fixture
def wav_file(tmp_path, audio):
    from cleartake import media

    path = tmp_path / "talk.wav"
    media.encode(audio, path, "wav")
    return path


@pytest.fixture
def mp4_file(tmp_path):
    path = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x120:rate=10:duration=3",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:duration=3",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
    )
    return path


@pytest.fixture
def fake_engine():
    return FakeEngine()
