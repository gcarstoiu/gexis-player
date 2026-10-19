"""The library's background with nothing playing is one of the player's own
Calm wallpapers (George, 2026-10-18). The core serves only names in the
credits list, so a picture renamed or dropped there would leave the panel
grey without an error."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_resting_picture_is_a_credited_calm_wallpaper():
    panel = (ROOT / "ui/src/screens/PanelBackground.svelte").read_text()
    name = re.search(r"RESTING = '/idle/wallpaper/own/([^']+)'", panel).group(1)
    credits = json.loads((ROOT / "wallpapers/credits.json").read_text())
    entries = credits if isinstance(credits, list) else credits.get("pictures", credits)
    files = {e["file"] for e in (entries.values() if isinstance(entries, dict) else entries)}
    assert name.startswith("calm/") and name in files
    assert (ROOT / "wallpapers" / name).is_file()
