import json

import pytest

from cleartake import cli, drift, engines, loudness, media, pipeline


@pytest.fixture(autouse=True)
def no_whisper(monkeypatch):
    monkeypatch.setattr(drift, "transcribe", lambda *a, **k: [drift.Word("hello", 0, 0.4)])


def test_audio_file_gets_the_preset_loudness(wav_file, fake_engine, tmp_path):
    out = tmp_path / "result.flac"
    report = pipeline.run(wav_file, pipeline.Options(preset="youtube"), out, engine=fake_engine)
    assert media.decode(out).size > 0
    assert report["loudness"]["after"]["integrated"] == pytest.approx(-14.0, abs=0.6)
    assert report["drift"]["changed"] == 0 and report["output"]["picture_kept"] is False


def test_video_in_video_out_keeps_the_picture(mp4_file, fake_engine, tmp_path):
    out = tmp_path / "result.mp4"
    report = pipeline.run(mp4_file, pipeline.Options(check=False), out, engine=fake_engine)
    assert report["output"]["picture_kept"] is True
    assert media.video_fingerprint(out) == media.video_fingerprint(mp4_file)


def test_audio_only_from_video(mp4_file, fake_engine, tmp_path):
    options = pipeline.Options(check=False, audio_only=True, fmt="mp3")
    out = pipeline.output_path(mp4_file, options, media.probe(mp4_file), tmp_path)
    assert out.suffix == ".mp3"
    pipeline.run(mp4_file, options, out, engine=fake_engine)
    assert not media.probe(out).has_video


def test_strength_zero_returns_the_original_level(wav_file, fake_engine, tmp_path):
    out = tmp_path / "same.wav"
    report = pipeline.run(
        wav_file,
        pipeline.Options(strength=0.0, preset="none", check=False),
        out,
        engine=fake_engine,
    )
    assert report["loudness"]["after"] == report["loudness"]["before"]


@pytest.mark.parametrize(
    "bad", [dict(strength=1.5), dict(preset="loud"), dict(engine="nope"), dict(fmt="ogg")]
)
def test_bad_options_are_rejected(bad):
    with pytest.raises(ValueError):
        pipeline.Options(**bad).validate()


def test_cli_writes_audio_and_a_report(wav_file, fake_engine, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pipeline.engines, "get", lambda _id: fake_engine)
    out = tmp_path / "cli.wav"
    code = cli.main([str(wav_file), "-o", str(out), "--preset", "broadcast", "--json"])
    assert code == 0 and out.is_file()
    printed = json.loads(capsys.readouterr().out)
    assert printed["loudness"]["target"] == list(loudness.PRESETS["broadcast"])
    assert "transcript_before" not in json.loads(out.with_suffix(".json").read_text())["drift"]


def test_cli_batch_folder_skips_earlier_results(wav_file, fake_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline.engines, "get", lambda _id: fake_engine)
    (tmp_path / "talk.cleartake.wav").write_bytes(b"old")
    assert cli.collect([tmp_path]) == [(wav_file, tmp_path)]
    out_dir = tmp_path / "done"
    assert cli.main([str(tmp_path), "-o", str(out_dir), "--no-check"]) == 0
    assert (out_dir / "talk.cleartake.wav").is_file()


def test_cli_reports_a_broken_file_and_exits_nonzero(tmp_path, capsys):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio")
    assert cli.main([str(bad)]) == 1
    assert "bad.wav" in capsys.readouterr().err


def test_cli_batch_keeps_the_folder_layout(wav_file, fake_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline.engines, "get", lambda _id: fake_engine)
    src = tmp_path / "src"
    for name in ("a", "b"):
        (src / name).mkdir(parents=True)
        (src / name / "intro.wav").write_bytes(wav_file.read_bytes())
    out = tmp_path / "out"
    assert cli.main([str(src), "-o", str(out), "--no-check"]) == 0
    assert (out / "a" / "intro.cleartake.wav").is_file() and (out / "b" / "intro.cleartake.wav").is_file()


def test_cli_refuses_two_inputs_with_one_output_name(wav_file, tmp_path):
    first, second = tmp_path / "x.wav", tmp_path / "x.mp3"
    first.write_bytes(wav_file.read_bytes())
    second.write_bytes(wav_file.read_bytes())
    with pytest.raises(SystemExit, match="both write"):
        cli.main([str(first), str(second), "--no-check"])


def test_cli_never_overwrites_its_input(wav_file):
    with pytest.raises(SystemExit, match="overwritten"):
        cli.main([str(wav_file), "-o", str(wav_file), "--no-check"])


def test_cli_batch_goes_on_after_an_unexpected_error(wav_file, tmp_path, monkeypatch, capsys):
    import subprocess

    calls = []

    def run(source, *a, **k):
        calls.append(source.name)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, "ffmpeg")
        return {
            "output": {"file": "x"},
            "loudness": {"before": {"integrated": 0}, "after": {"integrated": 0, "true_peak": 0}},
            "speed_x_realtime": 1,
            "drift": None,
        }

    monkeypatch.setattr(pipeline, "run", run)
    monkeypatch.setattr(pipeline, "write_report", lambda *a: None)
    (tmp_path / "b.wav").write_bytes(wav_file.read_bytes())
    assert cli.main([str(wav_file), str(tmp_path / "b.wav"), "-o", str(tmp_path / "o")]) == 1
    assert len(calls) == 2


def test_picture_kept_is_false_when_the_hashes_differ(mp4_file, fake_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(media, "video_fingerprint", lambda path: path.name)
    report = pipeline.run(mp4_file, pipeline.Options(check=False), tmp_path / "o.mp4", engine=fake_engine)
    assert report["output"]["picture_kept"] is False


def test_loudness_after_is_measured_on_the_written_file(wav_file, fake_engine, tmp_path):
    out = tmp_path / "o.mp3"
    report = pipeline.run(wav_file, pipeline.Options(check=False, fmt="mp3"), out, engine=fake_engine)
    written = loudness.measure(media.decode(out))
    assert report["loudness"]["after"] == written.as_dict()


def test_check_stage_is_announced_only_when_the_check_runs(wav_file, fake_engine, tmp_path):
    seen = {}
    for check in (True, False):
        names = seen.setdefault(check, [])
        pipeline.run(
            wav_file,
            pipeline.Options(check=check),
            tmp_path / f"{check}.wav",
            on_stage=names.append,
            engine=fake_engine,
        )
    assert seen[True] == ["decode", "enhance", "finish", "check", "write"]
    assert seen[False] == ["decode", "enhance", "finish", "write"]


def test_doctor_reports_which_models_are_on_disk(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLEARTAKE_HOME", str(tmp_path))
    monkeypatch.setattr(drift, "is_downloaded", lambda name: name == "base.en")
    checkpoint = tmp_path / "models" / "checkpoints" / "MossFormer2_SE_48K"
    checkpoint.mkdir(parents=True)
    (checkpoint / "last_best_checkpoint.pt").write_bytes(b"x")
    assert cli.main(["doctor"]) in (0, 1)
    lines = capsys.readouterr().out.splitlines()
    assert "engine studio (MossFormer2_SE_48K): downloaded" in lines
    assert "engine classic (FRCRN_SE_16K): downloads on first use" in lines
    assert "whisper base.en (word check, English): downloaded" in lines
    assert "whisper small (word check, other languages): downloads on first use" in lines


def test_an_empty_checkpoint_folder_does_not_count_as_downloaded(tmp_path, monkeypatch):
    monkeypatch.setenv("CLEARTAKE_HOME", str(tmp_path))
    (tmp_path / "models" / "checkpoints" / "FRCRN_SE_16K").mkdir(parents=True)
    assert not engines.is_downloaded(engines._INFOS["classic"])
