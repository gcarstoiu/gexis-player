# SPDX-License-Identifier: GPL-3.0-or-later
"""Volume bridge (criterion 5).

The hardware mixer is the single source of truth (ADR-0018: "one global
control shared by all renderers"). This keeps go-librespot's own volume in
sync with it. Reads and writes go through `amixer -D output ...` - the
same "output" ctl indirection squeezelite-mixer-check.sh uses, not a
direct `hw:sndrpihifiberry` reference (ADR-0009).

**Subscribed, not polled** (ADR-0018): `alsactl monitor` is spawned once
and read as a line stream, rather than periodically re-reading `amixer`.

**Scope, matching ADR-0018's own "Unverified" section:** the
hardware -> Spotify direction is implemented with confidence (amixer plus
go-librespot's documented POST /player/volume). The reverse direction
(Spotify -> hardware) depends on the "volume" WS event's undocumented
payload shape (adapters/spotify.py) and is best-effort. No bluez-alsa
AVRCP bridging is implemented - ADR-0018 leaves whether that's even
possible as an open question, not something to guess an implementation
for here.

**Echo suppression, amended 2026-09-06 after a real ratchet-to-zero was
measured on hardware.** Two scales (240 hardware steps, go-librespot's
own `volume_steps`, 100 on the tested build) cannot round-trip exactly,
and there are two feedback paths, not one: our own `set_raw` write shows
up on `alsactl monitor` as a change to sync outward again, *and*
go-librespot can echo our `POST /player/volume` back as its own
`"volume"` WS event, which this bridge would otherwise treat as a fresh
external change. A single boolean "skip exactly one incoming line" flag
(the previous approach) does not cover either case reliably: a single
mixer write can produce more than one `alsactl monitor` line (only the
first got skipped, the rest leaked through as "new" changes), and it did
nothing at all for the WS-echo path. Measured consequence, one real
sequence: 179, 172, 162, 140, 119, 97, 0/240, each hop ~50ms apart, one
direction, never stopping until it hit zero.

Replaced with a single shared timestamp, `_last_own_write`: anything
*we* write - either direction - arms a short window, and any incoming
signal (an `alsactl monitor` line, or a `"volume"` WS event) arriving
inside that window is treated as our own echo and dropped, however many
lines or events it produced. This is a mitigation, not a proof of
convergence: two independent *genuine* changes landing inside the same
window (a live slider drag against a near-simultaneous LMS change, say)
would have the second one dropped too. Not observed, but not excluded
either - the measured 325ms bridge round-trip (single deliberate
`amixer` change, logged separately) is the basis for the window below,
not a formal bound.

**Per-renderer memory, added 2026-09-07** (George's decision, after the
cross-renderer volume jumps this bridge alone couldn't fix): every
genuine hardware change is attributed to whichever renderer currently
holds the device (`get_active_renderer`) and fed to
`renderer_volume.RendererVolumeMemory`, which `arbitration.Supervisor`
reads from on the *next* acquire to restore that renderer's own level.
This module only records; it does not itself decide when to restore -
that's the supervisor's job, on takeover, not this bridge's.

A Spotify volume report while Spotify is *not* currently active is
still remembered (for whenever it next becomes active) but not applied
to the live mixer, which some other renderer currently owns - writing
it anyway would move that renderer's volume out from under it.

**Dummy mixer controls for LMS and Bluetooth, added 2026-09-08 (B2,
George's decision).** Spotify's volume is naturally isolated already -
go-librespot keeps its own software volume state and only *we* ever
write it to hardware. squeezelite (`-V DAC`) and bluealsa-aplay
(`--mixer-name=DAC`) have no equivalent: both write straight to the
shared hardware mixer whenever their own upstream (LMS's app, the
phone's AVRCP slider) tells them to, regardless of which renderer is
actually allowed to be heard - confirmed on hardware, 2026-09-08,
raising LMS's volume from the app audibly changed an active Bluetooth
stream's loudness.

Fixed by giving each of them a private control that isn't wired to any
audio path at all (a `snd-dummy` card per renderer - see the modprobe
config installed by image/stage-gexis/00-alsa) - `squeezelite -O
hw:gexislmsvol -V Master` and `bluealsa-aplay --mixer-device=hw:
gexisbtvol --mixer-name=Master`. Writing to a dummy control changes
nothing anyone can hear, by construction. `DummyMixerBridge` (below) is
the only thing that ever copies a dummy control's value onto the real
DAC, and only while that control's renderer is the currently active
one - the same "mirror when active, remember otherwise" shape
`_on_spotify_volume` already uses, generalised to two more renderers
instead of Spotify's own software state.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

from gexis_core import alsa

logger = logging.getLogger("gexis_core.volume")

# Covers the measured ~325ms round-trip (a single amixer change, through
# go-librespot and back) plus margin for a multi-line alsactl monitor
# burst from one write. Not a formal bound - see module docstring.
ECHO_WINDOW_S = 0.75

MIXER_DEVICE = "output"
HARDWARE_MAX = 240  # ADR-0018: 240 steps, 0=mute, 240=0dB
DB_MIN = -120.0  # raw 0
DB_STEP = 0.5  # dB per raw step (ADR-0018, confirmed against amixer's own dBscale readout)
# The real DAC's control ("Front Left: Playback 216 [90%]...") and a
# snd-dummy control's ("Front Left: 30 [53%]... Capture [off]") format
# this differently - amixer only prints "Playback" when a control has
# distinct playback/capture volumes; the dummy's Master reports as a
# single shared value with no such prefix. Found on hardware, 2026-09-08,
# when DummyMixerBridge's get_raw() against a dummy control silently
# returned None (the old Playback-only pattern never matched). Both
# forms share "Front Left: <n> [", with or without "Playback" in between.
_VALUE_RE = re.compile(rb"Front Left: (?:Playback )?(\d+) \[")

# snd-dummy's own scale (mixer_volume_level_min/max module params, left
# at their defaults) - measured on hardware, 2026-09-08, from a fresh
# `amixer -D hw:<dummy> sget Master`: raw -50..100, dBscale-min -45.00dB,
# step 0.30dB. Confirmed against the formula below (raw=0 -> -30.00dB,
# raw=59 -> -12.30dB, both matched a live reading exactly).
DUMMY_MIN_RAW = -50
DUMMY_MAX_RAW = 100
DUMMY_DB_MIN = -45.0
DUMMY_DB_STEP = 0.30
DUMMY_CARD_LMS = "gexislmsvol"
DUMMY_CARD_BLUETOOTH = "gexisbtvol"
DUMMY_CONTROL = "Master"


def dummy_raw_to_db(raw: int) -> float:
    return DUMMY_DB_MIN + (raw - DUMMY_MIN_RAW) * DUMMY_DB_STEP


def dummy_raw_to_hardware_raw(raw: int) -> int:
    """Map a dummy control's raw value onto the real DAC's raw scale.

    By *fractional position within each control's own dB range*, not a
    flat raw-to-raw ratio or a flat dB offset - raw steps are dB-linear
    on both controls but the two ranges differ (dummy: -45..0dB over
    150 steps; DAC: -120..0dB over 240 steps, ADR-0018), so a 1:1 dB
    copy would mean the dummy's quietest setting (-45dB) never reaches
    the DAC's true mute. Position-preserving keeps "all the way down"
    meaning the same thing on both.
    """
    db = dummy_raw_to_db(raw)
    frac = (db - DUMMY_DB_MIN) / (0.0 - DUMMY_DB_MIN)
    hardware_db = DB_MIN + frac * (0.0 - DB_MIN)
    return db_to_raw(hardware_db)


def raw_to_db(raw: int) -> float:
    """Raw ALSA step (0-240) to dB, per ADR-0018's documented scale.

    Found necessary on hardware, 2026-09-08: reasoning about this
    control in raw-step percentages is actively misleading - it's
    dB-linear per step, not perceptually linear, so e.g. 230/240 (96%)
    is -5dB but 60/240 (25%) is -90dB, nowhere near "a quarter as
    loud." Convert to dB before doing anything that should track
    perceived loudness - clamping a restore floor, comparing renderers'
    levels, anything like that.
    """
    return DB_MIN + raw * DB_STEP


def db_to_raw(db: float) -> int:
    raw = round((db - DB_MIN) / DB_STEP)
    return max(0, min(HARDWARE_MAX, raw))


async def get_raw(mixer_name: str, device: str = MIXER_DEVICE) -> int | None:
    """`device` defaults to the real hardware mixer ("output"); pass
    "hw:<dummy card id>" to read one of the per-renderer dummy controls
    instead (DummyMixerBridge, below) - same amixer call either way, a
    dummy control is a perfectly ordinary ALSA simple-mixer element."""
    proc = await asyncio.create_subprocess_exec(
        "amixer",
        "-D",
        device,
        "sget",
        mixer_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    m = _VALUE_RE.search(out)
    return int(m.group(1)) if m else None


async def set_raw(mixer_name: str, value: int) -> None:
    value = max(0, min(HARDWARE_MAX, value))
    proc = await asyncio.create_subprocess_exec(
        "amixer",
        "-D",
        MIXER_DEVICE,
        "sset",
        mixer_name,
        f"{value}",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()


class VolumeBridge:
    """Bridges the hardware mixer with go-librespot's own volume, and
    feeds every genuine hardware change to `volume_memory` (renderer_
    volume.py) so it can be restored the next time that renderer becomes
    active - George's decision, 2026-09-07.

    `get_active_renderer` is a zero-arg callable (typically
    `lambda: supervisor.active`) - who a hardware change gets attributed
    to, and whether an incoming Spotify volume report should actually
    touch the live mixer, both depend on who currently owns the device.
    Reporting into `volume_memory` while a renderer is *not* active is
    still correct (e.g. go-librespot firing a stale event) - it updates
    what will be restored later without touching the mixer someone else
    currently owns.
    """

    def __init__(self, mixer_name: str, spotify_adapter, *, volume_memory, get_active_renderer) -> None:
        self._mixer_name = mixer_name
        self._spotify = spotify_adapter
        self._volume_memory = volume_memory
        self._get_active_renderer = get_active_renderer
        self._last_own_write = 0.0
        spotify_adapter.on_volume_change(self._on_spotify_volume)

    def _within_echo_window(self) -> bool:
        return time.monotonic() - self._last_own_write < ECHO_WINDOW_S

    def _on_spotify_volume(self, value: int, max_: int) -> None:
        if max_ <= 0:
            logger.warning("volume: spotify reported max=%r, ignoring", max_)
            return
        if self._within_echo_window():
            logger.debug("volume: ignoring spotify volume event within echo window")
            return
        raw = round(value / max_ * HARDWARE_MAX)
        self._volume_memory.remember("spotify", raw)
        if self._get_active_renderer() != "spotify":
            # Remembered for next time, but spotify doesn't currently
            # own the mixer - writing now would move someone else's
            # volume out from under them.
            logger.debug(
                "volume: spotify reported %s/240 while inactive, remembered but not applied",
                raw,
            )
            return
        logger.info("volume: spotify -> hardware (%s/%s -> %s/240)", value, max_, raw)
        self._last_own_write = time.monotonic()
        asyncio.create_task(set_raw(self._mixer_name, raw))

    async def run(self) -> None:
        """Watch `alsactl monitor` and push hardware changes to Spotify.

        Scoped to the real card (`alsa.CARD_ID`), not every card - added
        2026-09-08 alongside `DummyMixerBridge`. Before the dummy
        controls existed, an unscoped `alsactl monitor` only ever saw
        changes on this one card anyway; now that squeezelite and
        bluealsa-aplay each have their own `snd-dummy` card, an unscoped
        monitor would double-process their changes here as well as in
        their own DummyMixerBridge instances.
        """
        proc = await asyncio.create_subprocess_exec(
            "alsactl",
            "monitor",
            f"hw:{alsa.CARD_ID}",
            stdout=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        last_raw: int | None = None
        while True:
            line = await proc.stdout.readline()
            if not line:
                logger.warning("volume: alsactl monitor exited, restarting in 5s")
                await asyncio.sleep(5)
                return await self.run()
            if self._within_echo_window():
                # Our own set_raw write, possibly reported as more than
                # one line for a single change - every line inside the
                # window is our own echo, not just the first.
                continue
            raw = await get_raw(self._mixer_name)
            if raw is None or raw == last_raw:
                continue
            last_raw = raw
            active = self._get_active_renderer()
            self._volume_memory.remember(active, raw)
            if active != "spotify":
                continue
            steps = await self._spotify.get_volume_steps()
            logger.info("volume: hardware -> spotify (%s/240)", raw)
            self._last_own_write = time.monotonic()
            await self._spotify.set_volume(round(raw / HARDWARE_MAX * steps))


class DummyMixerBridge:
    """Mirrors one renderer's private dummy mixer control onto the real
    hardware DAC, only while that renderer is active (B2, George's
    decision 2026-09-08 - see this module's docstring).

    One instance per dummy-backed renderer (LMS, Bluetooth - Spotify
    doesn't need one, `VolumeBridge` already isolates it via
    go-librespot's own software volume). `hardware_control` is the real
    DAC's control name ("DAC"); `dummy_card`/`dummy_control` identify the
    renderer's own snd-dummy control ("gexislmsvol"/"Master", say).
    """

    def __init__(
        self,
        renderer_id: str,
        dummy_card: str,
        dummy_control: str,
        hardware_control: str,
        *,
        volume_memory,
        get_active_renderer,
    ) -> None:
        self._renderer_id = renderer_id
        self._dummy_card = dummy_card
        self._dummy_control = dummy_control
        self._hardware_control = hardware_control
        self._volume_memory = volume_memory
        self._get_active_renderer = get_active_renderer
        self._last_own_write = 0.0

    def _within_echo_window(self) -> bool:
        return time.monotonic() - self._last_own_write < ECHO_WINDOW_S

    async def run(self) -> None:
        proc = await asyncio.create_subprocess_exec(
            "alsactl",
            "monitor",
            f"hw:{self._dummy_card}",
            stdout=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        last_raw: int | None = None
        while True:
            line = await proc.stdout.readline()
            if not line:
                logger.warning(
                    "volume: alsactl monitor(%s) exited, restarting in 5s", self._dummy_card
                )
                await asyncio.sleep(5)
                return await self.run()
            if self._within_echo_window():
                # Our own mirroring write lands back on the *hardware*
                # control, not this dummy one, so this only ever guards
                # against a burst of monitor lines from one dummy change
                # - same reasoning as VolumeBridge's echo window, applied
                # to the source side instead of the destination side.
                continue
            raw = await get_raw(self._dummy_control, device=f"hw:{self._dummy_card}")
            if raw is None or raw == last_raw:
                continue
            last_raw = raw
            hardware_raw = dummy_raw_to_hardware_raw(raw)
            # remember() no-ops for renderers outside MANAGED_RENDERERS
            # (renderer_volume.py) - currently just Bluetooth, per Finding
            # 006. Calling it unconditionally keeps this class the same
            # for both renderers rather than needing a persist flag.
            self._volume_memory.remember(self._renderer_id, hardware_raw)
            if self._get_active_renderer() != self._renderer_id:
                logger.debug(
                    "volume: %s's dummy control changed to %s while inactive, "
                    "remembered but not applied",
                    self._renderer_id,
                    raw,
                )
                continue
            logger.info(
                "volume: %s -> hardware (dummy %s -> %s/240)",
                self._renderer_id,
                raw,
                hardware_raw,
            )
            self._last_own_write = time.monotonic()
            await set_raw(self._hardware_control, hardware_raw)
