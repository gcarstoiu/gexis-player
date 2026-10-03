#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every skin's display name in an assembled pack (George, 2026-10-02: "C").

    names.py <pack root> <W>x<H> [<names.tsv>]  ->  <pack root>/names.json

**The skin's own name stays the key.** A section name is what meters.txt,
the visualiser and the device's stored `skin` setting use, so it is never
changed; the picker shows the label this writes instead, keyed
`<folder>/<skin>`, as badge-slots.json is.

**A label reads like a catalogue: "Brand · Model · variant".**
- Gelo5's numbers go ("113G5_", "02PMN_"), as do pack prefixes ("t1800_",
  "1920x1080_"), underscores, and hyphens between words; a model code keeps
  its own (PLX-500, TA-N77, S+M).
- A brand (BRANDS) leads, spelt as the maker spells it, with the model after
  it - also when the skin glued them ("SonyK770" -> "Sony · K770").
- What a skin is a version of goes last: "S+M" (meters and spectrum),
  "meters only", "fanart", and on the turntables the album art's place -
  01/02/03 are "art on label", "art as record", "art beside" (the three
  presentations, ADR-0111 review). Elsewhere a second and third take are
  "II" and "III".
- Words in lower case are capitalised; long words in capitals ("TURN",
  "TAPE") are not shouted; short ones (NAD, SME, LED) stay as they are.
- names.tsv overrides the rule for a name it gets wrong, by the name with its
  numbers taken off; Volumio's stock colours are listed there.

Two skins that would read the same take " II", " III" in pack order (Gelo5
first, as for renames). A label is unique within its pack, or the build fails.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from assemble import TEMPLATES, blocks, read_text  # noqa: E402

DOT = " · "

#: Makers as they spell themselves. A skin naming one leads with it.
BRANDS = [
    "Accuphase", "Advance", "Akai", "Albrecht", "Ampex", "Audio Research", "Auna", "Audizio", "BASF",
    "Bang & Olufsen", "Berlant", "Blaupunkt", "BMC", "Bose", "BOSS", "Braun", "Bryston", "Burmester",
    "Cayin", "Cocktail Audio", "Crosley", "Cyrus", "Dan D'Agostino", "Denon", "Denver", "Dorrough",
    "Emerson", "Emotiva", "Esoteric", "Eversolo", "Fisher", "Fostex", "Goldtech", "Gramovox", "Grandioso",
    "Gryphon", "Hartman", "Hitachi", "Hyundai", "Jadis", "Kenwood", "Klanghelm", "Korg", "Krell", "Leben",
    "Line Magnetic", "Linn", "LG", "Luxman", "Lyngdorf", "Magnetocord", "Marantz", "Mark Levinson",
    "Marshall", "Maxell", "McIntosh", "Meier", "Metaxas", "MION", "NAD", "Naim", "Onkyo", "Optonica",
    "Otari", "Philips", "Pioneer", "Pro-Ject", "Quad", "Realistic", "Reloop", "Revox", "Roadstar", "Rose",
    "Rotel", "Sansui", "Sharp", "Shanling", "Siemens", "SME", "Sony", "SPL", "Studer", "T+A", "Tandberg",
    "Tascam", "TDK", "Teac", "TechDAS", "Technics", "TechniSat", "Teletronix", "Teufel", "Thorens",
    "Triplett", "Unison Research", "Vertere", "Vincent", "Volumio", "Wadax", "Weston", "Winamp", "Yamaha",
]
#: Spellings a skin uses for a brand above.
ALIASES = {
    "technisc": "Technics", "techinics": "Technics", "struder": "Studer", "audioresearch": "Audio Research",
    "bang-olufsen": "Bang & Olufsen", "bo": "Bang & Olufsen", "burmaster": "Burmester", "marklev": "Mark Levinson",
    "coctailaudio": "Cocktail Audio", "magnetcord": "Magnetocord", "dagostini": "Dan D'Agostino",
    "dagostino": "Dan D'Agostino", "dan-dagostino": "Dan D'Agostino", "dan_dagostino": "Dan D'Agostino",
    "dan_dagostimo": "Dan D'Agostino", "dorrought": "Dorrough", "simens": "Siemens", "pro-ject": "Pro-Ject",
    "project": "Pro-Ject", "technisat": "TechniSat", "advence": "Advance", "adv": "Advance",
    "teac": "Teac", "mion": "MION",
}
#: Two-word spellings of a brand, as split from "dan-dagostino".
ALIASES2 = {
    ("dan", "dagostino"): "Dan D'Agostino", ("dan", "dagostimo"): "Dan D'Agostino",
    ("bang", "olufsen"): "Bang & Olufsen", ("mark", "lev"): "Mark Levinson", ("tech", "das"): "TechDAS",
    ("coctail", "audio"): "Cocktail Audio",
}
ALIASES["advanced"] = "Advance"
#: Slips in an ordinary word, and words that are names in capitals.
WORDS = {"Turnable": "Turntable", "TURNTABLE": "Turntable", "Casette": "Cassette", "Osciloscope": "Oscilloscope",
         "NIxI": "Nixi", "NIxI2": "Nixi2", "Sacd": "SACD", "SACD": "SACD"}
TURNTABLE_VARIANTS = {"01": "art on label", "02": "art as record", "03": "art beside"}
ROMAN = {2: "II", 3: "III", 4: "IV", 5: "V"}


def load_overrides(path: Path | None) -> dict[str, str]:
    out = {}
    if path is None:
        return out
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if cells[0] == "name":
            continue
        if len(cells) != 2:
            raise SystemExit(f"names.tsv: two columns wanted: {line!r}")
        out[cells[0]] = cells[1]
    return out


def split_number(name: str) -> tuple[str, str | None]:
    """The name without Gelo5's numbering, and its take (01/02/03) if any."""
    # A rename's " (<pack>)" (decision 13): the twin then takes " II".
    name = re.sub(r" \([a-z0-9 ]+\)$", "", name)
    name = re.sub(r"^\d+(?:G5|PMN)_", "", name)
    name = re.sub(r"^(?:t1800|\d+x\d+)_", "", name)
    take = re.match(r"^(0[1-9])_(.*)$", name)
    if take:
        return take.group(2), take.group(1)
    return name, None


#: Ordinary words a skin writes in capitals.
SHOUTED = {"OLD", "NEW", "RED", "ONLY", "TURN", "TAPE", "TURNTABLE", "FULL"}


def words(text: str) -> list[str]:
    text = text.replace("_", " ")
    # A hyphen between two words is a space; one in a model code stays.
    text = re.sub(r"(?<=[A-Za-z]{2})-(?=[A-Za-z]{2})", " ", text)
    # Words run together: "BlackBlur", "RecordPlayer", "TubeHeadPhone".
    text = re.sub(r"(?<=[a-z]{2})(?=[A-Z][a-z])", " ", text)
    return [w for w in text.split() if w]


def tidy(word: str) -> str:
    if word in WORDS:
        return WORDS[word]
    if word.isalpha() and word.islower():
        return word[0].upper() + word[1:]
    if word.isalpha() and word.isupper() and (len(word) >= 4 or word in SHOUTED):
        return word.capitalize()
    return word


def brand_of(tokens: list[str]) -> tuple[str | None, list[str]]:
    """(brand, the rest) when the name starts with a maker."""
    lowered = [t.lower() for t in tokens]
    for brand in sorted(BRANDS, key=len, reverse=True):
        parts = brand.lower().split()
        if lowered[:len(parts)] == parts:
            return brand, tokens[len(parts):]
    first = lowered[0] if lowered else ""
    if tuple(lowered[:2]) in ALIASES2:
        return ALIASES2[tuple(lowered[:2])], tokens[2:]
    if first in ALIASES:
        return ALIASES[first], tokens[1:]
    # Glued: "SonyK770", "Technics1600", "OnkyoM508" - the model starting
    # with a digit or a capital, so "Advanced" is not Advance + "d".
    for brand in sorted(BRANDS + list(ALIASES), key=len, reverse=True):
        key = brand.lower().replace(" ", "")
        if first.startswith(key) and len(first) > len(key) and \
                (tokens[0][len(key)].isdigit() or tokens[0][len(key)].isupper()):
            rest = tokens[0][len(key):]
            canonical = ALIASES.get(brand.lower(), brand) if brand.lower() in ALIASES else brand
            return canonical, [rest, *tokens[1:]]
    return None, tokens


def label(name: str, folder: str, overrides: dict[str, str]) -> tuple[str, bool]:
    """(label, from an override)"""
    base, take = split_number(name)
    variants = []
    fanart = re.search(r"[ _]?Fanart$", base, re.I)
    if fanart:
        base, variants = base[:fanart.start()], ["fanart"]
    elif "fanart" in folder.lower():
        # The fanart packs' tape decks are named as the plain ones are.
        variants = ["fanart"]
    if base in overrides:
        text, overridden = overrides[base], True
    else:
        overridden = False
        rest = base
        tail = []
        for pattern, variant in ((r"[ _]S\+M$", "S+M"),
                                 (r"[ _](?:only|ONLY|Only)(?:[ _]meters)?$", "meters only")):
            found = re.search(pattern, rest)
            if found:
                rest, tail = rest[:found.start()], [variant] + tail
        tokens = words(rest)
        brand, model = brand_of(tokens)
        model_text = " ".join(tidy(w) for w in model)
        text = DOT.join(p for p in (brand, model_text) if p) or " ".join(tidy(w) for w in tokens)
        variants = tail + variants
    if take is not None:
        if "urntable" in folder:
            variants.append(TURNTABLE_VARIANTS.get(take, f"take {int(take)}"))
        elif take != "01":
            variants.append(ROMAN.get(int(take), take))
    return DOT.join([text, *variants]), overridden


def main(argv: list[str]) -> int:
    root, size = Path(argv[0]), argv[1]
    overrides = load_overrides(Path(argv[2]) if len(argv) > 2 else None)
    entries = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        for kind in TEMPLATES:
            meters = folder / kind / size / "meters.txt"
            if meters.is_file():
                for name, _l in blocks(read_text(meters)):
                    if name:
                        entries.append((folder.name, name))
    # Gelo5's own first, then the rest by folder: the earlier keeps the plain label.
    entries.sort(key=lambda e: (not e[0].startswith("gelo5"), e[0] != "gelo5", e[0], e[1]))
    names, seen, overridden = {}, {}, 0
    for folder, name in entries:
        text, by_override = label(name, folder, overrides)
        overridden += by_override
        n = seen.get(text, 0) + 1
        seen[text] = n
        names[f"{folder}/{name}"] = text if n == 1 else f"{text} {ROMAN.get(n, str(n))}"
    labels = list(names.values())
    clashes = {x for x in labels if labels.count(x) > 1}
    if clashes:
        print(f"ERROR: display names shared in {size}: {sorted(clashes)[:5]}", file=sys.stderr)
        return 1
    (root / "names.json").write_text(json.dumps({
        "_about": "Each skin's display name (George, 2026-10-02): 'Brand · Model · variant', "
                  "made by packaging/skin-packs/names.py from the skin's own name, which stays "
                  "its key everywhere. Keyed <folder>/<skin>.",
        "names": dict(sorted(names.items())),
    }, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"display names {size}: {len(names)}, {overridden} from names.tsv, {len(names) - overridden} by rule")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
