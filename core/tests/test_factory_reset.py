"""ADR-0132: reset to factory settings - everything back to a freshly
flashed card, at the start of the next boot."""
from __future__ import annotations

from pathlib import Path

from gexis_core import board_apply, factory_reset


def _used_player(root: Path) -> None:
    def put(rel, text="x"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    for rel in ("var/lib/gexis-core/settings.db", "var/lib/gexis-core/enrichment.db",
                "var/lib/gexis-core/backups/gexis-living-room-20261009-120000.tgz",
                "var/lib/gexis-core/pictures/beach.jpg",
                "etc/gexis/device-name.env", "etc/machine-info", "var/lib/gexis/setup-done",
                "var/lib/gexis/screen.json", "etc/gexis/screen.env", "var/lib/gexis/components/plexamp.sha256",
                "var/lib/go-librespot/state.json", "var/lib/beszel-agent/fingerprint",
                "home/pi/.local/share/Plexamp/Settings/x", "home/pi/plexamp/js/index.js",
                "var/lib/squeezeboxserver/prefs/server.prefs", "var/lib/gexis-music/Album/track.flac",
                "var/lib/gexis-music/Playlists/Evening.m3u", "var/lib/bluetooth/DC:A6:32:00:00:01/settings",
                "etc/NetworkManager/system-connections/HomeNet.nmconnection",
                "var/log/journal/abc/system.journal", "var/lib/gexis/plugins/qobuz/current"):
        put(rel)
    put("etc/hostname", "livingroom\n")
    put("etc/hosts", "127.0.0.1\tlocalhost\n127.0.1.1\tlivingroom\n")
    put("var/lib/go-librespot/config.yml", "log_level: info\ndevice_name: Living Room\n")
    put("boot/firmware/cmdline.txt",
        "console=tty3 root=PARTUUID=abcd-02 rootwait quiet splash cfg80211.ieee80211_regdom=DE "
        "video=HDMI-A-1:320x1480,panel_orientation=left_side_up\n")
    put("boot/firmware/config.txt", "dtparam=audio=on\n[all]\n" + board_apply.BEGIN
        + "\ndtoverlay=hifiberry-dacplushd\n" + board_apply.END + "\n")
    (root / "usr/share/zoneinfo/Europe").mkdir(parents=True)
    (root / "usr/share/zoneinfo/Europe/London").write_text("tz")


def test_a_used_player_goes_back_to_a_freshly_flashed_card(tmp_path):
    _used_player(tmp_path)
    factory_reset.wipe(tmp_path)
    for gone in ("var/lib/gexis-core/settings.db", "var/lib/gexis-core/backups", "etc/gexis/device-name.env",
                 "etc/machine-info", "var/lib/gexis/setup-done", "var/lib/gexis/screen.json",
                 "etc/gexis/screen.env", "var/lib/gexis/components", "var/lib/go-librespot/state.json",
                 "var/lib/beszel-agent", "home/pi/.local/share/Plexamp", "home/pi/plexamp",
                 "var/lib/squeezeboxserver/prefs", "var/lib/gexis/plugins"):
        assert not (tmp_path / gone).exists(), gone
    # The owner's music, playlists and pictures stay (ADR-0132 as amended).
    for kept in ("var/lib/gexis-music/Album/track.flac", "var/lib/gexis-music/Playlists/Evening.m3u",
                 "var/lib/gexis-core/pictures/beach.jpg"):
        assert (tmp_path / kept).is_file(), kept
    for emptied in ("var/lib/bluetooth", "etc/NetworkManager/system-connections",
                    "var/log/journal"):
        assert (tmp_path / emptied).is_dir() and not any((tmp_path / emptied).iterdir()), emptied
    assert (tmp_path / "etc/hostname").read_text() == "raspberrypi\n"
    assert "127.0.1.1\traspberrypi" in (tmp_path / "etc/hosts").read_text()
    # TEMPORARY (journal.AFTER_RESET): the reset's own boot is kept on the card.
    kept = (tmp_path / "etc/systemd/journald.conf.d/61-gexis-after-reset.conf").read_text()
    assert "Storage=persistent" in kept and "TEMPORARY" in kept
    assert "device_name: gexis" in (tmp_path / "var/lib/go-librespot/config.yml").read_text()
    assert (tmp_path / "etc/timezone").read_text() == "Europe/London\n"
    cmdline = (tmp_path / "boot/firmware/cmdline.txt").read_text()
    assert "video=" not in cmdline and "regdom" not in cmdline and "root=PARTUUID=abcd-02" in cmdline
    config = (tmp_path / "boot/firmware/config.txt").read_text()
    assert "hifiberry" not in config and config.startswith("dtparam=audio=on")


def test_the_request_is_what_settings_writes(tmp_path):
    request = tmp_path / "var/lib/gexis/factory-reset"
    factory_reset.request(request)
    assert request.exists()


def test_a_step_that_fails_does_not_stop_the_rest(tmp_path, monkeypatch):
    _used_player(tmp_path)
    (tmp_path / "boot/firmware/cmdline.txt").unlink()
    done = factory_reset.wipe(tmp_path)
    assert "hostname" in done and not (tmp_path / "var/lib/gexis-core/settings.db").exists()


def test_the_reset_is_on_the_state_for_every_screen():
    """George, 2026-10-09: the panel and every phone show that the player is
    being reset - not only the phone that confirmed it."""
    from gexis_core.state import StateStore

    store = StateStore({})
    seen = []
    store.subscribe(lambda state: seen.append(state.to_json()["resetting"]))
    assert store.state.to_json()["resetting"] is False
    store.set_resetting()
    store.set_resetting()
    assert store.state.resetting is True and seen == [True]
