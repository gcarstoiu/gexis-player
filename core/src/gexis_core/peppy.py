# SPDX-License-Identifier: GPL-3.0-or-later
"""Who shows and hides the Peppy screen (Phase 5 criteria 6 and 8).

The daemon owns the policy because it is the only part that knows when a
renderer changes; labwc does the work, through `wlrctl` over
`wlr-foreign-toplevel-management` (ADR-0026, measured in Finding 025). The
meter process itself is never started or stopped for this — it keeps
rendering while hidden, which is what makes entry instant.

Rules, from [ADR-0036](../../../docs/decisions/0036-peppy-entry-and-no-rate-or-codec.md):

- **Attention** is a touch on the panel, a forced track change, or a renderer
  change. A volume change is not, from anywhere.
- **Five minutes of unattended playback** raises the screen.
- A renderer change lowers it (criterion 6), and the same timer brings it
  back afterwards.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time

logger = logging.getLogger("gexis_core.peppy")

#: SDL's default window title for a pygame window. Matched rather than an
#: app_id because that is what the toplevel actually advertises.
WINDOW_TITLE = "pygame window"
#: A track change is "forced" when the previous track ended this far short of
#: its duration - our own commands are detectable, a phone's skip is not
#: (ADR-0036's open question, resolved this way by George).
FORCED_TRACK_MARGIN_S = 5.0
#: A stop shorter than this keeps the unattended-playback count (see
#: `UnattendedPlayback.set_playing`).
STOP_GRACE_S = 10.0
#: The panel session's compositor socket. The kiosk runs as uid 1000.
DEFAULT_RUNTIME_DIR = "/run/user/1000"
DEFAULT_WAYLAND_DISPLAY = "wayland-0"


class PeppyScreen:
    """Show and hide, with `wlrctl`. Absent tooling is not fatal: a device
    without the meter process running is a device that shows now playing."""

    def __init__(
        self,
        *,
        title: str = WINDOW_TITLE,
        wlrctl: str | None = None,
        runtime_dir: str = DEFAULT_RUNTIME_DIR,
        wayland_display: str = DEFAULT_WAYLAND_DISPLAY,
    ) -> None:
        self._title = title
        self._wlrctl = wlrctl or shutil.which("wlrctl")
        # The daemon runs as root with no session of its own, so it must be
        # told where the compositor's socket is. Found on hardware: without
        # these, wlrctl exits with "XDG_RUNTIME_DIR is invalid or not set".
        # Root can open the panel user's socket; the ownership is not a
        # barrier, the missing environment was.
        self._env = {
            **os.environ,
            "XDG_RUNTIME_DIR": runtime_dir,
            "WAYLAND_DISPLAY": wayland_display,
        }
        self.visible = False
        if self._wlrctl is None:
            logger.warning("peppy: wlrctl not found; the Peppy screen cannot be raised")

    def _run(self, action: str) -> bool:
        if self._wlrctl is None:
            return False
        try:
            result = subprocess.run(
                [self._wlrctl, "toplevel", action, f"title:{self._title}"],
                capture_output=True,
                timeout=5,
                check=False,
                env=self._env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("peppy: %s failed: %s", action, exc)
            return False
        if result.returncode != 0:
            logger.info("peppy: %s found no window (%s)", action, result.stderr.decode().strip())
            return False
        return True

    def show(self) -> bool:
        if self._run("focus"):
            self.visible = True
            logger.info("peppy: shown")
            return True
        return False

    def hide(self) -> bool:
        if self._run("minimize"):
            self.visible = False
            logger.info("peppy: hidden")
            return True
        return False


class UnattendedPlayback:
    """The timer ADR-0036 defines. Counts while music plays and nobody has
    touched anything; any attention restarts it.

    Not ADR-0033's idle timer, which counts while *nothing* plays. A device
    playing music reaches the Peppy screen, never the idle screen.
    """

    def __init__(self, timeout_s: float = 300.0, *, now=time.monotonic) -> None:
        self.timeout_s = timeout_s
        self._now = now
        self._playing = False
        self._last_attention = now()
        #: When playback last stopped or paused; None before it ever played.
        self._stopped_at: float | None = None

    def attention(self) -> None:
        self._last_attention = self._now()

    def set_playing(self, playing: bool) -> None:
        """Starting or stopping playback is not attention, and silence earns
        no credit towards entry. A gap of up to STOP_GRACE_S is not counted
        but does not reset either: Spotify reports "stopped" for a few
        milliseconds between two tracks (measured 2026-09-16), and resetting
        there meant the screen never came up. A longer stop starts over."""
        if playing == self._playing:
            return
        self._playing = playing
        now = self._now()
        if not playing:
            self._stopped_at = now
            return
        gap = None if self._stopped_at is None else now - self._stopped_at
        if gap is None or gap > STOP_GRACE_S:
            self.attention()
        else:
            self._last_attention += gap

    def due(self) -> bool:
        return self._playing and (self._now() - self._last_attention) >= self.timeout_s


def is_forced_track_change(previous_position: float | None, previous_duration: float | None) -> bool:
    """Did somebody skip, or did the track simply end?

    The daemon sees *that* the track changed, never who caused it: a skip from
    a phone app looks identical to a natural end. ADR-0036 settles it by where
    the previous track stopped. A renderer that publishes no position has
    every track change read as natural. (Bluetooth was assumed to be one;
    Finding 028 found George's phone does publish it.)
    """
    if previous_position is None or previous_duration is None:
        return False
    return previous_position < previous_duration - FORCED_TRACK_MARGIN_S


class PeppyController:
    """Wires the rules to the screen. Held by `__main__`, fed by the state
    store's own callbacks so nothing here polls playback."""

    def __init__(self, screen: PeppyScreen, timer: UnattendedPlayback, *, tick_s: float = 5.0) -> None:
        self._screen = screen
        self._timer = timer
        self._tick_s = tick_s
        self._track: tuple | None = None
        self._now = timer._now
        # (position, duration, playing, when): the last position a renderer
        # *reported*, advanced by time while playing. Spotify reports position
        # only on events, so the last broadcast before a natural end still
        # says 0.0; read raw, every track end looked like a skip and the
        # screen never came up (found on hardware, 2026-09-16). The UI's
        # progress bar interpolates the same way.
        self._anchor: tuple[float | None, float | None, bool, float] = (None, None, False, 0.0)

    def on_active_change(self, renderer_id: str | None) -> None:
        """Criterion 6: a renderer change exits to now playing. The timer then
        runs normally and brings the screen back."""
        self._timer.attention()
        if self._screen.visible:
            logger.info("peppy: renderer changed to %s, exiting to now playing", renderer_id or "nobody")
            self._screen.hide()

    def on_touch(self) -> None:
        self._timer.attention()
        if self._screen.visible:
            self._screen.hide()

    def _position_now(self) -> float | None:
        position, _, playing, at = self._anchor
        if position is None:
            return None
        return position + (self._now() - at if playing else 0.0)

    def on_metadata(self, metadata) -> None:
        track = (metadata.title, metadata.artist, metadata.album)
        playing = metadata.transport == "playing"
        changed = self._track is not None and track != self._track
        if changed and is_forced_track_change(self._position_now(), self._anchor[1]):
            logger.info("peppy: forced track change counts as attention")
            self._timer.attention()
        self._track = track
        self._timer.set_playing(playing)
        # Re-anchor only on news: every broadcast repeats the last position,
        # volume-only ones included, and re-anchoring on those would stop the
        # clock. A transport change without a new position keeps what had
        # elapsed.
        # A "stopped" report's position is not a place in the track: Spotify
        # sends 0.0 between two tracks, which made every natural end look
        # like a skip (measured 2026-09-16). Only the clock stops there.
        position, duration, was_playing, _ = self._anchor
        stopped = metadata.transport == "stopped"
        if changed or (not stopped and (metadata.position != position or metadata.duration != duration)):
            self._anchor = (metadata.position, metadata.duration, playing, self._now())
        elif playing != was_playing:
            self._anchor = (self._position_now(), duration, playing, self._now())

    def request(self, action: str) -> bool:
        """The UI's own button (criterion 8) and anything else that asks."""
        self._timer.attention()
        return self._screen.show() if action == "show" else self._screen.hide()

    async def run(self) -> None:
        # Whether the meter is up is held in memory, so a daemon that starts
        # while it is on screen believes it is not - and then ignores every
        # touch, because `on_touch` only hides what it thinks is visible.
        # That strands the panel behind the meter with no way back
        # (George, 2026-09-18, after a restart mid-session; systemd would do
        # the same on its own after a crash). Minimising once at startup
        # makes the two agree: the device comes up on now playing, and the
        # timer raises the meter again in its own time.
        self._screen.hide()
        while True:
            await asyncio.sleep(self._tick_s)
            if self._timer.due() and not self._screen.visible:
                self._screen.show()
