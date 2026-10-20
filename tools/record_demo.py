"""Record assets/demo.gif from the real app: real server, real models, headless Chrome.

Usage: python tools/record_demo.py noisy.wav [out.gif]
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

from cleartake.server import create_app

SIZE = {"width": 1040, "height": 720}


def serve(work: Path) -> tuple[uvicorn.Server, str]:
    server = uvicorn.Server(
        uvicorn.Config(create_app(work_dir=work), host="127.0.0.1", port=0, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        thread.join(0.05)
    return server, f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}/"


def main() -> None:
    source = Path(sys.argv[1]).resolve()
    gif = Path(sys.argv[2] if len(sys.argv) > 2 else "assets/demo.gif").resolve()
    with tempfile.TemporaryDirectory() as tmp:
        server, url = serve(Path(tmp) / "work")
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            context = browser.new_context(
                viewport=SIZE,
                record_video_dir=tmp,
                record_video_size=SIZE,
                color_scheme="dark",
                locale="en-US",
            )
            page = context.new_page()
            page.goto(url)
            page.wait_for_selector("html[data-ready]")
            page.wait_for_timeout(900)
            page.set_input_files("#file", str(source))
            page.wait_for_timeout(900)
            page.click("#go")
            page.wait_for_selector("#result:not([hidden])", timeout=120000)
            page.wait_for_timeout(1300)
            page.click("#ab-a")
            page.wait_for_timeout(1300)
            page.click("#ab-b")
            page.wait_for_timeout(1300)
            page.mouse.wheel(0, 380)
            page.wait_for_timeout(1800)
            page.mouse.wheel(0, 400)
            page.wait_for_timeout(2200)
            video = Path(page.video.path())
            context.close()
            browser.close()
        server.should_exit = True
        palette = Path(tmp) / "palette.png"
        scale = "fps=12,scale=860:-1:flags=lanczos"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(video),
                "-vf",
                f"{scale},palettegen=max_colors=96",
                str(palette),
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(video),
                "-i",
                str(palette),
                "-lavfi",
                f"{scale}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
                str(gif),
            ],
            check=True,
        )
    print(gif, gif.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
