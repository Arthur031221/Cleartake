"""Speech enhancement engines. Both wrap models from ClearerVoice-Studio (Apache-2.0)."""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from .media import SAMPLE_RATE

_load_lock = threading.Lock()


def home() -> Path:
    """Where models and caches live. Override with CLEARTAKE_HOME."""
    return Path(os.environ.get("CLEARTAKE_HOME", Path.home() / ".cache" / "cleartake"))


def is_downloaded(info: EngineInfo) -> bool:
    """ClearerVoice unpacks a model to models/checkpoints/<name>/ in the working folder it runs from."""
    return (home() / "models" / "checkpoints" / info.model / "last_best_checkpoint.pt").is_file()


@dataclass(frozen=True)
class EngineInfo:
    id: str
    model: str
    sample_rate: int
    summary: str


class Engine(ABC):
    info: EngineInfo

    @abstractmethod
    def enhance(self, audio: np.ndarray) -> np.ndarray:
        """Take mono float32 at 48 kHz, return the same length at 48 kHz."""


class ClearerVoiceEngine(Engine):
    def __init__(self, info: EngineInfo) -> None:
        self.info = info
        self._model = None

    def _load(self):
        if self._model is None:
            with _load_lock, _in_dir(home() / "models"):
                os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
                from clearvoice import ClearVoice, networks

                # It draws a one step progress bar for every file, which is noise in a terminal.
                networks.tqdm = lambda iterable, *args, **kwargs: iterable

                with contextlib.redirect_stdout(sys.stderr):
                    self._model = ClearVoice(task="speech_enhancement", model_names=[self.info.model])
        return self._model

    def enhance(self, audio: np.ndarray) -> np.ndarray:
        import soundfile as sf

        rate = self.info.sample_rate
        down = resample_poly(audio, rate, SAMPLE_RATE) if rate != SAMPLE_RATE else audio
        model = self._load()
        with tempfile.TemporaryDirectory(prefix="cleartake-") as tmp:
            src = Path(tmp) / "in.wav"
            sf.write(src, down.astype(np.float32), rate, subtype="FLOAT")
            with contextlib.redirect_stdout(sys.stderr):
                out = model(input_path=str(src), online_write=False)
        mono = np.asarray(out, dtype=np.float32).reshape(-1, np.asarray(out).shape[-1]).mean(axis=0)
        if rate != SAMPLE_RATE:
            mono = resample_poly(mono, SAMPLE_RATE, rate)
        return fit_length(mono, len(audio))


@contextlib.contextmanager
def _in_dir(path: Path):
    """ClearerVoice keeps its checkpoints in a folder relative to the working directory."""
    path.mkdir(parents=True, exist_ok=True)
    before = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


def fit_length(audio: np.ndarray, length: int) -> np.ndarray:
    if len(audio) >= length:
        return audio[:length]
    return np.pad(audio, (0, length - len(audio)))


def blend(original: np.ndarray, enhanced: np.ndarray, strength: float) -> np.ndarray:
    """strength 1 is fully enhanced, 0 is the untouched original."""
    if not 0.0 <= strength <= 1.0:
        raise ValueError("strength must be between 0 and 1")
    if strength == 1.0:
        return enhanced
    return strength * enhanced + (1.0 - strength) * original


_INFOS = {
    "classic": EngineInfo("classic", "FRCRN_SE_16K", 16_000, "16 kHz denoiser, speech band up to 8 kHz"),
    "studio": EngineInfo(
        "studio",
        "MossFormer2_SE_48K",
        48_000,
        "Full band 48 kHz speech enhancement",
    ),
}
_cache: dict[str, Engine] = {}


def available() -> list[EngineInfo]:
    return [
        engine.info if isinstance(engine, Engine) else _INFOS[key]
        for key, engine in ((k, _cache.get(k)) for k in _INFOS)
    ]


def get(engine_id: str) -> Engine:
    if engine_id not in _INFOS:
        raise KeyError(f"unknown engine {engine_id!r}, choose one of {sorted(_INFOS)}")
    if engine_id not in _cache:
        _cache[engine_id] = ClearerVoiceEngine(_INFOS[engine_id])
    return _cache[engine_id]


def use_cpu_only() -> None:
    """Hide the GPU from torch. Must run before torch is imported."""
    if "torch" in sys.modules:
        raise RuntimeError("torch is already loaded, start a new process with --device cpu")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""


def device_name() -> str:
    try:
        import torch
    except ImportError:
        return "unavailable"
    if torch.cuda.is_available():
        return f"cuda ({torch.cuda.get_device_name(0)})"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"
