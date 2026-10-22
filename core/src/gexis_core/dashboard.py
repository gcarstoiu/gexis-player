# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0156: a Home Assistant dashboard on the screen** (Phase 18).

One dashboard per player, its room's, shown full screen by the panel in its
own page and every part of it usable. It comes up from a button on the panel
or a phone, from Home Assistant through the API, or - at the times set - in
place of the idle screen. Music is not touched, and it stays until it is
dismissed: by the panel's edge tab, a phone or the API, or by its scheduled
time ending when the schedule put it up.

The core holds whether it is up and who asked, and whether a scheduled time
is on now, in the panel state; the panel draws it. The player changes nothing
in Home Assistant (decision 8): framing and signing in are the user's to set
up there, and `probe` says which is missing.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
from collections.abc import Callable

from .standby import in_standby_time

logger = logging.getLogger("gexis_core.dashboard")

#: Who put the dashboard up: a person (panel, phone, Home Assistant) or the
#: schedule. Only what the schedule put up does the schedule take down.
ASKED = "asked"
SCHEDULE = "schedule"


class Dashboard:
    """Up or not, and who asked. `publish(shown, by)` tells the panel state."""

    def __init__(self, publish: Callable[[bool, str | None], None]) -> None:
        self._publish = publish
        self.shown = False
        self.by: str | None = None

    def show(self, by: str = ASKED) -> bool:
        # A person's ask over the schedule's makes it theirs: the schedule's
        # end no longer takes it down.
        if self.shown and (self.by == by or self.by == ASKED):
            return False
        self.shown, self.by = True, by
        self._publish(True, by)
        logger.info("dashboard: up (%s)", by)
        return True

    def hide(self, by: str = ASKED) -> bool:
        if not self.shown:
            return False
        self.shown, self.by = False, None
        self._publish(False, None)
        logger.info("dashboard: down (%s)", by)
        return True


class DashboardSchedule:
    """**Decision 2: in place of the idle screen at the times set.** Inside
    them the panel shows the dashboard where it would show the idle screen
    (it knows when that is; `on_time(True)` tells it); when they end, a
    dashboard the schedule put up comes down and the idle screen follows.

    `value(key)` reads a setting."""

    def __init__(self, dashboard: Dashboard, value, on_time: Callable[[bool], None],
                 *, now=datetime.datetime.now) -> None:
        self._dashboard = dashboard
        self._value = value
        self._on_time = on_time
        self._now = now

    def inside_now(self) -> bool:
        on = (self._value("dashboard_schedule") is True
              and self._value("headless") is not True
              and bool((self._value("dashboard_url") or "").strip()))
        return on and in_standby_time(self._now(), self._value("dashboard_times") or [])

    def tick(self) -> None:
        inside = self.inside_now()
        self._on_time(inside)
        if not inside and self._dashboard.shown and self._dashboard.by == SCHEDULE:
            self._dashboard.hide(SCHEDULE)

    async def run(self, every: float = 15.0) -> None:
        while True:
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - a schedule must not die quietly
                logger.exception("dashboard: the schedule's tick failed")
            await asyncio.sleep(every)


#: What the panel says when the dashboard cannot show (decision 8, and the
#: ADR's "never a blank screen"): what is missing, and where it is set.
REASONS = {
    "unconfigured": "No dashboard address is set. Add it in Settings → Display → Home Assistant dashboard.",
    "unreachable": "The dashboard's address does not answer. Check it in Settings, and that Home Assistant is running.",
    "refuses framing": "Home Assistant does not allow its pages to be shown inside another page. In Home Assistant, turn off Send X-Frame-Options (Settings → System → Network → HTTP server → More options), or set use_x_frame_options: false under http before version 2026.10.",
}


def explain(reason: str | None) -> str | None:
    """The panel's sentence for a probe's `reason`; an HTTP error says its status."""
    if reason is None:
        return None
    if reason.startswith("http "):
        return f"The dashboard's address answers with an error ({reason[5:]}). Check it in Settings."
    return REASONS.get(reason, "The dashboard cannot be shown here.")
