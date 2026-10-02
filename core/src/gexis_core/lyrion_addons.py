# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Lyrion add-ons that come preinstalled** (ADR-0115 decisions 6 and
12): Material Skin, Music & Artist Information and Radio Now Playing,
installed by Lyrion itself from its own plugin list - not shipped by us - the
first time the server answers with the internet.

Lyrion has no command for it: its plugin page is a form where every plugin is
a checkbox, and saving it installs the ticked ones that are missing and
**disables the unticked ones that are there**. So the form is read as it is,
every field kept, only ours ticked, and sent back - exactly what a person on
that page does. Lyrion then wants a restart to load them.
"""
from __future__ import annotations

import logging
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

#: Lyrion's own names for them (the checkboxes' `name`).
WANTED = ("MaterialSkin", "MusicArtistInfo", "RadioNowPlaying")
PAGE = "/settings/server/plugins.html"


class _Form(HTMLParser):
    """The plugin page's `settingsForm`: its action and every field as a
    browser would submit it."""

    def __init__(self) -> None:
        super().__init__()
        self.action: str | None = None
        self.inside = False
        self.fields: list[tuple[str, str]] = []
        self.boxes: dict[str, bool] = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and a.get("name") == "settingsForm":
            self.inside = True
            self.action = a.get("action")
        elif tag == "input" and self.inside and a.get("name"):
            kind = (a.get("type") or "text").lower()
            if kind == "checkbox":
                self.boxes[a["name"]] = "checked" in a
                if "checked" in a:
                    self.fields.append((a["name"], a.get("value") or "on"))
            elif kind not in ("submit", "button", "image"):
                self.fields.append((a["name"], a.get("value") or ""))

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False


def read(page: str) -> _Form:
    form = _Form()
    form.feed(page)
    return form


def missing(page: str, wanted=WANTED) -> list[str]:
    """Which of ours the page lists and are not ticked (not installed)."""
    form = read(page)
    return [name for name in wanted if name in form.boxes and not form.boxes[name]]


def submission(page: str, wanted=WANTED) -> tuple[str, list[tuple[str, str]]]:
    """(the form's action, its fields) with every box as it was and ours
    ticked - nothing the user or Lyrion set is changed."""
    form = read(page)
    if form.action is None:
        raise ValueError("no settingsForm on the plugin page")
    fields = list(form.fields)
    have = {name for name, _ in fields}
    for name in wanted:
        if name in form.boxes and name not in have:
            fields.append((name, "on"))
    if not any(name == "saveSettings" for name, _ in fields):
        fields.append(("saveSettings", "1"))
    return form.action, fields
