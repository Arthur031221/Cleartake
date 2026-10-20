"""Render assets/social-card.png (1200x675) from tools/social-card.html with headless Chrome."""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1200, "height": 675})
    page.goto((ROOT / "tools/social-card.html").as_uri())
    page.wait_for_timeout(400)
    page.screenshot(path=str(ROOT / "assets/social-card.png"))
    browser.close()
print(ROOT / "assets/social-card.png")
