# SPDX-License-Identifier: GPL-3.0-or-later
"""What the attached screen reports, and which tested model that suggests
(ADR-0109: recognition only suggests, and only a tested model).

Two witnesses, read from sysfs:
- **The screen's EDID**: its maker's three-letter PNP code, the name it gives
  itself, and its preferred mode. Its physical size is never used - the
  10.1" panel on sofa-pi claims 121 × 68 cm (Finding 100).
- **The touch controller's USB ID**, `vendor:product`.

A suggestion needs both a tested model's fingerprint to match and the
preferred mode to be that model's own size, so a screen that merely shares a
maker or a controller is not named for another.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import screens

DRM = Path("/sys/class/drm")
USB = Path("/sys/bus/usb/devices")


@dataclass(frozen=True)
class Fingerprint:
    edid_maker: str | None = None     # PNP code, e.g. "WAV"
    edid_name: str | None = None      # the monitor name descriptor
    usb: str | None = None            # touch controller "vvvv:pppp"


#: What each tested model reports, measured on the hardware. Filled in as
#: George connects each one (ADR-0109 step 6).
FINGERPRINTS: dict[str, Fingerprint] = {
    # sofa-pi's panel, 2026-10-01: EDID 5c 36 = "WAV", name "WaveShare",
    # preferred 1280x800; touch 0712:0010 "WaveShare".
    "waveshare-10.1-hdmi-b": Fingerprint(edid_maker="WAV", edid_name="WaveShare", usb="0712:0010"),
}


@dataclass(frozen=True)
class Seen:
    """What the device can see of its screen right now."""
    connected: bool = False
    connector: str | None = None
    edid_maker: str | None = None
    edid_name: str | None = None
    preferred: tuple[int, int] | None = None
    usb: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict:
        return {
            "connected": self.connected,
            "connector": self.connector,
            "edid_maker": self.edid_maker,
            "edid_name": self.edid_name,
            "preferred": f"{self.preferred[0]}x{self.preferred[1]}" if self.preferred else None,
            "usb": list(self.usb),
        }


def parse_edid(data: bytes) -> tuple[str | None, str | None, tuple[int, int] | None]:
    """(PNP maker, monitor name, preferred mode) from an EDID base block."""
    if len(data) < 128 or data[:8] != b"\x00\xff\xff\xff\xff\xff\xff\x00":
        return None, None, None
    word = (data[8] << 8) | data[9]
    maker = "".join(chr(((word >> shift) & 0x1F) + 64) for shift in (10, 5, 0))
    if not maker.isalpha():
        maker = None
    name = None
    preferred = None
    for start in range(54, 126, 18):
        block = data[start:start + 18]
        pixel_clock = block[0] | (block[1] << 8)
        if pixel_clock:
            if preferred is None:
                width = block[2] | ((block[4] & 0xF0) << 4)
                height = block[5] | ((block[7] & 0xF0) << 4)
                preferred = (width, height)
        elif block[3] == 0xFC:
            name = block[5:18].split(b"\n", 1)[0].decode("ascii", errors="replace").strip() or None
    return maker, name, preferred


def usb_devices(root: Path = USB) -> tuple[str, ...]:
    out = []
    for dev in sorted(root.glob("*")):
        try:
            vendor = (dev / "idVendor").read_text().strip()
            product = (dev / "idProduct").read_text().strip()
        except OSError:
            continue
        if vendor != "1d6b":            # root hubs, not devices
            out.append(f"{vendor}:{product}")
    return tuple(out)


def seen(drm: Path = DRM, usb: Path = USB) -> Seen:
    """The first connected HDMI connector's report, and the USB devices."""
    for connector in sorted(drm.glob("card*-HDMI-A-*")):
        try:
            if (connector / "status").read_text().strip() != "connected":
                continue
            data = (connector / "edid").read_bytes()
        except OSError:
            continue
        maker, name, preferred = parse_edid(data)
        return Seen(True, connector.name.split("-", 1)[1], maker, name, preferred, usb_devices(usb))
    return Seen(usb=usb_devices(usb))


def suggest(report: Seen) -> screens.Screen | None:
    """A tested model whose fingerprint and size match, or nothing."""
    if not report.connected or report.preferred is None:
        return None
    width, height = report.preferred
    for screen_id, fp in FINGERPRINTS.items():
        model = screens.by_id(screen_id)
        if model is None or not model.tested:
            continue
        native = {(model.width, model.height), (model.height, model.width)}
        if (width, height) not in native:
            continue
        edid_ok = fp.edid_maker is None or fp.edid_maker == report.edid_maker
        name_ok = fp.edid_name is None or fp.edid_name == report.edid_name
        usb_ok = fp.usb is None or fp.usb in report.usb
        if edid_ok and name_ok and usb_ok:
            return model
    return None
