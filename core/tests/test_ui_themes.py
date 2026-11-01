"""Every colour a theme changes reaches the screens through a token (ADR-0171).

A theme is a set of token values: a colour written into a component as a
literal stays today's in every theme, and on a light theme that is dark ink
on dark ground. This reads the sources, as test_ui_reveal_marker.py does:
every colour literal in a component's styles, and in its `style=`
attributes, that the design's rule recolours (ui/src/lib/themeRule.js,
read here so the two cannot part) must be a token instead; and every corner
the rule scales. ui/scripts/themes.mjs --check, run by the UI's build, keeps
themes.css itself current.
"""
import re
from pathlib import Path

import pytest

UI = Path(__file__).parents[2] / "ui" / "src"
RULE = (UI / "lib" / "themeRule.js").read_text()
#: Pictures of other screens - weather, the test pattern, Personalise's
#: miniatures of idle screens and phones - keep their own colours.
PICTURES = {"lib/weatherSets.js", "screens/WeatherIcon.svelte", "screens/TestPattern.svelte",
            "screens/personalise/PanelMini.svelte", "screens/personalise/PhoneDeviceList.svelte"}

FAMILY = {tuple(map(int, k.split(","))) for k in re.findall(r"'(\d+,\d+,\d+)': '\w+'", RULE)}
SPECIAL = set(re.findall(r"h === '(#[0-9a-f]{6})'", RULE))
COLOUR = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)"
                    r"|#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F\w])")
RADIUS = re.compile(r"border(?:-(?:top|bottom)-(?:left|right))?-radius\s*:\s*([^;\"}{]+)")


def recoloured(m) -> bool:
    """Whether the rule changes this colour in some theme (build.js's makeMap)."""
    if m.group(5):
        h = m.group(5).lower()
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        rgb, a, is_hex = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), 1.0, True
        if "#" + h in SPECIAL:
            return True
    else:
        rgb = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        a, is_hex = (1.0 if m.group(4) is None else float(m.group(4))), False
    if rgb in FAMILY:
        return True
    if rgb in ((255, 255, 255), (0, 0, 0)) and a < 1:
        return True
    return max(rgb) < 75 and rgb[2] >= rgb[0] and rgb[2] > 8


def styles(path: Path) -> list[str]:
    """The CSS of a component: its <style> blocks and its style= attributes, comments and url()s out."""
    text = path.read_text()
    if path.suffix == ".css":
        parts = [text]
    else:
        parts = re.findall(r"<style\b[^>]*>(.*?)</style>", text, re.S)
        markup = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", text, flags=re.S)
        parts += re.findall(r'\bstyle(?::[\w-]+)?="([^"]*)"', markup)
    return [re.sub(r"/\*.*?\*/|url\([^)]*\)", "", p, flags=re.S) for p in parts]


SOURCES = sorted(p for p in UI.rglob("*") if p.suffix in (".svelte", ".css")
                 and p.parent.name != "styles" and p.relative_to(UI).as_posix() not in PICTURES)


def test_the_rule_is_read():
    assert len(FAMILY) == 16 and len(SPECIAL) == 6, "themeRule.js's tables, not nothing"


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.relative_to(UI).as_posix())
def test_colours_and_corners_go_through_tokens(path):
    literals, corners = [], []
    for css in styles(path):
        literals += [m.group(0) for m in COLOUR.finditer(css) if recoloured(m)]
        for r in RADIUS.finditer(css):
            corners += [v for v in re.findall(r"(?<![\w.-])(\d+(?:\.\d+)?)px", r.group(1)) if 4 <= float(v) < 900]
    assert not literals, f"colours a theme changes, written as literals: {sorted(set(literals))}"
    assert not corners, f"corners a theme scales, written in px: {sorted(set(corners))}"
