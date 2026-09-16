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
    """How a renderer's volume gets bridged onto the shared real hardware
    mixer (criterion 3, replacing what used to be hardcoded by renderer
    name in __main__.py/volume.py/renderer_volume.py - found on hardware
    across Findings 006/008/009/010/011, not designed up front).

    Two mechanisms exist because the renderers genuinely differ, not as
    an arbitrary split: a renderer with its own software volume API
    (Spotify) needs bidirectional echo-suppressed sync with the real DAC
    (VolumeBridge); a renderer with no such API (LMS via squeezelite,
    Bluetooth via bluealsa-aplay) instead points its own mixer control at
    a private snd-dummy card, mirrored onto the real DAC only while it's
    active (DummyMixerBridge, B2/ADR-0018's amendment) - otherwise the
    three renderers would fight over the one real control continuously.
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
    playing control rendering and skin field blanking (ADR-0014) once a
    UI exists to consume it (Phase 4+) - Phase 3 only declares and
    publishes it.

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
    #: Whether a remembered volume level should be restored when this
    #: renderer becomes active (criterion 5, George's decision 2026-09-07).
    #: Replaces renderer_volume.py's old hardcoded `MANAGED_RENDERERS =
    #: ("lms", "spotify")` tuple (criterion 3) - False for Bluetooth,
    #: whose own volume path mixes confirmed hardware-mixer control with
    #: an unconfirmed software-attenuation regime below ~96% raw (Finding
    #: 006); restoring a remembered level there would write to a mixer
    #: that doesn't fully govern what the user actually hears.
    volume_managed: bool
    #: How this renderer's volume gets bridged onto the shared real
    #: hardware mixer (see VolumeMechanism's own docstring for why there
    #: are two, not a special case for a special case's sake). Replaces
    #: __main__.py's old by-name construction of DummyMixerBridge/
    #: VolumeBridge instances.
    volume_mechanism: VolumeMechanism
    #: Only meaningful when `volume_mechanism` is DUMMY_MIXER - the
    #: private snd-dummy ALSA card name this renderer's own process
    #: (squeezelite, bluealsa-aplay) points its mixer control at
    #: (image/stage-gexis's modprobe config; volume.py's DUMMY_CARD_LMS/
    #: DUMMY_CARD_BLUETOOTH are the same values, referenced here so the
    #: two never drift apart).
    dummy_mixer_card: str | None = None
    #: Transport commands accepted through our own control channel right
    #: now - deliberately empty on all three built-ins today. No adapter
    #: currently exposes a way to send play/pause/seek/etc on a user's
    #: behalf (LMS's pause/power/play/seek calls are only ever issued by
    #: this project's own takeover/resume logic); Phase 4's own criteria
    #: have no transport controls beyond LMS activation, and Phase 6
    #: ("capability-driven controls") is where sending a user's command
    #: through becomes real. Declared now, honestly empty, rather than
    #: invented when Phase 6 needs it (ADR-0020: hide a control that
    #: doesn't exist, never show one that would silently do nothing).
    controls: frozenset[str] = field(default_factory=frozenset)

    def to_json(self) -> dict:
        return {
            "audio_connection": self.audio_connection,
            "acquisition_events": sorted(self.acquisition_events),
            "supports_artwork": self.supports_artwork,
            "supports_sample_rate": self.supports_sample_rate,
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
    #: LmsAdapter sets this; adapters whose default timing is fine (or
    #: not yet measured) leave it None.
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
        supervisor checks that separately (alsa.device_busy).
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

        Exists for a renderer that must keep running continuously
        regardless of which renderer holds the device - see `LmsAdapter`
        (ADR-0010, Finding 013 §1): squeezelite is the base slot and has
        to stay connected to the LMS server even while paused, so if it
        ever needed a hard stop to actually free the device,
        `signal_stop` stopping it deliberately (not killing it) means
        nothing brings it back automatically - this hook is where that
        happens, under this code's own timing rather than systemd's blind
        `Restart=on-failure` retry cadence. A renderer whose process isn't
        expected to persist across a takeover (everyone else - `release_
        action` is DISCONNECT, not PAUSE) has no reason to override this.
        """
        return None
