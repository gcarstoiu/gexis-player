# SPDX-License-Identifier: GPL-3.0-or-later
"""**Read once per answer** (George, 2026-10-16: tapping wallpaper topics felt
slow on sofapi).

`GET /settings` took 0.14 s on sofapi, and every other request to the player
waited behind it: the registry asks the hardware and the installed skins
again for each row that depends on them, and the screen's ports alone were
read from sysfs about a third of the time (py-spy, 2026-10-16).

Inside `with scope():` a function marked `@once` answers each set of
arguments once; outside a scope it reads every time, as before. **Nothing is
kept between answers**: a time-limited cache would hand the reload that
follows a plugin's install the list from before it, and nothing would ask
again.
"""
from __future__ import annotations

import contextlib
import contextvars
import functools
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")

_SCOPE: contextvars.ContextVar[dict | None] = contextvars.ContextVar("gexis_memo", default=None)


@contextlib.contextmanager
def scope() -> Iterator[None]:
    """One answer's worth of reads. Nested, the outer scope holds."""
    if _SCOPE.get() is not None:
        yield
        return
    token = _SCOPE.set({})
    try:
        yield
    finally:
        _SCOPE.reset(token)


def once(fn: Callable[..., T]) -> Callable[..., T]:
    """`fn`'s answer for these arguments, read once per scope. The answer is
    shared by everyone in the scope who asks, so `fn` must return something
    its callers only read."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        memo = _SCOPE.get()
        if memo is None:
            return fn(*args, **kwargs)
        try:
            key = (fn, args, tuple(sorted(kwargs.items())))
            hash(key)
        except TypeError:
            return fn(*args, **kwargs)
        if key not in memo:
            memo[key] = fn(*args, **kwargs)
        return memo[key]
    return wrapper
