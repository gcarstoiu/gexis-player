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
*we* write - either direction - armed a short window, and any incoming
signal (an `alsactl monitor` line, or a `"volume"` WS event) arriving
inside that window was treated as our own echo and dropped, however many
lines or events it produced.

**That blanket time window was itself found wrong on hardware,
2026-09-11 (blocker 4).** Its own docstring already named the risk -
"two independent *genuine* changes landing inside the same window would
have the second one dropped too" - and that is exactly what a real
Spotify slider drag is: a rapid burst of genuine, *different* values.
The first one through armed the window and every later one, including
the value the user actually let go on, was discarded. Measured
directly: a fast ramp to 100/100 left the real DAC at 226/240, 7.0dB
below the selected level, reproducibly, while the identical ramp spaced
1.5s apart reached 240/240. Since Bluetooth and LMS lost their own echo
windows when `DummyMixerBridge` was fixed (see its docstring - same bug,
found there first), Spotify was left as the only renderer that could not
reach full scale from its own slider, which is what George reported as
"the highest volume for Bluetooth is higher than the highest volume with
Spotify."

Replaced with **value-matched echo suppression**: we record the exact
value we ourselves wrote in each direction (`_expected_hw_raw`,
`_expected_spotify_value`) and drop exactly one incoming signal carrying
*that same value*. An echo, by definition, carries back what we just
wrote; a genuine change carries something different and is never
dropped, however fast it arrives. The recorded expectation still expires
after `ECHO_WINDOW_S` so an echo that never arrives (dropped WS frame,
a value that rounded differently on the way back) cannot suppress a
later genuine change that happens to carry the same number.

This converges rather than ratchets, which the old flag could not
promise: the two scales are stable inverses to within a step (raw 226 ->
84/100 -> raw 226, checked against the live control), so a round trip
either matches the expectation and stops, or lands one step away and
stops on the next hop - it cannot walk downward indefinitely the way the
original measured ratchet (179, 172, 162, 140, 119, 97, 0) did.

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
import concurrent.futures
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
#
# `-?` on the value group: found on hardware, 2026-09-08, the *second*
# time - the dummy control's own range is -50..100 (unlike the DAC's
# 0..240), and `\d+` alone silently dropped the sign on every negative
# reading ("-50" parsed as 50), producing wrong mirrored values and
# erratic missed-update behaviour (a wrongly-sign-stripped reading could
# coincidentally equal a later or earlier *real* positive reading and
# get deduped against it) for roughly the bottom third of LMS/Bluetooth's
# own volume range. Silent, not a parse failure - `re.search` still
# matched, just the wrong number - so nothing short of comparing against
# a live reading would have caught it.
_VALUE_RE = re.compile(rb"Front Left: (?:Playback )?(-?\d+) \[")

# snd-dummy's own scale (mixer_volume_level_min/max module params, left
# at their defaults) - measured on hardware, 2026-09-08, from a fresh
# `amixer -D hw:<dummy> sget Master`: raw -50..100, dBscale-min -45.00dB,
# step 0.30dB. Confirmed against the formula below (raw=0 -> -30.00dB,
# raw=59 -> -12.30dB, both matched a live reading exactly).
# **0..127 since 2026-09-22**, so AVRCP's 128 steps round-trip through this
# control exactly (see the modprobe config for the ratchet this ends).
# snd-dummy's dB scale is fixed - -45 dB at the control's minimum, 0.30 dB
# a step - so the declared range is now -45.00..-6.90 dB, measured on the
# device. **The 6.9 dB is taken back here**, as a constant shift rather than
# a rescale: every step stays 0.30 dB and the curve keeps its shape, which
# is what the 2026-09-08 rejection of fractional rescaling was about. The
# window a renderer's own slider spans becomes -38.1..0 dB.
DUMMY_MIN_RAW = 0
DUMMY_MAX_RAW = 127
DUMMY_DB_MIN = -38.1
DUMMY_DB_STEP = 0.30
DUMMY_CARD_LMS = "gexislmsvol"
DUMMY_CARD_BLUETOOTH = "gexisbtvol"
DUMMY_CONTROL = "Master"


def dummy_raw_to_db(raw: int) -> float:
    return DUMMY_DB_MIN + (raw - DUMMY_MIN_RAW) * DUMMY_DB_STEP


def dummy_raw_to_hardware_raw(raw: int) -> int:
    """Map a dummy control's raw value onto the real DAC's raw scale.

    A direct dB copy (dummy's dB value applied unchanged to the DAC,
    clamped to its range) - **not** fractional-position rescaling, which
    is what this function did until found wrong on hardware, 2026-09-08:
    George reported LMS silent below ~75%. Measured directly (set LMS to
    0/25/50/75/100% via LMS's own RPC, read the resulting dummy raw):
    squeezelite computes its percent-to-dB curve *from the target
    control's own declared TLV range* - 0% lands exactly on the dummy's
    floor (-45dB) and 100% on its ceiling (0dB) - not from some fixed
    internal assumption. Against the real DAC directly (pre-B2, -120dB
    span) the identical logic would have made squeezelite's own curve
    spread across the full 120dB, putting 75% at -30dB and 50% at -60dB -
    quiet enough to read as "silent" in a normal room. That was never a
    B2 regression to reproduce faithfully; it's squeezelite's own
    curve-generation being naive about wide-range controls, and the
    dummy's narrower declared span happens to produce a *gentler, more
    usable* curve as a side effect. Rescaling by fractional position
    (the original approach here) undid that by re-stretching the gentle
    curve back across the DAC's full range - reintroducing the exact
    compression this is meant to avoid. A straight dB copy keeps the
    gentler curve: 75% lands at -12.3dB, 50% at -24.6dB, both clearly
    audible. Costs reachability of the DAC's own quietest ~140 raw steps
    from LMS/Bluetooth specifically (the dummy's floor, -45dB, is well
    short of the DAC's -120dB) - accepted, since dead silence is what
    pause/mute are for, not the bottom of a renderer's own volume slider.
    """
    return db_to_raw(dummy_raw_to_db(raw))


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


# ADR-0034: the panel slider spans -45..0dB, linear in dB, with the bottom
# of travel as silence - the span LMS's and Spotify's own sliders settled on
# (Findings 009, 010). The number shown is the slider position.
SLIDER_DB_MIN = -45.0

#: ADR-0052 §4. A new target is walked to rather than jumped to, because a
#: drag only ever delivers a *sample* of itself to us - measured, 6 of 12
#: finger positions on a fast one, in 4 dB steps (Finding 045 §2). The
#: hardware fills in the rest at its own pace: one raw step is 0.5 dB and
#: costs ~5.7 ms, so the cap is what bounds a big move rather than the step
#: count. A 4 dB gap becomes eight steps and ~46 ms - a slide.
RAMP_MAX_S = 0.12
#: Below this a move is a single write: one or two steps ramped would cost
#: more in bookkeeping than the smoothness is worth.
RAMP_MIN_STEPS = 3


def slider_percent_to_raw(percent: float) -> int:
    if percent <= 0:
        return 0
    return db_to_raw(SLIDER_DB_MIN + min(percent, 100) / 100 * -SLIDER_DB_MIN)


def raw_to_slider_percent(raw: int) -> int:
    """Quieter than the slider's floor but not silent reads as 0%."""
    if raw <= 0:
        return 0
    percent = (raw_to_db(raw) - SLIDER_DB_MIN) / -SLIDER_DB_MIN * 100
    return max(0, min(100, round(percent)))


class Mute:
    """ADR-0034: mute remembers the level and writes silence; unmute writes it
    back. Any other change to the level ends mute, so "muted" is never shown
    over audible music."""

    def __init__(self, write_hardware, current_raw) -> None:
        self._write_hardware = write_hardware
        self._current_raw = current_raw
        self.muted = False
        self._restore: int | None = None

    async def set(self, muted: bool) -> bool:
        if muted == self.muted:
            return True
        if muted:
            raw = self._current_raw()
            if raw is None:
                return False
            self._restore = raw
            self.muted = True
            await self._write_hardware(0)
        else:
            restore, self._restore = self._restore, None
            self.muted = False
            await self._write_hardware(restore)
        return True

    def observe(self, raw: int) -> None:
        if self.muted and raw != 0:
            self.muted = False
            self._restore = None


# Spotify's own volume report is a bare fraction (value/max_, go-librespot's
# software scale) with no hardware control - and therefore no declared TLV
# range - behind it, unlike LMS/Bluetooth which each derive their own
# curve from a real control's range (see dummy_raw_to_hardware_raw's
# docstring). `_on_spotify_volume` used to map that fraction *linearly in
# raw steps* straight onto the DAC's full 0..240 - found wrong on
# hardware, 2026-09-08, the same day and the same shape as LMS's bug:
# George reported 60% inaudible. Raw steps are dB-linear, not
# perceptually linear (raw_to_db's own docstring), so a linear-in-percent
# mapping across the DAC's full 120dB span compresses nearly all
# perceived loudness change into the last quarter of the slider - exactly
# what a wide-range control does to any naive curve, LMS's included
# before its own fix. -45dB matches the effective span LMS's curve
# settled on via the dummy control - chosen here for consistency across
# renderers' sliders, not derived from anything Spotify-specific (Spotify
# has no declared hardware range of its own to derive one from).
SPOTIFY_DB_MIN = -45.0


def spotify_fraction_to_hardware_raw(fraction: float) -> int:
    db = SPOTIFY_DB_MIN + fraction * (0.0 - SPOTIFY_DB_MIN)
    return db_to_raw(db)


def hardware_raw_to_spotify_fraction(raw: int) -> float:
    """Inverse of `spotify_fraction_to_hardware_raw` - used when a hardware
    change (a manual amixer change, a restored remembered level) needs
    reporting back to Spotify as its own value/steps. Clamped to 0..1:
    a raw value quieter than SPOTIFY_DB_MIN represents (reachable from
    LMS/Bluetooth's own dummy floor, or a manual amixer write) has no
    fraction below 0% to express - report 0%, not a negative one.
    """
    db = raw_to_db(raw)
    frac = (db - SPOTIFY_DB_MIN) / (0.0 - SPOTIFY_DB_MIN)
    return max(0.0, min(1.0, frac))


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


class _Mixer:
    """The DAC's volume control through libasound, opened once.

    **Measured, which is why this exists** (ADR-0052 §4, Finding 045 §1):
    one write costs **16.4 ms** as an `amixer` subprocess and **5.7 ms**
    through this, of which 5.7 is the DAC's own I²C - so two thirds of the
    cost was the process spawn, and removing it is what makes a ramp
    affordable at all.

    `amixer` stays as the fallback. A device whose mixer cannot be opened
    this way still has its volume, a little slower.
    """

    def __init__(self, device: str, control: str) -> None:
        self._device, self._control = device, control
        self._lib = None
        self._elem = None
        self._broken = False

    def _open(self) -> bool:
        if self._elem is not None:
            return True
        if self._broken:
            return False
        try:
            import ctypes

            lib = ctypes.CDLL("libasound.so.2")
            # **Every signature is declared.** ctypes assumes `int` for a
            # return value it has not been told about, which truncates a
            # 64-bit pointer to 32 bits - `snd_mixer_find_selem` then hands
            # back a plausible-looking address that is not the element, and
            # the first write through it takes the process down with SIGSEGV.
            # Found the hard way on the device, 2026-09-22: five restarts in
            # fifteen seconds.
            lib.snd_mixer_open.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_int]
            lib.snd_mixer_attach.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            lib.snd_mixer_selem_register.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
            ]
            lib.snd_mixer_load.argtypes = [ctypes.c_void_p]
            lib.snd_mixer_selem_id_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
            lib.snd_mixer_selem_id_set_index.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            lib.snd_mixer_selem_id_set_name.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            lib.snd_mixer_find_selem.restype = ctypes.c_void_p
            lib.snd_mixer_find_selem.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            lib.snd_mixer_selem_set_playback_volume_all.argtypes = [
                ctypes.c_void_p, ctypes.c_long
            ]
            handle = ctypes.c_void_p()
            if lib.snd_mixer_open(ctypes.byref(handle), 0) != 0:
                raise OSError("snd_mixer_open")
            for call in (
                lambda: lib.snd_mixer_attach(handle, self._device.encode()),
                lambda: lib.snd_mixer_selem_register(handle, None, None),
                lambda: lib.snd_mixer_load(handle),
            ):
                if call() != 0:
                    raise OSError("mixer setup")
            sid = ctypes.c_void_p()
            lib.snd_mixer_selem_id_malloc(ctypes.byref(sid))
            lib.snd_mixer_selem_id_set_index(sid, 0)
            lib.snd_mixer_selem_id_set_name(sid, self._control.encode())
            found = lib.snd_mixer_find_selem(handle, sid)
            if not found:
                raise OSError(f"no control {self._control!r} on {self._device!r}")
            self._lib, self._handle, self._ctypes = lib, handle, ctypes
            self._elem = ctypes.c_void_p(found)
            logger.info("volume: %s/%s opened directly", self._device, self._control)
            return True
        except Exception as exc:  # noqa: BLE001 - any failure means "use amixer"
            logger.warning("volume: %s/%s not openable (%s); using amixer",
                           self._device, self._control, exc)
            self._broken = True
            return False

    def set(self, value: int) -> bool:
        if not self._open():
            return False
        try:
            self._lib.snd_mixer_selem_set_playback_volume_all(
                self._elem, self._ctypes.c_long(value)
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("volume: direct write failed (%s); using amixer", exc)
            self._broken = True
            self._elem = None
            return False


#: One per control, built on first use. The hardware DAC is the only one
#: written here; the dummy controls are read, never written (§9 of the
#: finding: nothing of ours writes them).
_MIXERS: dict[tuple[str, str], _Mixer] = {}

#: One worker, so every libasound call on a mixer handle comes from the
#: thread that opened it.
_MIXER_THREAD = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="gexis-mixer"
)


async def set_raw(mixer_name: str, value: int) -> None:
    value = max(0, min(HARDWARE_MAX, value))
    key = (MIXER_DEVICE, mixer_name)
    mixer = _MIXERS.get(key)
    if mixer is None:
        mixer = _MIXERS[key] = _Mixer(*key)
    # **Off the event loop, and always the same thread.** 5.7 ms of the
    # write is the DAC's own I²C and a ramp makes that call twenty times
    # over, so it cannot sit on the loop - and an `snd_mixer` handle is not
    # thread-safe, so it cannot go to a pool either.
    if await asyncio.get_running_loop().run_in_executor(_MIXER_THREAD, mixer.set, value):
        return
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

    def __init__(
        self,
        mixer_name: str,
        adapter,
        *,
        volume_memory,
        get_active_renderer,
        on_hardware_level=None,
        ceiling_db=None,
    ) -> None:
        """`adapter` is any `VolumeMechanism.SOFTWARE_API` renderer
        (`adapters/base.py`'s `SoftwareVolumeAdapter` protocol) - only
        `SpotifyAdapter` today (criterion 3, fixed 2026-09-12: this class
        used to be hardcoded to a `spotify_adapter` param and compared
        `self._get_active_renderer() == "spotify"` by literal string
        throughout; both now go through `adapter.renderer_id`, so a
        second SOFTWARE_API renderer would need no change here).

        `on_hardware_level(raw)`, if given, is called whenever the real
        DAC's level is known to have changed - Phase 4 criterion 8's
        display. Reported from **both** the monitor loop (somebody else
        changed it) and `write_hardware` (we changed it), because the echo
        suppression that makes this class work means our own writes are
        deliberately skipped by the monitor path: a display fed only from
        there would silently miss every level we set ourselves, including
        restore-on-acquire and the UI's own slider.
        """
        self._mixer_name = mixer_name
        self._adapter = adapter
        self._volume_memory = volume_memory
        self._get_active_renderer = get_active_renderer
        self._on_hardware_level = on_hardware_level
        # Each is (value, armed_at) or None - the exact value we wrote in
        # that direction, awaiting its own echo back. See the module
        # docstring on why this is value-matched rather than a time window.
        self._expected_hw_raw: tuple[int, float] | None = None
        self._expected_adapter_value: tuple[int, float] | None = None
        #: ADR-0052 §3: `max_ceiling`, read through a callable so a change
        #: applies to the next write rather than the next restart. Returns
        #: dB or None.
        self._ceiling_db = ceiling_db or (lambda: None)
        #: The ramp in flight, cancelled when a newer target arrives.
        self._ramp: asyncio.Task | None = None
        self._last_written: int | None = None
        #: **Every value we write, not only the target** (ADR-0052 §4). A
        #: ramp writes a dozen intermediate values and `alsactl monitor`
        #: reports each one; matching only the target made every step look
        #: like somebody turning the knob - which republished the level a
        #: dozen times (the volume drawer then never auto-hid, George,
        #: 2026-09-22) and echoed each step out to Spotify.
        self._written: dict[int, float] = {}
        adapter.on_volume_change(self._on_adapter_volume)

    def _capped(self, raw: int) -> int:
        """Every level reaches the DAC through here, so the ceiling is
        enforced in one place (ADR-0052 §3) - panel, mirror and restore
        alike."""
        ceiling = self._ceiling_db()
        if ceiling is None:
            return raw
        return min(raw, db_to_raw(float(ceiling)))

    def _note_written(self, raw: int) -> None:
        now = time.monotonic()
        self._written = {
            value: at for value, at in self._written.items() if now - at < ECHO_WINDOW_S
        }
        self._written[raw] = now

    def _was_ours(self, raw: int) -> bool:
        """True if we wrote this value ourselves within the echo window -
        the ramp's own steps coming back through the monitor."""
        at = self._written.get(raw)
        return at is not None and time.monotonic() - at < ECHO_WINDOW_S

    @staticmethod
    def _consume(expected: tuple[int, float] | None, value: int) -> bool:
        """True if `value` is the echo we were waiting for, and not stale."""
        if expected is None:
            return False
        wanted, armed_at = expected
        if time.monotonic() - armed_at >= ECHO_WINDOW_S:
            return False
        return value == wanted

    async def write_hardware(self, raw: int) -> None:
        """Write `raw` to the real DAC and arm the echo window first.

        Found on hardware, 2026-09-08: `restore_volume` (`__main__.py`)
        was calling `set_raw()` directly on acquire, bypassing this
        class's echo window entirely. That write still shows up on
        `alsactl monitor` like any other, so `run()`'s loop treated it as
        a genuine external change and echoed it straight back out to
        go-librespot via `_spotify.set_volume()` - a spurious round trip
        on every Spotify acquisition, racing whatever go-librespot's own
        fresh-connect volume report happened to be at the same moment.
        Matches George's report exactly: volume "behind" the phone's own
        display, occasionally absent, and once actually inverted (phone
        showed the level dropping while the speaker got louder) - two
        writes to the same control, arriving in whichever order the two
        async tasks happened to schedule in.

        Anything that writes the real DAC outside a renderer's own live
        volume-report path (`_on_adapter_volume`) must go through this,
        not `set_raw` directly - restore-on-acquire and the unmanaged-
        renderer floor bump both do now.
        """
        raw = self._capped(raw)
        self._expected_hw_raw = (raw, time.monotonic())
        # **The panel is told the target, not the journey** (ADR-0052 §4):
        # a readout that crawled through the ramp would be worse than the
        # staircase it replaces.
        self._report_hardware_level(raw)
        if self._ramp is not None and not self._ramp.done():
            self._ramp.cancel()
        self._ramp = asyncio.ensure_future(self._ramp_to(raw))
        # Never raises: a ramp the next target supersedes ends quietly, and
        # its caller is not the one who cancelled it.
        await self._ramp

    async def _ramp_to(self, target: int) -> None:
        """Walk the DAC to `target` in single raw steps (0.5 dB each).

        A drag reaches us as a handful of positions a second, so the
        hardware fills in the rest - it will take ~175 changes a second and
        the ear hears a slide rather than a staircase (Finding 045 §1, §2).
        Cancelled the moment a newer target arrives, which is what makes a
        fast drag land on the last value rather than on a queue of old ones.
        """
        start = self._last_written
        try:
            if start is not None and abs(target - start) >= RAMP_MIN_STEPS:
                # One write per step unless that would outrun the cap, in
                # which case the steps get bigger rather than the move
                # slower.
                budget = max(1, int(RAMP_MAX_S / 0.006))
                stride = max(1, -(-abs(target - start) // budget))
                step = stride if target > start else -stride
                value = start
                while (step > 0 and value + step < target) or (step < 0 and value + step > target):
                    value += step
                    self._note_written(value)
                    await set_raw(self._mixer_name, value)
                    self._last_written = value
            # **The target is always written, and written last.** A ramp
            # that stopped short of it is the defect this replaced
            # ("blocker 4": a fast drag to maximum landing below full
            # scale), so it is unconditional and outside the cancellable
            # walk above.
            self._note_written(target)
            await set_raw(self._mixer_name, target)
            self._last_written = target
        except asyncio.CancelledError:
            # Superseded: whatever step we reached is where the hardware
            # is, and the newer target ramps from there. Swallowed rather
            # than re-raised so it never surfaces in the caller that asked
            # for the *earlier* level.
            return

    def _report_hardware_level(self, raw: int) -> None:
        if self._on_hardware_level is not None:
            self._on_hardware_level(raw)

    def _on_adapter_volume(self, value: int, max_: int) -> None:
        renderer_id = self._adapter.renderer_id
        if max_ <= 0:
            logger.warning("volume: %s reported max=%r, ignoring", renderer_id, max_)
            return
        if self._consume(self._expected_adapter_value, value):
            self._expected_adapter_value = None
            logger.debug("volume: ignoring %s's echo of our own %s", renderer_id, value)
            return
        raw = spotify_fraction_to_hardware_raw(value / max_)
        self._volume_memory.remember(renderer_id, raw)
        if self._get_active_renderer() != renderer_id:
            # Remembered for next time, but this renderer doesn't
            # currently own the mixer - writing now would move someone
            # else's volume out from under them.
            logger.debug(
                "volume: %s reported %s/240 while inactive, remembered but not applied",
                renderer_id,
                raw,
            )
            return
        logger.info("volume: %s -> hardware (%s/%s -> %s/240)", renderer_id, value, max_, raw)
        asyncio.create_task(self.write_hardware(raw))

    async def run(self) -> None:
        """Watch `alsactl monitor` and push hardware changes to the
        SOFTWARE_API adapter this bridge was built for.

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
            raw = await get_raw(self._mixer_name)
            if raw is None or raw == last_raw:
                # `raw == last_raw` also absorbs the extra monitor lines a
                # single write can produce - they all read back the same
                # value, so only the first reaches anything below.
                continue
            if self._consume(self._expected_hw_raw, raw) or self._was_ours(raw):
                # Our own write coming back at us, not somebody turning
                # the knob. Record it as the new baseline so the next
                # genuine change still registers as a change.
                self._expected_hw_raw = None
                last_raw = raw
                continue
            last_raw = raw
            # Reported before attribution, deliberately: the level is a
            # fact about the hardware whether or not anyone currently holds
            # the device, and criterion 8's display should be right even in
            # the nobody-active state the block below declines to attribute.
            self._report_hardware_level(raw)
            active = self._get_active_renderer()
            if active is None:
                # Nobody holds the device (ADR-0027 makes this routine, not
                # an error). A hardware change with no active renderer has
                # nobody to attribute it to - remembering it against None
                # would poison whichever renderer's level was looked up by
                # that key next. Track it as the new baseline and move on.
                logger.debug(
                    "volume: hardware changed to %s/240 with no active renderer, not attributed",
                    raw,
                )
                continue
            self._volume_memory.remember(active, raw)
            if active != self._adapter.renderer_id:
                continue
            steps = await self._adapter.get_volume_steps()
            value = round(hardware_raw_to_spotify_fraction(raw) * steps)
            logger.info("volume: hardware -> %s (%s/240)", self._adapter.renderer_id, raw)
            self._expected_adapter_value = (value, time.monotonic())
            await self._adapter.set_volume(value)


#: How long the control must stop moving before a gated renderer's change
#: is mirrored, and therefore how long before the transport is read.
#: Measured on hardware 2026-09-17: LMS's pause fade takes ~150 ms end to
#: end, a slider drag sends steps ~35-50 ms apart, and the core learns of
#: a pause or a new volume 0.51 s after the fact (CometD push). 0.8 s
#: clears that report; it is also how long an LMS app's volume change
#: takes to reach the DAC, which is the price of telling the two apart.
SETTLE_S = 0.8

#: ADR-0052 §5. Below a finger's rate, far below a fault's.
MIRROR_MIN_INTERVAL_S = 0.04


class DummyMixerBridge:
    """Mirrors one renderer's private dummy mixer control onto the real
    hardware DAC, only while that renderer is active (B2, George's
    decision 2026-09-08 - see this module's docstring).

    One instance per dummy-backed renderer (LMS, Bluetooth - Spotify
    doesn't need one, `VolumeBridge` already isolates it via
    go-librespot's own software volume). `hardware_control` is the real
    DAC's control name ("DAC"); `dummy_card`/`dummy_control` identify the
    renderer's own snd-dummy control ("gexislmsvol"/"Master", say).

    **Deliberately has no echo window**, unlike `VolumeBridge` - found
    wrong on hardware, 2026-09-08. This class watches the *dummy* card
    but writes to the *real DAC*; those are different ALSA cards, so a
    write here can never show up on the dummy's own `alsactl monitor`
    stream the way `VolumeBridge`'s writes echo back on the one card it
    both watches and writes. An earlier version armed a window here
    anyway (copied from `VolumeBridge` without re-deriving whether it
    applied) - since it could never see a genuine echo of its own write,
    all it did was silently swallow real, rapid updates from
    squeezelite/bluealsa-aplay arriving within the window of a previous
    mirror. Bluetooth's AVRCP volume updates during a phone slider drag
    land well under the old 0.75s window apart (as little as ~35ms) -
    every mirror re-armed the window before the next genuine update
    could get through, so once started, an update chain could silence
    itself for as long as updates kept arriving that fast, explaining
    both a Bluetooth session with *zero* mirrored volume changes despite
    a full slider drag, and Bluetooth's usable maximum reading quieter
    than Spotify/LMS's (a drag toward maximum getting silenced partway).
    `raw == last_raw` below already dedupes multiple monitor lines from
    one underlying change - the only case an echo window would have
    covered.

    **`renderer_volume` gates the mirror** (George, 2026-09-17: ignore the
    fade; amends ADR-0034/ADR-0018). LMS fades the player out when it
    pauses by sending volume steps, which squeezelite applies to this dummy
    control: measured 22 -> 7 -> -6 -> -20 -> -50 in ~150 ms. Mirrored,
    that put the DAC at its -45 dB floor, published the user's volume as 0%
    for as long as the pause lasted, and remembered the faded level as the
    renderer's - so a takeover during a pause brought LMS back nearly
    silent.

    So a gated renderer's change is decided **once the control has stopped
    moving for `SETTLE_S`**, and then only mirrored if `is_playing()`. The
    waiting is what makes the gate work: measured 2026-09-17, LMS fades
    *before* it reports the pause, and the core learns of that pause 0.51 s
    later, so deciding as each step arrives read the transport as "playing"
    and let every fade step through. One fade, or one slider drag, produces
    one decision.

    A change made from an LMS app while the player is paused is therefore
    not applied while it is paused; the next resume settles and applies
    whatever the control holds then.

    A renderer whose volume never fades (Bluetooth) passes no `is_playing`
    and mirrors every change as it arrives - unchanged behaviour, and its
    AVRCP updates during a slider drag are exactly the rapid stream an
    earlier echo window was found to swallow (above).
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
        is_playing=None,
    ) -> None:
        self._renderer_id = renderer_id
        self._dummy_card = dummy_card
        #: ADR-0052 §5's rate limit.
        self._last_mirror_at = 0.0
        self._pending: tuple[int, int, str] | None = None
        self._mirror_soon: asyncio.Task | None = None
        self._dummy_control = dummy_control
        self._hardware_control = hardware_control
        self._volume_memory = volume_memory
        self._get_active_renderer = get_active_renderer
        self._is_playing = is_playing
        #: The last reading, to absorb the repeated monitor lines one
        #: change produces.
        self._last_seen: int | None = None
        self._settling: asyncio.Task | None = None

    async def _mirror(self, raw: int, *, why: str = "") -> None:
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
            return
        # **One write per 40 ms, latest value wins** (ADR-0052 §5). A finger
        # on a phone's slider produces nothing like that rate; a bluealsa
        # meltdown produced 750 dummy changes a second (Finding 045 §10) and
        # this turned every one of them into a 16 ms hardware write.
        now = time.monotonic()
        since = now - self._last_mirror_at
        if since < MIRROR_MIN_INTERVAL_S:
            self._pending = (raw, hardware_raw, why)
            if self._mirror_soon is None or self._mirror_soon.done():
                self._mirror_soon = asyncio.ensure_future(
                    self._mirror_after(MIRROR_MIN_INTERVAL_S - since)
                )
            return
        self._last_mirror_at = now
        logger.info(
            "volume: %s -> hardware (dummy %s -> %s/240)%s",
            self._renderer_id,
            raw,
            hardware_raw,
            why,
        )
        await set_raw(self._hardware_control, hardware_raw)

    async def _mirror_after(self, delay: float) -> None:
        """The value that arrived during the quiet period, once it is over.
        Only the newest is kept: the ones in between are already stale."""
        await asyncio.sleep(delay)
        pending, self._pending = self._pending, None
        if pending is None:
            return
        raw, hardware_raw, why = pending
        self._last_mirror_at = time.monotonic()
        logger.info(
            "volume: %s -> hardware (dummy %s -> %s/240)%s [coalesced]",
            self._renderer_id,
            raw,
            hardware_raw,
            why,
        )
        await set_raw(self._hardware_control, hardware_raw)

    async def _on_dummy_change(self, raw: int | None) -> None:
        """One reading of the dummy control: dedupe, then the pause-fade
        gate, then mirror. Split out of `run()` so it is testable without
        an `alsactl monitor` subprocess."""
        if raw is None or raw == self._last_seen:
            return
        self._last_seen = raw
        if self._is_playing is None:
            await self._mirror(raw)
            return
        # Gated renderers settle first (see the class docstring). Each new
        # step restarts the wait, so one fade or one drag produces one
        # decision.
        if self._settling is not None and not self._settling.done():
            self._settling.cancel()
        self._settling = asyncio.create_task(self._settle_then_mirror())

    async def _settle_then_mirror(self) -> None:
        """Wait for the control to stop moving, then mirror what it settled
        on - unless the renderer is not playing, which makes it a fade (see
        the class docstring)."""
        await asyncio.sleep(SETTLE_S)
        raw = await get_raw(self._dummy_control, device=f"hw:{self._dummy_card}")
        if raw is None:
            return
        self._last_seen = raw
        if not self._is_playing():
            logger.info(
                "volume: %s's control settled at %s while it is not playing"
                " - a pause fade, not a volume change; ignored",
                self._renderer_id,
                raw,
            )
            return
        await self._mirror(raw)

    async def run(self) -> None:
        proc = await asyncio.create_subprocess_exec(
            "alsactl",
            "monitor",
            f"hw:{self._dummy_card}",
            stdout=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                logger.warning(
                    "volume: alsactl monitor(%s) exited, restarting in 5s", self._dummy_card
                )
                await asyncio.sleep(5)
                return await self.run()
            await self._on_dummy_change(
                await get_raw(self._dummy_control, device=f"hw:{self._dummy_card}")
            )
