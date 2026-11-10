"""ADR-0170: a plugin asks for permissions in its manifest; the player grants
exactly what it asked for and its person agreed to, with a drop-in under
/run written at every start."""
from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from gexis_core import plugin_permissions as pp
from gexis_core import outputs, plugins, uploads


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


# ADR-0172: Roon Bridge's one card, by its name.

def _asound(tmp_path, cards):
    asound = tmp_path / "asound"
    asound.mkdir()
    for name, index in cards.items():
        (asound / f"card{index}").mkdir()
        (asound / name).symlink_to(f"card{index}")
    return asound


def test_the_roon_card_is_found_by_its_name(tmp_path):
    asound = _asound(tmp_path, {"Loopback": 2, "Multiroom": 3, "Roon": 5})
    assert pp.card_nodes("Roon", asound) == (
        "/dev/snd/controlC5", "/dev/snd/pcmC5D0p", "/dev/snd/timer")


def test_a_card_not_loaded_grants_nothing(tmp_path):
    asound = _asound(tmp_path, {"Loopback": 2})
    assert pp.card_nodes("Roon", asound) == ()
    text = pp.card_dropin(())
    assert "DevicePolicy=closed" in text and "rw" not in text


def test_the_card_dropin_is_written_once_and_again_when_the_card_moves(tmp_path):
    asound = _asound(tmp_path, {"Roon": 5})
    root = tmp_path / "run"
    unit = "gexis-roonbridge.service"
    assert pp.apply_card(unit, "Roon", root, asound) == [unit]
    text = (root / f"{unit}.d" / pp.CARD_DROPIN).read_text()
    assert "DeviceAllow=/dev/snd/pcmC5D0p rw" in text and "DeviceAllow=\n" in text
    assert pp.apply_card(unit, "Roon", root, asound) == []
    (asound / "Roon").unlink()
    (asound / "card6").mkdir()
    (asound / "Roon").symlink_to("card6")
    assert pp.apply_card(unit, "Roon", root, asound) == [unit]
    assert "pcmC6D0p" in (root / f"{unit}.d" / pp.CARD_DROPIN).read_text()


def test_no_plugin_reaches_the_audio_chain_s_control_ports():
    """The review of 1.16.1: CamillaDSP's and Snapcast's control ports take
    orders from whoever reaches them; a plugin rewrote the equaliser's
    configuration through them. They listen on a loopback address of their
    own, which plugins' units are denied - 127.0.0.1, where the player's API
    is open to plugins, stays theirs."""
    assert outputs.CONTROL_HOST.startswith("127.") and outputs.CONTROL_HOST != "127.0.0.1"
    files = Path(__file__).resolve().parents[2] / "image/stage-gexis/03-core/files"
    for unit in ("gexis-uploaded-service@.service", "gexis-uploaded-renderer@.service"):
        lines = (files / unit).read_text().splitlines()
        assert f"IPAddressDeny={outputs.CONTROL_HOST}" in lines, unit
        assert not any(l.startswith("IPAddressAllow") for l in lines), unit
