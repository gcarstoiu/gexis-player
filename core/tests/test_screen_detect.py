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
