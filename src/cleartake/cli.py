"""Command line entry point: cleartake FILE..., cleartake serve, cleartake doctor."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__, engines, loudness, media, pipeline

MEDIA_SUFFIXES = media.MEDIA_SUFFIXES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleartake",
        description="Clean up speech recordings and videos on this machine. Nothing is uploaded.",
        epilog="Other commands: cleartake serve (web app), cleartake doctor (check the setup).",
    )
    parser.add_argument(
        "inputs", nargs="+", type=Path, help="audio or video files, or folders for batch mode"
    )
    parser.add_argument("-o", "--output", type=Path, help="output file (one input) or folder (several)")
    parser.add_argument(
        "--engine",
        choices=[i.id for i in engines.available()],
        default="studio",
        help="classic: 16 kHz denoiser. studio: full band 48 kHz (default)",
    )
    parser.add_argument(
        "--strength", type=float, default=1.0, help="0 keeps the original, 1 is fully enhanced"
    )
    parser.add_argument(
        "--preset",
        choices=[*loudness.PRESETS, "none"],
        default="podcast",
        help="loudness target: podcast -16 LUFS, youtube -14, broadcast -23, or none",
    )
    parser.add_argument(
        "--format", dest="fmt", choices=["auto", *sorted(media.AUDIO_FORMATS)], default="auto"
    )
    parser.add_argument(
        "--audio-only", action="store_true", help="write audio even when the input is a video"
    )
    parser.add_argument("--no-check", dest="check", action="store_false", help="skip the word drift check")
    parser.add_argument("--whisper", default="base.en", help="faster-whisper model for the drift check")
    parser.add_argument("--language", help="spoken language code for the drift check, default auto")
    parser.add_argument("--device", choices=["auto", "cpu"], default="auto")
    parser.add_argument("--json", action="store_true", help="print the report as JSON on stdout")
    parser.add_argument("--version", action="version", version=f"cleartake {__version__}")
    return parser


def collect(inputs: list[Path]) -> list[tuple[Path, Path | None]]:
    """Each file with the folder it was found under, so -o can keep the folder layout."""
    files: list[tuple[Path, Path | None]] = []
    for item in inputs:
        if item.is_dir():
            files += [
                (p, item)
                for p in sorted(item.rglob("*"))
                if p.suffix.lower() in MEDIA_SUFFIXES and ".cleartake." not in p.name
            ]
        elif item.is_file():
            files.append((item, None))
        else:
            raise SystemExit(f"cleartake: {item} does not exist")
    if not files:
        raise SystemExit("cleartake: no media files found")
    return files


def plan_targets(files: list[tuple[Path, Path | None]], out: Path | None, options: pipeline.Options):
    """Plan every output path now, and refuse two inputs that share one or a result that replaces an input."""
    single_file = out is not None and len(files) == 1 and bool(out.suffix)
    plan, seen = [], {}
    for source, root in files:
        try:
            info = media.probe(source)
        except media.MediaError as err:
            plan.append((source, None, err))
            continue
        if single_file:
            target = out
        else:
            folder = out / source.parent.relative_to(root) if out and root else out
            target = pipeline.output_path(source, options, info, folder)
        if target.resolve() == source.resolve():
            raise SystemExit(f"cleartake: {source} would be overwritten by its own result")
        key = target.with_suffix("").resolve()
        if key in seen:
            raise SystemExit(
                f"cleartake: {seen[key]} and {source} both write {target.name}, use -o with a folder"
            )
        seen[key] = source
        plan.append((source, target, None))
    return plan


def summary_line(report: dict) -> str:
    before, after = report["loudness"]["before"], report["loudness"]["after"]
    line = (
        f"{report['output']['file']}: {before['integrated']} -> {after['integrated']} LUFS, "
        f"true peak {after['true_peak']} dBTP, {report['speed_x_realtime']}x realtime"
    )
    if report["drift"]:
        d = report["drift"]
        line += (
            f", words changed {d['changed']} dropped {d['dropped']} added {d['added']} of {d['words_before']}"
        )
    return line


def enhance_files(args: argparse.Namespace) -> int:
    files = collect(args.inputs)
    out = args.output
    if len(files) > 1 and out and out.suffix:
        raise SystemExit("cleartake: -o must be a folder when there is more than one input")
    options = pipeline.Options(
        engine=args.engine,
        strength=args.strength,
        preset=args.preset,
        fmt=args.fmt,
        check=args.check,
        whisper=args.whisper,
        language=args.language,
        audio_only=args.audio_only,
    )
    reports, failures = [], 0
    for source, target, error in plan_targets(files, out, options):
        try:
            if error:
                raise error
            print(f"{source.name} ...", file=sys.stderr, flush=True)
            report = pipeline.run(
                source,
                options,
                target,
                on_stage=lambda name: print(f"  {name}", file=sys.stderr, flush=True),
            )
            pipeline.write_report(report, target)
            reports.append(report)
            print(summary_line(report), file=sys.stderr)
        except Exception as err:  # one bad file must not stop the batch
            failures += 1
            print(f"cleartake: {source.name}: {err}", file=sys.stderr)
    if args.json:
        print(json.dumps(reports if len(reports) != 1 else reports[0], indent=2))
    return 1 if failures else 0


def doctor() -> int:
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        ok &= path is not None
        print(f"{tool}: {path or 'MISSING, install ffmpeg'}")
    print(f"device: {engines.device_name()}")
    models = engines.home() / "models"
    for info in engines.available():
        present = (models / info.model).is_dir()
        print(f"engine {info.id} ({info.model}): {'downloaded' if present else 'downloads on first use'}")
    return 0 if ok else 1


def serve(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cleartake serve", description="Run the local web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", choices=["auto", "cpu"], default="auto")
    parser.add_argument("--max-upload-mb", type=int, default=2048)
    parser.add_argument("--open", action="store_true", help="open the page in a browser")
    args = parser.parse_args(argv)
    if args.device == "cpu":
        engines.use_cpu_only()
    import uvicorn

    from .server import create_app

    media.require_ffmpeg()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            f"cleartake: serving on {args.host} with no login, anyone who can reach it can use it",
            file=sys.stderr,
        )
    if args.open:
        import threading
        import webbrowser

        threading.Timer(1.0, webbrowser.open, [f"http://{args.host}:{args.port}/"]).start()
    uvicorn.run(
        create_app(max_upload_mb=args.max_upload_mb, host=args.host),
        host=args.host,
        port=args.port,
        log_level="warning",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["serve"]:
        return serve(argv[1:])
    if argv[:1] == ["doctor"]:
        return doctor()
    args = build_parser().parse_args(argv)
    if args.device == "cpu":
        engines.use_cpu_only()
    try:
        media.require_ffmpeg()
    except media.MediaError as err:
        raise SystemExit(f"cleartake: {err}") from err
    return enhance_files(args)


if __name__ == "__main__":
    raise SystemExit(main())
