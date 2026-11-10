# SPDX-License-Identifier: GPL-3.0-or-later
"""**Room correction as the player keeps it and shows it** (ADR-0175).

Between the routes and the rest: the state is read from the settings store
(`room_correction.KEY`), changed through `room_correction.Room`'s
operations, written back, published on `/state` (the summary every screen
needs: the Settings row, the *Room* control, the panel while it measures)
and given in full by `GET /room-correction` (the page and its chart).

**The stage is the equaliser's** (items 1-2): `in_path` and `stage` are what
the equaliser's controller asks for each output, so switching room
correction on or off changes the path when the equaliser is off (a moment
of silence, C7) and only the cuts when it is on; *Hear it without* only
ever changes the cuts.

**A run** (`room_run.Run`) takes the stage for itself while it measures:
the equaliser flat, the cuts none or those being checked.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Awaitable, Callable

from gexis_core import room_correction as rc
from gexis_core.room_correction import Room, RoomError

logger = logging.getLogger("gexis_core.room_control")

#: The month names for *Full range · measured 3 November*.
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December")


def day(date: str, year: bool = False) -> str:
    """*3 November* (or *3 November 2026*) from the stored ISO date."""
    try:
        d = datetime.date.fromisoformat(date)
    except (TypeError, ValueError):
        return date or ""
    return f"{d.day} {_MONTHS[d.month - 1]}" + (f" {d.year}" if year else "")


class RoomControl:
    def __init__(self, store, *,
                 output: Callable[[], object | None],
                 kind: Callable[[object], str],
                 reopen: Callable[[str], Awaitable[None]],
                 sync: Callable[[], Awaitable[None]],
                 take: Callable[[], Awaitable[None]],
                 release: Callable[[], Awaitable[None]],
                 loud: Callable[[], Awaitable[None]],
                 quiet: Callable[[], Awaitable[None]],
                 eq_on: Callable[[str], bool],
                 dsd: Callable[[], bool] = lambda: False,
                 grouped: Callable[[], bool] = lambda: False,
                 busy: Callable[[], str | None] = lambda: None,
                 screen: Callable[[], bool] = lambda: True,
                 playing: Callable[[], str | None] = lambda: None,
                 address: Callable[[], str | None] = lambda: None,
                 find_mic=None, audio=None,
                 publish: Callable[[dict], None] = lambda summary: None,
                 changed: Callable[[], None] = lambda: None,
                 today: Callable[[], str] | None = None,
                 run_options: dict | None = None):
        from gexis_core import room_mic
        self._store = store
        self._output = output
        self._kind = kind
        self._reopen = reopen
        self._sync = sync
        self._take = take
        self._release = release
        self._loud = loud
        self._quiet = quiet
        self._eq_on = eq_on
        self._dsd = dsd
        self._grouped = grouped
        self._busy = busy
        self._screen = screen
        self._playing = playing
        self._address = address
        self._find_mic = find_mic or room_mic.find
        self._audio = audio or (lambda mic, cal: room_mic.Audio(mic, cal))
        self._publish = publish
        self._changed = changed
        self._today = today or (lambda: datetime.date.today().isoformat())
        #: For the tests: the run's clock and sweep length.
        self._run_options = run_options or {}
        self._lock = asyncio.Lock()
        self.run = None              # the run in progress, or the last until *Done*
        self._run_stage = None       # what a run wants on the stage
        self._run_card: str | None = None
        self._ended: dict | None = None

    # -- reading ------------------------------------------------------------------

    def state(self) -> Room:
        return Room.from_settings(self._store.get(rc.KEY))

    def running(self) -> bool:
        """A run shows: from its start until it has ended (Cancel ends it at
        once, though putting the player back follows)."""
        return self.run is not None and self.run.ended is None

    def _active(self, card: str | None = None) -> bool:
        """A run holds the player (from its start to its end, *Keep it*'s
        storing excluded), on `card` if given."""
        return (self.run is not None and self.run.ended is None
                and (card is None or self._run_card == card))

    def in_path(self, card: str) -> bool:
        """Whether room correction needs the stage on `card`: on (*Without*
        included), or measuring there."""
        return self._active(card) or self.state().in_path(card)

    def eq_bypassed(self, card: str) -> bool:
        """While a run measures on `card`, the equaliser is flat: the room as
        it is (item 4)."""
        return self._active(card)

    def stage(self, card: str):
        """The cuts the stage plays on `card` (`equaliser.room_stage`'s
        argument)."""
        if self._active(card):
            return self._run_stage
        return self.state().stage(card)

    def frozen(self) -> str | None:
        """The reason no source may take the device (arbitration's `frozen`),
        while a run holds it - until the player is put back after it."""
        held = self.run is not None and not self.run.released
        return "the room is being measured" if held else None

    def _microphone(self) -> dict:
        status, mic = self._find_mic()
        cal = self.state().calibration()
        out = {"state": status, "name": "miniDSP UMIK-1" if status == "found" else None,
               "gain_db": mic.gain_db if mic else None}
        # `again`: kept by Phase 29 to 2 kHz only, so given again before a
        # measurement (George, 2026-11-08).
        out["calibration"] = None if cal is None else {
            "serial": rc.shown_serial(cal.serial), "angle": cal.angle, "date": cal.date, "again": not cal.full}
        return out

    def _row(self, here: rc.OutputRoom) -> str:
        """The Settings row's state (design/source/29 R01-R04, worded as
        design/source/30 draws it: the reach, or Without)."""
        if here.measured is None or here.measured.nothing_to_correct:
            return "Not measured yet"
        if not here.on:
            return "Off"
        if here.without:
            return "Without · comparing, no correction"
        if here.measured.range != rc.FULL:
            return "Bass · measured for the bass only"
        return f"{'Bass' if here.reach == rc.BASS else 'Full range'} · measured {day(here.measured.date)}"

    def summary(self) -> dict | None:
        """**What `/state` carries**: enough for the Settings row, the *Room*
        control and the panel while it measures; the curves are not in it."""
        output = self._output()
        if output is None:
            return None
        here = self.state().output(output.card)
        measured = here.measured if (here.measured and not here.measured.nothing_to_correct) else None
        run = self.run
        return {
            "output": {"card": output.card, "name": output.label, "kind": self._kind(output)},
            "on": here.on,
            "without": here.without,
            # ADR-0177: how far it reaches, and how far the measurement was
            # made (one from before Phase 30 holds it at the bass).
            "reach": here.reach,
            "measured": None if measured is None else {
                "date": measured.date, "day": day(measured.date), "checked": measured.checked,
                "range": measured.range},
            "row": self._row(here),
            "dsd": bool(here.on and self._dsd()),
            "run": run.state.as_dict() if self.running() else None,
            "ended": self._ended,
        }

    def snapshot(self) -> dict | None:
        """**Everything the page draws** (`GET /room-correction`): the
        summary, the microphone and its calibration, whether a run can start
        and why not, the last measurement's chart, and a run's own."""
        out = self.summary()
        if out is None:
            return None
        output = self._output()
        here = self.state().output(output.card)
        measured = here.measured if (here.measured and not here.measured.nothing_to_correct) else None
        out["microphone"] = self._microphone()
        out["can_measure"], out["why_not"] = self._can_measure(out["microphone"])
        out["screen"] = bool(self._screen())
        out["playing"] = self._playing()
        # The panel's *Measure from your phone*: the player's page, opened
        # at Room correction (`#room`), and the address as it is typed.
        at = self._address()
        out["address"] = None if not at else {"shown": at, "url": f"http://{at}/#room"}
        out["eq_on"] = bool(self._eq_on(output.card))
        out["chart"] = rc.chart(measured)
        if measured is not None:
            out["measured"].update(self._figures(measured), year=day(measured.date, year=True),
                                   positions=measured.positions)
            out["cuts"] = {k: rc.shown(measured.cuts(k)) for k in rc.CHANNELS}
            out["above"] = {k: rc.shown(measured.above(k)) for k in rc.CHANNELS}
        pending = getattr(self.run, "pending", None) if self.run is not None else None
        if pending is not None and self.running():
            out["pending"] = {
                "chart": rc.chart(pending), "nothing_to_cut": pending.nothing_to_cut,
                "nothing_to_correct": pending.nothing_to_correct, "checked": pending.checked,
                **self._figures(pending),
                "cuts": {k: rc.shown(pending.cuts(k)) for k in rc.CHANNELS},
                "above": {k: rc.shown(pending.above(k)) for k in rc.CHANNELS}}
        return out

    @staticmethod
    def _figures(m: rc.Measurement) -> dict:
        """The result's figures (the design's §2): *Peaks down by up to N
        dB*, *within N dB of the speaker's own balance* after and the room's
        own, the positions worse than before, and how far it was made."""
        return {"peaks_down": round(m.peaks_down()), "within": m.within(), "room_within": m.within(room=True),
                "nothing_to_cut": m.nothing_to_cut, "nothing_above": m.nothing_above, "range": m.range,
                "worse": [list(w) for w in m.worse]}

    def _held(self) -> bool:
        """A run, or putting the player back after one."""
        return self.run is not None and not self.run.released

    def _can_measure(self, mic: dict) -> tuple[bool, str | None]:
        if self._held():
            return False, "running"
        if mic["state"] != "found":
            return False, "microphone"
        if mic["calibration"] is None or mic["calibration"]["again"]:
            return False, "calibration"
        if self._grouped():
            return False, "grouped"
        if self._busy():
            return False, "busy"
        return True, None

    def publish(self) -> None:
        self._publish(self.summary())

    # -- changing ------------------------------------------------------------------

    def _card(self) -> str:
        output = self._output()
        if output is None:
            raise RoomError("There is no output to set it for.")
        return output.card

    async def update(self, changes: dict) -> dict:
        """`on`, `without` and `reach` (ADR-0177), for the output in use."""
        if not isinstance(changes, dict) or not changes:
            raise RoomError("Nothing to change.")
        unknown = set(changes) - {"on", "without", "reach"}
        if unknown:
            raise RoomError(f"Unknown: {', '.join(sorted(unknown))}.")
        for key in ("on", "without"):
            if key in changes and not isinstance(changes[key], bool):
                raise RoomError(f"{key.capitalize()} is true or false.")
        if "reach" in changes and changes["reach"] not in rc.REACHES:
            raise RoomError("Reach is bass or full.")
        async with self._lock:
            if self._held():
                raise RoomError("Not while the room is being measured.")
            card = self._card()
            old = self.state()
            new = old
            if "on" in changes:
                new = new.set_on(card, changes["on"])
                if not changes["on"]:
                    here = new.output(card)
                    new = new._with(card, rc.OutputRoom(False, False, here.measured, here.reach))
            if "without" in changes:
                new = new.set_without(card, changes["without"])
            if "reach" in changes:
                new = new.set_reach(card, changes["reach"])
            await self._commit(old, new, card)
        return self.snapshot()

    async def _commit(self, old: Room, new: Room, card: str) -> None:
        self._store.set(rc.KEY, new.to_settings())
        path_before = self._eq_on(card) or old.in_path(card)
        path_after = self._eq_on(card) or new.in_path(card)
        if path_before != path_after:
            await self._reopen("room correction was switched " + ("on" if new.in_path(card) else "off"))
        else:
            await self._sync()
        self._changed()
        self.publish()

    async def calibration(self, text, name=None) -> dict:
        """**The 90° file given from the phone** (decision 4 as changed,
        George 2026-11-05), checked and kept by its serial."""
        cal = rc.parse_calibration(text, self._today(), name if isinstance(name, str) else None)
        async with self._lock:
            self._store.set(rc.KEY, self.state().with_calibration(cal).to_settings())
        self._changed()
        logger.info("room: calibration for %s kept", rc.shown_serial(cal.serial))
        return self.snapshot()

    # -- a run -----------------------------------------------------------------------

    async def start(self) -> dict:
        from gexis_core.room_run import Host, Run
        async with self._lock:
            mic_state = self._microphone()
            ok, why = self._can_measure(mic_state)
            if not ok:
                raise RoomError({
                    "running": "The room is being measured already.",
                    "microphone": "Plug in the UMIK-1.",
                    "calibration": "Choose the microphone's calibration file again: it is needed now for the full range."
                    if mic_state["calibration"] else "Give the player the microphone's calibration file first.",
                    "grouped": "Leave the group to measure the room.",
                    "busy": "Not while an update installs.",
                }[why])
            card = self._card()
            _, mic = self._find_mic()
            cal = self.state().calibration()
            audio = self._audio(mic, cal)
            self._ended = None
            self._run_card = card
            self._run_stage = None
            host = Host(take=self._run_take, stage=self._run_stage_to, loud=self._run_loud,
                        finish=self._run_finish, publish=self._run_published)
            self.run = Run(card, audio, cal, host, today=self._today, **self._run_options)
            self._path_before = self._eq_on(card) or self.state().in_path(card)
        if hasattr(audio, "prepare"):
            await audio.prepare()
        await self.run.start()
        return self.snapshot()

    async def tap(self, what: str) -> dict:
        if what == "cancel":
            if self.run is not None:
                self.run.cancel()
            return self.snapshot()
        if what == "done" and not self.running():
            # The phone has shown how it ended; nothing left to show.
            self._ended = None
            self.publish()
            return self.snapshot()
        if not self.running():
            raise RoomError("The room is not being measured.")
        # `done` while it runs: *Nothing to correct*'s button, which ends it.
        if what not in ("start", "next", "check", "skip", "keep", "discard", "again", "done"):
            raise RoomError(f"Unknown: {what}.")
        self.run.tap(what)
        await asyncio.sleep(0)
        return self.snapshot()

    async def _run_take(self) -> None:
        # `frozen` holds from here: the run exists and has not ended.
        await self._take()

    async def _run_stage_to(self, cuts) -> None:
        card = self._run_card
        self._run_stage = cuts
        if not self._path_before and not getattr(self, "_path_taken", False):
            self._path_taken = True
            await self._reopen("room correction measures")
        else:
            await self._sync()

    async def _run_loud(self) -> None:
        await self._loud()

    async def _run_finish(self, measurement) -> None:
        card = self._run_card
        if measurement is not None:
            async with self._lock:
                self._store.set(rc.KEY, self.state().keep(card, measurement).to_settings())
            self._changed()
            logger.info("room: kept the measurement for %s", card)
        try:
            await self._quiet()
        finally:
            took = getattr(self, "_path_taken", False)
            self._path_taken = False
            # The run has ended (`_active` is false): the path and the stage
            # are the store's again.
            path_now = self._eq_on(card) or self.state().in_path(card)
            self._run_stage = None
            if took and not path_now:
                await self._reopen("room correction measured")
            else:
                await self._sync()
            await self._release()

    def _run_published(self, state, ended) -> None:
        if ended is not None:
            self._ended = dict(ended)
        self.publish()
