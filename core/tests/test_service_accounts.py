"""ADR-0179: the music services under accounts of their own, not `pi`'s.

`pi` is the screen's user: the panel's token, the kiosk's runtime folder,
its compositor's socket and Chromium are in reach of every process running
as `pi` (the review of 1.16.1). The services that take data from the
network run as accounts of their own, each made by its package."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "image" / "stage-gexis"

#: Unit, its account, whether it opens a sound device.
UNITS = {
    "02-renderers/files/squeezelite.service": ("gexis-squeezelite", True),
    "02-renderers/files/go-librespot.service": ("gexis-spotify", True),
    "13-airplay/files/gexis-shairport-sync.service": ("gexis-airplay", True),
    "12-multiroom/files/gexis-snapserver.service": ("gexis-snap", False),
    "12-multiroom/files/gexis-snapclient.service": ("gexis-snap", True),
}


def _service(path: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    section = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("["):
            section = line
        elif section == "[Service]" and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            found.setdefault(key, []).append(value)
    return found


@pytest.mark.parametrize("unit", sorted(UNITS))
def test_a_music_service_runs_as_its_own_account(unit):
    account, sound = UNITS[unit]
    service = _service(STAGE / unit)
    assert service["User"] == [account] and service["Group"] == [account], unit
    assert service.get("SupplementaryGroups", []) == (["audio"] if sound else []), unit


def _installed_sysusers() -> dict[str, str]:
    """Each sysusers file a package installs: its source, by the name it is
    installed under; and that the package's postinst applies it."""
    installed = {}
    for script in (ROOT / "packaging").glob("*/build.sh"):
        text = script.read_text()
        for source, name in re.findall(r'(\S+-sysusers\.conf)"?\s*\\?\s*"?(?:\$STAGE)?/usr/lib/sysusers\.d/(\S+?\.conf)', text):
            assert re.search(rf"systemd-sysusers [^\n]*\b{re.escape(name)}\b", text), (script, name)
            installed[name] = source.split("/files/")[-1]
    return installed


@pytest.mark.parametrize("account", sorted({a for a, _ in UNITS.values()}))
def test_each_account_is_made_by_its_package(account):
    sources = _installed_sysusers().values()
    made = [s for s in sources
            for f in STAGE.glob(f"*/files/{s}")
            if re.search(rf"^u {re.escape(account)} ", f.read_text(), re.M)]
    assert made, account


def test_the_airplay_plugin_runs_as_shairport_sync_does():
    """Its own unit comes from the plugin's release and names pi; they share
    a runtime folder, the metadata pipe and the hook's socket."""
    drop_in = STAGE / "13-airplay" / "files" / "gexis-airplay-account.conf"
    service = _service(drop_in)
    assert service["User"] == ["gexis-airplay"] and service["Group"] == ["gexis-airplay"]
    assert service["SupplementaryGroups"] == ["gexis-plugins"], "the core's plugin socket"
    build = (ROOT / "packaging" / "airplay" / "build.sh").read_text()
    assert "/usr/lib/systemd/system/gexis-airplay.service.d/" in build and "gexis-airplay-account.conf" in build
    policy = (STAGE / "13-airplay" / "files" / "gexis-airplay-dbus.conf").read_text()
    assert '<policy user="gexis-airplay">' in policy and 'user="pi"' not in policy


def test_go_librespot_s_folder_is_given_to_its_account_at_every_start():
    """systemd re-owns a StateDirectory only when the folder itself has
    another owner; a restore puts the sign-in back as pi's."""
    service = _service(STAGE / "02-renderers" / "files" / "go-librespot.service")
    assert "+/usr/bin/chown -R gexis-spotify:gexis-spotify /var/lib/go-librespot" in service["ExecStartPre"]
    build = (ROOT / "packaging" / "go-librespot" / "build.sh").read_text()
    assert "-o 1000" not in build
