"""Runs the real models on the shipped demo clip. Opt in with: pytest -m model (downloads the models)."""

from pathlib import Path

import pytest

from cleartake import media, pipeline

pytestmark = pytest.mark.model
DEMO = Path(__file__).resolve().parents[1] / "docs" / "demo" / "original.mp3"


@pytest.mark.parametrize("engine", ["classic", "studio"])
def test_engine_cleans_the_demo_clip(tmp_path, engine):
    out = tmp_path / f"{engine}.wav"
    report = pipeline.run(DEMO, pipeline.Options(engine=engine, check=True), out=out)
    before, after = media.decode(DEMO), media.decode(out)
    assert abs(len(after) - len(before)) < 480
    assert abs(report["loudness"]["after"]["integrated"] - (-16.0)) < 1.0
    assert report["drift"]["words_before"] > 30
    assert report["drift"]["difference_rate"] < 0.15
    assert float(abs(after - before).mean()) > 1e-4
