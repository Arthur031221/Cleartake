"""Local web app: upload a file, watch the stages, compare original and result."""

from __future__ import annotations

import json
import queue
import shutil
import tempfile
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, engines, loudness, media, pipeline

WEB_DIR = Path(__file__).with_name("web")
ALLOWED_SUFFIXES = media.MEDIA_SUFFIXES
KEEP_FINISHED_JOBS = 12
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
OPEN_RESULT_SECONDS = 300  # a finished job someone polled this recently is not pruned


class Cancelled(Exception):
    """Raised between stages when the user cancelled a running job."""


@dataclass
class Job:
    id: str
    folder: Path
    source: Path
    label: str
    options: pipeline.Options
    state: str = "queued"
    stage: str = ""
    error: str = ""
    report: dict | None = None
    output: Path | None = None
    cancel: bool = False
    created: float = field(default_factory=time.time)
    seen: float = 0.0

    def public(self, position: int = 0) -> dict:
        return {
            "id": self.id,
            "state": self.state,
            "stage": self.stage,
            "error": self.error,
            "label": self.label,
            "queue_position": position,
            "stages": list(pipeline.STAGES),
            "report": self.report,
        }


class Jobs:
    """One worker thread, because the models want the whole GPU."""

    def __init__(self, root: Path, engine_factory: Callable[[str], engines.Engine]) -> None:
        self.root = root
        self.engine_factory = engine_factory
        self.items: dict[str, Job] = {}
        self.pending: queue.Queue[str] = queue.Queue()
        self.lock = threading.Lock()
        threading.Thread(target=self._work, daemon=True).start()

    def add(self, job: Job) -> None:
        with self.lock:
            self.items[job.id] = job
            self.pending.put(job.id)
            self._prune()

    def cancel(self, job: Job) -> None:
        """Stop a queued or running job, or discard a finished one."""
        with self.lock:
            if job.state == "queued":
                job.state = "cancelled"
            elif job.state == "running":
                job.cancel = True
                return
            else:
                self.items.pop(job.id, None)
        shutil.rmtree(job.folder, ignore_errors=True)

    def _prune(self) -> None:
        """Keep the newest finished jobs, so a long session does not fill the disk.

        A job whose page polled it a moment ago stays, so a big batch is not pruned under the user.
        """
        now = time.time()
        finished = sorted(
            (
                j
                for j in self.items.values()
                if j.state in ("done", "error", "cancelled") and now - j.seen > OPEN_RESULT_SECONDS
            ),
            key=lambda j: j.created,
        )
        for old in finished[: max(0, len(finished) - KEEP_FINISHED_JOBS)]:
            del self.items[old.id]
            shutil.rmtree(old.folder, ignore_errors=True)

    def position(self, job: Job) -> int:
        waiting = sorted(
            (j for j in list(self.items.values()) if j.state == "queued"), key=lambda j: j.created
        )
        return waiting.index(job) + 1 if job in waiting else 0

    def _stage(self, job: Job, name: str) -> None:
        if job.cancel:
            raise Cancelled
        job.stage = name

    def _work(self) -> None:
        while True:
            job = self.items.get(self.pending.get())
            with self.lock:
                if job is None or job.state != "queued":
                    continue  # cancelled or pruned while it waited
                job.state = "running"
            try:
                target = (
                    job.folder
                    / f"result{pipeline.output_path(job.source, job.options, media.probe(job.source)).suffix}"
                )
                job.report = pipeline.run(
                    job.source,
                    job.options,
                    target,
                    on_stage=lambda name, j=job: self._stage(j, name),
                    preview_dir=job.folder,
                    engine=self.engine_factory(job.options.engine),
                )
                if job.cancel:
                    raise Cancelled
                job.output = target
                job.state = "done"
            except Cancelled:
                job.state = "cancelled"
                shutil.rmtree(job.folder, ignore_errors=True)
            except Exception as err:  # the worker must outlive any single bad file
                job.state, job.error = "error", str(err) or err.__class__.__name__


class Guard:
    """Refuse other websites and oversized uploads before the body is read.

    A page on another origin can still POST a form to 127.0.0.1, and a rebinding DNS name can read the
    API, so the Host header must name this machine and a browser Origin must match the Host.
    """

    def __init__(self, app, allowed_hosts: set[str] | None, max_body: int) -> None:
        self.app = app
        self.allowed_hosts = allowed_hosts
        self.max_body = max_body

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        host = headers.get("host", "").lower()
        hostname = host.split("]")[0] + "]" if host.startswith("[") else host.rsplit(":", 1)[0]
        refusal = None
        if self.allowed_hosts is not None and hostname not in self.allowed_hosts:
            refusal = (403, "host not allowed")
        elif scope["method"] not in ("GET", "HEAD") and headers.get("origin") not in (None, f"http://{host}"):
            refusal = (403, "cross origin request refused")
        elif scope["method"] == "POST" and int(headers.get("content-length") or 0) > self.max_body:
            refusal = (413, "upload is too large")
        if refusal:
            await self._refuse(send, *refusal)
            return
        received, stopped = 0, False

        async def counted():
            nonlocal received, stopped
            message = await receive()
            if message["type"] == "http.request" and scope["method"] == "POST":
                received += len(message.get("body", b""))
                if received > self.max_body and not stopped:
                    stopped = True
                    await self._refuse(send, 413, "upload is too large")
                if stopped:
                    return {"type": "http.disconnect"}
            return message

        async def quiet(message):
            if not stopped:
                await send(message)

        await self.app(scope, counted, quiet)

    @staticmethod
    async def _refuse(send, status: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def create_app(
    max_upload_mb: int = 2048,
    engine_factory: Callable[[str], engines.Engine] = engines.get,
    work_dir: Path | None = None,
    host: str = "127.0.0.1",
) -> FastAPI:
    root = work_dir or Path(tempfile.mkdtemp(prefix="cleartake-jobs-"))
    root.mkdir(parents=True, exist_ok=True)
    jobs = Jobs(root, engine_factory)
    app = FastAPI(title="Cleartake", version=__version__, docs_url=None, redoc_url=None)
    open_bind = host in ("0.0.0.0", "::")
    app.add_middleware(
        Guard,
        allowed_hosts=None if open_bind else LOCAL_HOSTS | {host.lower()},
        max_body=(max_upload_mb + 1) * 1024 * 1024,
    )

    def find(job_id: str) -> Job:
        job = jobs.items.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown job")
        return job

    @app.get("/api/health")
    def health() -> dict:
        models = engines.home() / "models"
        return {
            "version": __version__,
            "device": engines.device_name(),
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "engines": [
                {
                    "id": i.id,
                    "model": i.model,
                    "summary": i.summary,
                    "downloaded": (models / i.model).is_dir(),
                }
                for i in engines.available()
            ],
            "presets": {
                name: {"lufs": lufs, "true_peak": tp} for name, (lufs, tp) in loudness.PRESETS.items()
            },
            "max_upload_mb": max_upload_mb,
        }

    @app.post("/api/jobs")
    async def create_job(
        file: UploadFile = File(...),
        engine: str = Form("studio"),
        strength: float = Form(1.0),
        preset: str = Form("podcast"),
        check: bool = Form(True),
        language: str = Form("en"),
    ) -> JSONResponse:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(415, f"unsupported file type {suffix or '(none)'}")
        language = language or "en"
        if language not in pipeline.CHECK_LANGUAGES:
            raise HTTPException(422, f"unknown language {language!r}")
        whisper, code = pipeline.check_model(language)
        options = pipeline.Options(
            engine=engine, strength=strength, preset=preset, check=check, whisper=whisper, language=code
        )
        try:
            options.validate()
        except ValueError as err:
            raise HTTPException(422, str(err)) from err
        job_id = uuid.uuid4().hex[:12]
        folder = root / job_id
        folder.mkdir()
        source = folder / f"input{suffix}"
        limit, size = max_upload_mb * 1024 * 1024, 0
        with source.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    handle.close()
                    shutil.rmtree(folder, ignore_errors=True)
                    raise HTTPException(413, f"file is larger than {max_upload_mb} MB")
                handle.write(chunk)
        label = Path(file.filename or "recording").stem[:80]
        jobs.add(Job(job_id, folder, source, label, options))
        return JSONResponse({"id": job_id}, status_code=202)

    @app.get("/api/jobs/{job_id}")
    def status(job_id: str) -> dict:
        job = find(job_id)
        job.seen = time.time()
        return job.public(jobs.position(job))

    @app.delete("/api/jobs/{job_id}")
    def cancel(job_id: str) -> dict:
        job = find(job_id)
        jobs.cancel(job)
        return {"state": job.state, "cancelling": job.cancel and job.state == "running"}

    def result_file(job_id: str, name: str) -> Path:
        job = find(job_id)
        path = job.folder / name
        if job.state != "done" or not path.is_file():
            raise HTTPException(409, "result is not ready")
        return path

    @app.get("/api/jobs/{job_id}/original.wav")
    def original(job_id: str) -> FileResponse:
        return FileResponse(result_file(job_id, "original.wav"), media_type="audio/wav")

    @app.get("/api/jobs/{job_id}/enhanced.wav")
    def enhanced(job_id: str) -> FileResponse:
        return FileResponse(result_file(job_id, "enhanced.wav"), media_type="audio/wav")

    @app.get("/api/jobs/{job_id}/download")
    def download(job_id: str) -> FileResponse:
        job = find(job_id)
        path = result_file(job_id, job.output.name if job.output else "result")
        return FileResponse(path, filename=f"{job.label}.cleartake{path.suffix}")

    @app.get("/api/jobs/{job_id}/report.json")
    def report(job_id: str) -> JSONResponse:
        job = find(job_id)
        result_file(job_id, "original.wav")
        slim = pipeline.slim_report(job.report)
        name = quote(f"{job.label}.cleartake.json")
        return JSONResponse(slim, headers={"Content-Disposition": f"attachment; filename*=utf-8''{name}"})

    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
