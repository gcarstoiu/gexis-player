"""No page the panel shows in a frame opens a window over the player
(ADR-0178 decision 3).

A dashboard link that opened a new window put it over the player, with no
way back by touch: the kiosk has no tabs and no window controls. This reads
the sources: there is no UI test harness, and the rule is one of markup.
"""
import re
from pathlib import Path

UI = Path(__file__).parents[2] / "ui" / "src"
SANDBOX = re.compile(r'sandbox="([^"]*)"')


def test_no_frame_may_open_a_window_or_leave_the_player():
    found = {path: SANDBOX.findall(path.read_text()) for path in UI.rglob("*.svelte")}
    frames = {path: flags for path, flags in found.items() if flags}
    assert len(frames) >= 3, "found the frames, not nothing"
    for path, flags in frames.items():
        for flag in flags:
            assert "allow-popups" not in flag.split(), f"{path.name}: {flag}"
            assert not any(f.startswith("allow-top-navigation") for f in flag.split()), f"{path.name}: {flag}"
