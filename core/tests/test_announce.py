# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0142: the player announces for its plugins - checked, written as avahi
service files under the Pi's own name, withdrawn when the plugin goes."""
from __future__ import annotations

from pathlib import Path

import pytest

from gexis_core import announce, plugin_server

FILES = Path(__file__).resolve().parents[2] / "image" / "stage-gexis" / "03-core" / "files"


def test_a_service_is_written_under_the_pis_own_name_and_withdrawn(tmp_path):
    services = announce.checked([{"type": "_radio-foo._tcp", "port": 8183,
                                  "txt": {"Name": "Sofa & Co", "path": "/x"}}], "SofaPi")
    announce.write("radio", services, tmp_path)
    text = (tmp_path / "gexis-plugin-radio.service").read_text()
    assert "<name>SofaPi</name>" in text and "<type>_radio-foo._tcp</type>" in text
    assert "<port>8183</port>" in text and "<txt-record>Name=Sofa &amp; Co</txt-record>" in text
    # No host-name element: avahi publishes it under the Pi's own.
    assert "host-name" not in text
    announce.withdraw("radio", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_several_services_go_in_several_files_and_an_empty_list_withdraws(tmp_path):
    two = announce.checked([{"type": "_a._tcp", "port": 1}, {"type": "_b._udp", "port": 2, "name": "B"}], "P")
    announce.write("x", two, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["gexis-plugin-x.1.service", "gexis-plugin-x.service"]
    announce.write("x", two[:1], tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["gexis-plugin-x.service"]
    announce.write("x", [], tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_the_core_clears_every_plugins_announcement_and_nothing_else(tmp_path):
    (tmp_path / "gexis-plugin-a.service").write_text("x")
    (tmp_path / "gexis-plugin-a.1.service").write_text("x")
    (tmp_path / "gexis-player.service").write_text("ours")
    announce.clear(tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["gexis-player.service"]


@pytest.mark.parametrize("services, why", [
    ("x", "not a list"),
    ([{"type": "_a._tcp", "port": 1}] * 5, "at most 4"),
    ([{"type": "a._tcp", "port": 1}], "is not _name"),
    ([{"type": "_gexis._tcp", "port": 1}], "player's own"),
    ([{"type": "_smb._tcp", "port": 445}], "player's own"),
    ([{"type": "_a._tcp", "port": 0}], "not 1-65535"),
    ([{"type": "_a._tcp", "port": True}], "not 1-65535"),
    ([{"type": "_a._tcp", "port": 1, "name": "n" * 64}], "63 bytes"),
    ([{"type": "_a._tcp", "port": 1, "txt": {"bad key": "v"}}], "txt key"),
    ([{"type": "_a._tcp", "port": 1, "txt": {"k": "v" * 300}}], "255 bytes"),
    ([{"type": "_a._tcp", "port": 1, "txt": {f"k{i}": "v" for i in range(21)}}], "at most 20"),
])
def test_what_is_refused(services, why):
    with pytest.raises(announce.Refused, match=why):
        announce.checked(services, "P")


def test_announce_is_an_event_plugins_may_send():
    assert "announce" in plugin_server.EVENTS


def test_uploaded_plugins_may_not_answer_mdns_themselves():
    for unit in ("gexis-uploaded-renderer@.service", "gexis-uploaded-service@.service"):
        text = (FILES / unit).read_text()
        assert "SocketBindDeny=ipv4:udp:5353" in text and "SocketBindDeny=ipv6:udp:5353" in text


def test_an_empty_list_withdraws_every_numbered_file_too(tmp_path):
    # Finding 125 #18: three services, then [] while still connected - the
    # second and third must go as well, not only the plain file.
    three = announce.checked([{"type": "_a._tcp", "port": 1}, {"type": "_b._tcp", "port": 2},
                              {"type": "_c._tcp", "port": 3}], "P")
    announce.write("x", three, tmp_path)
    assert len(list(tmp_path.iterdir())) == 3
    announce.write("x", [], tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_long_device_name_is_cut_to_avahis_63_bytes_not_refused():
    # Finding 125 #20: the device name has no length limit; when it is the
    # default it is cut at a character boundary, never the reason to refuse.
    long = "Wohnzimmer Regal links neben dem Fernseher und der großen Standuhr"
    [s] = announce.checked([{"type": "_a._tcp", "port": 1}], long)
    assert len(s["name"].encode()) <= 63 and long.startswith(s["name"])
    cyrillic = "Гостиная" * 5  # 40 characters, 80 bytes
    [s] = announce.checked([{"type": "_a._tcp", "port": 1}], cyrillic)
    assert len(s["name"].encode()) <= 63 and cyrillic.startswith(s["name"])
    assert s["name"] == cyrillic[:31]  # 62 bytes; the 32nd character would make 64


def test_a_plugins_own_name_is_measured_in_bytes():
    # Finding 125 #20: 40 Cyrillic characters pass a character count but are
    # 80 bytes, which avahi cannot register - refused with the reason logged.
    with pytest.raises(announce.Refused, match="63 bytes"):
        announce.checked([{"type": "_a._tcp", "port": 1, "name": "Ж" * 40}], "P")
    [s] = announce.checked([{"type": "_a._tcp", "port": 1, "name": "Ж" * 31}], "P")
    assert s["name"] == "Ж" * 31


def test_a_name_that_cannot_be_written_as_utf8_is_refused():
    # A lone surrogate survives json.loads; it is refused, not a crash.
    with pytest.raises(announce.Refused, match="63 bytes"):
        announce.checked([{"type": "_a._tcp", "port": 1, "name": "a\ud800"}], "P")
