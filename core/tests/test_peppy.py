"""Phase 5 criteria 6 and 8: who shows and hides the Peppy screen (ADR-0036)."""
from __future__ import annotations

import pytest

from gexis_core.model import TrackMetadata
from gexis_core.peppy import (
    PeppyController,
    PeppyScreen,
    UnattendedPlayback,
    is_forced_track_change,
)


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class FakeScreen:
    def __init__(self, visible=False):
        self.visible = visible
        self.calls = []

    def show(self):
        self.calls.append("show")
        self.visible = True
        return True

    def hide(self):
        self.calls.append("hide")
        self.visible = False
        return True


def playing(**kw):
    return TrackMetadata(transport="playing", **kw)


def test_the_timer_fires_after_five_minutes_of_unattended_playback():
    clock = FakeClock()
    timer = UnattendedPlayback(300, now=clock)
    timer.set_playing(True)

    clock.advance(299)
    assert not timer.due()
    clock.advance(2)
    assert timer.due()


def test_attention_restarts_it():
    clock = FakeClock()
    timer = UnattendedPlayback(300, now=clock)
    timer.set_playing(True)
    clock.advance(299)

    timer.attention()
    clock.advance(299)

    assert not timer.due()


def test_it_does_not_count_while_nothing_plays():
    clock = FakeClock()
    timer = UnattendedPlayback(300, now=clock)
    timer.set_playing(False)

    clock.advance(600)

    assert not timer.due()


def test_a_volume_change_is_not_attention():
    """ADR-0036, George: volume is the one thing people adjust without
    looking at the screen. The controller is never told about it."""
    clock = FakeClock()
    screen = FakeScreen()
    controller = PeppyController(screen, UnattendedPlayback(300, now=clock))
    controller.on_metadata(playing(title="A", position=10.0, duration=200.0))

    clock.advance(301)

    assert controller._timer.due()


def test_a_renderer_change_exits_to_now_playing():
    """Criterion 6."""
    screen = FakeScreen(visible=True)
    controller = PeppyController(screen, UnattendedPlayback(300))

    controller.on_active_change("spotify")

    assert screen.calls == ["hide"] and not screen.visible


def test_a_renderer_change_while_hidden_changes_nothing():
    screen = FakeScreen(visible=False)
    controller = PeppyController(screen, UnattendedPlayback(300))

    controller.on_active_change("spotify")

    assert screen.calls == []


def test_a_renderer_change_restarts_the_timer_so_the_screen_comes_back():
    clock = FakeClock()
    screen = FakeScreen(visible=True)
    controller = PeppyController(screen, UnattendedPlayback(300, now=clock))
    controller.on_metadata(playing(title="A", position=1.0, duration=200.0))

    clock.advance(299)
    controller.on_active_change("spotify")
    clock.advance(299)
    assert not controller._timer.due()

    clock.advance(2)
    assert controller._timer.due()


def test_touch_hides_it_and_restarts_the_timer():
    clock = FakeClock()
    screen = FakeScreen(visible=True)
    controller = PeppyController(screen, UnattendedPlayback(300, now=clock))
    controller.on_metadata(playing(title="A", position=1.0, duration=200.0))
    clock.advance(299)

    controller.on_touch()

    assert screen.calls == ["hide"]
    clock.advance(299)
    assert not controller._timer.due()


@pytest.mark.parametrize(
    ("position", "duration", "forced"),
    [
        (100.0, 200.0, True),      # skipped mid-track
        (198.0, 200.0, False),     # ran to the end
        (200.0, 200.0, False),
        (None, 200.0, False),      # Bluetooth publishes no position
        (100.0, None, False),
    ],
)
def test_forced_versus_natural_track_change(position, duration, forced):
    assert is_forced_track_change(position, duration) is forced


def test_a_forced_track_change_is_attention_but_a_natural_one_is_not():
    clock = FakeClock()
    controller = PeppyController(FakeScreen(), UnattendedPlayback(300, now=clock))
    controller.on_metadata(playing(title="A", position=10.0, duration=200.0))

    clock.advance(200)
    controller.on_metadata(playing(title="B", position=0.0, duration=200.0))  # skipped at 10s
    clock.advance(200)
    assert not controller._timer.due()

    # now let B run to its end, which is not attention
    controller.on_metadata(playing(title="B", position=197.0, duration=200.0))
    clock.advance(101)
    controller.on_metadata(playing(title="C", position=0.0, duration=200.0))
    assert controller._timer.due()


def test_missing_wlrctl_is_not_fatal():
    screen = PeppyScreen(wlrctl="/nonexistent/wlrctl")
    assert screen.show() is False
    assert screen.visible is False


async def test_the_routes(tmp_path):
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    screen = FakeScreen(visible=True)
    controller = PeppyController(screen, UnattendedPlayback(300))
    server = StateServer(StateStore({}), peppy=controller)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/touch")).status == 200
        assert screen.calls == ["hide"]
        assert (await client.post("/peppy/show")).status == 200
        assert screen.visible
        assert (await client.post("/peppy/hide")).status == 200
        assert (await client.post("/peppy/sideways")).status == 404


async def test_the_routes_answer_503_when_not_wired():
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    server = StateServer(StateStore({}))
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/peppy/show")).status == 503
        assert (await client.post("/touch")).status == 200  # harmless, nothing to tell
