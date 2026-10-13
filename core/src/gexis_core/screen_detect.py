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
    # George's 13.3" on gexis, 2026-10-03: EDID "RTK" / "RTK FHD" - Realtek's
    # controller, which many makers' screens report, so the touch controller
    # (ILI 222a:0001) and 1920x1080 carry the match with it.
    "waveshare-13.3-hdmi-h": Fingerprint(edid_maker="RTK", edid_name="RTK FHD", usb="222a:0001"),
    # The bar player's 11.9", read on it 2026-10-10: EDID "WSD" /
    # "WaveShare-119", preferred 320x1480 (its native portrait); touch
    # 0712:000a. Without it setup showed the whole list on the phone where
    # the 10.1" and 13.3" were recognised (George, the same day).
    "waveshare-11.9-hdmi": Fingerprint(edid_maker="WSD", edid_name="WaveShare-119", usb="0712:000a"),
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


def ports(drm: Path = DRM, usb: Path = USB) -> list[Seen]:
    """**Every HDMI port, connected or not** (ADR-0141 D4; George,
    2026-10-12: *"for video we don't even show the second hdmi port"*), in
    connector order, each with what is plugged into it."""
    devices = usb_devices(usb)
    out = []
    for connector in sorted(drm.glob("card*-HDMI-A-*")):
        name = connector.name.split("-", 1)[1]
        try:
            connected = (connector / "status").read_text().strip() == "connected"
            data = (connector / "edid").read_bytes() if connected else b""
        except OSError:
            connected, data = False, b""
        if not connected:
            out.append(Seen(False, name, usb=devices))
            continue
        maker, edid_name, preferred = parse_edid(data)
        out.append(Seen(True, name, maker, edid_name, preferred, devices))
    return out


def has_touch(screen_id: str) -> bool:
    """Whether the player knows `screen_id` has a touch input: a model whose
    fingerprint names its USB touch device (ADR-0147 D3)."""
    fp = FINGERPRINTS.get(screen_id)
    return bool(fp and fp.usb)


def _chosen_connector() -> str | None:
    """The port chosen under *Screen port*, if the screen in use was put
    there by choice (ADR-0147 D1)."""
    from . import screen_apply
    current = screen_apply.read_state().get("current") or {}
    return current.get("connector") if current.get("chosen") else None


def _applied_connector() -> str | None:
    """The port the screen was last applied on, from screen.json."""
    from . import screen_apply
    current = screen_apply.read_state().get("current")
    return current.get("connector") if isinstance(current, dict) else None


def seen(drm: Path = DRM, usb: Path = USB, prefer: str | None = "applied") -> Seen:
    """**The screen's port**, and the USB devices. With one port connected,
    that one. With both (ADR-0141 D2: a panel on one, a sound bar on the
    other), in this order: the port the screen was applied on, if a known
    panel is there; any port a known panel is on (a panel moved to HDMI 2
    with a receiver now on HDMI 1); the port applied on, if anything is
    there; else the first connected. Until 2026-10-12 it was always the
    first connected, so a chosen second port could not hold. `prefer` is a
    connector, or "applied" for screen.json's."""
    connected = [p for p in ports(drm, usb) if p.connected]
    if not connected:
        return Seen(usb=usb_devices(usb))
    if len(connected) == 1:
        return connected[0]
    if prefer == "applied":
        # **A port chosen holds** (ADR-0147 D1; George, 2026-10-13: the
        # LG TV chosen on HDMI 2 went back to the panel on HDMI 1 at every
        # start), as long as something is connected to it.
        try:
            chosen = _chosen_connector()
        except (OSError, AttributeError):
            chosen = None
        held = next((p for p in connected if p.connector == chosen), None)
        if held is not None:
            return held
        try:
            prefer = _applied_connector()
        except OSError:
            prefer = None
    known = [p for p in connected if suggest(p) is not None]
    chosen = next((p for p in connected if p.connector == prefer), None)
    if chosen is not None and chosen in known:
        return chosen
    if known:
        return known[0]
    return chosen or connected[0]


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
