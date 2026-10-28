# SPDX-License-Identifier: GPL-3.0-or-later
"""**A plugin's cover, handed over as bytes** (ADR-0167 T9; the contract's
`artwork` event, added within version 1).

A renderer whose covers arrive as pictures rather than addresses - AirPlay's
come from the Apple device - sends each one in an `artwork` event; the core
keeps the last two per plugin in memory and serves them at
`/plugins/<id>/artwork/<key>`, the key being the first 16 hexadecimal digits
of the picture's sha256. The plugin names that path as its metadata's
`artwork`, so the screens fetch it from the player as they fetch any cover.

In memory only: a cover lasts as long as the plugin's connection, and a
restart of the core forgets them, as it forgets what the plugin said.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

TYPES = ("image/jpeg", "image/png")
#: The picture itself, decoded; the line carrying it is already bounded at
#: 1 MiB by the plugin server.
MOST_BYTES = 1024 * 1024
#: The cover on screen and the one before it, so a screen that has not yet
#: fetched the new one still finds the old.
KEPT = 2


class Refused(ValueError):
    pass


def key_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


class PluginArtwork:
    def __init__(self) -> None:
        self._kept: dict[str, OrderedDict[str, tuple[str, bytes]]] = {}

    def put(self, plugin_id: str, message: dict) -> str:
        """Keep one event's picture; its key. Refused whole when it is not
        a JPEG or PNG within the size."""
        kind = message.get("type")
        if kind not in TYPES:
            raise Refused(f"type {kind!r} is not one of {', '.join(TYPES)}")
        encoded = message.get("data")
        if not isinstance(encoded, str) or not encoded:
            raise Refused("no data")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise Refused("data is not base64") from None
        if len(data) > MOST_BYTES:
            raise Refused(f"{len(data)} bytes, more than {MOST_BYTES}")
        signature = b"\xff\xd8\xff" if kind == "image/jpeg" else b"\x89PNG\r\n\x1a\n"
        if not data.startswith(signature):
            raise Refused(f"the data is not a {kind}")
        key = key_of(data)
        kept = self._kept.setdefault(plugin_id, OrderedDict())
        kept[key] = (kind, data)
        kept.move_to_end(key)
        while len(kept) > KEPT:
            kept.popitem(last=False)
        return key

    def get(self, plugin_id: str, key: str) -> tuple[str, bytes] | None:
        return self._kept.get(plugin_id, {}).get(key)

    def forget(self, plugin_id: str) -> None:
        self._kept.pop(plugin_id, None)
