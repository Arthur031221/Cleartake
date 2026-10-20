import pytest

from cleartake import media


def test_probe_audio_and_video(wav_file, mp4_file):
    audio = media.probe(wav_file)
    assert not audio.has_video and audio.sample_rate == 48_000
    video = media.probe(mp4_file)
    assert video.has_video and 2.5 < video.duration < 3.5


def test_roundtrip_formats(tmp_path, audio):
    for fmt in sorted(media.AUDIO_FORMATS):
        path = tmp_path / f"out.{fmt}"
        media.encode(audio, path, fmt)
        back = media.decode(path)
        assert abs(len(back) - len(audio)) < 4_000, fmt


def test_unsupported_format(tmp_path, audio):
    with pytest.raises(media.MediaError):
        media.encode(audio, tmp_path / "x.ogg", "ogg")


def test_file_without_audio_is_rejected(tmp_path):
    import subprocess

    silent = tmp_path / "silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=64x64:duration=1",
            "-c:v",
            "libx264",
            str(silent),
        ],
        check=True,
    )
    with pytest.raises(media.MediaError, match="no audio"):
        media.probe(silent)


def test_mux_keeps_the_picture_bit_for_bit(tmp_path, mp4_file, audio):
    wav = tmp_path / "new.wav"
    media.encode(audio[: 3 * 48_000], wav, "wav")
    out = tmp_path / "out.mp4"
    media.mux_video(mp4_file, wav, out)
    assert media.video_fingerprint(out) == media.video_fingerprint(mp4_file)
