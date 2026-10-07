# SPDX-License-Identifier: GPL-3.0-or-later
"""The adapter protocol every renderer implements (ARCHITECTURE.md §8).

Policy - who wins, what happens to who loses - lives in the supervisor
(arbitration.py). An adapter owns *mechanism* only: how this specific
renderer is told to let go, and how to tell whether it actually did.
"""
from __future__ import annotations

import abc
import enum
import typing
from dataclasses import dataclass, field

if typing.TYPE_CHECKING:
    from gexis_core.arbitration import TimeoutLadder


#: ADR-0037 §1: every transport command the route knows. An adapter
#: declares the ones it accepts in `Capabilities.controls` and implements
#: each as a coroutine method of the same name returning success.
TRANSPORT_COMMANDS = frozenset({"play", "pause", "next", "previous", "shuffle", "repeat"})


class ReleaseAction(enum.Enum):
    """What happens to a renderer that loses the device (ADR-0010 table)."""

    PAUSE = "pause"  # LMS only: stays connected, becomes idle
    DISCONNECT = "disconnect"  # everyone else


class VolumeMechanism(enum.Enum):
    """How the daemon learns a renderer's volume (criterion 3, replacing
    what used to be hardcoded by renderer name in __main__.py/volume.py -
    found on hardware across Findings 006/008/009/010/011, not designed up
    front). Whichever it is, the renderer's own number is the truth
    (ADR-0053) and reaches the output by one curve (ADR-0054 §3).

    A renderer with its own software volume API (Spotify) reports its
    number through `VolumeBridge`. A renderer with no such API (LMS via
    squeezelite) points its own mixer control at a private snd-dummy card;
    `DummyMixerBridge` treats a change there as a signal to ask the
    renderer its level (ADR-0054 §2). Bluetooth is declared DUMMY_MIXER but
    goes over bluealsa's D-Bus `Volume` property instead
    (`Capabilities.volume_over_bluealsa`, ADR-0054 §1).
    """

    DUMMY_MIXER = "dummy_mixer"
    SOFTWARE_API = "software_api"


class SoftwareVolumeAdapter(typing.Protocol):
    """The extra surface a `VolumeMechanism.SOFTWARE_API` adapter must
    expose, beyond the base `Adapter` contract - `VolumeBridge` (volume.py)
    calls these polymorphically. Only `SpotifyAdapter` implements this
    today; documented as a Protocol (not an ABC every adapter must
    inherit) since it's conditional on `capabilities.volume_mechanism`,
    not universal.
    """

    renderer_id: str

    def on_volume_change(self, callback: "typing.Callable[[int, int], None]") -> None: ...

    async def get_volume_steps(self) -> int: ...

    async def set_volume(self, value: int) -> None: ...


@dataclass(frozen=True)
class Capabilities:
    """ADR-0013's "contract fields", as data every adapter declares -
    derived from the three built-in adapters' actual behaviour (Phase 3
    criterion 2), not designed in advance: ADR-0013 is explicit that "the
    error is skipping the derivation, not doing it late." Drives now-
    playing control rendering and skin field blanking (ADR-0014).

    `release_action` (ADR-0010/0027's pause-vs-disconnect) is deliberately
    not repeated here - it already exists as `Adapter.release_action`,
    used directly by arbitration.py, and duplicating it risks the two
    drifting apart. Everything in this object is new declared surface, not
    already captured elsewhere on `Adapter`.
    """

    #: ADR-0009: every renderer writes to the same logical "output" device
    #: today. Declared rather than assumed elsewhere, so a future renderer
    #: with a genuinely different audio path isn't a silent special case.
    audio_connection: str
    #: What this adapter treats as "took the device" (ADR-0010's table) -
    #: not exhaustive code paths, the *names* of the acquisition signals,
    #: so a future accountability UI ("why did this take over") has
    #: something to point at instead of "it just did" (the "never show a
    #: state the user cannot account for" rule, decisions/README.md).
    acquisition_events: frozenset[str]
    #: Which of ADR-0014's seven skin fields this renderer can ever
    #: supply - not whether the *current* track happens to have one.
    #: title/artist/album/remaining_time/source_type are universal (every
    #: adapter can always attempt them); only these two genuinely vary by
    #: renderer protocol.
    supports_artwork: bool
    supports_sample_rate: bool
    #: Whether the panel drives this renderer's own volume (ADR-0053: the
    #: panel is a remote for what is playing). For a plugin it decides
    #: whether the renderer is registered as a remote volume channel when
    #: it connects.
    volume_managed: bool
    #: How this renderer's volume gets bridged onto the shared real
    #: hardware mixer (see VolumeMechanism's own docstring for why there
    #: are two, not a special case for a special case's sake). Replaces
    #: __main__.py's old by-name construction of DummyMixerBridge/
    #: VolumeBridge instances.
    volume_mechanism: VolumeMechanism
    #: Only meaningful when `volume_mechanism` is DUMMY_MIXER - the
    #: private snd-dummy ALSA card name this renderer's own process
    #: points its mixer control at - squeezelite's only, today
    #: (image/stage-gexis's modprobe config; volume.py's DUMMY_CARD_LMS/
    #: DUMMY_CARD_BLUETOOTH are the same values, referenced here so the
    #: two never drift apart).
    dummy_mixer_card: str | None = None
    #: **ADR-0054 §1.** This renderer's level is read and written over
    #: bluealsa's own D-Bus API rather than through any ALSA control.
    #:
    #: True for Bluetooth, and it replaced a mixer round trip that was
    #: measured wrong one time in three and that pushed a stale mixer value
    #: at the phone whenever a stream started (Finding 047 §2). It still
    #: declares `dummy_mixer_card` (`gexisbtvol`), but bluealsa-aplay runs
    #: `--volume=none` with no mixer: nothing writes that card, and nothing
    #: reads it.
    volume_over_bluealsa: bool = False
    #: **ADR-0054 §5, amended 2026-09-28: this renderer is handed its level on
    #: acquisition.** Its own level at a takeover is only what its app last
    #: had (an app's leftover), so the core gives it the
    #: DAC's level, capped by `start_max`, as it does Spotify.
    volume_handed: bool = False
    #: Transport commands this renderer accepts through our own control
    #: channel (ADR-0037), from `TRANSPORT_COMMANDS`, each implemented as a
    #: coroutine method of the same name and reached by
    #: `/transport/{command}`. This is what the renderer can ever do; the
    #: published `controls.available` says which of them work right now
    #: (ADR-0020: hide a control that doesn't exist, never show one that
    #: would silently do nothing).
    controls: frozenset[str] = field(default_factory=frozenset)
    #: **The rate it reports is the file's own** (ADR-0036 as amended
    #: 2026-10-02): what the visualiser shows. LMS's is; Spotify's 44.1 kHz
    #: is a decoder's for a lossy stream, so it does not say so; a plugin
    #: says so in its `hello` when it is true of it.
    sample_rate_is_source: bool = False

    def to_json(self) -> dict:
        return {
            "audio_connection": self.audio_connection,
            "acquisition_events": sorted(self.acquisition_events),
            "supports_artwork": self.supports_artwork,
            "supports_sample_rate": self.supports_sample_rate,
            "sample_rate_is_source": self.sample_rate_is_source,
            "volume_managed": self.volume_managed,
            "volume_mechanism": self.volume_mechanism.value,
            "dummy_mixer_card": self.dummy_mixer_card,
            "controls": sorted(self.controls),
        }


class Adapter(abc.ABC):
    """One renderer's acquisition/release behaviour."""

    #: Set by subclasses. Matches the key it's registered under in the
    #: supervisor's adapter map.
    renderer_id: str
    release_action: ReleaseAction
    #: Set by subclasses (Phase 3 criterion 2). Static per class, not
    #: per-instance state - every adapter of a given type declares the
    #: same contract regardless of configuration.
    capabilities: Capabilities

    #: Set by subclasses. The systemd unit whose process actually opens
    #: the ALSA device for this renderer - used by the release ladder's
    #: device_held_by check (alsa.py) to attribute a still-busy device to
    #: the right PID, not just "someone" (see arbitration.py's `_busy`).
    unit_name: str

    #: Per-renderer override of the supervisor's default timeout ladder.
    #: None means "use the supervisor's default". Exists because release
    #: timing is not uniform across renderers - measured on gexis,
    #: 2026-09-06: go-librespot frees the device in <100ms via its own
    #: /player/stop, but a commanded LMS pause does not make squeezelite
    #: release faster than its `-C` idle timeout (~8.5s measured) - a
    #: shared ladder sized for one renderer is wrong for the other.
    #: A plugin sets this from its `hello` (ADR-0091); the built-ins leave
    #: it None.
    release_ladder: "TimeoutLadder | None" = None

    @abc.abstractmethod
    async def run(self, on_acquire, on_release) -> None:
        """Long-running task. Watch for this renderer's acquisition event
        (ADR-0010's table as amended by ADR-0027 - a deliberate
        connect/activate, not a stream start) and call `on_acquire()`
        (sync, non-blocking) each time it fires. Runs for the lifetime of
        the process; must not return on a transient error, only log and
        keep watching.

        `on_release()` (also sync, non-blocking) is the opposite edge: this
        renderer gave up the device with nobody taking over, so nobody
        holds it - LMS on the player being deactivated, Spotify on
        go-librespot's own "inactive" event, Bluetooth on its MediaPlayer1
        disappearing (all three wired as of 2026-09-12; Spotify/Bluetooth's
        absence until then was an oversight found live via the state
        WebSocket showing stale `active`/metadata after a disconnect with
        nothing taking over, not a deliberate ADR-0027 deferral). Calling
        it is safe from any adapter: the supervisor ignores a release from
        a renderer that is not currently active, which is what makes the
        echo of our own takeover-driven release (also a "went inactive"/
        "disappeared" event from the same renderer) a harmless no-op.
        """

    @abc.abstractmethod
    async def release(self) -> bool:
        """Act on this renderer through its own control channel per
        `release_action` (pause for LMS, disconnect for everyone else).
        Return True if the renderer's own API confirmed the action - this
        is the "polite stop" step, not a guarantee the device is free; the
        supervisor checks that separately (`alsa.device_held_by(unit)`).
        """

    @abc.abstractmethod
    async def signal_stop(self, force: bool) -> None:
        """Process-level escalation when `release()` didn't free the device
        in time. `force=False` is the SIGTERM step, `force=True` is SIGKILL.
        """

    async def device_freed(self) -> None:
        """Called by the supervisor on the *incoming* renderer's adapter,
        once per acquisition, immediately after the outgoing renderer's
        release is confirmed and its own volume is restored. Default is a
        no-op.

        Exists for a renderer whose own acquisition attempt can race the
        release ladder's timing and lose - see `SpotifyAdapter` (ADR-0010,
        Finding 014): go-librespot attempts its ALSA open within about a
        second of the event that triggers `on_acquire()`, well before
        LMS's ~3.1s polite release typically completes, so the very
        attempt that caused this acquisition has usually already failed
        by the time the supervisor gets here. A renderer that doesn't have
        this problem (LMS frees in <1s via `-C 1`; Bluetooth's own
        acquisition doesn't depend on winning a race against another
        renderer's release) has no reason to override this.
        """
        return None

    async def restart_after_release(self) -> None:
        """Called by the supervisor on the *outgoing* renderer's adapter,
        once per acquisition, as the very last step - after the incoming
        renderer's own `device_freed()` chance to retry and its volume
        restore. Default is a no-op.

        Exists for a renderer whose process must be brought back after a
        hard stop freed the device; a plugin can ask for it (the plugin
        adapter forwards it). No built-in overrides it: LMS tried and
        reverted it - squeezelite is SIGKILLed by `signal_stop`, and
        systemd's `Restart=on-failure` is what brings it back (see
        `LmsAdapter`).
        """
        return None
