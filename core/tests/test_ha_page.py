# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0176: a page from Home Assistant on the screen, for a while."""
import asyncio

import pytest

from gexis_core import ha_page
from gexis_core.ha_page import Page, Refused, explain, parse, parse_preload, too_hot

URL = "http://ha.example:8123/home-security/tv"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _page(**kw):
    told, prepared, restored = [], [], []

    async def prepare():
        prepared.append(True)
        return {"standby": True}

    async def restore(token, back):
        restored.append((token, back))

    page = Page(told.append, prepare=prepare, restore=restore, clock=Clock(), **kw)
    return page, told, prepared, restored


def test_the_call_is_read_with_its_defaults():
    assert parse({"url": URL}) == (URL, "page", 600)
    assert parse({"url": f" {URL} ", "id": " cameras ", "seconds": 60}) == (URL, "cameras", 60)


@pytest.mark.parametrize("body", [
    None, [], {}, {"url": ""}, {"url": "ftp://ha.example/x"}, {"url": "ha.example/x"},
    {"url": URL, "id": ""}, {"url": URL, "id": "x" * 65}, {"url": URL, "id": 3},
    {"url": URL, "seconds": 9}, {"url": URL, "seconds": 3601}, {"url": URL, "seconds": True},
    {"url": URL, "seconds": "60"},
])
def test_a_call_out_of_bounds_is_refused_with_a_400(body):
    with pytest.raises(Refused) as caught:
        parse(body)
    assert caught.value.status == 400


def test_the_longest_limit_is_an_hour_and_the_default_ten_minutes():
    """George, 2026-11-07: 10 minutes when the call gives none, at most 60."""
    assert (ha_page.DEFAULT_S, ha_page.MAX_S) == (600, 3600)
    assert parse({"url": URL, "seconds": 3600})[2] == 3600


def test_the_caller_is_told_why_a_page_cannot_be_framed():
    assert "Send X-Frame-Options" in explain("refuses framing")
    assert "(404)" in explain("http 404")
    assert "does not answer" in explain("unreachable")


async def test_up_then_down_prepares_once_and_puts_back_what_was_there():
    page, told, prepared, restored = _page()
    await page.show(URL, "cameras", 60)
    assert page.shown and page.id == "cameras" and page.until == 1060.0
    assert told[-1] == {"shown": True, "id": "cameras", "until": 1060.0, "seq": 1, "closed": None,
                        "preloaded": False}
    assert await page.hide("touch")
    assert told[-1]["shown"] is False and told[-1]["closed"] == {"id": "cameras", "by": "touch", "at": 1000.0}
    assert prepared == [True] and restored == [({"standby": True}, True)]
    assert not await page.hide("touch")


async def test_the_address_never_reaches_the_state():
    """P2: the socket is open on the network and an address can carry a token."""
    page, told, _, _ = _page()
    await page.show(URL, "cameras", 60)
    assert all(URL not in repr(state) for state in told)
    await page.hide("asked")


async def test_a_new_id_replaces_the_page_without_putting_anything_back():
    page, told, prepared, restored = _page()
    await page.show(URL, "cameras", 60)
    await page.show(URL + "/doorbell", "doorbell", 60)
    assert page.id == "doorbell" and told[-1]["seq"] == 2
    assert told[-1]["closed"]["id"] == "cameras" and told[-1]["closed"]["by"] == "replaced"
    assert prepared == [True] and restored == []
    await page.hide("asked")
    assert restored == [({"standby": True}, True)]


async def test_the_same_id_again_restarts_its_limit_and_reloads_only_for_a_new_address():
    page, told, _, _ = _page()
    await page.show(URL, "doorbell", 60)
    page._clock.now += 30
    await page.show(URL, "doorbell", 60)
    assert page.until == 1090.0 and told[-1]["seq"] == 1
    await page.show(URL + "?x", "doorbell", 60)
    assert told[-1]["seq"] == 2
    await page.hide("asked")


async def test_a_hide_with_an_id_closes_only_that_page():
    page, _, _, _ = _page()
    await page.show(URL, "cameras", 60)
    assert not await page.hide("asked", page_id="doorbell") and page.shown
    assert await page.hide("asked", page_id="cameras") and not page.shown


async def test_a_persons_request_takes_it_down_without_putting_back():
    """P5: someone who asked the panel for something else wants that."""
    page, _, _, restored = _page()
    await page.show(URL, "cameras", 60)
    await page.hide("asked", back=False)
    assert restored == [({"standby": True}, False)]


async def test_the_limit_takes_it_down():
    page, told, _, restored = _page()
    await page.show(URL, "cameras", 0)
    await asyncio.sleep(0.05)
    assert not page.shown and told[-1]["closed"]["by"] == "limit"
    assert restored == [({"standby": True}, True)]


async def test_a_page_taken_down_early_does_not_close_a_later_one_at_its_limit():
    page, _, _, _ = _page()
    await page.show(URL, "cameras", 0.05)
    await page.hide("touch")
    await page.show(URL, "doorbell", 60)
    await asyncio.sleep(0.1)
    assert page.shown and page.id == "doorbell"
    await page.hide("asked")


def test_heat_is_80_degrees_or_the_firmware_throttling_now():
    assert not too_hot(79.9, 0x0) and too_hot(80.0, 0x0)
    assert too_hot(60.0, 0x4) and too_hot(60.0, 0x8) and too_hot(60.0, 0x2)
    # Under-voltage alone, and throttling that happened earlier, are not heat.
    assert not too_hot(60.0, 0x1) and not too_hot(60.0, 0x50000)
    assert not too_hot(None, None)


async def test_the_heat_takes_it_down():
    """P8: the music comes first (George, 2026-11-07)."""
    readings = iter([(70.0, 0), (81.0, 0)])
    page, told, _, _ = _page(heat=lambda: next(readings), heat_every=0.01)
    await page.show(URL, "cameras", 60)
    for _ in range(50):
        await asyncio.sleep(0.01)
        if not page.shown:
            break
    assert not page.shown and told[-1]["closed"]["by"] == "heat"


async def test_a_reading_that_fails_does_not_stop_the_watch():
    calls = []

    def heat():
        calls.append(1)
        if len(calls) == 1:
            raise OSError("no vcgencmd")
        return (85.0, 0)

    page, _, _, _ = _page(heat=heat, heat_every=0.01)
    await page.show(URL, "cameras", 60)
    for _ in range(50):
        await asyncio.sleep(0.01)
        if not page.shown:
            break
    assert not page.shown and len(calls) >= 2


# --- the amendment: one page kept loaded (K1-K8) ---------------------------

def test_a_page_to_keep_is_an_http_address_and_null_or_empty_clears_it():
    assert parse_preload({"url": f" {URL} "}) == URL
    assert parse_preload({"url": None}) is None
    assert parse_preload({"url": " "}) is None
    for body in (None, {}, [], {"url": 3}, {"url": "ftp://ha.example/x"}, {"url": "ha.example/x"}):
        with pytest.raises(Refused) as caught:
            parse_preload(body)
        assert caught.value.status == 400


def test_the_page_kept_is_saved_and_read_again_at_the_next_start(tmp_path):
    path = tmp_path / "page-preload.json"
    page, told, _, _ = _page(preload_path=path)
    assert page.preload is None and page.state()["preloaded"] is False
    page.set_preload(URL)
    assert told[-1]["preloaded"] is True and told[-1]["seq"] == 1
    again, _, _, _ = _page(preload_path=path)
    assert again.preload == URL and again.preloaded
    again.set_preload(None)
    assert _page(preload_path=path)[0].preload is None


def test_a_damaged_file_keeps_nothing(tmp_path):
    path = tmp_path / "page-preload.json"
    for text in ("not json", "[]", '{"url": "ftp://x/y"}', '{"url": 3}'):
        path.write_text(text)
        assert _page(preload_path=path)[0].preload is None


def test_the_same_address_again_is_loaded_afresh():
    """K1: Home Assistant's way to renew it, after a crash the panel cannot see."""
    page, told, _, _ = _page()
    page.set_preload(URL)
    n, seq = page.preload_n, page.seq
    page.set_preload(URL)
    assert page.preload_n == n + 1 and page.seq == seq + 1


def test_it_is_preloaded_only_while_the_switch_is_on_with_a_screen():
    """K5: off, it is unloaded; the address stays for when it is on again."""
    on = [True]
    page, told, _, _ = _page(available=lambda: on[0])
    page.set_preload(URL)
    assert page.preloaded
    on[0] = False
    page.refresh()
    assert told[-1]["preloaded"] is False and page.preload == URL
    on[0] = True
    page.refresh()
    assert told[-1]["preloaded"] is True


async def test_closing_the_page_kept_leaves_it_kept():
    """K4: every close only hides it."""
    page, told, _, _ = _page()
    page.set_preload(URL)
    await page.show(URL, "cameras", 60)
    assert await page.hide("touch")
    assert page.preload == URL and told[-1]["preloaded"] is True and told[-1]["shown"] is False


def test_the_address_kept_never_reaches_the_state():
    page, told, _, _ = _page()
    page.set_preload(URL)
    assert URL not in repr(told) and URL not in repr(page.state())
