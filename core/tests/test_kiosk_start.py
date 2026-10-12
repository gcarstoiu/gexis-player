"""ADR-0109: the kiosk's labwc configuration, written for the HDMI port the
screen is on (George, 2026-10-12: a panel on the second port had its touch
tied to the first). The script's own generation, run under bash with a fake
/etc/xdg/labwc and a fake /sys/class/drm."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

FILES = Path(__file__).resolve().parents[2] / "image" / "stage-gexis" / "04-ui" / "files"
SCRIPT = FILES / "gexis-kiosk-start"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _write(tmp_path: Path, connector: str | None = None, connected: tuple[str, ...] = ()) -> str:
    source = tmp_path / "xdg"
    source.mkdir(exist_ok=True)
    shutil.copy(FILES / "labwc-rc.xml", source / "rc.xml")
    (source / "environment").write_text("XKB_DEFAULT_LAYOUT=gb\n")
    drm = tmp_path / "drm"
    for name in ("card1-HDMI-A-1", "card1-HDMI-A-2"):
        (drm / name).mkdir(parents=True, exist_ok=True)
        (drm / name / "status").write_text("connected\n" if name.split("-", 1)[1] in connected else "disconnected\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GEXIS_")}
    env.update(GEXIS_LABWC_SOURCE=str(source), GEXIS_DRM=str(drm))
    if connector is not None:
        env["GEXIS_SCREEN_CONNECTOR"] = connector
    out = tmp_path / "config"
    subprocess.run(["bash", str(SCRIPT), "labwc-config", str(out)], env=env, check=True,
                   capture_output=True, timeout=30)
    assert (out / "environment").read_text() == "XKB_DEFAULT_LAYOUT=gb\n", "the rest of labwc's config comes along"
    return (out / "rc.xml").read_text()


def test_touch_is_tied_to_the_port_screen_env_names(tmp_path):
    rc = _write(tmp_path, "HDMI-A-2", connected=("HDMI-A-1", "HDMI-A-2"))
    assert '<touch mapToOutput="HDMI-A-2"/>' in rc and "HDMI-A-1\"" not in rc
    assert '<action name="MoveToOutput" output="HDMI-A-2"/>' in rc, "the window on the screen, not on HDMI-A-1"
    assert rc.rstrip().endswith("</labwc_config>")


def test_on_the_first_port_the_installed_configuration_is_used_as_it_is(tmp_path):
    rc = _write(tmp_path, "HDMI-A-1", connected=("HDMI-A-1",))
    assert rc == (FILES / "labwc-rc.xml").read_text()


def test_with_no_screen_chosen_the_connected_port_is_used(tmp_path):
    assert '<touch mapToOutput="HDMI-A-2"/>' in _write(tmp_path, None, connected=("HDMI-A-2",))
    assert '<touch mapToOutput="HDMI-A-1"/>' in _write(tmp_path, None, connected=())


def test_a_connector_that_is_not_an_hdmi_port_is_not_written_into_the_xml(tmp_path):
    rc = _write(tmp_path, 'HDMI-A-2"/><x a="', connected=("HDMI-A-2",))
    assert '<touch mapToOutput="HDMI-A-2"/>' in rc and "<x " not in rc


def test_the_service_starts_labwc_through_the_script():
    unit = (FILES / "gexis-kiosk.service").read_text()
    assert "ExecStart=/usr/bin/gexis-kiosk-start compositor" in unit
    script = SCRIPT.read_text()
    assert 'exec labwc -C "${config}" -s "$0"' in script
    assert 'exec labwc -s "$0"' in script, "a configuration not written still starts the panel"


def test_with_both_ports_connected_the_window_is_pinned_to_the_screen_on_the_first(tmp_path):
    """ADR-0141: a sound bar on HDMI 2 could take the window otherwise."""
    rc = _write(tmp_path, "HDMI-A-1", connected=("HDMI-A-1", "HDMI-A-2"))
    assert '<action name="MoveToOutput" output="HDMI-A-1"/>' in rc
