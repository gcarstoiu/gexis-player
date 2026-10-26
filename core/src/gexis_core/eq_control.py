# SPDX-License-Identifier: GPL-3.0-or-later
"""**The equaliser as the player keeps it and shows it** (ADR-0162).

Between the routes and the engine: the state is read from the settings store
(`_equaliser`, backed up and wiped with every setting), changed through
`equaliser.Equaliser`'s operations, written back, published on `/state`,
and handed to the engine for the output in use.

**Switching it on or off changes the path** (D2, D5): `output.conf` is
written again and the renderers reopen it - a moment of silence. Every
other change is heard at once, in the running CamillaDSP.

**The volume gives the headroom back** (D3 as amended, George 2026-10-26):
`give_back_for` says how much, on which control; the engine says when.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from gexis_core import equaliser as eq
from gexis_core import outputs, volume
from gexis_core.equaliser import Equaliser, EqualiserError

logger = logging.getLogger("gexis_core.eq_control")

KEY = "_equaliser"


def kind_of(output: outputs.Output) -> str:
    """The output in a word, as the editor's crumbs name it: *the DAC*,
    *HDMI*, *optical*."""
    if output.card in outputs.CONNECTORS:
        return "HDMI"
    if output.card == outputs.JACK:
        return "Headphones"
    if output.usb_id in outputs.FIXED_BY_DEFAULT_USB:
        return "Optical"
    if output.usb_id:
        return "USB DAC"
    return "DAC"


def give_back_for(value, output: outputs.Output | None, headroom: float | None = None) -> volume.GiveBack | None:
    """What the volume gives back on `output` with the store's `value`:
    the headroom of its bands, at its level control - the card's own or the
    software stage (`output` as `_with_software` gives it). None with the
    equaliser off there, no boost, or no control to give it back at.
    `headroom` is the engine's, mid-change; else the store's."""
    if output is None or not output.control:
        return None
    here = Equaliser.from_settings(value).output(output.card)
    if not here.on:
        return None
    db = eq.headroom_db(here.gains) if headroom is None else headroom
    if db <= 0:
        return None
    return volume.GiveBack(output.control, db, output.scale or volume.current_scale())


class EqualiserControl:
    def __init__(self, store, engine, *,
                 output: Callable[[], outputs.Output | None],
                 fixed: Callable[[], bool],
                 reopen: Callable[[str], Awaitable[None]],
                 publish: Callable[[dict], None] = lambda snapshot: None,
                 changed: Callable[[], None] = lambda: None):
        self._store = store
        self._engine = engine
        self._output = output
        self._fixed = fixed
        self._reopen = reopen
        self._publish = publish
        self._changed = changed
        self._lock = asyncio.Lock()

    # -- reading ---------------------------------------------------------------

    def state(self) -> Equaliser:
        return Equaliser.from_settings(self._store.get(KEY))

    def in_path(self, card: str) -> bool:
        return self.state().output(card).on

    def summary(self) -> str:
        """The Settings row's value: *Off*, or the setting in use."""
        output = self._output()
        if output is None:
            return "No output"
        e = self.state()
        here = e.output(output.card)
        if not here.on:
            return "Off"
        return "Custom" if here.sel == eq.CUSTOM else (e.name_of(here.sel) or "Flat")

    def snapshot(self) -> dict | None:
        """**What every screen draws from** (`/state`'s `equaliser`, and
        `GET /equaliser`): the output in use and what it keeps, the presets
        and the owner's list, the headroom, and what stands the equaliser
        aside now."""
        output = self._output()
        if output is None:
            return None
        e = self.state()
        here = e.output(output.card)
        engine = self._engine.status()
        fixed = bool(self._fixed())
        given = None if fixed else give_back_for(self._store.get(KEY), output)
        return {
            "output": {"card": output.card, "name": output.label, "kind": kind_of(output)},
            "on": here.on,
            "sel": here.sel,
            "name": "Custom" if here.sel == eq.CUSTOM else e.name_of(here.sel),
            "from": here.source,
            "from_name": e.name_of(here.source),
            "gains": list(here.gains),
            "headroom_db": eq.headroom_db(here.gains),
            # D3 as amended: the volume makes the headroom up, all of it up
            # to `given_up_to` per cent of the slider.
            "gives_back": given is not None,
            "given_up_to": volume.given_back_up_to(given),
            "fixed": fixed,
            "dsd": bool(here.on and engine.get("dsd")),
            "bands": list(eq.BANDS),
            "range": [eq.GAIN_MIN, eq.GAIN_MAX],
            "presets": [{"key": p.key, "name": p.name, "gains": list(p.gains)} for p in eq.PRESETS],
            "own": [o.as_dict() for o in e.own],
            "own_max": eq.OWN_MAX,
        }

    # -- changing ----------------------------------------------------------------

    def _card(self) -> str:
        output = self._output()
        if output is None:
            raise EqualiserError("There is no output to set it for.")
        return output.card

    async def _commit(self, new: Equaliser, card: str, reopen: str | None = None) -> None:
        self._store.set(KEY, new.to_settings())
        if reopen:
            # The path changes: the file again, the renderers again; the
            # engine follows inside it (`sync`, from the rewrite).
            await self._reopen(reopen)
        else:
            await self.sync()
        self._changed()

    async def update(self, changes: dict) -> dict:
        """`on`, `sel`, `gains` or `band` with `gain`, for the output in use;
        several at once apply in that order."""
        if not isinstance(changes, dict) or not changes:
            raise EqualiserError("Nothing to change.")
        unknown = set(changes) - {"on", "sel", "gains", "band", "gain"}
        if unknown:
            raise EqualiserError(f"Unknown: {', '.join(sorted(unknown))}.")
        async with self._lock:
            card = self._card()
            old = self.state()
            new = old
            if "on" in changes:
                if not isinstance(changes["on"], bool):
                    raise EqualiserError("On is true or false.")
                new = new.set_on(card, changes["on"])
            if "sel" in changes:
                new = new.choose(card, changes["sel"])
            if "gains" in changes:
                new = new.set_gains(card, changes["gains"])
            if "band" in changes:
                if "gain" not in changes:
                    raise EqualiserError("A band needs its gain.")
                new = new.set_band(card, changes["band"], changes["gain"])
            switched = new.output(card).on != old.output(card).on
            await self._commit(new, card, reopen=(
                ("the equaliser was switched on" if new.output(card).on else "the equaliser was switched off")
                if switched else None))
        return self.snapshot()

    async def save_as(self, name) -> dict:
        async with self._lock:
            card = self._card()
            new, own = self.state().save_as(card, name)
            await self._commit(new, card)
        return {"saved": own.as_dict(), "equaliser": self.snapshot()}

    async def rename(self, key: str, name) -> dict:
        async with self._lock:
            card = self._card()
            await self._commit(self.state().rename(key, name), card)
        return self.snapshot()

    async def delete(self, key: str) -> dict:
        async with self._lock:
            card = self._card()
            await self._commit(self.state().delete(key), card)
        return self.snapshot()

    # -- the engine --------------------------------------------------------------

    async def sync(self, restart: bool = False) -> None:
        """The engine to the output in use: on with its bands, or out of
        the path. `restart` after `output.conf` was written under it. Called
        by the rewrite of the output's chain, after the file and before the
        renderers start."""
        output = self._output()
        here = self.state().output(output.card) if output is not None else None
        card = output.card if (output is not None and here.on) else None
        try:
            await self._engine.configure(card, here.gains if here else eq.FLAT, restart=restart)
        except Exception:  # noqa: BLE001 - a broken engine must not take the core down
            logger.exception("equaliser: the engine did not follow")
        self.publish()

    def publish(self) -> None:
        self._publish(self.snapshot())
