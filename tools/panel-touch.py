#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A synthetic finger for the panel, through the kernel.

**Why not the DevTools protocol.** Touches synthesised with
`Input.dispatchTouchEvent` are delivered straight to the renderer, around the
browser's own gesture pipeline: every frame in Finding 032 came back
`SCROLL_MAIN_THREAD`, so the harness may have produced the stutter it was
measuring. `Input.synthesizeScrollGesture`, which does use that pipeline,
scrolled nothing in this layout.

This writes to `/dev/uinput` instead. The events go kernel -> libinput ->
labwc -> Chromium, which is the path a finger takes, so what is measured
afterwards is the panel rather than the harness.

Run **on the device, as root** (`/dev/uinput` is root-only):

    sudo python3 panel-touch.py tap 640 400
    sudo python3 panel-touch.py swipe 1100 300 200 300 --ms 400

The panel reports every touch to the daemon (`POST /touch`, ADR-0036), so
the core's journal is an oracle for "did this reach Chromium at all".
"""
from __future__ import annotations

import argparse
import fcntl
import struct
import sys
import time

UINPUT = "/dev/uinput"

# linux/input-event-codes.h
EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
SYN_REPORT = 0
BTN_TOUCH = 0x14A
ABS_X, ABS_Y = 0x00, 0x01
ABS_MT_SLOT = 0x2F
ABS_MT_POSITION_X, ABS_MT_POSITION_Y = 0x35, 0x36
ABS_MT_TRACKING_ID = 0x39
INPUT_PROP_DIRECT = 0x01

# linux/uinput.h: _IOW(UINPUT_IOCTL_BASE='U', n, int) and _IO('U', n)
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_ABSBIT = 0x40045567
UI_SET_PROPBIT = 0x4004556E
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502

ABS_CNT = 64

#: The panel. Coordinates are its pixels, because `INPUT_PROP_DIRECT` plus a
#: range matching the mode makes libinput map them 1:1 onto the output.
WIDTH, HEIGHT = 1280, 800


class Touchscreen:
    """A multitouch device of the same shape as the panel's own WaveShare
    (type B: slots and tracking ids), so libinput handles it the same way."""

    def __init__(self, width: int = WIDTH, height: int = HEIGHT) -> None:
        self.width, self.height = width, height
        self._fd = open(UINPUT, "wb", buffering=0)
        for ev in (EV_KEY, EV_ABS):
            fcntl.ioctl(self._fd, UI_SET_EVBIT, ev)
        fcntl.ioctl(self._fd, UI_SET_KEYBIT, BTN_TOUCH)
        for axis in (ABS_X, ABS_Y, ABS_MT_SLOT, ABS_MT_POSITION_X,
                     ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID):
            fcntl.ioctl(self._fd, UI_SET_ABSBIT, axis)
        # Without this libinput treats the device as a touchpad - relative
        # pointer motion - instead of a screen you touch directly.
        fcntl.ioctl(self._fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT)

        absmax = [0] * ABS_CNT
        for axis in (ABS_X, ABS_MT_POSITION_X):
            absmax[axis] = width - 1
        for axis in (ABS_Y, ABS_MT_POSITION_Y):
            absmax[axis] = height - 1
        absmax[ABS_MT_SLOT] = 9
        absmax[ABS_MT_TRACKING_ID] = 65535
        # struct uinput_user_dev: name, input_id, ff_effects_max, then the
        # four per-axis arrays. The legacy setup path, which needs no
        # further ioctl structs.
        payload = struct.pack(
            "80sHHHHi",
            b"gexis-panel-touch",
            0x03,  # BUS_USB - what a panel controller reports
            0x1234, 0x5678, 1,
            0,
        )
        payload += struct.pack(f"{ABS_CNT}i", *absmax)
        payload += struct.pack(f"{ABS_CNT}i", *([0] * ABS_CNT))   # absmin
        payload += struct.pack(f"{ABS_CNT}i", *([0] * ABS_CNT))   # absfuzz
        payload += struct.pack(f"{ABS_CNT}i", *([0] * ABS_CNT))   # absflat
        self._fd.write(payload)
        fcntl.ioctl(self._fd, UI_DEV_CREATE)
        # libinput adds the device asynchronously; events sent before the
        # compositor has it are dropped silently.
        time.sleep(1.0)

    def close(self) -> None:
        try:
            fcntl.ioctl(self._fd, UI_DEV_DESTROY)
        finally:
            self._fd.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # --- events ------------------------------------------------------------

    def _emit(self, type_: int, code: int, value: int) -> None:
        now = time.time()
        self._fd.write(struct.pack(
            "qqHHi", int(now), int((now % 1) * 1e6), type_, code, value))

    def _sync(self) -> None:
        self._emit(EV_SYN, SYN_REPORT, 0)

    def _down(self, x: int, y: int, tracking_id: int) -> None:
        self._emit(EV_ABS, ABS_MT_SLOT, 0)
        self._emit(EV_ABS, ABS_MT_TRACKING_ID, tracking_id)
        self._emit(EV_ABS, ABS_MT_POSITION_X, x)
        self._emit(EV_ABS, ABS_MT_POSITION_Y, y)
        self._emit(EV_KEY, BTN_TOUCH, 1)
        self._emit(EV_ABS, ABS_X, x)
        self._emit(EV_ABS, ABS_Y, y)
        self._sync()

    def _move(self, x: int, y: int) -> None:
        self._emit(EV_ABS, ABS_MT_SLOT, 0)
        self._emit(EV_ABS, ABS_MT_POSITION_X, x)
        self._emit(EV_ABS, ABS_MT_POSITION_Y, y)
        self._emit(EV_ABS, ABS_X, x)
        self._emit(EV_ABS, ABS_Y, y)
        self._sync()

    def _up(self) -> None:
        self._emit(EV_ABS, ABS_MT_SLOT, 0)
        self._emit(EV_ABS, ABS_MT_TRACKING_ID, -1)
        self._emit(EV_KEY, BTN_TOUCH, 0)
        self._sync()

    # --- gestures ----------------------------------------------------------

    def tap(self, x: int, y: int, hold_ms: int = 60) -> None:
        self._down(x, y, 1)
        time.sleep(hold_ms / 1000)
        self._up()

    def swipe(self, x0: int, y0: int, x1: int, y1: int, ms: int = 400,
              steps: int = 0) -> None:
        """One finger, moved in steps paced to the panel's 60 Hz: a scroll is
        only a scroll if the compositor sees motion across many frames."""
        steps = steps or max(2, round(ms / 16.7))
        self._down(x0, y0, 1)
        for i in range(1, steps + 1):
            f = i / steps
            self._move(round(x0 + (x1 - x0) * f), round(y0 + (y1 - y0) * f))
            time.sleep(ms / 1000 / steps)
        self._up()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="what", required=True)

    tap = sub.add_parser("tap")
    tap.add_argument("x", type=int)
    tap.add_argument("y", type=int)

    swipe = sub.add_parser("swipe")
    swipe.add_argument("x0", type=int)
    swipe.add_argument("y0", type=int)
    swipe.add_argument("x1", type=int)
    swipe.add_argument("y1", type=int)
    swipe.add_argument("--ms", type=int, default=400)

    args = parser.parse_args()
    with Touchscreen() as screen:
        if args.what == "tap":
            screen.tap(args.x, args.y)
        else:
            screen.swipe(args.x0, args.y0, args.x1, args.y1, ms=args.ms)
        # Let the events drain before the device disappears.
        time.sleep(0.3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
