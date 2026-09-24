# SPDX-License-Identifier: GPL-3.0-or-later
"""Core configuration.

Loaded from a TOML file rather than baked into the package, so values like
the safe boot volume are a configuration change, not a code change - ADR-
0018 is explicit that the specific safe level "is a configuration value,
not a decision for this record", i.e. this file, not arbitration.py.

stdlib `tomllib` (3.11+, read-only) rather than PyYAML: one less pinned
dependency, one less wheel to trust, for a format we only ever read.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("/etc/gexis/core.toml")


@dataclass(frozen=True)
class Config:
    mixer_name: str = "DAC"

    # LMS runs on its own machine, not on gexis - there is no sane
    # localhost default here (unlike go-librespot, which is local).
    # image/stage-gexis/03-core/files/core.toml overrides this for the
    # actual deployment; the class default below is only a fallback for
    # ad hoc/test use off the image.
    lms_host: str = "192.168.178.188"
    lms_port: int = 9000
    lms_player_name: str = "gexis"

    go_librespot_host: str = "127.0.0.1"
    go_librespot_port: int = 3678

    # Phase 3 criterion 1's state WebSocket (wsserver.py). 0.0.0.0 so the
    # UI (a future phase, running as a separate process - possibly a
    # remote browser per ARCHITECTURE.md's "same page served to a remote
    # browser") can reach it without a same-host assumption; nothing about
    # this state is sensitive enough to warrant binding to loopback only.
    state_host: str = "0.0.0.0"
    state_port: int = 8090

    # Phase 3 criterion 4: moOde's own path (metadata_file.py), so an
    # external display project built against moOde's file finds it in the
    # place it already expects. A `str`, not a `Path`, matching every
    # other field here - TOML gives back strings, and metadata_file.py
    # wraps it in `Path(...)` itself.
    metadata_file_path: str = "/var/local/www/currentsong.txt"

    # Phase 4b: the built Svelte output this daemon serves (ADR-0028).
    # Empty string means "no UI installed" - the daemon then runs headless
    # and answers the API only, which is what every deployment before
    # Phase 4b did and what a core-only development install still does.
    ui_dir: str = "/opt/gexis-ui"
    # ADR-0047 §2a: Pixabay forbids permanent hotlinking, so the wallpapers
    # on screen are files on this device. Beside the settings database -
    # they are what the idle screen shows when the network is not there, so
    # /tmp would empty them at exactly the wrong moment.
    wallpaper_dir: str = "/var/lib/gexis-core/wallpapers"
    # "Wallpapers on device". **How pictures get here is ADR-0047's open
    # question** - today SSH or a card - and whatever answers it writes into
    # this directory rather than changing any of the code that reads it.
    pictures_dir: str = "/var/lib/gexis-core/pictures"

    # Phase 5 criterion 1: the visualisation service (ADR-0011). The two
    # peppyalsa pipes are read by that service alone - a FIFO splits its
    # bytes between readers - and it republishes on the passthrough pair,
    # which is what our vendored PeppyMeter is pointed at.
    # **In /run, not /tmp** (ADR-0011, amended 2026-09-22). `bluealsa-aplay`
    # ships with `PrivateTmp=yes`, so peppyalsa loaded inside it opened
    # `/tmp/peppymeter` in a *private* /tmp - a different file with no
    # reader - and got ENXIO on every period, for ever. The visualiser was
    # blind for the whole of Bluetooth and nothing said so. /run/gexis is
    # where this device's runtime files already live and no sandbox hides
    # it.
    meter_fifo: str = "/run/gexis/meter.fifo"
    spectrum_fifo: str = "/run/gexis/spectrum.fifo"
    meter_passthrough: str = "/run/gexis/meter-peppy.fifo"
    spectrum_passthrough: str = "/run/gexis/spectrum-peppy.fifo"
    spectrum_bands: int = 30  # peppyalsa's spectrum_size, output.conf
    # **The spectrum engine's own config, read to find out how many bars it
    # is about to draw.** A pipe has no message boundaries: PeppySpectrum
    # reads `4 * size` bytes at a time, so a frame of any other length
    # leaves it reading across record boundaries and every bar shows a
    # different band from one refresh to the next (Finding 051). The
    # passthrough follows what the consumer declares rather than guessing.
    spectrum_consumer_config: str = "/opt/gexis-peppy/spectrum/config.txt"
    # **PeppyMeter's own config**, which carries how many samples the
    # needle is averaged over (ADR-0058). It reads it once, at start, so a
    # change to it means restarting `gexis-peppy`.
    meter_consumer_config: str = "/opt/gexis-peppy/peppymeter/config.txt"
    # **Where the daemon leaves the dB it is currently cutting** (ADR-0057).
    # `volume.ATTENUATION_PATH` is the writer's copy of this and the two
    # are pinned together by a test - a meter reading a path nobody writes
    # would show the source level and say nothing about it.
    attenuation_path: str = "/run/gexis/attenuation"
    meter_frame_rate: int = 30  # the skins' own ui.refresh.period, ADR-0015
    meter_port: int = 8091
    # Empty by default: pushing to a PeppyMeter web server elsewhere is for a
    # remote display, not for the panel's own process, which reads the pipe.
    meter_http_target: str = ""

    # Phase 5: where the panel's compositor socket lives, for raising and
    # hiding the Peppy screen. The daemon runs as root with no session.
    # ADR-0050: the picker's previews are the skins' own pictures, read from
    # where the image installs them. Several packs live under this, each with
    # its own templates directories.
    peppy_skins_dir: str = "/opt/gexis-peppy/skins"
    peppy_runtime_dir: str = "/run/user/1000"
    peppy_wayland_display: str = "wayland-0"

    # Phase 4d: the idle screen's external page (ADR-0019). Empty means
    # unconfigured, and the UI shows its built-in clock. Set on the device
    # only - the real URL carries a per-display identifier.
    idle_url: str = ""

    # Phase 4 criterion 4: renderer pairs whose measured takeover gap is
    # below ADR-0010's 1s threshold, so a transition screen would be a
    # flicker rather than information. Published in the state payload
    # rather than hardcoded in the UI, because the criterion is explicit
    # that this is "data, not a constant" - a pair earns its exemption by
    # being measured (Finding 020: 224.6/335.2ms medians) and loses it if
    # a later measurement moves it back above. Config rather than a user
    # setting: it is evidence, not preference.
    handoff_exempt_pairs: tuple[tuple[str, str], ...] = (
        ("lms", "spotify"),
        ("spotify", "lms"),
    )

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Config":
        if not path.exists():
            return cls()
        data = tomllib.loads(path.read_text())
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"{path}: unknown config key(s): {sorted(unknown)}")
        return cls(**data)
