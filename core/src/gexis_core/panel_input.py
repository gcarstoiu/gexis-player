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
- **text and keys** - key presses from a virtual keyboard, as a USB keyboard
  would make them: each character is found on the compositor's own keyboard
  layout (libxkbcommon, with the layout labwc runs with) as a key and the
  Shift or AltGr it needs. `wlrctl keyboard type` was tried first: it types
  ASCII only, and one call per character lost characters - every call makes
  a keyboard of its own, and the first keys after it are dropped (sofapi,
  2026-10-21: "test.user@example.com" arrived as "test.usereaple.co").

Only the panel's own session receives them. The devices are made at the
first use and kept: one made per tap would be added by libinput a moment
after the tap was sent, and the tap lost.
"""
from __future__ import annotations

import asyncio
import ctypes
import ctypes.util
import fcntl
import logging
import struct
import time
from pathlib import Path

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
#: Named keys the phone sends (linux/input-event-codes.h).
KEYS = {"Backspace": 14, "Enter": 28, "Tab": 15}
KEY_LEFTSHIFT, KEY_RIGHTALT = 42, 100
#: Between one key and the next: a burst of events with none is where a
#: client can drop keys.
KEY_GAP_S = 0.012
#: libinput adds a new device a moment after it is made; events before then
#: are dropped silently.
SETTLE_S = 1.0


class _RuleNames(ctypes.Structure):
    _fields_ = [(name, ctypes.c_char_p) for name in ("rules", "model", "layout", "variant", "options")]


def compositor_layout(environ: Path | None = None) -> dict[str, str]:
    """The XKB names labwc runs with: its own environment (`XKB_DEFAULT_*`),
    which is what a keyboard the compositor sees is read with. None set means
    libxkbcommon's defaults - on the image, US (sofapi, 2026-10-21; not the
    console's `/etc/default/keyboard`)."""
    if environ is None:
        for proc in Path("/proc").iterdir():
            try:
                if (proc / "comm").read_text().strip() == "labwc":
                    environ = proc / "environ"
                    break
            except OSError:
                continue
    names: dict[str, str] = {}
    try:
        for entry in environ.read_bytes().split(b"\0") if environ else []:
            key, _, value = entry.decode(errors="replace").partition("=")
            if key.startswith("XKB_DEFAULT_") and value:
                names[key[len("XKB_DEFAULT_"):].lower()] = value
    except OSError:
        pass
    return names


def char_keys(names: dict[str, str] | None = None) -> dict[str, tuple[int, bool, bool]]:
    """Each character the layout can type, as (evdev key, Shift, AltGr) - the
    lowest level that makes it. Empty when libxkbcommon cannot be loaded."""
    path = ctypes.util.find_library("xkbcommon") or "libxkbcommon.so.0"
    try:
        xkb = ctypes.CDLL(path)
    except OSError:
        logger.warning("panel input: libxkbcommon not found; text cannot be typed")
        return {}
    xkb.xkb_context_new.restype = ctypes.c_void_p
    xkb.xkb_keymap_new_from_names.restype = ctypes.c_void_p
    xkb.xkb_keymap_new_from_names.argtypes = [ctypes.c_void_p, ctypes.POINTER(_RuleNames), ctypes.c_int]
    for fn in ("xkb_keymap_min_keycode", "xkb_keymap_max_keycode"):
        getattr(xkb, fn).argtypes = [ctypes.c_void_p]
    xkb.xkb_keymap_num_levels_for_key.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
    xkb.xkb_keymap_key_get_syms_by_level.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.POINTER(ctypes.POINTER(ctypes.c_uint32))]
    xkb.xkb_keymap_key_get_mods_for_level.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t]
    xkb.xkb_keymap_mod_get_index.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    xkb.xkb_keysym_to_utf32.restype = ctypes.c_uint32
    xkb.xkb_keymap_unref.argtypes = [ctypes.c_void_p]
    xkb.xkb_context_unref.argtypes = [ctypes.c_void_p]

    names = compositor_layout() if names is None else names
    rule = _RuleNames(*(names.get(k, "").encode() or None for k in ("rules", "model", "layout", "variant", "options")))
    context = xkb.xkb_context_new(0)
    keymap = xkb.xkb_keymap_new_from_names(context, ctypes.byref(rule), 0) if context else None
    if not keymap:
        logger.warning("panel input: no keymap for %s; text cannot be typed", names or "the defaults")
        if context:
            xkb.xkb_context_unref(context)
        return {}
    shift = 1 << xkb.xkb_keymap_mod_get_index(keymap, b"Shift")
    altgr = 1 << xkb.xkb_keymap_mod_get_index(keymap, b"Mod5")
    found: dict[str, tuple[int, bool, bool]] = {}
    for keycode in range(xkb.xkb_keymap_min_keycode(keymap), xkb.xkb_keymap_max_keycode(keymap) + 1):
        evdev = keycode - 8
        if not 0 < evdev < 248:
            continue
        for level in range(xkb.xkb_keymap_num_levels_for_key(keymap, keycode, 0)):
            syms = ctypes.POINTER(ctypes.c_uint32)()
            count = xkb.xkb_keymap_key_get_syms_by_level(keymap, keycode, 0, level, ctypes.byref(syms))
            masks = (ctypes.c_uint32 * 8)()
            nmasks = xkb.xkb_keymap_key_get_mods_for_level(keymap, keycode, 0, level, masks, 8)
            mask = min((masks[i] for i in range(nmasks)), default=None)
            if mask is None or mask & ~(shift | altgr):
                continue
            for i in range(count):
                point = xkb.xkb_keysym_to_utf32(syms[i])
                if point >= 32 and point != 127:
                    found.setdefault(chr(point), (evdev, bool(mask & shift), bool(mask & altgr)))
    xkb.xkb_keymap_unref(keymap)
    xkb.xkb_context_unref(context)
    return found


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

    def __init__(self, *, runtime_dir: str = "", wayland_display: str = "") -> None:
        #: Read at the first text, once labwc runs (`char_keys`).
        self._chars: dict[str, tuple[int, bool, bool]] | None = None
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
            # Every key a layout can put a character on, and the modifiers.
            self._keys = _Device(b"gexis-phone-keys", list(range(1, 248)))
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

    def _press(self, code: int, shift: bool = False, altgr: bool = False) -> None:
        keys = self._keys
        for mod, on in ((KEY_LEFTSHIFT, shift), (KEY_RIGHTALT, altgr)):
            if on:
                keys.emit(EV_KEY, mod, 1)
        keys.emit(EV_KEY, code, 1)
        keys.sync()
        keys.emit(EV_KEY, code, 0)
        for mod, on in ((KEY_LEFTSHIFT, shift), (KEY_RIGHTALT, altgr)):
            if on:
                keys.emit(EV_KEY, mod, 0)
        keys.sync()

    async def key(self, name: str) -> bool:
        code = KEYS.get(name)
        if code is None:
            return False
        async with self._lock:
            await self._devices()
            self._press(code)
        return True

    async def type(self, text: str) -> bool:
        """Each character as its key on the compositor's layout; False when
        one of them is not on it (it is left out, the rest typed)."""
        if not text:
            return False
        if self._chars is None:
            self._chars = await asyncio.to_thread(char_keys)
        whole = True
        async with self._lock:
            await self._devices()
            for char in text:
                if char == "\n":
                    found = (KEYS["Enter"], False, False)
                elif char == "\t":
                    found = (KEYS["Tab"], False, False)
                else:
                    found = self._chars.get(char)
                if found is None:
                    whole = False
                    logger.info("panel input: %r is not on the panel's keyboard layout", char)
                    continue
                self._press(*found)
                await asyncio.sleep(KEY_GAP_S)
        return whole
