import functools
import http.server
import threading
from pathlib import Path

import pytest
import uvicorn

from cleartake import drift
from cleartake.server import create_app

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "src" / "cleartake" / "web"
DEMO = ROOT / "docs" / "demo"

playwright_sync = pytest.importorskip("playwright.sync_api")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def browser():
    with playwright_sync.sync_playwright() as p:
        try:
            launched = p.chromium.launch(channel="chrome")
        except Exception:
            launched = p.chromium.launch()
        yield launched
        launched.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1100, "height": 900}, locale="en-US")
    page = context.new_page()
    page.errors = []
    goto = page.goto

    def goto_ready(url, **kwargs):
        response = goto(url, **kwargs)
        page.wait_for_selector("html[data-ready]")
        return response

    page.goto = goto_ready
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    yield page
    context.close()


@pytest.fixture
def app_url(fake_engine, tmp_path_factory, monkeypatch):
    """The real FastAPI app on a free port, with a fake engine and a stubbed transcript."""
    monkeypatch.setattr(drift, "transcribe", lambda *a, **k: [drift.Word("hello", 0, 0.3)])
    app = create_app(engine_factory=lambda _id: fake_engine, work_dir=tmp_path_factory.mktemp("work"))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        thread.join(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}/"
    server.should_exit = True
    thread.join(5)


@pytest.fixture(scope="session")
def demo_url(tmp_path_factory):
    """The static site as GitHub Pages serves it: web files plus the pre-rendered demo."""
    import shutil

    site = tmp_path_factory.mktemp("site")
    shutil.copytree(WEB, site, dirs_exist_ok=True)
    shutil.copytree(DEMO, site / "demo")
    handler = functools.partial(_Quiet, directory=str(site))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()
