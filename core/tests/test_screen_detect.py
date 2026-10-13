"""ADR-0109: recognition suggests only a tested model whose report matches."""
from __future__ import annotations

from pathlib import Path

from gexis_core import screen_detect

EDID = (Path(__file__).parent / "data" / "edid-waveshare-10.1-hdmi-b.bin").read_bytes()


def fake_sysfs(tmp_path, edid=EDID, status="connected", usb=(("0712", "0010"), ("1d6b", "0002"))):
    drm = tmp_path / "drm" / "card0-HDMI-A-1"
    drm.mkdir(parents=True)
    (drm / "status").write_text(status + "\n")
    (drm / "edid").write_bytes(edid)
    for i, (v, p) in enumerate(usb):
        d = tmp_path / "usb" / f"1-{i}"
        d.mkdir(parents=True)
        (d / "idVendor").write_text(v + "\n")
        (d / "idProduct").write_text(p + "\n")
    return tmp_path / "drm", tmp_path / "usb"


def test_the_10_1_inch_panel_s_own_edid_reads_as_it_does_on_the_device():
    """Measured on sofa-pi, 2026-10-01 (its size, 121 × 68 cm, is ignored)."""
    assert screen_detect.parse_edid(EDID) == ("WAV", "WaveShare", (1280, 800))


def test_the_panel_on_sofa_pi_is_recognised(tmp_path):
    drm, usb = fake_sysfs(tmp_path)
    report = screen_detect.seen(drm, usb)
    assert report.connected and report.connector == "HDMI-A-1" and report.usb == ("0712:0010",)
    assert screen_detect.suggest(report).id == "waveshare-10.1-hdmi-b"


def test_a_screen_that_only_shares_the_maker_is_not_named(tmp_path):
    other = bytearray(EDID)
    # the preferred mode's width 1280 -> 1024 (DTD 1, bytes 56/58)
    other[56] = 1024 & 0xFF
    other[58] = (other[58] & 0x0F) | ((1024 >> 8) << 4)
    drm, usb = fake_sysfs(tmp_path, edid=bytes(other))
    assert screen_detect.suggest(screen_detect.seen(drm, usb)) is None


def test_without_its_touch_controller_it_is_not_named(tmp_path):
    drm, usb = fake_sysfs(tmp_path, usb=(("1d6b", "0002"),))
    assert screen_detect.suggest(screen_detect.seen(drm, usb)) is None


def test_nothing_connected_is_nothing_seen(tmp_path):
    drm, usb = fake_sysfs(tmp_path, status="disconnected")
    report = screen_detect.seen(drm, usb)
    assert not report.connected and screen_detect.suggest(report) is None


def test_a_broken_edid_is_read_as_nothing():
    assert screen_detect.parse_edid(b"\x00" * 128) == (None, None, None)


def test_the_13_3_inch_is_recognised_by_what_it_reported_on_gexis():
    """2026-10-03: EDID RTK / RTK FHD, 1920x1080, touch ILI 222a:0001."""
    seen = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="RTK",
                              edid_name="RTK FHD", preferred=(1920, 1080), usb=("2109:3431", "222a:0001"))
    assert screen_detect.suggest(seen).id == "waveshare-13.3-hdmi-h"
    other = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="RTK",
                               edid_name="RTK FHD", preferred=(1920, 1080), usb=("2109:3431",))
    assert screen_detect.suggest(other) is None, "a Realtek screen without that touch is not named"


def test_the_11_9_inch_bar_is_recognised_by_what_it_reported_on_the_bar_player():
    """2026-10-10, read on the bar player: EDID WSD / WaveShare-119, 320x1480
    (its native portrait), touch 0712:000a - exactly what the Seen below
    holds. Setup showed the whole list for it until then."""
    seen = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="WSD",
                              edid_name="WaveShare-119", preferred=(320, 1480), usb=("2109:3431", "0712:000a"))
    assert screen_detect.suggest(seen).id == "waveshare-11.9-hdmi"
    without_touch = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="WSD",
                                       edid_name="WaveShare-119", preferred=(320, 1480), usb=("2109:3431",))
    assert screen_detect.suggest(without_touch) is None


def test_the_screen_already_on_shows_as_one_that_changes_nothing():
    """2026-10-11: setup warned *Keep this screen?* on the recognised bar,
    already applied for setup; the choices that change nothing say so."""
    from gexis_core import screen_apply, screens, setup_flow
    bar = next(s for s in screens.all_screens() if s.width == 1480 and s.height == 320)
    standard = next(s for s in screens.all_screens() if s.width == 1280 and s.height == 800)
    report = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="WSD", edid_name="WaveShare-119",
                     preferred=(320, 1480), usb=("0712:000a",))
    now = screen_apply.picture_of(screen_apply.Applied(bar.id, 0))
    page = setup_flow.screen_choices(report, 0, now=now)
    assert bar.id in page["unchanged"] and standard.id not in page["unchanged"]


# --- ADR-0141 D2/D4: both ports ----------------------------------------------

def _receiver_edid():
    """Another device's EDID: the panel's, its maker and size changed."""
    other = bytearray(EDID)
    other[8], other[9] = 0x4C, 0x2D          # PNP "SAM"
    other[56] = 1920 & 0xFF
    other[58] = (other[58] & 0x0F) | ((1920 >> 8) << 4)
    return bytes(other)


def two_ports(tmp_path, one, two):
    """HDMI-A-1 and HDMI-A-2, each `None` (nothing) or an EDID."""
    for name, edid in (("card0-HDMI-A-1", one), ("card0-HDMI-A-2", two)):
        d = tmp_path / "drm" / name
        d.mkdir(parents=True)
        (d / "status").write_text("connected\n" if edid else "disconnected\n")
        (d / "edid").write_bytes(edid or b"")
    u = tmp_path / "usb" / "1-0"
    u.mkdir(parents=True)
    (u / "idVendor").write_text("0712\n"); (u / "idProduct").write_text("0010\n")
    return tmp_path / "drm", tmp_path / "usb"


def test_every_port_is_listed_connected_or_not(tmp_path):
    drm, usb = two_ports(tmp_path, EDID, None)
    ports = screen_detect.ports(drm, usb)
    assert [(p.connector, p.connected) for p in ports] == [("HDMI-A-1", True), ("HDMI-A-2", False)]
    assert ports[0].edid_name == "WaveShare"


def test_with_both_ports_the_known_panel_is_the_screen_not_the_first_port(tmp_path):
    """A sound bar on HDMI 1 and the panel on HDMI 2: the panel."""
    drm, usb = two_ports(tmp_path, _receiver_edid(), EDID)
    assert screen_detect.seen(drm, usb, prefer=None).connector == "HDMI-A-2"


def test_with_both_ports_the_applied_port_holds_when_no_panel_is_known(tmp_path):
    """Two unlisted screens: the one chosen stays the screen across starts."""
    drm, usb = two_ports(tmp_path, _receiver_edid(), _receiver_edid())
    assert screen_detect.seen(drm, usb, prefer="HDMI-A-2").connector == "HDMI-A-2"
    assert screen_detect.seen(drm, usb, prefer=None).connector == "HDMI-A-1"


def test_a_panel_moved_away_from_the_applied_port_is_followed(tmp_path):
    """Applied on HDMI-A-1, now a receiver there and the panel on HDMI-A-2."""
    drm, usb = two_ports(tmp_path, _receiver_edid(), EDID)
    assert screen_detect.seen(drm, usb, prefer="HDMI-A-1").connector == "HDMI-A-2"
