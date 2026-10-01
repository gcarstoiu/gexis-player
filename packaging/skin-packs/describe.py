#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write what a skin pack says about itself (ADR-0111), from assemble.py's
report and pins.json:

- `<pack root>/pack.json`, for the visualiser and the core: the size, the
  skin count, the sources with their pins and licences, and each folder;
- `/usr/share/gexis/plugins/skins-<WxH>/plugin.json`, the ADR-0086 manifest
  with kind `"skins"`: the pack is a plugin (decision 3);
- `/usr/share/doc/gexis-skins-<WxH>/copyright`, each source and the licence it
  is taken under (decision 6), and `dropped.txt`, every skin, pack and file
  left out and why (decision 8).

    describe.py <report.json> <pins.json> <stage root>

Every output is sorted and carries no time, so the same inputs give the same
bytes (packaging/build.sh: reproducible).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKS = "/opt/gexis-peppy/packs"


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def sources(report: dict, pins: dict) -> list[dict]:
    size = report["size"]
    used = {p["source"] for p in report["packs"]}
    out = []
    gelo, cat = pins["gelo5"], pins["catalog"]
    if "Gelo5" in used:
        s = gelo["sets"][size]
        out.append({"name": gelo["name"], "url": f"{gelo['release']}/{s['file']}",
                    "pin": f"sha256:{s['sha256']}", "licence": gelo["licence"],
                    "credit": gelo["credit"]})
    if cat["name"] in used:
        out.append({"name": cat["name"], "url": f"{cat['url']}/tree/{cat['commit']}",
                    "pin": f"commit:{cat['commit']}; each zip by catalog/index.json's sha256",
                    "licence": cat["licence"], "credit": cat["credit"]})
    return out


def main(argv: list[str]) -> int:
    report = json.loads(Path(argv[0]).read_text())
    pins = json.loads(Path(argv[1]).read_text())
    stage = Path(argv[2])
    size = report["size"]
    width, height = (int(v) for v in size.split("x"))
    package = f"gexis-skins-{size}"
    src = sources(report, pins)

    dump(stage / PACKS.lstrip("/") / size / "pack.json", {
        "size": size,
        "width": width,
        "height": height,
        "package": package,
        "skins": report["skins"],
        "sources": src,
        # Each folder under this root: its source, its skins, and for the
        # 1280x720 packs the size they were letterboxed from.
        "packs": report["packs"],
    })

    # ADR-0086's manifest. `kind: "skins"` is new: the core's KINDS does not
    # know it yet, and until it does it skips this manifest with a warning
    # rather than failing (plugins.installed). `unit` is the visualiser's, the
    # unit this pack is what gives anything to draw.
    dump(stage / "usr/share/gexis/plugins" / f"skins-{size}" / "plugin.json", {
        "id": f"skins-{size}",
        "name": f"Visualiser skins, {width}×{height}",
        "kind": "skins",
        "unit": "gexis-peppy.service",
        "area": "display",
        "package": package,
        "size": size,
        "skins": report["skins"],
        "pack": f"{PACKS}/{size}",
    })

    doc = stage / "usr/share/doc" / package
    doc.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{package}: PeppyMeter skins for a {width}x{height} screen (ADR-0111).",
        "",
        "No skin states a licence of its own. Each is redistributed under the",
        "licence of the repository that publishes it (ADR-0111 decision 6,",
        "ADR-0096 decision 2; Finding 107):",
        "",
    ]
    for s in src:
        lines += [f"Source:  {s['name']}", f"URL:     {s['url']}", f"Pin:     {s['pin']}",
                  f"Licence: {s['licence']}", f"Credit:  {s['credit']}", ""]
    lines += [
        "The licence texts are beside this file: LICENSE.peppy_templates (MIT)",
        "and LICENSE.PeppyMeter.doc (GPL-3.0).",
        "",
        "Many skins show a manufacturer's name, logo or product, and some show",
        "other third-party artwork (Finding 107). Those marks belong to their",
        "owners; their appearance here implies no endorsement.",
        "",
        "Gexis Player's own changes: previews and repeated skins left out (see",
        "dropped.txt), and the 1280x720 packs of the 1280x800 set letterboxed",
        "by letterbox.py (ADR-0096).",
    ]
    (doc / "copyright").write_text("\n".join(lines) + "\n")

    d = [f"What {package} leaves out of its archives, and why (ADR-0111 decision 8).", ""]
    d.append(f"Skins shipped: {report['skins']}, in {len(report['packs'])} folders.")
    d += ["", f"Folders left out ({len(report['dropped_packs'])}):"]
    d += [f"  {p['pack']}: {p['reason']}" for p in report["dropped_packs"]] or ["  none"]
    d += ["", f"Skins left out as byte-identical repeats ({len(report['dropped_skins'])}):",
          "  (identical keys and values, and identical files behind every file they name)"]
    d += [f"  {s['pack']}: {s['skin']}  =  {s['same_as']}" for s in report["dropped_skins"]] or ["  none"]
    d += ["", f"Files left out ({len(report['dropped_files'])}):"]
    d += [f"  {f['pack']}: {f['file']} ({f['reason']})" for f in report["dropped_files"]] or ["  none"]
    d += ["", f"Names two folders share, with different skins behind them ({len(report['name_clashes'])}):",
          "  (shipped, since they are not repeats; a name resolves to one of them)"]
    d += [f"  {c['skin']}: {', '.join(c['in'])}" for c in report["name_clashes"]] or ["  none"]
    (doc / "dropped.txt").write_text("\n".join(d) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
