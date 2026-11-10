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
                "home/pi/Library/Caches/x", "home/pi/.cache/Plexamp/x",
                "var/lib/squeezeboxserver/prefs/server.prefs", "var/lib/gexis-music/Album/track.flac",
                "var/lib/gexis-music/Playlists/Evening.m3u", "var/lib/bluetooth/DC:A6:32:00:00:01/settings",
                "etc/NetworkManager/system-connections/HomeNet.nmconnection",
                "var/log/journal/abc/system.journal", "var/lib/gexis/plugins/qobuz/current",
                "var/lib/gexis-kiosk/Default/Cookies", "var/lib/gexis-kiosk/Default/Local Storage/leveldb/000003.log"):
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
    for gone in ("var/lib/gexis-core/settings.db", "etc/gexis/device-name.env",
                 "etc/machine-info", "var/lib/gexis/setup-done", "var/lib/gexis/screen.json",
                 "etc/gexis/screen.env", "var/lib/gexis/components", "var/lib/go-librespot/state.json",
                 "var/lib/beszel-agent", "home/pi/.local/share/Plexamp", "home/pi/plexamp",
                 "home/pi/Library", "home/pi/.cache/Plexamp",
                 "var/lib/squeezeboxserver/prefs", "var/lib/gexis/plugins"):
        assert not (tmp_path / gone).exists(), gone
    # The owner's music, playlists and pictures stay (ADR-0132 as amended).
    for kept in ("var/lib/gexis-music/Album/track.flac", "var/lib/gexis-music/Playlists/Evening.m3u",
                 "var/lib/gexis-core/pictures/beach.jpg"):
        assert (tmp_path / kept).is_file(), kept
    # The backups go, their folder stays: it is the Backups share, made
    # `pi`'s by gexis-core's postinst, and recreated by root it refused
    # every copy into the share (the review of 2026-10-12).
    for emptied in ("var/lib/bluetooth", "etc/NetworkManager/system-connections",
                    "var/log/journal", "var/lib/gexis-core/backups",
                    # The panel browser's profile: cookies, storage and cache
                    # of every page it showed (the review of 2026-10-12).
                    "var/lib/gexis-kiosk"):
        assert (tmp_path / emptied).is_dir() and not any((tmp_path / emptied).iterdir()), emptied
    assert (tmp_path / "etc/hostname").read_text() == "raspberrypi\n"
    assert "127.0.1.1\traspberrypi" in (tmp_path / "etc/hosts").read_text()
    # Nothing of the reset's own boot is kept on the card: the temporary
    # drop-in of 2026-10-10 went before the first public release (ADR-0132).
    assert not (tmp_path / "etc/systemd/journald.conf.d").exists()
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


async def test_a_refused_restart_is_asked_again_until_it_is_taken():
    """The bar player, 2026-10-10: a pack install's shutdown block made
    systemd refuse setup's restart; asked again, it goes through."""
    from gexis_core.__main__ import _systemctl_reboot

    answers = [(1, b"Call to Reboot failed: Access denied")] * 3 + [(0, b"")]
    calls, slept = [], []

    class Proc:
        def __init__(self, code, out):
            self.returncode, self._out = code, out

        async def communicate(self):
            return self._out, None

    async def exec_(*argv, **_):
        calls.append(argv)
        return Proc(*answers[len(calls) - 1])

    async def sleep(s):
        slept.append(s)

    assert await _systemctl_reboot(retry_s=15, give_up_s=600, exec_=exec_, sleep=sleep) is True
    assert len(calls) == 4 and slept == [15, 15, 15]


async def test_a_restart_refused_for_too_long_gives_up():
    from gexis_core.__main__ import _systemctl_reboot

    class Proc:
        returncode = 1

        async def communicate(self):
            return b"Access denied", None

    async def exec_(*argv, **_):
        return Proc()

    async def sleep(s):
        pass

    assert await _systemctl_reboot(retry_s=15, give_up_s=45, exec_=exec_, sleep=sleep) is False


def test_the_settings_chosen_at_flash_time_go(tmp_path):
    """George, 2026-10-12, answer 4: firstrun.sh's `SETTINGS`, read as
    defaults at every start, do not survive a reset."""
    seed = tmp_path / "etc/gexis/settings-seed.json"
    seed.parent.mkdir(parents=True)
    seed.write_text('{"idle_timeout": 10}\n')
    factory_reset.wipe(tmp_path)
    assert not seed.exists()


def test_core_toml_goes_back_to_the_images_copy(tmp_path):
    """The flash-time `idle_url` firstrun.sh appended is gone; the file is
    the one gexis-core installs, byte for byte."""
    shipped = Path(__file__).resolve().parents[2] / "image/stage-gexis/03-core/files/core.toml"
    default = tmp_path / factory_reset.DEFAULT_CORE_TOML
    default.parent.mkdir(parents=True)
    default.write_bytes(shipped.read_bytes())
    target = tmp_path / factory_reset.CORE_TOML
    target.parent.mkdir(parents=True)
    target.write_bytes(shipped.read_bytes() + b'\nidle_url = "https://example.invalid/display/1"\n')
    done = factory_reset.wipe(tmp_path)
    assert target.read_bytes() == shipped.read_bytes()
    assert factory_reset.CORE_TOML in done
    assert (target.stat().st_mode & 0o777) == 0o644
    # And the core reads the code's defaults from it.
    from gexis_core.config import Config
    assert Config.load(target) == Config()


def test_core_toml_without_the_images_copy_is_removed(tmp_path):
    """No copy to go back to: without the file the core reads its defaults,
    which is what the image's copy amounts to."""
    target = tmp_path / factory_reset.CORE_TOML
    target.parent.mkdir(parents=True)
    target.write_text('idle_url = "https://example.invalid/display/1"\n')
    factory_reset.wipe(tmp_path)
    assert not target.exists()


def test_the_images_copy_is_where_gexis_core_installs_it():
    """`DEFAULT_CORE_TOML` is the package's path, not a guess."""
    build = (Path(__file__).resolve().parents[2] / "packaging/core/build.sh").read_text()
    assert f'"$STAGE/{factory_reset.DEFAULT_CORE_TOML}"' in build


def _with_a_dsi_panel(root: Path) -> dict:
    """`_used_player` whose screen is the Waveshare 10.1" DSI-TOUCH-A, kept:
    its overlay in config.txt's screen block, beside the board's."""
    from gexis_core import screen_apply
    _used_player(root)
    files = {"state": root / "var/lib/gexis/screen.json", "env": root / "etc/gexis/screen.env",
             "cmdline": root / "boot/firmware/cmdline.txt", "config": root / "boot/firmware/config.txt"}
    screen_apply.choose(screen_apply.Applied("waveshare-dsi-v2-10.1a", 0, "DSI-1"), **files, now=1)
    screen_apply.keep(state=files["state"])
    assert screen_apply.overlays_in(files["config"].read_text()) == ("vc4-kms-dsi-waveshare-panel-v2,10_1_inch_a",)
    return files


def test_the_reset_takes_the_screen_s_block_out_of_config_txt(tmp_path, monkeypatch):
    """The review of 1.16.1: the screen's state files went, its block in
    config.txt (ADR-0158, newer than the reset) stayed - not a freshly
    flashed card (ADR-0132 §3: the screen goes)."""
    from gexis_core import screen_apply, screen_detect
    monkeypatch.setattr(screen_detect, "ports", lambda *a, **k: [])
    files = _with_a_dsi_panel(tmp_path)
    factory_reset.wipe(tmp_path)
    config = files["config"].read_text()
    assert screen_apply.overlays_in(config) == () and screen_apply.CONFIG_BEGIN not in config
    assert "hifiberry" not in config and config == "dtparam=audio=on\n"


def test_the_reset_s_own_boot_lays_the_panel_out_without_a_restart(tmp_path, monkeypatch):
    """The panel is up at this boot - the firmware read the block before the
    wipe - and nothing is chosen, so setup lays it out from its own mode.
    With the block left, that removed it and restarted, and setup ran with
    the panel dark (the review of 1.16.1)."""
    from gexis_core import screen_apply, screen_detect, screen_watch
    monkeypatch.setattr(screen_detect, "ports", lambda *a, **k: [])
    files = _with_a_dsi_panel(tmp_path)
    factory_reset.wipe(tmp_path)
    panel = screen_detect.Seen(True, "DSI-1", preferred=(800, 1280), panel=("goodix",))
    assert screen_watch.during_setup(panel, path=tmp_path / "seen.json", files=files) == "switched"
    assert screen_apply.read_state(files["state"])["current"]["connector"] == "DSI-1"
