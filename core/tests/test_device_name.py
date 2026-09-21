# SPDX-License-Identifier: GPL-3.0-or-later
"""One name to four services (ADR-0048), Phase 9 subphase 9e.

Every write goes to a file, so every test here points the module at a
tmp_path and reads the file back. The four paths are module constants for
exactly this reason.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from gexis_core import device_name


# ── the sanitiser ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "typed, host",
    [
        ("gexis", "gexis"),
        ("Gexis Living Room", "gexis-living-room"),
        # Accents fold rather than becoming hyphens: a name is not mangled
        # into initials because it was typed in a language with diacritics.
        ("Café Münster", "cafe-munster"),
        ("  spaced  out  ", "spaced-out"),
        ("-leading-and-trailing-", "leading-and-trailing"),
        ("a" * 80, "a" * 63),
        # Nothing usable survives, so the design's fallback stands - and the
        # header shows it beside what was typed rather than substituting it
        # silently (ADR-0022).
        ("***", "gexis"),
        ("", "gexis"),
    ],
)
def test_the_hostname_is_the_sanitised_name(typed, host):
    assert device_name.sanitise(typed) == host


def test_a_cap_that_lands_on_a_hyphen_does_not_leave_one_trailing():
    """RFC 1123 has no room for 64, and a label may not end in a hyphen -
    truncating first and trimming second is the order that gets both."""
    name = ("x" * 62) + "-y"
    assert device_name.sanitise(name) == "x" * 62


# ── the four writes ───────────────────────────────────────────────────────

@pytest.fixture
def paths(tmp_path, monkeypatch):
    files = {
        "HOSTNAME_PATH": tmp_path / "hostname",
        "HOSTS_PATH": tmp_path / "hosts",
        "ENV_PATH": tmp_path / "gexis" / "device-name.env",
        "LIBRESPOT_PATH": tmp_path / "config.yml",
        "MACHINE_INFO_PATH": tmp_path / "machine-info",
    }
    for attr, path in files.items():
        monkeypatch.setattr(device_name, attr, path)
    files["HOSTNAME_PATH"].write_text("gexis\n")
    files["HOSTS_PATH"].write_text("127.0.0.1\tlocalhost\n127.0.1.1\tgexis\n")
    files["LIBRESPOT_PATH"].write_text(
        "# a comment\ndevice_name: gexis\naudio_backend: alsa\n"
    )
    files["MACHINE_INFO_PATH"].write_text("PRETTY_HOSTNAME=gexis\nICON_NAME=audio-card\n")
    return files


def test_a_rename_writes_all_four(paths):
    written = device_name.apply("Gexis Living Room")
    assert written.ok and written.hostname == "gexis-living-room"
    assert paths["HOSTNAME_PATH"].read_text() == "gexis-living-room\n"
    assert "GEXIS_DEVICE_NAME=Gexis Living Room\n" == paths["ENV_PATH"].read_text()
    # The three display names are verbatim; only the hostname is sanitised.
    assert "device_name: Gexis Living Room\n" in paths["LIBRESPOT_PATH"].read_text()
    assert "PRETTY_HOSTNAME=Gexis Living Room\n" in paths["MACHINE_INFO_PATH"].read_text()


def test_the_hosts_entry_carries_the_new_name_and_the_running_one(paths, monkeypatch):
    """A rename takes effect at the restart, so in between the system is
    still running under the old name. A hosts file naming only the new one
    would leave the *current* hostname unresolvable for that whole window,
    and sudo complains on every call when it is."""
    monkeypatch.setattr(device_name, "hostname", lambda: "gexis")
    device_name.apply("Studio")
    text = paths["HOSTS_PATH"].read_text()
    assert "127.0.1.1\tstudio\tgexis\n" in text
    assert "127.0.0.1\tlocalhost\n" in text, "the rest of the file is left alone"


def test_the_old_alias_goes_once_the_restart_has_happened(paths, monkeypatch):
    """After the restart the system runs under the new name, so renaming to
    it again - or renaming onward - leaves one name on the line. It never
    grows past two."""
    monkeypatch.setattr(device_name, "hostname", lambda: "studio")
    device_name.apply("Studio")
    assert "127.0.1.1\tstudio\n" in paths["HOSTS_PATH"].read_text()
    device_name.apply("Kitchen")
    line = [l for l in paths["HOSTS_PATH"].read_text().splitlines() if l.startswith("127.0.1.1")]
    assert line == ["127.0.1.1\tkitchen\tstudio"]


def test_the_surrounding_config_is_left_alone(paths):
    device_name.apply("Studio")
    yaml = paths["LIBRESPOT_PATH"].read_text()
    assert yaml.startswith("# a comment\n") and "audio_backend: alsa\n" in yaml
    assert "ICON_NAME=audio-card\n" in paths["MACHINE_INFO_PATH"].read_text()


def test_bluetooth_takes_the_name_from_machine_info_not_main_conf(paths):
    """**main.conf's `Name =` does nothing.** BlueZ's hostname plugin
    overrides it - the shipped file says so two lines above the setting -
    and both this module and the image wrote it for months. It looked right
    only because the hostname was the same string. Measured on the device
    2026-09-21: `Name = SofaPi` with no PRETTY_HOSTNAME reported `sofapi`.
    """
    paths["MACHINE_INFO_PATH"].unlink()
    device_name.apply("Studio")
    assert paths["MACHINE_INFO_PATH"].read_text() == "PRETTY_HOSTNAME=Studio\n"
    assert not hasattr(device_name, "BLUETOOTH_PATH"), "main.conf is not a target"


def test_a_missing_key_is_appended_rather_than_dropped(paths):
    paths["LIBRESPOT_PATH"].write_text("audio_backend: alsa\n")
    device_name.apply("Studio")
    assert paths["LIBRESPOT_PATH"].read_text() == "audio_backend: alsa\ndevice_name: Studio\n"


def test_a_target_that_refuses_is_named_and_the_others_still_land(paths, monkeypatch):
    """ADR-0048 §3: not reported successful unless every target took it. A
    half-renamed device with nothing on screen to say so only surfaces at
    the restart, hours after the cause."""
    def refuse(_name):
        raise OSError("read-only file system")

    monkeypatch.setattr(device_name, "_write_librespot", refuse)
    written = device_name.apply("Studio")
    assert written.ok is False and written.failed == ("Spotify",)
    assert written.to_json() == {"hostname": "studio", "ok": False, "failed": ["Spotify"]}
    # Everything else still happened - one refusal is not a reason to leave
    # the rest on the old name.
    assert paths["HOSTNAME_PATH"].read_text() == "studio\n"
    assert "PRETTY_HOSTNAME=Studio\n" in paths["MACHINE_INFO_PATH"].read_text()


def test_the_env_directory_is_created_if_it_is_not_there(paths):
    assert not paths["ENV_PATH"].parent.exists()
    assert device_name.apply("Studio").ok
    assert paths["ENV_PATH"].read_text() == "GEXIS_DEVICE_NAME=Studio\n"


def test_renaming_twice_replaces_rather_than_accumulates(paths, monkeypatch):
    monkeypatch.setattr(device_name, "hostname", lambda: "gexis")
    device_name.apply("First")
    device_name.apply("Second")
    yaml = paths["LIBRESPOT_PATH"].read_text()
    assert yaml.count("device_name:") == 1 and "device_name: Second" in yaml
    assert paths["MACHINE_INFO_PATH"].read_text().count("PRETTY_HOSTNAME=") == 1
    assert paths["HOSTS_PATH"].read_text().count("127.0.1.1") == 1


# ── the header's facts ────────────────────────────────────────────────────

def test_the_address_is_not_the_loopback_one():
    """`gethostbyname(gethostname())` answers 127.0.1.1 on a Debian-derived
    image: true, and useless to someone typing it into a phone."""
    found = device_name.address()
    assert found is None or not found.startswith("127."), found


def test_the_unit_reads_the_env_file_this_module_writes():
    """The one coupling that cannot be tested from inside the daemon: if the
    unit stops reading the file, a rename silently does nothing to the LMS
    name. The image's own build asserts this too."""
    unit = (
        Path(__file__).parents[2]
        / "image/stage-gexis/02-renderers/files/squeezelite.service"
    ).read_text()
    assert f"EnvironmentFile=-{device_name.ENV_PATH}" in unit
    assert "-n ${%s}" % device_name.ENV_KEY in unit
