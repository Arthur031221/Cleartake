import re
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cleartake import drift, pipeline, server
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
        if data["state"] in {"done", "error", "cancelled"}:
            return data
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def test_health_lists_both_engines(client):
    data = client.get("/api/health").json()
    assert {e["id"] for e in data["engines"]} == {"classic", "studio"} and data["ffmpeg"]


def post_with_language(client, wav_file, monkeypatch, **data):
    seen = []

    def transcribe(audio, model_name="base.en", language=None):
        seen.append((model_name, language))
        return [drift.Word("hi", 0, 0.3)]

    monkeypatch.setattr(drift, "transcribe", transcribe)
    with wav_file.open("rb") as handle:
        response = client.post("/api/jobs", files={"file": ("talk.wav", handle, "audio/wav")}, data=data)
    if response.status_code == 202:
        job = wait(client, response.json()["id"])
        assert job["state"] == "done", job
    return response, seen


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (None, ("base.en", "en")),
        ("en", ("base.en", "en")),
        ("de", ("small", "de")),
        ("auto", ("small", None)),
    ],
)
def test_word_check_model_follows_the_spoken_language(client, wav_file, monkeypatch, language, expected):
    data = {"check": "true", **({"language": language} if language else {})}
    response, seen = post_with_language(client, wav_file, monkeypatch, **data)
    assert response.status_code == 202 and seen and set(seen) == {expected}


def test_unknown_spoken_language_is_refused(client, wav_file, monkeypatch):
    response, seen = post_with_language(client, wav_file, monkeypatch, check="true", language="../../etc")
    assert response.status_code == 422 and not seen


def test_language_menu_in_the_page_matches_what_the_server_accepts():
    page = (Path(server.__file__).parent / "web" / "index.html").read_text(encoding="utf-8")
    menu = re.search(r'<select id="check-language">(.*?)</select>', page, re.S).group(1)
    assert set(re.findall(r'value="([^"]+)"', menu)) == pipeline.CHECK_LANGUAGES


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
    monkeypatch.setattr(server, "KEEP_FINISHED_JOBS", 2)
    monkeypatch.setattr(server, "OPEN_RESULT_SECONDS", 0)
    ids = []
    for _ in range(4):
        job = client.post(
            "/api/jobs", files={"file": ("a.wav", wav_file.read_bytes())}, data={"check": "false"}
        )
        ids.append(job.json()["id"])
        wait(client, ids[-1])
    assert client.get(f"/api/jobs/{ids[0]}").status_code == 404
    assert client.get(f"/api/jobs/{ids[-1]}").status_code == 200


@pytest.fixture
def gated(gate, tmp_path, monkeypatch):
    monkeypatch.setattr(drift, "transcribe", lambda *a, **k: [drift.Word("hi", 0, 0.3)])
    app = create_app(engine_factory=lambda _id: gate, work_dir=tmp_path)
    return TestClient(app, base_url="http://127.0.0.1:8765"), gate, tmp_path


def submit(client, wav_file, **data):
    response = client.post(
        "/api/jobs", files={"file": ("a.wav", wav_file.read_bytes())}, data={"check": "false", **data}
    )
    return response.json()["id"]


def test_cancel_a_queued_job_and_the_next_one_still_runs(gated, wav_file):
    client, gate, tmp_path = gated
    first = submit(client, wav_file)
    assert gate.entered.wait(5)
    second, third = submit(client, wav_file), submit(client, wav_file)
    assert client.get(f"/api/jobs/{third}").json()["queue_position"] == 2
    assert client.delete(f"/api/jobs/{second}").json()["state"] == "cancelled"
    assert client.get(f"/api/jobs/{third}").json()["queue_position"] == 1
    assert not (tmp_path / second).exists()
    gate.release.set()
    assert wait(client, first)["state"] == "done"
    assert wait(client, third)["state"] == "done"
    assert client.get(f"/api/jobs/{second}").json()["state"] == "cancelled"


def test_cancel_a_running_job_stops_at_the_next_stage(gated, wav_file):
    client, gate, tmp_path = gated
    job = submit(client, wav_file)
    assert gate.entered.wait(5)
    answer = client.delete(f"/api/jobs/{job}").json()
    assert answer == {"state": "running", "cancelling": True}
    gate.release.set()
    assert wait(client, job)["state"] == "cancelled"
    assert not (tmp_path / job).exists()
    after = submit(client, wav_file)
    assert wait(client, after)["state"] == "done"


def test_deleting_a_finished_job_removes_it(client, wav_file):
    job = submit(client, wav_file)
    assert wait(client, job)["state"] == "done"
    assert client.delete(f"/api/jobs/{job}").status_code == 200
    assert client.get(f"/api/jobs/{job}").status_code == 404
    assert client.delete(f"/api/jobs/{job}").status_code == 404


def test_a_job_the_page_just_polled_is_not_pruned(client, wav_file, monkeypatch):
    monkeypatch.setattr(server, "KEEP_FINISHED_JOBS", 1)
    ids = [submit(client, wav_file) for _ in range(3)]
    for job in ids:
        wait(client, job)
    submit(client, wav_file)  # triggers a prune while all three were polled seconds ago
    assert all(client.get(f"/api/jobs/{job}").status_code == 200 for job in ids)


def test_foreign_origin_cannot_cancel(client, wav_file):
    job = submit(client, wav_file)
    wait(client, job)
    refused = client.delete(f"/api/jobs/{job}", headers={"Origin": "http://evil.example"})
    assert refused.status_code == 403
    assert client.get(f"/api/jobs/{job}").status_code == 200
