"""The whole job for one file: decode, enhance, blend, finish loudness, check, write."""

from __future__ import annotations

import json
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from . import __version__, drift, engines, loudness, media

STAGES = ("decode", "enhance", "finish", "check", "write")
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv"}


@dataclass(frozen=True)
class Options:
    engine: str = "studio"
    strength: float = 1.0
    preset: str = "podcast"
    fmt: str = "auto"
    check: bool = True
    whisper: str = "base.en"
    language: str | None = None
    audio_only: bool = False

    def validate(self) -> None:
        if self.engine not in {i.id for i in engines.available()}:
            raise ValueError(f"unknown engine {self.engine!r}")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("strength must be between 0 and 1")
        if self.preset != "none" and self.preset not in loudness.PRESETS:
            raise ValueError(f"unknown preset {self.preset!r}")
        if self.fmt != "auto" and self.fmt not in media.AUDIO_FORMATS:
            raise ValueError(f"unknown format {self.fmt!r}")


def output_path(source: Path, options: Options, info: media.MediaInfo, out_dir: Path | None = None) -> Path:
    folder = out_dir or source.parent
    if info.has_video and not options.audio_only and options.fmt == "auto":
        suffix = source.suffix.lower() if source.suffix.lower() in VIDEO_SUFFIXES else ".mkv"
    else:
        wanted = options.fmt if options.fmt != "auto" else source.suffix.lower().lstrip(".")
        suffix = "." + (wanted if wanted in media.AUDIO_FORMATS else "wav")
    return folder / f"{source.stem}.cleartake{suffix}"


def run(
    source: Path,
    options: Options,
    out: Path | None = None,
    on_stage: Callable[[str], None] | None = None,
    preview_dir: Path | None = None,
    engine: engines.Engine | None = None,
) -> dict:
    options.validate()
    notify = on_stage or (lambda _name: None)
    started = time.perf_counter()
    timings: dict[str, float] = {}

    def stage(name: str) -> None:
        notify(name)
        timings[name] = time.perf_counter()

    info = media.probe(source)
    target = out or output_path(source, options, info)
    stage("decode")
    original = media.decode(source)

    stage("enhance")
    engine = engine or engines.get(options.engine)
    enhanced = engine.enhance(original)
    enhanced = engines.blend(original, enhanced, options.strength)

    stage("finish")
    before_loudness = loudness.measure(original)
    final = loudness.apply_preset(enhanced, options.preset) if options.preset != "none" else enhanced

    report_drift = None
    stage("check")
    if options.check:
        report_drift = drift.check(original, final, options.whisper, options.language)

    stage("write")
    keep_picture = info.has_video and not options.audio_only and target.suffix.lower() in VIDEO_SUFFIXES
    target.parent.mkdir(parents=True, exist_ok=True)
    if keep_picture:
        with tempfile.TemporaryDirectory(prefix="cleartake-") as tmp:
            wav = Path(tmp) / "audio.wav"
            media.encode(final, wav, "wav")
            media.mux_video(source, wav, target)
    else:
        media.encode(final, target, target.suffix.lstrip("."))
    picture_kept = keep_picture and media.video_fingerprint(source) == media.video_fingerprint(target)
    after_loudness = loudness.measure(media.decode(target))
    if preview_dir:
        media.write_preview(original, preview_dir / "original.wav")
        media.write_preview(final, preview_dir / "enhanced.wav")
    finished = time.perf_counter()

    report = {
        "cleartake": __version__,
        "input": {"file": source.name, **asdict(info)},
        "output": {"file": target.name, "picture_kept": picture_kept},
        "options": asdict(options),
        "model": {"engine": options.engine, "name": engine.info.model},
        "device": engines.device_name(),
        "loudness": {
            "before": before_loudness.as_dict(),
            "after": after_loudness.as_dict(),
            "target": loudness.PRESETS.get(options.preset),
        },
        "drift": report_drift,
        "seconds": round(finished - started, 2),
        "speed_x_realtime": round(info.duration / max(finished - started, 1e-6), 1),
        "enhance_seconds": round(timings["finish"] - timings["enhance"], 2),
    }
    return report


def slim_report(report: dict) -> dict:
    """A copy of the report without the full transcripts, which are only needed by the web page."""
    slim = json.loads(json.dumps(report))
    if slim.get("drift"):
        slim["drift"].pop("transcript_before", None)
        slim["drift"].pop("transcript_after", None)
    return slim


def write_report(report: dict, target: Path) -> Path:
    path = target.with_suffix(".json")
    path.write_text(json.dumps(slim_report(report), indent=2) + "\n", encoding="utf-8")
    return path
