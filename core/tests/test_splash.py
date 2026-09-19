# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0043: the boot animation ends when the panel has painted.

The failure this guards against is a device that boots to an animation
nobody can get past, on a screen with no keyboard - so every path here is
about `drop()` being safe to call in situations where there is no splash.
"""
from __future__ import annotations

import subprocess

import pytest

from gexis_core.splash import Splash


class Recorder:
    def __init__(self, returncode=0, raises=None):
        self.calls = []
        self._returncode = returncode
        self._raises = raises

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if self._raises is not None:
            raise self._raises
        return subprocess.CompletedProcess(argv, self._returncode, b"", b"")


def test_the_panel_painting_quits_plymouth_retaining_the_last_frame(monkeypatch):
    run = Recorder()
    monkeypatch.setattr(subprocess, "run", run)
    splash = Splash(plymouth="/bin/plymouth")

    assert splash.drop() is True
    assert run.calls == [["/bin/plymouth", "quit", "--retain-splash"]]


def test_retain_splash_is_not_optional():
    """Without it plymouth clears to black, and the panel would paint over a
    blank screen instead of over the last frame - which is the flash this
    whole mechanism exists to avoid."""
    import inspect

    from gexis_core import splash as module

    assert "--retain-splash" in inspect.getsource(module.Splash.drop)


def test_a_second_report_does_nothing(monkeypatch):
    """A panel that reloads reports a first frame again. Quitting a splash
    that is already gone is harmless, but doing it once is honest."""
    run = Recorder()
    monkeypatch.setattr(subprocess, "run", run)
    splash = Splash()

    assert splash.drop() is True
    assert splash.drop() is False
    assert splash.drop() is False
    assert len(run.calls) == 1
    assert splash.dropped is True


@pytest.mark.parametrize(
    "recorder",
    [
        Recorder(raises=FileNotFoundError("no plymouth here")),
        Recorder(raises=subprocess.TimeoutExpired("plymouth", 5)),
        Recorder(returncode=1),
    ],
    ids=["not installed", "hung", "nothing to quit"],
)
def test_no_plymouth_is_not_an_error(monkeypatch, recorder):
    """A development machine has no plymouth, and a device booted without
    the splash has nothing to quit. Neither is the panel's problem, and
    neither may raise into the request handler."""
    monkeypatch.setattr(subprocess, "run", recorder)

    assert Splash().drop() is False
