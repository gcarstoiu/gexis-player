"""Read once per answer, never kept between answers (George, 2026-10-16)."""
from __future__ import annotations

import pytest

from gexis_core import memo


def test_read_once_inside_an_answer_and_again_in_the_next():
    calls = []

    @memo.once
    def ports(where="drm"):
        calls.append(where)
        return [where]

    with memo.scope():
        assert ports() == ports() == ["drm"]
        assert ports("usb") == ["usb"]
    assert calls == ["drm", "usb"]
    # **Nothing kept between answers**: the reload after a plugin's install
    # has to see it.
    with memo.scope():
        ports()
    assert calls == ["drm", "usb", "drm"]
    # Outside any answer it reads every time, as it always did.
    ports()
    ports()
    assert calls == ["drm", "usb", "drm", "drm", "drm"]


def test_a_nested_scope_shares_the_outer_one_and_a_failure_is_not_kept():
    calls = []

    @memo.once
    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise OSError("not yet")
        return "ok"

    with memo.scope():
        with pytest.raises(OSError):
            flaky()
        with memo.scope():
            assert flaky() == "ok"
        assert flaky() == "ok"
    assert len(calls) == 2


def test_unhashable_arguments_are_read_as_before():
    @memo.once
    def first(items):
        return items[0]

    with memo.scope():
        assert first([3, 4]) == 3
