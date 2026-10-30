# SPDX-License-Identifier: GPL-3.0-or-later
"""**Plugins that ask for more** (ADR-0170).

A plugin the player did not ship runs in one sandbox (ADR-0106); a service
gets no devices. It may ask, in its manifest, for one of a fixed list of
permissions (`"permissions": ["cec"]`); the person adding it is told, and the
player grants exactly that with a drop-in for its unit, written under `/run`
at every start from the manifest and the consent kept in the plugin's record -
never kept on its own, so a permission no longer asked for or consented to is
gone after the next start.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("gexis_core.plugin_permissions")

#: name -> (what the notice says it does, the devices it opens as `DeviceAllow`
#: groups from /proc/devices, the groups those devices belong to).
KNOWN: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "cec": ("Talk to the TV over its HDMI connection (HDMI-CEC)",
            ("char-cec",), ("video",)),
    # I²C, SPI and IR receivers only once their buses are on; the player
    # switches none on (George, 2026-10-30).
    "gpio": ("Use the player's GPIO pins and what is wired to them",
             ("char-gpiochip", "char-gpiomem", "char-i2c", "char-spi", "char-lirc"),
             ("gpio", "i2c", "spi", "video")),
    # Raw USB and HID are root's only on the image: our udev rule gives them
    # to `plugdev` (60-gexis-plugins.rules).
    "usb": ("Use USB devices plugged into the player",
            ("char-usb_device", "char-hidraw", "char-ttyUSB", "char-ttyACM"),
            ("plugdev", "dialout")),
}

#: Under /run: gone at the next boot, written again at every start.
DROPINS = Path("/run/systemd/system")
DROPIN = "gexis-permissions.conf"


class Unknown(ValueError):
    """A permission this player does not grant."""


def parse(raw: object) -> tuple[str, ...]:
    """A manifest's `permissions`: absent is none; anything else must be a
    list of known names, each once."""
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(name, str) for name in raw):
        raise Unknown("permissions must be a list of names")
    for name in raw:
        if name not in KNOWN:
            raise Unknown(f"it asks for {name!r}, which this player does not grant")
    if len(set(raw)) != len(raw):
        raise Unknown("permissions names one twice")
    return tuple(sorted(raw))


def words(names) -> list[dict]:
    """What the notice lists, in order."""
    return [{"name": name, "words": KNOWN[name][0]} for name in sorted(names) if name in KNOWN]


def dropin(names) -> str:
    """The drop-in that grants `names` and nothing else. The renderer's base
    already opens the sound devices this way; a service's hides every device,
    so it goes from `PrivateDevices=yes` to a closed policy with these
    allowed."""
    devices = [d for name in sorted(names) for d in KNOWN[name][1]]
    groups = sorted({g for name in names for g in KNOWN[name][2]})
    lines = ["# Written by gexis-core at its start (ADR-0170): what this plugin asked for",
             "# and the person adding it agreed to. Not kept: /run goes at the next boot.",
             "[Service]", "PrivateDevices=no", "DevicePolicy=closed"]
    lines += [f"DeviceAllow={device} rw" for device in devices]
    lines.append("SupplementaryGroups=" + " ".join(groups))
    return "\n".join(lines) + "\n"


def apply(grants: dict[str, tuple[str, ...]], root: Path = DROPINS) -> list[str]:
    """Make the drop-ins say exactly `grants` (unit -> names): written where
    something is granted, removed where nothing is. The units whose grant
    changed, so that systemd is told (`daemon-reload`) and a unit it started
    at boot, before these were written, is restarted with them."""
    changed = []
    for unit, names in grants.items():
        path = root / f"{unit}.d" / DROPIN
        if names:
            text = dropin(names)
            try:
                if path.read_text() == text:
                    continue
            except OSError:
                pass
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            logger.info("permissions: %s granted %s", unit, ", ".join(names))
            changed.append(unit)
        elif path.exists():
            path.unlink()
            logger.info("permissions: %s granted nothing", unit)
            changed.append(unit)
    if root.is_dir():
        # A plugin removed since: its drop-in goes too.
        for stale in root.glob(f"gexis-uploaded-*.d/{DROPIN}"):
            unit = stale.parent.name[:-2]
            if unit not in grants:
                stale.unlink()
                changed.append(unit)
    return changed
