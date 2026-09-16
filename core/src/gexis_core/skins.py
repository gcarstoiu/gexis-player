# SPDX-License-Identifier: GPL-3.0-or-later
"""Skin corpus parser and build-time validator (Phase 5 criteria 2 and 3).

**This does not change how skins are rendered.** The vendored PeppyMeter
parses them at runtime and is permissive by construction: Finding 007 §4
confirmed at the line level that it enumerates no keys and has no `else`
branch for an unknown `meter.type` — an unknown type is merely never
populated, and fails later as a `KeyError` when the skin is first selected.
ADR-0015 therefore makes this a separate, additive check that fails the
build instead.

The key sets below are **our corpus's**, not upstream's (Finding 007 §4's
recommendation): foonerd's fork deprecates `playinfo.maxwidth` in favour of
per-field spellings, while every Gelo5 section uses the legacy key, so a
validator built from upstream's current set would reject the whole corpus on
day one over a rename.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SECTION = re.compile(r"^\[(?P<name>.+?)\]\s*$")

CIRCULAR = "circular"
LINEAR = "linear"
METER_TYPES = {CIRCULAR, LINEAR}

#: Present in every section of both types.
COMMON_KEYS = {
    "albumart.border", "albumart.dimension", "albumart.mask", "albumart.pos",
    "bgr.filename", "channels", "config.extend", "fgr.filename", "font.color",
    "font.size.bold", "font.size.digi", "font.size.light", "font.size.regular",
    "indicator.filename", "meter.type", "meter.visible", "meter.x", "meter.y",
    "playinfo.album.color", "playinfo.album.maxwidth", "playinfo.album.pos",
    "playinfo.artist.color", "playinfo.artist.maxwidth", "playinfo.artist.pos",
    "playinfo.center", "playinfo.maxwidth", "playinfo.samplerate.pos",
    "playinfo.text.center", "playinfo.title.color", "playinfo.title.maxwidth",
    "playinfo.title.pos", "playinfo.type.color", "playinfo.type.dimension",
    "playinfo.type.pos", "screen.bgr", "spectrum.name", "spectrum.size",
    "spectrum.visible", "time.remaining.color", "time.remaining.pos",
    "ui.refresh.period",
}
CIRCULAR_KEYS = {
    "distance", "left.origin.x", "left.origin.y", "left.start.angle",
    "left.stop.angle", "right.origin.x", "right.origin.y", "right.start.angle",
    "right.stop.angle", "start.angle", "steps.per.degree", "stop.angle",
}
LINEAR_KEYS = {
    "direction", "indicator.type", "left.x", "left.y", "position.overload",
    "position.regular", "right.x", "right.y", "step.width.overload",
    "step.width.regular",
}
SPECTRUM_KEYS = {
    "bar.color", "bar.filename", "bar.gap", "bar.gradient", "bar.height",
    "bar.type", "bar.width", "bgr.color", "bgr.filename", "bgr.gradient",
    "bgr.type", "fgr.filename", "origin.x", "origin.y", "reflection.color",
    "reflection.filename", "reflection.gap", "reflection.gradient",
    "reflection.type", "spectrum.x", "spectrum.y", "steps", "topping.height",
    "topping.step",
}


class SkinError(Exception):
    """Raised with every problem found, not the first — a skin pack that
    breaks the contract should say how, once."""


@dataclass(frozen=True)
class Skin:
    name: str
    options: dict[str, str]

    @property
    def meter_type(self) -> str:
        return self.options.get("meter.type", "")

    @property
    def visible(self) -> bool:
        """`meter.visible = False` is honoured (criterion 3): a spectrum-only
        skin keeps its meter geometry but draws no meter."""
        return self.options.get("meter.visible", "True").strip().lower() != "false"

    @property
    def spectrum_name(self) -> str | None:
        """Linked to a spectrum section **by name, never by position**
        (ADR-0015; the reference document records that assuming by-index cost
        real time)."""
        return self.options.get("spectrum.name")


def parse(text: str) -> list[Skin]:
    skins: list[Skin] = []
    name: str | None = None
    options: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = SECTION.match(stripped)
        if match:
            if name is not None:
                skins.append(Skin(name, options))
            name, options = match.group("name"), {}
            continue
        if "=" in stripped and name is not None:
            key, value = stripped.split("=", 1)
            options[key.strip()] = value.strip()
    if name is not None:
        skins.append(Skin(name, options))
    return skins


def validate(meters: list[Skin], spectrum: list[Skin] | None = None) -> None:
    spectrum = spectrum or []
    problems: list[str] = []
    spectrum_names = {s.name for s in spectrum}

    seen: set[str] = set()
    for skin in meters:
        if skin.name in seen:
            problems.append(f"{skin.name}: duplicate section")
        seen.add(skin.name)

        if skin.meter_type not in METER_TYPES:
            problems.append(
                f"{skin.name}: meter.type {skin.meter_type!r} is not one of {sorted(METER_TYPES)}"
            )
            continue
        allowed = COMMON_KEYS | (CIRCULAR_KEYS if skin.meter_type == CIRCULAR else LINEAR_KEYS)
        for key in sorted(set(skin.options) - allowed):
            problems.append(f"{skin.name}: unknown key {key!r} for a {skin.meter_type} meter")

        linked = skin.spectrum_name
        if linked is not None and linked not in spectrum_names:
            problems.append(f"{skin.name}: spectrum.name {linked!r} matches no spectrum section")

    for section in spectrum:
        for key in sorted(set(section.options) - SPECTRUM_KEYS):
            problems.append(f"spectrum {section.name}: unknown key {key!r}")

    if problems:
        raise SkinError(f"{len(problems)} problem(s):\n  " + "\n  ".join(problems))


def load(directory: Path) -> tuple[list[Skin], list[Skin]]:
    """The corpus as shipped: `templates/meters.txt` plus the spectrum pair."""
    meters = parse((directory / "templates" / "meters.txt").read_text())
    spectrum_dir = directory / "templates_spectrum"
    meters += parse((spectrum_dir / "meters.txt").read_text())
    spectrum = parse((spectrum_dir / "spectrum.txt").read_text())
    return meters, spectrum


def main(argv: list[str] | None = None) -> int:
    """`python -m gexis_core.skins <corpus dir>` — the build-time gate."""
    import sys

    args = sys.argv[1:] if argv is None else argv
    directory = Path(args[0]) if args else Path("skins")
    meters, spectrum = load(directory)
    try:
        validate(meters, spectrum)
    except SkinError as exc:
        print(f"ERROR: {directory}: {exc}", file=sys.stderr)
        return 1
    print(f"{directory}: {len(meters)} skins and {len(spectrum)} spectrum sections validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
