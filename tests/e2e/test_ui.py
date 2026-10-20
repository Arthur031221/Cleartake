import json

import pytest

from cleartake import drift

from .conftest import DEMO

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


def test_spoken_language_reaches_the_word_check_and_follows_the_check_switch(
    page, app_url, wav_file, monkeypatch
):
    page.goto(app_url)
    seen = []
    monkeypatch.setattr(
        drift,
        "transcribe",
        lambda audio, model="base.en", language=None: seen.append((model, language)) or [],
    )
    assert page.input_value("#check-language") == "en"
    page.select_option("#check-language", "de")
    page.set_input_files("#file", str(wav_file))
    page.click("#go")
    page.wait_for_selector("#result:not([hidden])", timeout=60000)
    assert set(seen) == {("small", "de")}
    page.click("#again")
    page.click("label.switch:has(#check)")
    assert page.is_disabled("#check-language")
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
    assert "Drop" not in page.inner_text("#intro")
    assert page.locator("#transcript span").count() > 30
    assert page.errors == []


def test_demo_page_makes_no_failed_requests(page, demo_url):
    failed = []
    page.on("response", lambda r: failed.append((r.status, r.url)) if r.status >= 400 else None)
    page.goto(demo_url + "?sample")
    page.wait_for_selector("#result:not([hidden])", timeout=30000)
    assert failed == []


def test_changes_sample_shows_marked_words_and_the_picture_has_a_name(page, demo_url):
    page.goto(demo_url)
    page.wait_for_selector("html[data-ready]")
    page.click("#sample-changes")
    page.wait_for_selector("#result:not([hidden])", timeout=30000)
    report = json.loads((DEMO / "changes" / "report.json").read_text())
    assert page.locator("#transcript .changed, #transcript .dropped, #transcript .added").count() >= 1
    assert page.inner_text("#drift-chip") != "No word changed"
    assert report["drift"]["changes"]
    assert page.get_attribute("#dl-report", "href") == "demo/changes/report.json"
    assert (
        page.get_attribute("#stage", "aria-label")
        == "Spectrogram of the recording. Arrow keys move the playhead."
    )
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


def test_several_files_run_as_a_list_and_each_can_be_reviewed(page, app_url, wav_file, tmp_path):
    second = tmp_path / "second.wav"
    second.write_bytes(wav_file.read_bytes())
    page.goto(app_url)
    page.set_input_files("#file", [str(wav_file), str(second)])
    assert "2" in page.inner_text("#file-name")
    page.click("#go")
    page.wait_for_selector("#files li[data-status=done] >> nth=1", timeout=60000)
    assert page.locator("#files li").count() == 2
    assert page.is_hidden("#result")
    page.locator("#files button[data-act=review]").nth(1).click()
    page.wait_for_selector("#result:not([hidden])", timeout=30000)
    assert page.is_hidden("#again") and page.is_visible("#back")
    page.click("#back")
    assert page.is_visible("#files") and page.is_hidden("#result")
    assert page.locator("#files a[download]").count() == 2
    assert page.errors == []


def test_cancel_a_waiting_file_and_a_running_one(page, held_app_url, gate, wav_file, tmp_path):
    second = tmp_path / "second.wav"
    second.write_bytes(wav_file.read_bytes())
    page.goto(held_app_url)
    page.set_input_files("#file", [str(wav_file), str(second)])
    page.click("#go")
    page.wait_for_selector("#files li[data-status=queued]", timeout=30000)
    assert gate.entered.wait(10)
    page.locator("#files button[data-act=cancel]").nth(1).click()
    page.wait_for_selector("#files li[data-status=cancelled]", timeout=10000)
    page.locator("#files button[data-act=cancel]").first.click()
    page.wait_for_selector("#files li[data-status=cancelling]", timeout=10000)
    gate.release.set()
    page.wait_for_function(
        "document.querySelectorAll('#files li[data-status=cancelled]').length === 2", timeout=30000
    )
    assert page.is_visible("#retry")
    assert page.errors == []


def test_single_file_can_be_cancelled_while_it_waits(page, held_app_url, gate, wav_file):
    page.goto(held_app_url)
    page.set_input_files("#file", str(wav_file))
    page.click("#go")
    assert gate.entered.wait(10)
    page.click("#cancel")
    gate.release.set()
    page.wait_for_function("document.getElementById('retry').hidden === false", timeout=30000)
    assert page.is_hidden("#cancel") and page.is_hidden("#result")
    page.click("#retry")
    assert page.is_visible("#setup")


def test_a_pruned_job_shows_an_error_instead_of_hanging(page, app_url, wav_file):
    page.route(
        "**/api/jobs/*",
        lambda route: (
            route.fulfill(status=404, body="{}")
            if route.request.method == "GET" and route.request.url.count("/") == 5
            else route.continue_()
        ),
    )
    page.goto(app_url)
    page.set_input_files("#file", str(wav_file))
    page.click("#go")
    page.wait_for_selector("#error:not([hidden])", timeout=15000)
    assert "no longer" in page.inner_text("#error")
    assert page.is_visible("#retry")


def test_keys_do_not_leak_out_of_form_fields_and_words_are_reachable(page, demo_url):
    page.goto(demo_url + "?sample")
    page.wait_for_selector("#result:not([hidden])", timeout=30000)
    assert page.get_attribute("#ab-b", "aria-pressed") == "true"
    page.focus("#lang")
    page.keyboard.press("b")
    assert page.get_attribute("#ab-b", "aria-pressed") == "true"
    page.focus("#stage")
    page.keyboard.press("b")
    assert page.get_attribute("#ab-a", "aria-pressed") == "true"
    page.select_option("#lang", "de")
    page.wait_for_function("document.getElementById('play').getAttribute('aria-label') === 'Wiedergabe'")
    word = page.locator("#transcript span").first
    assert word.get_attribute("role") == "button" and word.get_attribute("tabindex") == "0"
    word.focus()
    page.keyboard.press("Enter")
    page.wait_for_function("document.getElementById('play').getAttribute('aria-label') === 'Pause'")


def test_arrow_keys_seek_when_the_picture_has_focus(page, demo_url):
    page.goto(demo_url + "?sample")
    page.wait_for_selector("#result:not([hidden])", timeout=30000)
    page.focus("#stage")
    page.keyboard.press("ArrowRight")
    page.wait_for_function("document.getElementById('time').textContent.startsWith('0:05')")
    page.keyboard.press("ArrowLeft")
    page.wait_for_function("document.getElementById('time').textContent.startsWith('0:00')")
