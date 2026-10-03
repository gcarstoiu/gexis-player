"""ADR-0050, amended 2026-10-03: the picker's pictures at the width it shows."""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys

import pytest

from gexis_core import skin_previews as sp


def _picture(tmp_path):
    picture = tmp_path / "pack" / "skin_bgr.png"
    picture.parent.mkdir()
    picture.write_bytes(b"png")
    return picture


def test_a_width_is_made_once_and_then_read(tmp_path):
    calls = []

    def run(command, **kw):
        calls.append(command)
        open(command[-2], "wb").write(b"jpeg")
        return subprocess.CompletedProcess(command, 0)

    picture, cache = _picture(tmp_path), tmp_path / "cache"
    first = asyncio.run(sp.scaled(picture, 960, cache=cache, run=run))
    again = asyncio.run(sp.scaled(picture, 960, cache=cache, run=run))
    assert first == again and first.read_bytes() == b"jpeg"
    assert len(calls) == 1 and calls[0][:3] == ["nice", "-n", "10"]


def test_only_the_picker_s_widths_and_a_failure_falls_back(tmp_path):
    def fail(command, **kw):
        raise subprocess.CalledProcessError(1, command)

    picture = _picture(tmp_path)
    assert asyncio.run(sp.scaled(picture, 4000, cache=tmp_path / "c")) is None
    assert asyncio.run(sp.scaled(picture, 480, cache=tmp_path / "c", run=fail)) is None


def test_a_changed_picture_is_made_again(tmp_path):
    picture = _picture(tmp_path)
    before = sp.path_for(picture, 960, tmp_path)
    picture.write_bytes(b"a different png")
    assert sp.path_for(picture, 960, tmp_path) != before


def test_the_oldest_go_past_the_limit(tmp_path):
    for i in range(5):
        (tmp_path / f"{i}-960.jpg").write_bytes(b"x")
    sp._prune(tmp_path, keep=3)
    assert len(list(tmp_path.glob("*.jpg"))) == 3


@pytest.mark.skipif(subprocess.run([sys.executable, "-c", "import PIL"], capture_output=True).returncode != 0,
                    reason="no Pillow here")
def test_the_real_scale_makes_a_smaller_jpeg(tmp_path, monkeypatch):
    """The script the player runs, with this machine's Pillow."""
    from PIL import Image

    src = tmp_path / "big.png"
    Image.new("RGB", (1920, 1080), (40, 80, 120)).save(src)
    monkeypatch.setattr(sp, "PYTHON", sys.executable)
    if not shutil.which("nice"):
        pytest.skip("no nice here")
    out = asyncio.run(sp.scaled(src, 960, cache=tmp_path / "cache"))
    with Image.open(out) as im:
        assert im.size == (960, 540) and im.format == "JPEG"


def test_every_preview_is_made_ahead_in_one_run_and_only_once(tmp_path):
    """George, 2026-10-03: "I would create the thumbs upfront for all"."""
    pictures = []
    for i in range(3):
        p = tmp_path / f"skin{i}.png"
        p.write_bytes(b"png%d" % i)
        pictures.append(p)
    calls = []

    def run(command, **kw):
        calls.append((command, kw["input"]))
        for line in kw["input"].splitlines():
            open(line.split("\t")[1], "wb").write(b"jpeg")
        return subprocess.CompletedProcess(command, 0, "", "")

    cache = tmp_path / "cache"
    assert sp.make_ahead(pictures, cache=cache, run=run) == 3
    assert len(calls) == 1 and calls[0][0][:4] == ["nice", "-n", "19", "ionice"], "one Python, lowest priority"
    assert sp.make_ahead(pictures, cache=cache, run=run) == 0 and len(calls) == 1
    assert asyncio.run(sp.scaled(pictures[0], 960, cache=cache, run=run)) == sp.path_for(pictures[0], 960, cache)
