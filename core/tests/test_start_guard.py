"""ADR-0054 §5: the starting volume holds for a moment after it is handed.
Levels in percent; the caller compares a report against it in its own scale."""
from gexis_core.start_guard import HOLD_S, UNTOLD_MAX_S, StartGuard


def test_the_phone_s_own_level_arriving_at_once_is_answered():
    """2026-10-05: handed 60, Spotify reported 100 0.9 s later."""
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0)
    assert guard.held("spotify", now=100.9) == 60


def test_after_the_hold_everything_is_followed():
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0)
    assert guard.held("spotify", now=100.0 + HOLD_S + 0.1) is None, "after the hold, a person is heard"
    assert guard.held("spotify", now=200.0) is None


def test_only_the_renderer_handed_a_level_is_held():
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0)
    assert guard.held("lms", now=100.5) is None


def test_a_renderer_not_yet_told_is_held_until_it_is():
    """2026-10-07, guestpi: Spotify's session became active 3.7 s after it took
    the device, after the handoff had run out of time - and it started at 100."""
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0, told=False)
    assert guard.held("spotify", now=100.0 + HOLD_S + 2) == 60, "not told yet: still held"
    guard.told("spotify", now=106.0)
    assert guard.held("spotify", now=106.0 + HOLD_S - 0.1) == 60, "the hold runs from the telling"
    assert guard.held("spotify", now=106.0 + HOLD_S + 0.1) is None


def test_a_renderer_never_told_is_not_held_for_ever():
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0, told=False)
    assert guard.held("spotify", now=100.0 + UNTOLD_MAX_S + HOLD_S + 1) is None


def test_a_restart_holds_longer_than_a_takeover():
    """guestpi, 2026-10-07: go-librespot's first report after an output
    change came 12 s after its restart - past a takeover's 15 s would still
    hold it, but a slow reconnect would not; a restart holds 30 s."""
    guard = StartGuard()
    guard.handed("spotify", 20, now=0.0, told=False, untold_max_s=30.0)
    assert guard.held("spotify", now=20.0) == 20
    assert guard.held("spotify", now=31.0) is None
