"""ADR-0131 amended 2026-10-18: what a backup restores, a line each, by the
Settings section the setting is in."""

from types import SimpleNamespace

from gexis_core import restore_review
from gexis_core.settings_registry import load_registry

REGISTRY = [
    {"id": "audio", "label": "Audio", "rows": [
        {"key": "output_device", "type": "choice", "label": "Output"},
        {"key": "hidden_one", "type": "toggle", "label": "Hidden", "surfaced": False},
        {"key": "backup", "type": "action", "label": "Back up now"}]},
    {"id": "display", "label": "Display", "rows": [
        {"type": "group", "label": "Idle screen"},
        {"key": "idle_enabled", "type": "toggle", "label": "Idle screen"},
        {"key": "idle_background", "type": "choice", "label": "Background"}]},
    {"id": "sources", "label": "Sources", "rows": []},
    {"id": "plugins", "label": "Plugins", "rows": []},
]
PLEX = SimpleNamespace(id="plexamp", name="Plexamp", area="sources", settings=(
    {"key": "claim_token", "type": "text", "label": "Claim", "secret": True},
    {"key": "quality", "type": "choice", "label": "Quality"}))


def test_settings_by_section_in_settings_order_with_their_subgroup():
    values = {"idle_background": "Black", "output_device": "DAC", "idle_enabled": True,
              "hidden_one": True, "backup": None, "_settings_schema": 12}
    got = restore_review.sections(values, [], REGISTRY)
    assert got == [{"id": "audio", "label": "Audio", "items": ["Output"]},
                   {"id": "display", "label": "Display", "items": ["Idle screen", "Idle screen · Background"]}]


def test_plugins_and_what_the_backup_carries_go_where_they_belong():
    values = {"plexamp.enabled": True, "plexamp.claim_token": "x", "plexamp.quality": "High"}
    got = restore_review.sections(values, [("sources", "Spotify sign-in"), ("nowhere", "lost")], REGISTRY, [PLEX])
    assert got == [{"id": "sources", "label": "Sources", "items": ["Plexamp · Quality", "Spotify sign-in"]},
                   {"id": "plugins", "label": "Plugins", "items": ["Plexamp, switched on"]}]


def test_the_shipped_registry_groups_every_section():
    """The real registry: a section id the carried data names exists."""
    ids = {g["id"] for g in load_registry()}
    assert {"audio", "sources", "handoff", "display", "enrich", "plugins", "system"} <= ids
