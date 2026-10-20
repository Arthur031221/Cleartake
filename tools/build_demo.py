"""Rebuild docs/demo, the pre-rendered sample behind the hosted demo.

The input is five consecutive VoiceBank-DEMAND test clips of one speaker (p232), joined with 0.35 s of
silence between them. Nothing is added to the recordings. VoiceBank-DEMAND is CC BY 4.0, see
https://doi.org/10.7488/ds/2117

Usage: python tools/build_demo.py [work_dir]    (writes docs/demo/*.mp3 and report.json)
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf
from huggingface_hub import hf_hub_download

from cleartake import pipeline

ROOT = Path(__file__).resolve().parents[1]
CLIPS = ("p232_003", "p232_005", "p232_006", "p232_007", "p232_009")


def main() -> None:
    work = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="cleartake-demo-"))
    work.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(
        "JacobLinCool/VoiceBank-DEMAND-16k", "data/test-00000-of-00001.parquet", repo_type="dataset"
    )
    rows = {r["id"]: r for r in pq.read_table(path).to_pylist()}
    gap = np.zeros(int(0.35 * 16_000), dtype="float32")
    parts = []
    for clip in CLIPS:
        audio, rate = sf.read(io.BytesIO(rows[clip]["noisy"]["bytes"]), dtype="float32")
        assert rate == 16_000
        parts += [audio, gap]
    sample = work / "sample.wav"
    sf.write(sample, np.concatenate(parts), 16_000)

    previews = work / "previews"
    previews.mkdir(exist_ok=True)
    report = pipeline.run(sample, pipeline.Options(), out=work / "sample.cleartake.wav", preview_dir=previews)
    for name in ("original", "enhanced"):
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(previews / f"{name}.wav"),
                "-b:a",
                "96k",
                str(ROOT / "docs/demo" / f"{name}.mp3"),
            ],
            check=True,
        )
    slim = json.loads(json.dumps(report))
    slim["input"]["file"] = "sample.wav"
    (ROOT / "docs/demo/report.json").write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    print(sample, report["loudness"], report["drift"]["difference_rate"])


if __name__ == "__main__":
    main()
