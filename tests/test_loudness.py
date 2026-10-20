import numpy as np
import pytest

from cleartake import loudness


def test_measure_matches_a_known_signal():
    t = np.arange(48_000 * 5) / 48_000
    sine = (0.1 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    result = loudness.measure(sine)
    assert result.integrated == pytest.approx(-23.1, abs=0.3)
    assert result.true_peak == pytest.approx(-20.0, abs=0.3)


@pytest.mark.parametrize("preset", ["podcast", "youtube", "broadcast"])
def test_presets_land_on_target(audio, preset):
    target, ceiling = loudness.PRESETS[preset]
    result = loudness.measure(loudness.apply_preset(audio, preset))
    assert result.integrated == pytest.approx(target, abs=0.6)
    assert result.true_peak <= ceiling + 0.1


def test_silence_is_left_alone():
    silence = np.zeros(48_000, dtype=np.float32)
    assert np.array_equal(loudness.apply_preset(silence, "podcast"), silence)
    assert loudness.measure(silence).integrated == -70.0
