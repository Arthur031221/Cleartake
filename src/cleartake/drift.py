"""Word drift check: what Whisper hears in the original against what it hears in the result."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from difflib import SequenceMatcher

import numpy as np
from scipy.signal import resample_poly

from .media import SAMPLE_RATE

_models: dict[str, object] = {}
_lock = threading.Lock()


# Whisper writes small numbers as digits in one pass and as words in the next. Treat them as the same word.
_NUMBER_WORDS = dict(
    enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
        "sixteen seventeen eighteen nineteen twenty".split()
    )
)


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float

    @property
    def key(self) -> str:
        key = re.sub(r"[^\w']", "", self.text.lower())
        return _NUMBER_WORDS[int(key)] if key.isdigit() and int(key) in _NUMBER_WORDS else key


def transcribe(audio: np.ndarray, model_name: str = "base.en", language: str | None = None) -> list[Word]:
    from faster_whisper import WhisperModel

    with _lock:
        if model_name not in _models:
            _models[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
        model = _models[model_name]
    mono16 = resample_poly(audio, 16_000, SAMPLE_RATE).astype(np.float32)
    segments, _ = model.transcribe(
        mono16, word_timestamps=True, language=language, condition_on_previous_text=False
    )
    words = [Word(w.word.strip(), w.start, w.end) for s in segments for w in s.words]
    return [w for w in words if w.key]


def compare(before: list[Word], after: list[Word]) -> dict:
    """Align the two transcripts and list every word that differs, with timestamps."""
    matcher = SequenceMatcher(a=[w.key for w in before], b=[w.key for w in after], autojunk=False)
    changes, kinds = [], {"changed": 0, "dropped": 0, "added": 0}
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            continue
        old, new = before[a0:a1], after[b0:b1]
        kind = "changed" if old and new else "dropped" if old else "added"
        kinds[kind] += max(len(old), len(new))
        anchor = new[0] if new else old[0]
        changes.append(
            {
                "kind": kind,
                "before": " ".join(w.text for w in old),
                "after": " ".join(w.text for w in new),
                "start": round(anchor.start, 2),
                "end": round((new[-1] if new else old[-1]).end, 2),
            }
        )
    total = max(len(before), 1)
    return {
        "words_before": len(before),
        "words_after": len(after),
        **kinds,
        "difference_rate": round(sum(kinds.values()) / total, 4),
        "changes": changes,
        "transcript_before": [_word_json(w) for w in before],
        "transcript_after": [_word_json(w) for w in after],
    }


def _word_json(word: Word) -> dict:
    return {"text": word.text, "start": round(word.start, 2), "end": round(word.end, 2)}


def check(
    original: np.ndarray,
    enhanced: np.ndarray,
    model_name: str = "base.en",
    language: str | None = None,
) -> dict:
    result = compare(transcribe(original, model_name, language), transcribe(enhanced, model_name, language))
    result["model"] = model_name
    return result
