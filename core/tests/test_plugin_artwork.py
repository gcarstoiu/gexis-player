# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0167 T9: a cover a plugin hands over as bytes, kept and served."""
import base64

import pytest

from gexis_core.plugin_artwork import KEPT, MOST_BYTES, PluginArtwork, Refused, key_of

JPEG = b"\xff\xd8\xff\xe0" + b"jpeg body"
PNG = b"\x89PNG\r\n\x1a\n" + b"png body"


def event(data: bytes, kind: str = "image/jpeg") -> dict:
    return {"t": "artwork", "type": kind, "data": base64.b64encode(data).decode()}


def test_a_cover_is_kept_under_its_key():
    art = PluginArtwork()
    key = art.put("airplay", event(JPEG))
    assert key == key_of(JPEG) and len(key) == 16
    assert art.get("airplay", key) == ("image/jpeg", JPEG)
    assert art.get("plexamp", key) is None


def test_only_the_last_two_are_kept():
    art = PluginArtwork()
    keys = [art.put("airplay", event(JPEG + bytes([i]))) for i in range(KEPT + 1)]
    assert art.get("airplay", keys[0]) is None
    assert all(art.get("airplay", k) for k in keys[1:])


@pytest.mark.parametrize("message", [
    {"type": "image/gif", "data": base64.b64encode(JPEG).decode()},
    {"type": "image/jpeg", "data": "not base64!"},
    {"type": "image/jpeg"},
    event(PNG, "image/jpeg"),
    event(b"\xff\xd8\xff" + b"x" * MOST_BYTES),
])
def test_what_is_not_a_cover_is_refused(message):
    with pytest.raises(Refused):
        PluginArtwork().put("airplay", message)


def test_a_disconnected_plugin_takes_its_covers_with_it():
    art = PluginArtwork()
    key = art.put("airplay", event(PNG, "image/png"))
    art.forget("airplay")
    assert art.get("airplay", key) is None


async def test_the_route_serves_it():
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    art = PluginArtwork()
    key = art.put("airplay", event(PNG, "image/png"))
    server = StateServer(StateStore({}), plugin_artwork=art)
    async with TestClient(TestServer(server.make_app())) as client:
        served = await client.get(f"/plugins/airplay/artwork/{key}")
        assert served.status == 200
        assert served.content_type == "image/png" and await served.read() == PNG
        assert "immutable" in served.headers["Cache-Control"]
        assert (await client.get("/plugins/airplay/artwork/0000000000000000")).status == 404
        assert (await client.get(f"/plugins/plexamp/artwork/{key}")).status == 404
