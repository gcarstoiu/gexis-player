# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0157: the phone's touchpad and keyboard as real input on the panel.**

The phone's touchpad moves a pointer the panel's page draws, and its taps
and typing are made up inside that page - which a page from another site in
a frame (the Home Assistant dashboard, ADR-0156) is closed to. Over such a
frame the panel asks the core instead, and the core makes them real:

- **a tap** - a touch from a virtual touchscreen (`/dev/uinput`), at the same
  fraction of the screen as the drawn pointer. labwc maps every touch device
  to the panel's output (`<touch mapToOutput>`), so the device's range is the
  whole screen whatever its size or turn, as `tools/panel-touch.py` does for
  measurements;
- **text** - the compositor's virtual keyboard (`wlrctl keyboard type`, on the
  image for the visualiser), which types any character the phone sends;
- **Backspace, Enter, Tab** - keys of a small virtual keyboard, which
  `wlrctl` cannot press.

Only the panel's own session receives them. The devices are made at the
first use and kept: one made per tap would be added by libinput a moment
after the tap was sent, and the tap lost.
"""
from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import shutil
import struct
import subprocess
import time

logger = logging.getLogger("gexis_core.panel_input")

UINPUT = "/dev/uinput"
EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
SYN_REPORT = 0
BTN_TOUCH = 0x14A
ABS_X, ABS_Y = 0x00, 0x01
ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 0x2F, 0x35, 0x36, 0x39
ABS_CNT = 0x40
INPUT_PROP_DIRECT = 0x01
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_ABSBIT, UI_SET_PROPBIT = 0x40045564, 0x40045565, 0x40045567, 0x4004556E
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502

#: The touchscreen's range: fine enough for any panel, mapped to the screen.
SPAN = 32767
#: The keys `wlrctl keyboard type` cannot press (linux/input-event-codes.h).
KEYS = {"Backspace": 14, "Enter": 28, "Tab": 15}
#: libinput adds a new device a moment after it is made; events before then
#: are dropped silently.
SETTLE_S = 1.0


class _Device:
    """One uinput device, by the legacy setup path (no further ioctl structs)."""

    def __init__(self, name: bytes, keys: list[int], axes: dict[int, int] | None = None,
                 direct: bool = False) -> None:
        self._fd = open(UINPUT, "wb", buffering=0)
        fcntl.ioctl(self._fd, UI_SET_EVBIT, EV_KEY)
        for key in keys:
            fcntl.ioctl(self._fd, UI_SET_KEYBIT, key)
        absmax = [0] * ABS_CNT
        if axes:
            fcntl.ioctl(self._fd, UI_SET_EVBIT, EV_ABS)
            for axis, top in axes.items():
                fcntl.ioctl(self._fd, UI_SET_ABSBIT, axis)
                absmax[axis] = top
        if direct:
            # A screen touched directly, not a touchpad moving a pointer.
            fcntl.ioctl(self._fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT)
        payload = struct.pack("80sHHHHi", name, 0x06, 0x1d6b, 0x0157, 1, 0)  # BUS_VIRTUAL
        payload += struct.pack(f"{ABS_CNT}i", *absmax)
        payload += struct.pack(f"{ABS_CNT}i", *([0] * ABS_CNT)) * 3
        self._fd.write(payload)
        fcntl.ioctl(self._fd, UI_DEV_CREATE)

    def emit(self, type_: int, code: int, value: int) -> None:
        now = time.time()
        self._fd.write(struct.pack("qqHHi", int(now), int((now % 1) * 1e6), type_, code, value))

    def sync(self) -> None:
        self.emit(EV_SYN, SYN_REPORT, 0)


class PanelInput:
    """Real taps, text and keys on the panel, on the panel's request."""

    def __init__(self, *, runtime_dir: str, wayland_display: str, wlrctl: str | None = None) -> None:
        self._wlrctl = wlrctl or shutil.which("wlrctl")
        self._env = {**os.environ, "XDG_RUNTIME_DIR": runtime_dir, "WAYLAND_DISPLAY": wayland_display}
        self._touch: _Device | None = None
        self._keys: _Device | None = None
        self._tracking = 0
        self._lock = asyncio.Lock()

    async def _devices(self) -> None:
        if self._touch is None:
            self._touch = _Device(
                b"gexis-phone-touch", [BTN_TOUCH],
                {ABS_X: SPAN, ABS_Y: SPAN, ABS_MT_SLOT: 9, ABS_MT_POSITION_X: SPAN,
                 ABS_MT_POSITION_Y: SPAN, ABS_MT_TRACKING_ID: 65535},
                direct=True)
            self._keys = _Device(b"gexis-phone-keys", list(KEYS.values()))
            await asyncio.sleep(SETTLE_S)

    async def tap(self, fx: float, fy: float) -> None:
        """A touch at `fx`, `fy` - fractions of the screen's width and height."""
        x = round(min(max(fx, 0.0), 1.0) * SPAN)
        y = round(min(max(fy, 0.0), 1.0) * SPAN)
        async with self._lock:
            await self._devices()
            device = self._touch
            self._tracking = (self._tracking + 1) % 65535
            for code, value in ((ABS_MT_SLOT, 0), (ABS_MT_TRACKING_ID, self._tracking),
                                (ABS_MT_POSITION_X, x), (ABS_MT_POSITION_Y, y), (ABS_X, x), (ABS_Y, y)):
                device.emit(EV_ABS, code, value)
            device.emit(EV_KEY, BTN_TOUCH, 1)
            device.sync()
            await asyncio.sleep(0.05)
            device.emit(EV_ABS, ABS_MT_SLOT, 0)
            device.emit(EV_ABS, ABS_MT_TRACKING_ID, -1)
            device.emit(EV_KEY, BTN_TOUCH, 0)
            device.sync()

    async def key(self, name: str) -> bool:
        code = KEYS.get(name)
        if code is None:
            return False
        async with self._lock:
            await self._devices()
            self._keys.emit(EV_KEY, code, 1)
            self._keys.sync()
            self._keys.emit(EV_KEY, code, 0)
            self._keys.sync()
        return True

    async def type(self, text: str) -> bool:
        if not text or self._wlrctl is None:
            return False
        async with self._lock:
            try:
                result = await asyncio.to_thread(
                    subprocess.run, [self._wlrctl, "keyboard", "type", text],
                    capture_output=True, timeout=5, check=False, env=self._env)
            except (OSError, subprocess.TimeoutExpired) as exc:
                logger.warning("panel input: typing failed: %s", exc)
                return False
        if result.returncode != 0:
            logger.warning("panel input: wlrctl could not type (%s)", result.stderr.decode().strip())
            return False
        return True
