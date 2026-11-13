"""ADR-0109: the kiosk's labwc configuration, written for the HDMI port the
screen is on (George, 2026-10-12: a panel on the second port had its touch
tied to the first). The script's own generation, run under bash with a fake
/etc/xdg/labwc and a fake /sys/class/drm."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

FILES = Path(__file__).resolve().parents[2] / "image" / "stage-gexis" / "04-ui" / "files"
SCRIPT = FILES / "gexis-kiosk-start"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _write(tmp_path: Path, connector: str | None = None, connected: tuple[str, ...] = (), dsi: bool = False) -> str:
    source = tmp_path / "xdg"
    source.mkdir(exist_ok=True)
    shutil.copy(FILES / "labwc-rc.xml", source / "rc.xml")
    (source / "environment").write_text("XKB_DEFAULT_LAYOUT=gb\n")
    drm = tmp_path / "drm"
    for name in ("card1-HDMI-A-1", "card1-HDMI-A-2") + (("card1-DSI-1",) if dsi else ()):
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
    # sofapi, 2026-10-18: to the screen's output, then filling it - one rule.
    assert rc.count("<windowRule ") == 1
    assert rc.index('output="HDMI-A-2"/>') < rc.index('<action name="Maximize"/>')
    assert rc.rstrip().endswith("</labwc_config>")


def test_on_the_first_port_the_installed_configuration_is_used_as_it_is(tmp_path):
    rc = _write(tmp_path, "HDMI-A-1", connected=("HDMI-A-1",))
    assert rc == (FILES / "labwc-rc.xml").read_text()
    assert '<action name="Maximize"/>' in rc, "every window fills its screen (sofapi, 2026-10-18)"


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


def test_any_output_but_the_screens_is_black():
    """ADR-0141 D3 (George, 2026-10-12): a sound-only port shows black, not
    the boot logo stretched onto a TV."""
    script = SCRIPT.read_text()
    assert script.count("swaybg -o '*' --color '#000000'") == 2
    assert '-o "${screen_output}"' in script and "screen_output=$(screen_connector)" in script


def test_the_stored_window_size_is_forgotten_before_chromium_starts(tmp_path):
    """sofapi, 2026-10-20: a stored 800x480, restored at scale 0.625, drew the
    page at 500x300 in a corner of the 7". Every other preference stays."""
    import json
    prefs = tmp_path / "Default" / "Preferences"
    prefs.parent.mkdir()
    prefs.write_text(json.dumps({"browser": {"window_placement": {"right": 800, "bottom": 480},
                                             "has_seen_welcome_page": True}, "profile": {"name": "x"}}))
    subprocess.run(["bash", str(SCRIPT), "forget-window", str(tmp_path)], check=True, capture_output=True)
    kept = json.loads(prefs.read_text())
    assert "window_placement" not in kept["browser"]
    assert kept["browser"]["has_seen_welcome_page"] is True and kept["profile"] == {"name": "x"}
    # No profile yet (a first start): nothing to do, and no error.
    subprocess.run(["bash", str(SCRIPT), "forget-window", str(tmp_path / "none")], check=True, capture_output=True)


def test_chromium_is_started_only_after_the_window_size_is_forgotten():
    text = SCRIPT.read_text()
    assert text.index('forget_window "${GEXIS_KIOSK_PROFILE}"') < text.index("exec chromium \\")


def test_a_dsi_panel_s_touch_and_window_are_tied_to_dsi(tmp_path):
    """ADR-0158: the core names DSI-1 in screen.env; touch follows it, and
    the window is moved there - labwc would otherwise open it on HDMI-A-1."""
    rc = _write(tmp_path, "DSI-1", connected=("DSI-1",), dsi=True)
    assert '<touch mapToOutput="DSI-1"/>' in rc
    assert '<action name="MoveToOutput" output="DSI-1"/>' in rc


def test_with_no_screen_chosen_a_dsi_panel_comes_before_hdmi(tmp_path):
    """ADR-0158 D3: with a receiver on HDMI 1 and the panel on the ribbon,
    the panel is the screen."""
    rc = _write(tmp_path, None, connected=("DSI-1", "HDMI-A-1"), dsi=True)
    assert '<touch mapToOutput="DSI-1"/>' in rc and '<action name="MoveToOutput" output="DSI-1"/>' in rc



def _session(tmp_path: Path, token: str | None) -> tuple[list[str], Path]:
    """The script's session part, as labwc runs it, with Chromium a stand-in
    that writes down its arguments: those arguments, and the user's runtime
    folder."""
    token_file = tmp_path / "panel-token"
    if token is not None:
        token_file.write_text(token + "\n")
    runtime = tmp_path / "run-user"
    runtime.mkdir(mode=0o700)
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "chromium").write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$CHROMIUM_ARGS"\n')
    (fake / "sleep").write_text("#!/bin/sh\n")
    for name in ("chromium", "sleep"):
        (fake / name).chmod(0o755)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GEXIS_", "WAYLAND_", "XDG_")) and k != "DISPLAY"}
    env.update(PATH=f"{fake}:{os.environ['PATH']}", XDG_RUNTIME_DIR=str(runtime),
               GEXIS_KIOSK_URL="http://127.0.0.1:8090/", GEXIS_KIOSK_PROFILE=str(tmp_path / "profile"),
               GEXIS_PANEL_TOKEN=str(token_file), GEXIS_DRM=str(tmp_path / "drm"),
               CHROMIUM_ARGS=str(tmp_path / "args"))
    subprocess.run(["bash", str(SCRIPT)], env=env, check=True, capture_output=True, timeout=30)
    return (tmp_path / "args").read_text().splitlines(), runtime


def test_the_panel_s_token_is_never_on_chromium_s_command_line(tmp_path):
    """The review of 1.16.1: any process on the player can read another's
    command line - a Lyrion plugin, Roon Bridge - and the token in the
    address let it pass for the panel. The kiosk opens a page only its own
    user can read, which goes on to the panel's address with the token."""
    args, runtime = _session(tmp_path, "Ab_9-token")
    assert not any("Ab_9-token" in a for a in args)
    url = args[-1]
    assert url.startswith("file://")
    page = Path(url[len("file://"):])
    assert page.parent == runtime and stat.S_IMODE(page.stat().st_mode) == 0o600
    assert 'location.replace("http://127.0.0.1:8090/#panel=Ab_9-token")' in page.read_text()
    assert "#101a21" in page.read_text(), "the panel's ground colour, not a white flash"


def test_with_no_token_the_panel_s_address_is_opened_as_it_is(tmp_path):
    args, runtime = _session(tmp_path, None)
    assert args[-1] == "http://127.0.0.1:8090/" and not list(runtime.iterdir())
