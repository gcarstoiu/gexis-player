# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0129: a service's connection, read from the kernel's TCP table."""
from gexis_core import connections

HEADER = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"


def _line(remote: str, state: str, uid: int) -> str:
    return f"   0: 1500A8C0:A1B2 {remote} {state} 00000000:00000000 00:00000000 00000000  {uid}        0 1 1\n"


def test_an_established_connection_off_the_device_by_the_unit_s_user_counts(tmp_path):
    table = tmp_path / "tcp"
    hub = "450200C0:1F9A"  # 192.0.2.69:8090
    table.write_text(HEADER + _line(hub, "01", 990))
    assert connections.established(990, (table,)) is True
    assert connections.established(991, (table,)) is False, "another user's connection"


def test_listening_closing_and_loopback_do_not_count(tmp_path):
    v4, v6 = tmp_path / "tcp", tmp_path / "tcp6"
    v4.write_text(HEADER + _line("450200C0:1F9A", "0A", 990)  # listening
                  + _line("450200C0:1F9A", "06", 990)  # time wait
                  + _line("0100007F:1F9A", "01", 990))  # 127.0.0.1
    v6.write_text(HEADER + _line("00000000000000000000000001000000:1F9A", "01", 990)
                  + _line("0000000000000000FFFF00000100007F:1F9A", "01", 990))
    assert connections.established(990, (v4, v6, tmp_path / "missing")) is False
    v6.write_text(HEADER + _line("0000000000000000FFFF0000450200C0:1F9A", "01", 990))
    assert connections.established(990, (v4, v6)) is True


def test_the_reading_goes_from_connecting_to_not_connected_after_the_grace():
    assert connections.reading("active", True, 500) == ("ok", "Connected")
    assert connections.reading("active", False, 5) == ("wait", "Connecting")
    assert connections.reading("activating", False, 0) == ("wait", "Connecting")
    assert connections.reading("active", False, connections.GRACE_S + 1) == ("bad", "Not connected")
    assert connections.reading("failed", False, 0) == ("bad", "Not connected")


def test_a_sandboxed_plugin_s_uid_is_its_running_process_s(tmp_path, monkeypatch):
    """ADR-0174: a catalogue plugin runs as a temporary user, so `User=` is
    empty; its uid is read from its main process. Root and a stopped unit
    give none."""
    shown = {"User": "", "MainPID": "4242"}
    monkeypatch.setattr(connections, "_show", lambda unit, prop: shown[prop])
    (tmp_path / "4242").mkdir()
    (tmp_path / "4242" / "status").write_text("Name:\trun\nUid:\t61523\t61523\t61523\t61523\n")
    assert connections.unit_uid("gexis-uploaded-service@beszel.service", tmp_path) == 61523
    (tmp_path / "4242" / "status").write_text("Uid:\t0\t0\t0\t0\n")
    assert connections.unit_uid("gexis-uploaded-service@beszel.service", tmp_path) is None
    shown["MainPID"] = "0"
    assert connections.unit_uid("gexis-uploaded-service@beszel.service", tmp_path) is None
