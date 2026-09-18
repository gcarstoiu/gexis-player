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
        (None, 200.0, False),      # a renderer that publishes no position
        (100.0, None, False),
    ],
)
def test_forced_versus_natural_track_change(position, duration, forced):
    assert is_forced_track_change(position, duration) is forced


def test_a_forced_track_change_is_attention_but_a_natural_one_is_not():
    clock = FakeClock()
    controller = PeppyController(FakeScreen(), UnattendedPlayback(300, now=clock))
    controller.on_metadata(playing(title="A", position=10.0, duration=200.0))

    clock.advance(20)
    controller.on_metadata(playing(title="B", position=0.0, duration=200.0))  # skipped at 30s
    clock.advance(200)
    assert not controller._timer.due()

    # B ran to its end (200 s since it started), which is not attention
    controller.on_metadata(playing(title="C", position=0.0, duration=200.0))
    clock.advance(101)
    assert controller._timer.due()


def test_a_natural_end_is_natural_when_the_renderer_reported_no_position_since_the_start():
    """Spotify's shape: position 0.0 at the start of a track and nothing more.
    Every track shorter than the timeout used to reset it."""
    clock = FakeClock()
    controller = PeppyController(FakeScreen(), UnattendedPlayback(300, now=clock))
    for title in ("A", "B", "C"):
        controller.on_metadata(playing(title=title, position=0.0, duration=240.0))
        clock.advance(120)
        controller.on_metadata(playing(title=title, position=0.0, duration=240.0))  # a volume broadcast
        clock.advance(120)
    controller.on_metadata(playing(title="D", position=0.0, duration=240.0))
    assert controller._timer.due()


def test_paused_time_does_not_count_towards_the_track_position():
    clock = FakeClock()
    controller = PeppyController(FakeScreen(), UnattendedPlayback(300, now=clock))
    controller.on_metadata(playing(title="A", position=0.0, duration=200.0))
    clock.advance(50)
    controller.on_metadata(TrackMetadata(title="A", position=0.0, duration=200.0, transport="paused"))
    clock.advance(500)
    controller.on_metadata(playing(title="A", position=0.0, duration=200.0))
    clock.advance(50)
    controller.on_metadata(playing(title="B", position=0.0, duration=200.0))  # 100 s in: a skip
    clock.advance(299)
    assert not controller._timer.due()


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


def test_the_screen_passes_the_compositor_socket_to_wlrctl(monkeypatch):
    """The daemon runs as root with no session: without these, wlrctl exits
    with "XDG_RUNTIME_DIR is invalid or not set" (found on hardware)."""
    seen = {}

    def fake_run(args, **kwargs):
        seen["env"] = kwargs["env"]
        seen["args"] = args

        class Result:
            returncode = 0
            stderr = b""

        return Result()

    monkeypatch.setattr("gexis_core.peppy.subprocess.run", fake_run)
    screen = PeppyScreen(wlrctl="/usr/bin/wlrctl", runtime_dir="/run/user/1000", wayland_display="wayland-0")

    assert screen.show() is True
    assert seen["env"]["XDG_RUNTIME_DIR"] == "/run/user/1000"
    assert seen["env"]["WAYLAND_DISPLAY"] == "wayland-0"
    assert seen["args"][:3] == ["/usr/bin/wlrctl", "toplevel", "focus"]


def test_a_long_pause_gives_no_credit_on_resume():
    clock = FakeClock()
    timer = UnattendedPlayback(300, now=clock)
    timer.set_playing(True)
    clock.advance(100)
    timer.set_playing(False)
    clock.advance(1000)
    timer.set_playing(True)
    clock.advance(299)
    assert not timer.due()
    clock.advance(1)
    assert timer.due()


def test_spotifys_stop_between_two_tracks_is_neither_a_skip_nor_a_restart():
    """The exact sequence go-librespot sent at a natural track end, recorded
    on the device 2026-09-16: "stopped" with position 0 on the old track, then
    the new track, then "playing" - all within 10 ms."""
    clock = FakeClock()
    controller = PeppyController(FakeScreen(), UnattendedPlayback(300, now=clock))
    controller.on_metadata(playing(title="Spider Silk", position=0.0, duration=386.267))
    clock.advance(200)
    controller.on_metadata(playing(title="Spider Silk", position=200.0, duration=386.267))
    clock.advance(186.2)
    controller.on_metadata(TrackMetadata(title="Spider Silk", position=0.002, duration=386.267, transport="stopped"))
    controller.on_metadata(TrackMetadata(title="The Poet", position=0.0, duration=300.0, transport="stopped"))
    clock.advance(0.01)
    controller.on_metadata(playing(title="The Poet", position=0.011, duration=300.0))
    clock.advance(113.8)  # 386.2 + 0.01 + 113.8 = five minutes of music
    assert controller._timer.due()


def test_a_short_stop_is_not_counted_and_not_reset():
    clock = FakeClock()
    timer = UnattendedPlayback(300, now=clock)
    timer.set_playing(True)
    clock.advance(200)
    timer.set_playing(False)
    clock.advance(5)
    timer.set_playing(True)
    clock.advance(99)
    assert not timer.due()
    clock.advance(1)
    assert timer.due()


@pytest.mark.asyncio
async def test_the_screen_is_minimised_at_startup_so_a_touch_can_dismiss_it():
    """**The defect this test exists for.** Whether the meter is up is held
    in memory, so a daemon started while it is on screen believed it was
    hidden - and `on_touch` only hides what it thinks is visible. George,
    2026-09-18: the meter could not be dismissed by touch at all after the
    daemon restarted under it, and the panel was unreachable behind it.
    Reconciling once at startup is what makes the two agree."""
    import asyncio

    screen = FakeScreen(visible=False)
    controller = PeppyController(screen, UnattendedPlayback(300), tick_s=0.01)

    task = asyncio.ensure_future(controller.run())
    await asyncio.sleep(0)
    task.cancel()

    assert screen.calls == ["hide"]
