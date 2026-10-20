import json

import pytest

pytestmark = pytest.mark.e2e


def test_upload_enhance_and_download(page, app_url, wav_file):
    page.goto(app_url)
    page.set_input_files("#file", str(wav_file))
    page.click("#go")
    page.wait_for_selector("#result:not([hidden])", timeout=60000)
    assert "LUFS" in page.inner_text("#stat-lufs-sub")
    assert page.inner_text("#drift-chip").strip()
    with page.expect_download() as download:
        page.click("#dl-audio")
    assert download.value.suggested_filename.endswith(".cleartake.wav")
    assert page.errors == []


def test_ab_toggle_and_keyboard(page, app_url, wav_file):
    page.goto(app_url)
    page.set_input_files("#file", str(wav_file))
    page.click("#go")
    page.wait_for_selector("#result:not([hidden])", timeout=60000)
    assert page.get_attribute("#ab-b", "aria-pressed") == "true"
    page.click("#ab-a")
    assert page.get_attribute("#ab-a", "aria-pressed") == "true"
    page.keyboard.press("b")
    assert page.get_attribute("#ab-b", "aria-pressed") == "true"


def test_demo_mode_without_server(page, demo_url):
    page.goto(demo_url + "?sample")
    page.wait_for_selector("#result:not([hidden])", timeout=30000)
    assert page.is_visible("#demo-banner")
    assert page.locator("#transcript span").count() > 30
    assert page.errors == []


def test_changed_words_are_marked_and_clickable(page, demo_url):
    def tamper(route):
        report = json.loads(route.fetch().text())
        first = report["drift"]["transcript_after"][0]
        report["drift"].update(
            changed=1,
            changes=[
                {
                    "kind": "changed",
                    "before": "xyz",
                    "after": first["text"],
                    "start": first["start"],
                    "end": first["end"],
                }
            ],
        )
        route.fulfill(json=report)

    page.route("**/demo/report.json", tamper)
    page.goto(demo_url + "?sample")
    page.wait_for_selector("#result:not([hidden])", timeout=30000)
    assert page.locator("#transcript .changed").count() == 1
    assert page.inner_text("#drift-chip") == "1 word differs"
    page.click("#transcript .changed")
    assert page.errors == []


def test_language_switch_translates_and_persists(page, demo_url):
    page.goto(demo_url)
    english = page.inner_text("h1")
    page.select_option("#lang", "ja")
    page.wait_for_function("document.documentElement.lang === 'ja'")
    assert page.inner_text("h1") != english
    page.reload()
    assert page.input_value("#lang") == "ja"


def test_theme_toggle(page, demo_url):
    page.goto(demo_url)
    before = page.evaluate("document.documentElement.dataset.theme")
    page.click("#theme")
    assert page.evaluate("document.documentElement.dataset.theme") != before


def test_switches_render_a_track(page, app_url):
    page.goto(app_url)
    width = page.evaluate("document.querySelector('label.switch .track').getBoundingClientRect().width")
    assert width >= 30
