"""ADR-0170: a plugin asks for permissions in its manifest; the player grants
exactly what it asked for and its person agreed to, with a drop-in under
/run written at every start."""
from __future__ import annotations

import io
import json
import tarfile

import pytest

from gexis_core import plugin_permissions as pp
from gexis_core import plugins, uploads


def test_a_manifest_asks_only_for_what_the_player_knows():
    assert pp.parse(None) == ()
    assert pp.parse(["usb", "cec"]) == ("cec", "usb")
    for bad in (["root"], "cec", ["cec", "cec"], [1]):
        with pytest.raises(pp.Unknown):
            pp.parse(bad)
    with pytest.raises(plugins.BadManifest, match="does not grant"):
        plugins.parse({"id": "tv", "name": "TV", "kind": "service", "unit": "x.service", "permissions": ["root"]})


def test_the_drop_in_opens_those_devices_and_no_others():
    text = pp.dropin(("cec",))
    assert "PrivateDevices=no" in text and "DevicePolicy=closed" in text
    assert "DeviceAllow=char-cec rw" in text and "SupplementaryGroups=video" in text
    assert "gpiochip" not in text and "usb" not in text
    both = pp.dropin(("gpio", "usb"))
    assert "DeviceAllow=char-gpiochip rw" in both and "DeviceAllow=char-hidraw rw" in both
    assert "char-cec" not in both


def test_apply_writes_what_is_granted_and_removes_the_rest(tmp_path):
    unit = "gexis-uploaded-service@tv.service"
    assert pp.apply({unit: ("cec",)}, root=tmp_path) == [unit]
    path = tmp_path / f"{unit}.d" / pp.DROPIN
    assert "char-cec" in path.read_text()
    # The same again changes nothing, so nothing is reloaded or restarted.
    assert pp.apply({unit: ("cec",)}, root=tmp_path) == []
    assert pp.apply({unit: ()}, root=tmp_path) == [unit] and not path.exists()
    # A plugin removed since: its drop-in goes at the next start.
    pp.apply({unit: ("cec",)}, root=tmp_path)
    assert pp.apply({}, root=tmp_path) == [unit] and not path.exists() and not path.parent.exists()


def _archive(**manifest) -> bytes:
    raw = {"id": "tv", "name": "TV remote", "kind": "service", "version": "0.1.0", "run": "tv.sh", **manifest}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in (("plugin.json", json.dumps(raw).encode()), ("tv.sh", b"#!/bin/sh\n")):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o755
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_a_grant_needs_both_the_manifest_and_the_consent(tmp_path):
    root, known = tmp_path / "plugins", tmp_path / "known.json"
    checked = uploads.install(_archive(permissions=["cec"]), ours=set(), root=root)
    assert checked.permissions == ("cec",)
    unit = uploads.unit_for("tv", "service")
    assert uploads.grants(root=root, path=known) == {unit: ()}
    uploads.grant("tv", ("cec", "usb"), path=known)
    assert uploads.grants(root=root, path=known) == {unit: ("cec",)}
    # Kept with the record a backup carries, through the record's rewrite.
    uploads.remember(root=root, path=known)
    assert uploads.granted(path=known) == {"tv": ("cec", "usb")}


def test_an_upload_asking_for_a_permission_this_player_lacks_is_refused():
    with pytest.raises(uploads.Refused, match="does not grant"):
        uploads.check(_archive(permissions=["root"]), ours=set(), installed={})
