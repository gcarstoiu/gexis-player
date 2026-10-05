"""ADR-0054 §5: the starting volume holds for a moment after it is handed."""
from gexis_core.start_guard import HOLD_S, StartGuard


def test_the_phone_s_own_level_arriving_at_once_is_not_followed():
    """2026-10-05: handed 60, Spotify reported 100 0.9 s later."""
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0)
    assert guard.holding("spotify", 100, now=100.9) == 60


def test_lower_is_followed_and_after_the_hold_everything_is():
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0)
    assert guard.holding("spotify", 40, now=101.0) is None, "turning it down is heard"
    assert guard.holding("spotify", 90, now=100.0 + HOLD_S + 0.1) is None, "after the hold, a person is heard"
    assert guard.holding("spotify", 100, now=200.0) is None


def test_only_the_renderer_handed_a_level_is_held():
    guard = StartGuard()
    guard.handed("spotify", 60, now=100.0)
    assert guard.holding("lms", 100, now=100.5) is None
