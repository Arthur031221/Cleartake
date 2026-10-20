"""Rebuild docs/demo, the pre-rendered sample behind the hosted demo.

Two samples, each made of VoiceBank-DEMAND test clips of one speaker joined with 0.35 s of silence between
them. Nothing is added to the recordings. VoiceBank-DEMAND is CC BY 4.0, see https://doi.org/10.7488/ds/2117

* docs/demo: five consecutive clips of p232, where the word check finds nothing.
* docs/demo/changes: five clips of p257 picked from the ones where the word check fired, so the page shows
  what a flagged word looks like. The differences listed are whatever the check reported.

Usage: python tools/build_demo.py [main|changes] [work_dir]    (writes the .mp3 files and report.json)
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
SAMPLES = {
    "main": ("docs/demo", ("p232_003", "p232_005", "p232_006", "p232_007", "p232_009")),
    "changes": ("docs/demo/changes", ("p257_050", "p257_251", "p257_171", "p257_291", "p257_331")),
}


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "main"
    target, clips = SAMPLES[name]
    out_dir = ROOT / target
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.mkdtemp(prefix="cleartake-demo-"))
    work.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(
        "JacobLinCool/VoiceBank-DEMAND-16k", "data/test-00000-of-00001.parquet", repo_type="dataset"
    )
    rows = {r["id"]: r for r in pq.read_table(path).to_pylist()}
    gap = np.zeros(int(0.35 * 16_000), dtype="float32")
    parts = []
    for clip in clips:
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
                str(out_dir / f"{name}.mp3"),
            ],
            check=True,
        )
    slim = json.loads(json.dumps(report))
    slim["input"]["file"] = "sample.wav"
    (out_dir / "report.json").write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    print(sample, report["loudness"], report["drift"]["difference_rate"])


if __name__ == "__main__":
    main()
