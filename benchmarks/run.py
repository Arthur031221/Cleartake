"""Measure Cleartake on the VoiceBank-DEMAND test set.

Usage: python benchmarks/run.py [--every 8] [--out benchmarks/results.json]

Needs `pip install speechmos jiwer` and the dataset from the Hugging Face hub
(JacobLinCool/VoiceBank-DEMAND-16k, test split, 824 utterances). Metrics per variant:

* DNSMOS (speechmos): OVRL, SIG, BAK, on audio taken back to 16 kHz, no loudness step applied.
  The 16 kHz inputs are upsampled to the 48 kHz working rate first, as the app does.
* WER: Whisper base.en transcript of the variant against the Whisper transcript of the clean file.
* Drift rate: the same number the app reports, noisy against variant.
* Speed: audio seconds per wall second for the enhancement stage alone.
"""

from __future__ import annotations

import argparse
import io
import json
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import hf_hub_download
from jiwer import wer
from scipy.signal import resample_poly
from speechmos import dnsmos

from cleartake import drift, engines
from cleartake.media import SAMPLE_RATE

REPO = "JacobLinCool/VoiceBank-DEMAND-16k"


def load(cell: dict) -> np.ndarray:
    audio, rate = sf.read(io.BytesIO(cell["bytes"]), dtype="float32")
    assert rate == 16_000, rate
    mono = audio if audio.ndim == 1 else audio.mean(axis=1)
    return resample_poly(mono, SAMPLE_RATE, rate).astype(np.float32)


def text(words: list[drift.Word]) -> str:
    return " ".join(w.text.strip(".,!?;:\"'").lower() for w in words)


def score(audio: np.ndarray) -> dict:
    result = dnsmos.run(resample_poly(audio, 16_000, SAMPLE_RATE).astype(np.float32), 16_000)
    return {k: float(result[k]) for k in ("ovrl_mos", "sig_mos", "bak_mos")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--every", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()

    path = hf_hub_download(REPO, "data/test-00000-of-00001.parquet", repo_type="dataset")
    rows = pq.read_table(path).to_pylist()[:: args.every]
    variants = {"noisy": None, "classic": engines.get("classic"), "studio": engines.get("studio")}
    acc = {
        name: {"mos": [], "refs": [], "hyps": [], "drift": [], "audio_s": 0.0, "wall_s": 0.0}
        for name in variants
    }

    for index, row in enumerate(rows):
        noisy, clean = load(row["noisy"]), load(row["clean"])
        reference = text(drift.transcribe(clean))
        noisy_words = drift.transcribe(noisy)
        for name, engine in variants.items():
            if engine is None:
                audio, words = noisy, noisy_words
            else:
                started = time.perf_counter()
                audio = engine.enhance(noisy)
                acc[name]["wall_s"] += time.perf_counter() - started
                acc[name]["audio_s"] += len(noisy) / SAMPLE_RATE
                words = drift.transcribe(audio)
                acc[name]["drift"].append(drift.compare(noisy_words, words)["difference_rate"])
            acc[name]["mos"].append(score(audio))
            acc[name]["refs"].append(reference)
            acc[name]["hyps"].append(text(words))
        if index % 10 == 0:
            print(f"{index + 1}/{len(rows)}", flush=True)

    summary = {"utterances": len(rows), "every": args.every, "device": engines.device_name(), "variants": {}}
    for name, a in acc.items():
        keep = [i for i, r in enumerate(a["refs"]) if r.strip()]
        summary["variants"][name] = {
            **{
                k: round(float(np.mean([m[k] for m in a["mos"]])), 3)
                for k in ("ovrl_mos", "sig_mos", "bak_mos")
            },
            "wer_vs_clean_transcript": round(
                wer([a["refs"][i] for i in keep], [a["hyps"][i] for i in keep]), 4
            ),
            "drift_rate_vs_noisy": round(float(np.mean(a["drift"])), 4) if a["drift"] else None,
            "speed_x_realtime": round(a["audio_s"] / a["wall_s"], 1) if a["wall_s"] else None,
        }
    args.out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
