"""ADR-0111: one pack per device, chosen by the screen."""
from __future__ import annotations

import json

from gexis_core import skin_packs as sp


def test_a_screen_gets_its_own_size():
    for size in sp.SIZES:
        assert sp.for_screen(*size) == size


def test_otherwise_the_largest_pack_that_fits_uncropped():
    """George: "exact resolution or nearest neighbour that doesn't get cropped"."""
    assert sp.for_screen(1366, 768) == (800, 480)
    assert sp.for_screen(1920, 1200) == (1920, 1080)
    assert sp.for_screen(2560, 1440) == (1920, 1080)
    # a bar keeps a bar's pack; of those that fit, the one with most area
    assert sp.for_screen(1600, 400) == (1280, 400)
    assert sp.for_screen(1500, 330) == (1480, 320)
    assert sp.for_screen(1024, 600) == (800, 480)


def test_a_screen_smaller_than_every_pack_gets_none():
    assert sp.for_screen(480, 320) is None


def test_a_device_keeps_one_pack(tmp_path):
    def pack(w, h):
        d = tmp_path / "packs" / f"{w}x{h}"
        d.mkdir(parents=True)
        (d / "pack.json").write_text(json.dumps({"size": f"{w}x{h}"}))
    pack(1280, 800)
    have = sp.installed(tmp_path / "packs", tmp_path / "none")
    assert sp.plan((1920, 1080), have) == ((1920, 1080), [(1280, 800)])
    pack(1920, 1080)
    have = sp.installed(tmp_path / "packs", tmp_path / "none")
    assert sp.plan((1920, 1080), have) == (None, [(1280, 800)])


def test_the_kept_gexis_skins_counts_as_the_1280x800_pack(tmp_path):
    """Decision 10: devices that had gexis-skins keep it, as it is."""
    (tmp_path / "skins").mkdir()
    have = sp.installed(tmp_path / "packs", tmp_path / "skins")
    assert have == [(1280, 800)]
    assert sp.plan((1280, 800), have) == (None, [])
    assert sp.root_of((1280, 800), tmp_path / "packs", tmp_path / "skins") == tmp_path / "skins"


def test_package_names():
    assert sp.package((1480, 320)) == "gexis-skins-1480x320"
