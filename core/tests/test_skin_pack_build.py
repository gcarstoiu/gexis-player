"""ADR-0111: one skin pack per screen size, built by packaging/skin-packs.

`assemble.py` decides what a skin is and which ones repeat; `describe.py`
writes what a pack says about itself. Both run in the package builder, and
are imported here from there, as `test_letterbox` imports the stage's script.
The rest are the policy the record sets: no pack in the image, none in the
release's Depends, every pack in the release."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]
HERE = REPO / "packaging" / "skin-packs"
sys.path.insert(0, str(HERE))

import assemble  # noqa: E402
import describe  # noqa: E402

SIZES = ("1920x1080", "1280x400", "1480x320", "800x480", "1280x800")


def meter(name, bgr, extra=""):
    return f"[{name}]\nmeter.type = circular\nbgr.filename = {bgr}\nindicator.filename = n.png\n{extra}\n"


def write(folder: Path, files: dict[str, bytes | str]) -> None:
    for rel, data in files.items():
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)


def run(tmp_path, gelo5: dict, catalog: dict[str, tuple[list, dict]], size="800x480",
        stock: dict | None = None):
    """`gelo5`: {"<top>/<folder>/<file>": data}. `catalog`: name -> (units,
    files), the units as catalog/index.json has them; a name starting with
    another size is that size's pack. `stock`: peppy_screensaver's files."""
    g = tmp_path / "gelo5"
    write(g, gelo5)
    cat = tmp_path / "cat"
    templates = []
    for name, (units, files) in catalog.items():
        write(cat / name, files)
        w, h = (name.split("_")[0] if re.match(r"^\d+x\d+_", name) else size).split("x")
        templates.append({"name": name, "width": int(w), "height": int(h), "sha256": "0" * 64,
                          "units": units})
    (tmp_path / "index.json").write_text(json.dumps({"templates": templates}))
    out = tmp_path / "out" / size
    extra = ["--letterbox", str(REPO / "image/stage-gexis/05-peppy/files/letterbox.py")]
    if stock is not None:
        write(tmp_path / "stock", stock)
        extra += ["--stock", str(tmp_path / "stock")]
    rc = assemble.main([
        "--size", size, "--index", str(tmp_path / "index.json"), "--catalog", str(cat),
        "--gelo5", str(g), "--out", str(out), "--work", str(tmp_path / "work"),
        "--report", str(tmp_path / "report.json"), *extra,
    ])
    report = json.loads((tmp_path / "report.json").read_text()) if rc == 0 else None
    return rc, out, report


GELO = {
    "templates/800x480_Gelo5 00-99 Skin_1000/meters.txt": meter("01G5_A", "a.png") + meter("02G5_B", "b.png"),
    "templates/800x480_Gelo5 00-99 Skin_1000/a.png": b"A",
    "templates/800x480_Gelo5 00-99 Skin_1000/b.png": b"B",
    "templates/800x480_Gelo5 00-99 Skin_1000/n.png": b"N",
    "templates/800x480_Gelo5 01-20 Skin_1001/meters.txt": meter("01G5_A", "a.png"),
    "templates/800x480_Gelo5 01-20 Skin_1001/a.png": b"A",
    "templates/800x480_Gelo5 01-20 Skin_1001/n.png": b"N",
}


def unit(folder, install="templates", src=None):
    return {"kind": "meter", "install": install, "from": f"{src or folder}/", "folder": folder}


def test_gelo5s_split_folders_repeat_its_merged_one_and_go(tmp_path):
    rc, out, report = run(tmp_path, GELO, {})
    assert rc == 0
    assert (out / "gelo5/templates/800x480/meters.txt").is_file()
    assert not (out / "gelo5-1001").exists()
    assert report["skins"] == 2
    assert report["dropped_skins"] == [{"pack": "gelo5-1001", "skin": "01G5_A",
                                        "file": "templates/meters.txt", "same_as": "gelo5: 01G5_A"}]


def test_a_skin_is_its_values_and_its_pictures_not_its_name(tmp_path):
    """The catalog's copy under another name and folder is a repeat; one
    whose picture differs by a byte is a skin of its own, shipped, and its
    shared name reported."""
    rc, out, report = run(tmp_path, GELO, {
        "800x480_g5_copy": ([unit("800x480_g5_copy")], {
            "800x480_g5_copy/meters.txt": meter("Another name", "a_renamed.png"),
            "800x480_g5_copy/a_renamed.png": b"A", "800x480_g5_copy/n.png": b"N"}),
        "800x480_g5_revised": ([unit("800x480_g5_revised")], {
            "800x480_g5_revised/meters.txt": meter("02G5_B", "b.png"),
            "800x480_g5_revised/b.png": b"B2", "800x480_g5_revised/n.png": b"N"}),
    })
    assert rc == 0
    assert not (out / "800x480_g5_copy").exists()
    assert (out / "800x480_g5_revised/templates/800x480/b.png").read_bytes() == b"B2"
    assert {d["pack"] for d in report["dropped_packs"]} == {"gelo5-1001", "800x480_g5_copy"}
    assert report["renamed"] == [{"pack": "800x480_g5_revised", "file": "templates/meters.txt",
                                  "from": "02G5_B", "to": "02G5_B (g5 revised)"}]


def test_a_shared_name_keeps_both_skins_and_renames_the_later(tmp_path):
    """Decision 13. Gelo5 keeps its names; the catalog's copy is renamed
    after its pack, with a number when that is taken too, and only the
    section header changes - its spectrum link stays."""
    revised = {"meters.txt": meter("02G5_B", "b.png", "spectrum.name = S") + meter("02G5_B (g5 x)", "c.png"),
               "b.png": b"B2", "c.png": b"C", "n.png": b"N"}
    rc, out, report = run(tmp_path, GELO, {
        "800x480_g5_x": ([unit("800x480_g5_x")], {f"800x480_g5_x/{k}": v for k, v in revised.items()}),
    })
    assert rc == 0
    text = (out / "800x480_g5_x/templates/800x480/meters.txt").read_text()
    assert "[02G5_B (g5 x 2)]\nmeter.type = circular\nbgr.filename = b.png" in text
    assert "spectrum.name = S" in text and "[02G5_B (g5 x)]" in text
    assert [r["to"] for r in report["renamed"]] == ["02G5_B (g5 x 2)"]


def test_a_partly_repeated_pack_keeps_its_new_skins_and_loses_the_rest(tmp_path):
    rc, out, report = run(tmp_path, GELO, {
        "800x480_mixed": ([unit("800x480_mixed")], {
            "800x480_mixed/meters.txt": "# header\n" + meter("01G5_A", "a.png") + meter("New", "c.png"),
            "800x480_mixed/a.png": b"A", "800x480_mixed/c.png": b"C", "800x480_mixed/n.png": b"N"}),
    })
    assert rc == 0
    folder = out / "800x480_mixed/templates/800x480"
    text = (folder / "meters.txt").read_text()
    assert "[New]" in text and "[01G5_A]" not in text and text.startswith("# header\n")
    assert not (folder / "a.png").exists()          # only the repeat named it
    assert (folder / "n.png").is_file()             # the kept skin still names it
    assert [p for p in report["packs"] if p["dir"] == "800x480_mixed"][0]["skins"] == 1


def test_previews_and_debris_are_left_out_and_sub_folders_kept(tmp_path):
    rc, out, report = run(tmp_path, GELO, {
        "800x480_tape": ([unit("800x480_tape")], {
            "800x480_tape/meters.txt": meter("Tape", "t.png", "playstate.icon = icons/play.png,icons/stop.png"),
            "800x480_tape/t.png": b"T", "800x480_tape/n.png": b"N",
            "800x480_tape/icons/play.png": b"P", "800x480_tape/icons/stop.png": b"S",
            "800x480_tape/preview.png": b"screenshot", "800x480_tape/.DS_Store": b"x",
            "800x480_tape/rescale.py": "print()",
            "__MACOSX/800x480_tape/._meters.txt": b"x"}),
    })
    assert rc == 0
    folder = out / "800x480_tape/templates/800x480"
    assert (folder / "icons/play.png").read_bytes() == b"P"
    assert not list(out.rglob("preview.png")) and not list(out.rglob(".DS_Store")) and not list(out.rglob("*.py"))
    reasons = {d["file"]: d["reason"] for d in report["dropped_files"] if d["pack"] == "800x480_tape"}
    assert reasons["preview.png"].startswith("preview")
    assert reasons["__MACOSX/800x480_tape/._meters.txt"] == "macOS metadata"


SPEC_AND_MET = {
    "template/800x480_Gelo5 00-99 Skin_1000/meters.txt": meter("01G5_A", "a.png"),
    "template/800x480_Gelo5 00-99 Skin_1000/a.png": b"A",
    "template/800x480_Gelo5 00-99 Skin_1000/n.png": b"N",
    "template/800x480_Gelo5 Spec&Met_1020/meters.txt": meter("107G5_Marantz S+M", "Marantz_bgr.png",
                                                             "spectrum.name = Marantz"),
    "template/800x480_Gelo5 Spec&Met_1020/Marantz_bgr.png": b"the dials",
    "template/800x480_Gelo5 Spec&Met_1020/n.png": b"N",
    "template_spectrum/800x480_Gelo5 Spec&Met_1020/spectrum.txt": "[Marantz]\nbgr.filename = Marantz_bgr.png\n",
    "template_spectrum/800x480_Gelo5 Spec&Met_1020/Marantz_bgr.png": b"the blank panel",
}


def test_a_spec_and_met_set_keeps_its_meter_picture_apart_from_its_spectrum(tmp_path):
    """**Finding 050's cause.** gexis-skins copied a set's meter folder and
    its spectrum folder into one, and the spectrum's `Marantz_bgr.png`
    overwrote the meter's. Kept apart, as upstream ships them, each has its
    own."""
    rc, out, _ = run(tmp_path, SPEC_AND_MET, {})
    assert rc == 0
    sm = out / "gelo5-1020"
    assert (sm / "templates/800x480/Marantz_bgr.png").read_bytes() == b"the dials"
    assert (sm / "templates_spectrum/800x480/Marantz_bgr.png").read_bytes() == b"the blank panel"
    assert (sm / "templates_spectrum/800x480/spectrum.txt").is_file()


def test_a_meter_that_draws_a_spectrum_panel_fails_the_build(tmp_path, capsys):
    broken = dict(SPEC_AND_MET)
    broken["template/800x480_Gelo5 Spec&Met_1020/Marantz_bgr.png"] = b"the blank panel"
    rc, _, _ = run(tmp_path, broken, {})
    assert rc == 1
    assert "draws Marantz_bgr.png, the panel of spectrum Marantz" in capsys.readouterr().err


def test_the_stock_skins_are_a_pack_of_their_own(tmp_path):
    """Decision 14: peppy_screensaver's `<size>_custom_<n>` folders, meters
    and spectra apart, as gexis-skins has them."""
    rc, out, report = run(tmp_path, GELO, {}, stock={
        "templates/800x480_custom_10/meters.txt": meter("gold", "g.png", "spectrum.name = s.1"),
        "templates/800x480_custom_10/g.png": b"G", "templates/800x480_custom_10/n.png": b"N",
        "templates/1280x800_custom_4/meters.txt": meter("other size", "g.png"),
        "templates_spectrum/800x480_custom_10/spectrum.txt": "[s.1]\nbgr.filename = p.png\n",
        "templates_spectrum/800x480_custom_10/p.png": b"P",
    })
    assert rc == 0
    assert (out / "stock/templates/800x480/meters.txt").read_text().startswith("[gold]")
    assert (out / "stock/templates_spectrum/800x480/spectrum.txt").is_file()
    assert [p for p in report["packs"] if p["dir"] == "stock"] == [
        {"dir": "stock", "source": "foonerd/peppy_screensaver", "skins": 1}]
    assert report["skins"] == 3


def test_a_1280x720_pack_with_a_spectrum_is_letterboxed_into_1280x800(tmp_path):
    """Decision 15: each unit is letterboxed in its own folder - the meter
    moved by its origin, the spectrum by its position."""
    pytest.importorskip("PIL.Image")   # letterbox.py measures the pictures
    gelo = {k.replace("800x480", "1280x800").replace("_1000", "_400"): v for k, v in GELO.items()
            if "01-20" not in k}
    name = "1280x720_g5_sm"
    rc, out, report = run(tmp_path, gelo, {
        name: ([unit(name, src=f"{name}/templates/{name}"),
                {**unit(name, "templates_spectrum", src=f"{name}/templates_spectrum/{name}"), "kind": "spectrum"}], {
            f"{name}/templates/{name}/meters.txt": "[SM]\nmeter.type = circular\nmeter.x = 10\nmeter.y = 10\n"
                                                    "bgr.filename = d.png\nspectrum.name = S\n",
            f"{name}/templates/{name}/d.png": b"D",
            f"{name}/templates_spectrum/{name}/spectrum.txt": "[S]\nspectrum.x = 5\nspectrum.y = 300\n",
        }),
    }, size="1280x800")
    assert rc == 0
    pack = out / name
    assert "meter.y = 50" in (pack / "templates/1280x800/meters.txt").read_text()
    assert "spectrum.y = 340" in (pack / "templates_spectrum/1280x800/spectrum.txt").read_text()
    assert [p["letterboxed_from"] for p in report["packs"] if p["dir"] == name] == ["1280x720"]


def test_describe_writes_the_pack_and_the_credits(tmp_path):
    rc, out, report = run(tmp_path, GELO, {})
    assert rc == 0
    stage = tmp_path / "stage"
    report_path = tmp_path / "report.json"
    assert describe.main([str(report_path), str(HERE / "pins.json"), str(stage)]) == 0
    assert not (stage / "usr/share/gexis/plugins").exists(), "the switch is the plugin row"
    pack = json.loads((stage / "opt/gexis-peppy/packs/800x480/pack.json").read_text())
    assert pack["size"] == "800x480" and pack["skins"] == 2
    assert [s["licence"] for s in pack["sources"]] == ["GPL-3.0"]
    assert pack["sources"][0]["pin"] == "sha256:" + json.loads((HERE / "pins.json").read_text())["gelo5"]["sets"]["800x480"]["sha256"]
    doc = stage / "usr/share/doc/gexis-skins-800x480"
    assert "GPL-3.0" in (doc / "copyright").read_text()
    assert "gelo5-1001: 01G5_A  =  gelo5: 01G5_A" in (doc / "dropped.txt").read_text()
    assert "Renamed (0):" in (doc / "renamed.txt").read_text()


def test_pins_cover_the_five_sizes_and_nothing_else():
    pins = json.loads((HERE / "pins.json").read_text())
    assert set(pins["gelo5"]["sets"]) == set(SIZES)
    for entry in pins["gelo5"]["sets"].values():
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        assert entry["file"].startswith("Gelo5_")
    # The 1280x800 set is the one gexis-skins has always pinned.
    old = (REPO / "packaging/skins/build.sh").read_text()
    assert pins["gelo5"]["sets"]["1280x800"]["sha256"] in old


def test_packaging_builds_every_pack_by_default():
    build = (REPO / "packaging/build.sh").read_text()
    line = re.search(r'^SKIN_PACKS="([^"]+)"', build, re.M).group(1).split()
    assert line == [f"skins-{s}" for s in SIZES]
    assert "$SKIN_PACKS" in re.search(r"^for pkg in \$\{\*:-([^}]+)\}", build, re.M).group(1)


def test_the_image_installs_no_skins():
    """ADR-0111 decision 9: the stage copies every package but the skins."""
    stage = (REPO / "image/stage-gexis/01-packages/00-run.sh").read_text()
    assert 'cp "${DEBS}"/*.deb' not in stage
    assert "gexis-skins_*|gexis-skins-*)" in stage
    verify = (REPO / "image/verify-image.sh").read_text()
    assert "/opt/gexis-peppy/skins /opt/gexis-peppy/packs" in verify


def test_the_release_does_not_depend_on_skins():
    """Decisions 9 and 10: nothing pulls a pack in, and a device that has
    gexis-skins keeps it - it hands over the one file gexis-player now
    carries, the screensaver's licence."""
    player = (REPO / "packaging/player/build.sh").read_text()
    names = re.search(r"^for pkg in (.+?); do", player, re.M | re.S).group(1)
    assert "gexis-skins" not in names
    assert "Replaces: gexis-skins" in player
    assert "licenses/peppy_screensaver/LICENSE" in player


def test_the_release_carries_every_pack():
    release = (REPO / "packaging/release/build.sh").read_text()
    assert "for size in " + " ".join(SIZES) + "; do" in release
    assert "image_count + pack_count" in release
