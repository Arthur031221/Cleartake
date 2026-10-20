import time

import pytest
from fastapi.testclient import TestClient

from cleartake import drift
from cleartake.server import create_app


@pytest.fixture
def client(fake_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(drift, "transcribe", lambda *a, **k: [drift.Word("hi", 0, 0.3)])
    return TestClient(
        create_app(engine_factory=lambda _id: fake_engine, work_dir=tmp_path, max_upload_mb=5),
        base_url="http://127.0.0.1:8765",
    )


def wait(client, job_id):
    for _ in range(100):
        data = client.get(f"/api/jobs/{job_id}").json()
        if data["state"] in {"done", "error"}:
            return data
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def test_health_lists_both_engines(client):
    data = client.get("/api/health").json()
    assert {e["id"] for e in data["engines"]} == {"classic", "studio"} and data["ffmpeg"]


def test_upload_to_download(client, wav_file):
    with wav_file.open("rb") as handle:
        response = client.post(
            "/api/jobs",
            files={"file": ("my talk.wav", handle, "audio/wav")},
            data={"engine": "classic", "preset": "podcast", "check": "true"},
        )
    assert response.status_code == 202
    job = wait(client, response.json()["id"])
    assert job["state"] == "done" and job["report"]["drift"]["changed"] == 0
    base = f"/api/jobs/{job['id']}"
    assert client.get(f"{base}/original.wav").content[:4] == b"RIFF"
    assert client.get(f"{base}/enhanced.wav").content[:4] == b"RIFF"
    download = client.get(f"{base}/download")
    assert "my%20talk.cleartake.wav" in download.headers["content-disposition"]
    assert "transcript_before" not in client.get(f"{base}/report.json").json()["drift"]


def test_rejects_unknown_type_bad_option_and_oversize(client, wav_file):
    assert client.post("/api/jobs", files={"file": ("a.exe", b"x")}).status_code == 415
    assert (
        client.post("/api/jobs", files={"file": ("a.wav", b"x")}, data={"strength": "2"}).status_code == 422
    )
    big = b"0" * (6 * 1024 * 1024)
    assert client.post("/api/jobs", files={"file": ("a.wav", big)}).status_code == 413


def test_broken_upload_reports_an_error_and_the_worker_survives(client, wav_file):
    bad = client.post("/api/jobs", files={"file": ("a.wav", b"nope")}).json()["id"]
    assert wait(client, bad)["state"] == "error"
    good = client.post(
        "/api/jobs", files={"file": ("b.wav", wav_file.read_bytes())}, data={"check": "false"}
    ).json()["id"]
    assert wait(client, good)["state"] == "done"


def test_unknown_job_and_early_download(client):
    assert client.get("/api/jobs/missing").status_code == 404
    assert client.get("/api/jobs/missing/original.wav").status_code == 404


def test_work_dir_is_created_when_missing(fake_engine, tmp_path, wav_file):
    app = create_app(engine_factory=lambda _id: fake_engine, work_dir=tmp_path / "not" / "yet")
    with wav_file.open("rb") as handle:
        response = TestClient(app, base_url="http://127.0.0.1:8765").post(
            "/api/jobs", files={"file": ("a.wav", handle, "audio/wav")}
        )
    assert response.status_code == 202


def test_foreign_host_and_foreign_origin_are_refused(client, wav_file):
    assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 403
    upload = {"file": ("a.wav", wav_file.read_bytes())}
    assert (
        client.post("/api/jobs", files=upload, headers={"origin": "https://evil.example"}).status_code == 403
    )
    same = client.post("/api/jobs", files=upload, headers={"origin": "http://127.0.0.1:8765"})
    assert same.status_code == 202


def test_oversize_body_is_refused_before_it_is_stored(client, tmp_path):
    big = b"0" * (7 * 1024 * 1024)
    assert client.post("/api/jobs", files={"file": ("a.wav", big)}).status_code == 413
    assert not any(p.is_dir() for p in tmp_path.iterdir())


def test_old_jobs_are_removed(client, wav_file, monkeypatch):
    from cleartake import server

    monkeypatch.setattr(server, "KEEP_FINISHED_JOBS", 2)
    ids = []
    for _ in range(4):
        job = client.post(
            "/api/jobs", files={"file": ("a.wav", wav_file.read_bytes())}, data={"check": "false"}
        )
        ids.append(job.json()["id"])
        wait(client, ids[-1])
    assert client.get(f"/api/jobs/{ids[0]}").status_code == 404
    assert client.get(f"/api/jobs/{ids[-1]}").status_code == 200
