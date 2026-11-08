# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0176: the routes for a page from Home Assistant on the screen."""
import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import panel_token
from gexis_core.ha_page import Page
from gexis_core.settings_registry import UnknownSetting
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

URL = "http://ha.example:8123/home-security/tv"
TOKEN = "t" * 32


class _Settings:
    def __init__(self, **values):
        self.values = {"ha_pages": True, "headless": False, **values}

    def value(self, key):
        if key not in self.values:
            raise UnknownSetting(key)
        return self.values[key]

    def set(self, key, value):
        self.values[key] = value
        return value

    def row(self, key):
        return {}


class _Keys:
    def __init__(self):
        self.pressed = []

    async def dpad(self, name):
        self.pressed.append(name)
        return True


def _setup(check=None, **settings):
    store = StateStore({})
    restored = []

    async def restore(token, back):
        restored.append(back)

    page = Page(lambda state: store.set_panel(page=state), restore=restore)

    async def ok(url):
        return {"url": url, "embeddable": True, "reason": None}

    server = StateServer(store, settings=_Settings(**settings), page=page, page_check=check or ok,
                         panel_input=_Keys())
    return store, page, server, restored


@pytest.mark.asyncio
async def test_a_show_puts_it_up_without_the_address_in_the_state():
    store, page, server, _ = _setup()
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/panel/page/show", json={"url": URL, "id": "cameras", "seconds": 120})
        assert r.status == 200 and (await r.json())["shown"] is True
        assert store.state.panel["page"]["id"] == "cameras" and page.url == URL
        assert URL not in repr(store.state.panel)


@pytest.mark.asyncio
@pytest.mark.parametrize("settings, status", [
    ({"ha_pages": False}, 403),
    ({"ha_pages": None}, 403),
    ({"headless": True}, 409),
])
async def test_the_switch_off_or_no_screen_refuses_a_show(settings, status):
    _, page, server, _ = _setup(**settings)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/panel/page/show", json={"url": URL})
        assert r.status == status and "error" in await r.json()
        assert not page.shown


@pytest.mark.asyncio
async def test_a_bad_call_is_a_400_and_an_unknown_action_a_404():
    _, page, server, _ = _setup()
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/panel/page/show", json={"url": "ftp://x"})).status == 400
        assert (await client.post("/panel/page/show", data="nonsense")).status == 400
        assert (await client.post("/panel/page/show", json={"url": URL, "seconds": 4000})).status == 400
        assert (await client.post("/panel/page/raise", json={"url": URL})).status == 404
        assert not page.shown


@pytest.mark.asyncio
async def test_a_page_that_cannot_be_framed_is_refused_with_its_sentence():
    async def refuses(url):
        return {"url": url, "embeddable": False, "reason": "refuses framing"}

    _, page, server, _ = _setup(check=refuses)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/panel/page/show", json={"url": URL})
        body = await r.json()
        assert r.status == 422 and body["reason"] == "refuses framing"
        assert "Send X-Frame-Options" in body["error"] and not page.shown


@pytest.mark.asyncio
async def test_the_address_is_given_to_the_panel_only():
    store = StateStore({})
    page = Page(lambda state: store.set_panel(page=state))

    async def ok(url):
        return {"url": url, "embeddable": True, "reason": None}

    server = StateServer(store, settings=_Settings(), page=page, page_check=ok, panel_token=TOKEN)
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/show", json={"url": URL})
        anyone = await (await client.get("/panel/page")).json()
        panel = await (await client.get("/panel/page", headers={panel_token.HEADER: TOKEN})).json()
        assert "url" not in anyone and anyone["shown"] is True and anyone["pages"] is True
        assert panel["url"] == URL


@pytest.mark.asyncio
async def test_a_hide_with_an_id_closes_only_that_page_and_a_touch_is_the_panels_word():
    store, page, server, restored = _setup()
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/show", json={"url": URL, "id": "cameras"})
        r = await client.post("/panel/page/hide", json={"id": "doorbell"})
        assert (await r.json())["hidden"] is False and page.shown
        r = await client.post("/panel/page/hide?by=touch")
        assert (await r.json())["hidden"] is True
        assert store.state.panel["page"]["closed"]["by"] == "touch" and restored == [True]


@pytest.mark.asyncio
async def test_a_touch_from_anyone_but_the_panel_is_an_ordinary_hide():
    store = StateStore({})
    page = Page(lambda state: store.set_panel(page=state))
    server = StateServer(store, settings=_Settings(), page=page, panel_token=TOKEN)
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/show", json={"url": URL})
        await client.post("/panel/page/hide?by=touch")
        assert store.state.panel["page"]["closed"]["by"] == "asked"


@pytest.mark.asyncio
async def test_any_key_closes_the_page_and_is_not_passed_on():
    """P4 (George, 2026-11-07): the remote's version of any touch."""
    store, page, server, _ = _setup()
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/show", json={"url": URL})
        r = await client.post("/panel/key", json={"key": "down"})
        assert await r.json() == {"key": "down", "page": "hidden"}
        assert server._panel_input.pressed == [] and store.state.panel["page"]["closed"]["by"] == "key"
        await client.post("/panel/key", json={"key": "down"})
        assert server._panel_input.pressed == ["down"]


@pytest.mark.asyncio
async def test_a_persons_request_takes_the_page_down_without_putting_back():
    """P5 (George, 2026-11-07): a person's request wins."""
    store, page, server, restored = _setup()
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/show", json={"url": URL})
        assert (await client.post("/panel/go/home")).status == 200
        assert not page.shown and restored == [False]
        assert store.state.panel["page"]["closed"]["by"] == "asked"


class _Visualiser:
    """Refused while a page is up, as the real one is."""
    refused = False

    def __init__(self, page, store):
        self.page, self.store, self.raised_under = page, store, []

    def on_touch(self):
        pass

    def _has_levels(self):
        return True

    async def request_async(self, action):
        if action == "show" and self.page.shown:
            return False
        self.raised_under.append(self.store.state.panel["page"]["shown"])
        return True


@pytest.mark.asyncio
async def test_the_visualiser_asked_for_is_raised_over_the_page_before_it_goes():
    """P5 with nothing between them: now playing showed while the visualiser
    was raised after the page had gone (sofapi, 2026-11-08)."""
    store, page, server, restored = _setup()
    server._peppy = visualiser = _Visualiser(page, store)
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/show", json={"url": URL})
        r = await client.post("/peppy/show")
        assert r.status == 200 and visualiser.raised_under == [True]
        assert not page.shown and store.state.panel["page"]["closed"]["by"] == "asked"
        assert restored == [False]
        await client.post("/peppy/show")
        assert visualiser.raised_under == [True, False]


@pytest.mark.asyncio
async def test_the_switch_turned_off_takes_a_page_down_and_the_status_says_so():
    store, page, server, _ = _setup()
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.get("/player/status")).json())["pages"] is True
        await client.post("/panel/page/show", json={"url": URL})
        assert (await client.put("/settings/ha_pages", json={"value": False})).status == 200
        assert not page.shown and store.state.panel["page"]["closed"]["by"] == "off"
        assert store.state.panel["pages"] is False
        assert (await (await client.get("/player/status")).json())["pages"] is False


# --- the amendment: one page kept loaded (K1-K8) ---------------------------

def _setup_preload(check=None, **values):
    store = StateStore({})
    settings = _Settings(**values)
    checked = []

    async def ok(url):
        checked.append(url)
        return {"url": url, "embeddable": True, "reason": None}

    page = Page(lambda state: store.set_panel(page=state),
                available=lambda: settings.values["ha_pages"] is True and settings.values["headless"] is not True)
    server = StateServer(store, settings=settings, page=page, page_check=check or ok, panel_token=TOKEN)
    return store, page, server, checked


@pytest.mark.asyncio
async def test_a_page_to_keep_is_checked_and_its_address_given_to_the_panel_only():
    store, page, server, checked = _setup_preload()
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/panel/page/preload", json={"url": URL})
        assert r.status == 200 and (await r.json())["preloaded"] is True and checked == [URL]
        assert store.state.panel["page"]["preloaded"] is True and URL not in repr(store.state.panel)
        anyone = await (await client.get("/panel/page")).json()
        panel = await (await client.get("/panel/page", headers={panel_token.HEADER: TOKEN})).json()
        assert "preload" not in anyone and anyone["preloaded"] is True
        assert panel["preload"] == {"url": URL, "n": 1} and "url" not in panel


@pytest.mark.asyncio
async def test_a_show_of_the_page_kept_is_not_checked_again():
    """K3: it shows at once - the check can take seconds."""
    _, page, server, checked = _setup_preload()
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/preload", json={"url": URL})
        assert (await client.post("/panel/page/show", json={"url": URL, "id": "door"})).status == 200
        assert page.shown and checked == [URL]
        await client.post("/panel/page/show", json={"url": URL + "/other"})
        assert checked == [URL, URL + "/other"]


@pytest.mark.asyncio
@pytest.mark.parametrize("values, status", [
    ({"ha_pages": False}, 403),
    ({"headless": True}, 409),
])
async def test_keeping_a_page_is_the_switchs_but_clearing_it_is_always_allowed(values, status):
    _, page, server, _ = _setup_preload(**values)
    page.set_preload(URL)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/panel/page/preload", json={"url": URL + "/x"})).status == status
        assert page.preload == URL
        r = await client.post("/panel/page/preload", json={"url": None})
        assert r.status == 200 and page.preload is None


@pytest.mark.asyncio
async def test_a_page_to_keep_that_cannot_be_framed_or_a_bad_call_is_refused():
    async def refuses(url):
        return {"url": url, "embeddable": False, "reason": "refuses framing"}

    _, page, server, _ = _setup_preload(check=refuses)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/panel/page/preload", json={"url": URL})
        assert r.status == 422 and "Send X-Frame-Options" in (await r.json())["error"]
        assert (await client.post("/panel/page/preload", json={})).status == 400
        assert (await client.post("/panel/page/preload", json={"url": "ftp://x"})).status == 400
        assert page.preload is None


@pytest.mark.asyncio
async def test_the_switch_turned_off_unloads_the_page_kept_and_on_loads_it_again():
    """K5: the address stays for when it is turned back on."""
    store, page, server, _ = _setup_preload()
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/panel/page/preload", json={"url": URL})
        await client.put("/settings/ha_pages", json={"value": False})
        assert store.state.panel["page"]["preloaded"] is False and page.preload == URL
        await client.put("/settings/ha_pages", json={"value": True})
        assert store.state.panel["page"]["preloaded"] is True
