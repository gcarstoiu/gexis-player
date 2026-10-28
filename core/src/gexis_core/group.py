# SPDX-License-Identifier: GPL-3.0-or-later
"""**The group: players joined to play the same music** (ADR-0166 D3-D6).

**One record, kept by every member.** A group is its members (each player's
stable id, ADR-0160 D5, with its name and address), its leader - the player
whose source the group plays - and a revision. The player asked to change it
(join, remove, leave, undo, a source starting there) makes the new record,
keeps it (`/var/lib/gexis/group.json`, so it lasts a restart, decision 3)
and sends it to every member, old and new, over their HTTP API
(`POST /group/record`). A member that was off is sent it when it is seen
again (`reconcile`). Of two records for one group the later change wins.

**What being in a group does to a player** is not decided here: `apply` is
told the record before and after, and `__main__` rewrites the chain, starts
Snapcast or Lyrion's sync, and stops this player's own source (C1).

**The members' states, live**: while grouped, each player follows every
other member's `/state` (`Peers`), for the group's Now Playing on a member
(D5), the group volume's rows (D6) and who is reachable (C2).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Awaitable, Callable

import aiohttp

logger = logging.getLogger("gexis_core.group")

PATH = Path("/var/lib/gexis/group.json")
#: The version of the players' group API, in `/player/status`; a player
#: without it cannot be joined (it is older than multiroom).
PROTOCOL = 1
PUSH_TIMEOUT_S = 3.0


@dataclass(frozen=True)
class Member:
    id: str
    name: str
    host: str
    port: int = 8090

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "host": self.host, "port": self.port}

    @classmethod
    def from_json(cls, data: dict) -> "Member":
        return cls(id=str(data["id"]), name=str(data.get("name") or data["id"]),
                   host=str(data.get("host") or ""), port=int(data.get("port") or 8090))


@dataclass(frozen=True)
class Record:
    """One group, as one change left it. `ended` is a group undone: kept so
    the change reaches every member, then forgotten."""

    id: str
    revision: int
    leader: str
    members: tuple[Member, ...]
    #: When this change was made (epoch seconds) and by whom: the order of
    #: two changes made at once.
    changed: float = 0.0
    by: str = ""
    ended: bool = False

    @classmethod
    def new(cls, leader: Member, *others: Member, clock=time.time) -> "Record":
        members = (leader, *[m for m in others if m.id != leader.id])
        return cls(id=uuid.uuid4().hex, revision=1, leader=leader.id, members=members,
                   changed=clock(), by=leader.id)

    def ids(self) -> list[str]:
        return [m.id for m in self.members]

    def member(self, player_id: str) -> Member | None:
        return next((m for m in self.members if m.id == player_id), None)

    def has(self, player_id: str) -> bool:
        return self.member(player_id) is not None

    def bumped(self, by: str, clock=time.time, **changes) -> "Record":
        return replace(self, revision=self.revision + 1, changed=clock(), by=by, **changes)

    def with_member(self, member: Member, by: str, clock=time.time) -> "Record":
        kept = tuple(m for m in self.members if m.id != member.id)
        return self.bumped(by, clock, members=(*kept, member))

    def without(self, player_id: str, by: str, clock=time.time) -> "Record":
        """`player_id` taken out; a group of one is no group (the design's
        `removeFrom`). The leader is never taken out this way."""
        members = tuple(m for m in self.members if m.id != player_id)
        return self.bumped(by, clock, members=members, ended=len(members) < 2)

    def led_by(self, player_id: str, by: str, clock=time.time) -> "Record":
        return self.bumped(by, clock, leader=player_id)

    def order(self) -> tuple:
        return (self.revision, self.changed, self.by)

    def to_json(self) -> dict:
        return {"id": self.id, "revision": self.revision, "leader": self.leader,
                "members": [m.to_json() for m in self.members], "changed": self.changed,
                "by": self.by, "ended": self.ended}

    @classmethod
    def from_json(cls, data: dict) -> "Record":
        members = tuple(Member.from_json(m) for m in data.get("members") or [])
        return cls(id=str(data["id"]), revision=int(data["revision"]), leader=str(data["leader"]),
                   members=members, changed=float(data.get("changed") or 0.0),
                   by=str(data.get("by") or ""), ended=bool(data.get("ended")))


def accepts(current: Record | None, new: Record, me: str) -> bool:
    """**Whether a record sent by another player is taken.** The same group:
    a later change. Another group: only one this player is in, and not older
    than the one it is in (it was joined to it)."""
    if current is not None and new.id == current.id:
        return new.order() > current.order()
    if new.ended or not new.has(me):
        return False
    return current is None or new.changed >= current.changed


def leaving(current: Record, me: str) -> Record:
    """`current` after this player has gone to another group."""
    return current.without(me, by=me)


def read(path: Path = PATH) -> Record | None:
    try:
        data = json.loads(path.read_text())
        record = Record.from_json(data)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.warning("group: %s is unreadable (%s); this player is in no group", path, exc)
        return None
    return None if record.ended else record


def write(record: Record | None, path: Path = PATH) -> None:
    try:
        if record is None or record.ended:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record.to_json()))
        os.replace(tmp, path)
    except OSError as exc:
        logger.error("group: cannot keep the group in %s: %s", path, exc)


class Group:
    """This player's record, and the changes it makes or is sent.

    `me()` is this player as a member; `members_known()` the other players
    found on the network, as members (by id); `send(member, record)` posts a
    record to a member and says whether it arrived; `apply(old, new)` puts
    a change in force here. One change at a time."""

    def __init__(self, *, me: Callable[[], Member | None],
                 send: Callable[[Member, Record], Awaitable[bool]],
                 apply: Callable[[Record | None, Record | None], Awaitable[None]],
                 path: Path = PATH, clock=time.time) -> None:
        self._me = me
        self._send = send
        self._apply = apply
        self._path = path
        self._clock = clock
        self.record: Record | None = read(path)
        self._lock = asyncio.Lock()
        #: Records a member has not had yet, by member id: sent again when it
        #: is next seen (`reconcile`).
        self._owed: dict[str, Record] = {}
        #: Changes kept and not yet put in force here, in order.
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._tasks: set[asyncio.Task] = set()

    @property
    def me(self) -> str | None:
        member = self._me()
        return member.id if member else None

    def leads(self) -> bool:
        return self.record is not None and self.record.leader == self.me

    # -- changes made here -------------------------------------------------------
    #
    # **A change is kept, sent, and put in force here - in that order of
    # haste** (guestpi, 2026-10-28: an undo reached the leader 27 s late, after
    # the player asked had rewritten its own chain). Each is kept under the
    # lock; the members are sent it at once; this player's part runs after,
    # one change at a time in the order they were kept (`_worker`).

    async def join(self, other: Member) -> Record:
        """`other` joins this player's group; a new group, led by this
        player, if it is in none."""
        me = self._me()
        if me is None:
            raise GroupError("this player has no id to group by")
        if other.id == me.id:
            raise GroupError("a player cannot join itself")
        async with self._lock:
            current = self.record
            if current is None:
                new = Record.new(me, other, clock=self._clock)
            elif current.has(other.id):
                return current
            else:
                new = current.with_member(other, by=me.id, clock=self._clock)
            self._keep(new)
        await self._tell(new, also=(other,))
        return new

    async def remove(self, player_id: str) -> Record:
        """A member taken out (the design's Remove; Leave is this with this
        player's own id). Never the leader: *Undo group* ends a group."""
        me = self.me
        async with self._lock:
            current = self._current()
            if player_id == current.leader:
                raise GroupError("the leader cannot be taken out; undo the group instead")
            if not current.has(player_id):
                return current
            new = current.without(player_id, by=me or "", clock=self._clock)
            self._keep(new)
        await self._tell(new, also=(current.member(player_id),))
        return new

    async def leave(self) -> Record:
        return await self.remove(self.me or "")

    async def undo(self) -> Record:
        """Every member plays on its own again; the music stays on the
        leader (the design's rule)."""
        async with self._lock:
            current = self._current()
            new = current.bumped(self.me or "", self._clock, ended=True)
            self._keep(new)
        await self._tell(new, also=current.members)
        return new

    async def lead(self) -> Record | None:
        """**A source started here leads the group** (D4, decision 4)."""
        me = self.me
        async with self._lock:
            current = self.record
            if current is None or me is None or current.leader == me:
                return current
            new = current.led_by(me, by=me, clock=self._clock)
            self._keep(new)
        await self._tell(new)
        return new

    async def hand_over(self, player_id: str) -> Record | None:
        """The leader gives the lead to another member (it was unsynced in
        Lyrion, decision 10, and leaves after)."""
        me = self.me
        async with self._lock:
            current = self.record
            if current is None or not current.has(player_id) or current.leader == player_id:
                return current
            new = current.led_by(player_id, by=me or "", clock=self._clock)
            self._keep(new)
        await self._tell(new)
        return new

    # -- changes sent here --------------------------------------------------------

    async def receive(self, new: Record) -> bool:
        """A record another player sent. True when it was taken - answered
        as soon as it is kept, so the sender never waits on this player's
        own part of the change."""
        me = self.me
        if me is None:
            return False
        async with self._lock:
            current = self.record
            if not accepts(current, new, me):
                return False
            if current is not None and new.id != current.id:
                # Joined to another group: out of this one first (the
                # design's "takes it out of any other group").
                left = leaving(current, me)
                self._spawn(self._tell(left))
            self._keep(new)
        return True

    async def settled(self) -> None:
        """Every change kept so far has been put in force here."""
        await self._queue.join()

    # -- keeping members in step ---------------------------------------------------

    async def reconcile(self, statuses: dict[str, dict]) -> None:
        """What each member said of itself (its `/player/status`, by id):
        a member behind is sent the record again; one ahead is asked
        nothing - it sends its own when it changes - but a record it owes us
        arrives through `receive`."""
        record = self.record
        if record is None:
            for player_id, owed in list(self._owed.items()):
                status = statuses.get(player_id)
                if status is not None and await self._deliver(owed.member(player_id) or
                                                              _member_of(status), owed):
                    self._owed.pop(player_id, None)
            return
        for member in record.members:
            if member.id == self.me:
                continue
            status = statuses.get(member.id)
            if status is None:
                continue
            theirs = status.get("group") or {}
            if theirs.get("id") == record.id and int(theirs.get("revision") or 0) >= record.revision:
                self._owed.pop(member.id, None)
                continue
            if theirs.get("id") not in (None, record.id) and float(theirs.get("changed") or 0) > record.changed:
                # In another group since: it went, and its word did not
                # reach us. Taken out here, without a word back to it.
                logger.info("group: %s is in another group now; taken out of this one", member.name)
                async with self._lock:
                    if self.record is not None and self.record.has(member.id) \
                            and member.id != self.record.leader:
                        self._keep(self.record.without(member.id, by=self.me or "", clock=self._clock))
                continue
            if await self._deliver(member, record):
                self._owed.pop(member.id, None)

    # -- inside ---------------------------------------------------------------------

    def _current(self) -> Record:
        if self.record is None:
            raise GroupError("this player is in no group")
        return self.record

    def _keep(self, new: Record) -> None:
        """The change kept (under the lock), and queued to be put in force."""
        old = self.record
        self.record = None if new.ended or not new.has(self.me or "") else new
        write(self.record, self._path)
        logger.info("group: %s (revision %d, %d players, led by %s)",
                    "ended" if new.ended else ("left" if self.record is None else "now"),
                    new.revision, len(new.members), new.leader)
        self._queue.put_nowait((old, self.record))
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.get_running_loop().create_task(self._worker())

    async def _worker(self) -> None:
        """This player's part of each change, one at a time, in order."""
        while True:
            old, new = await self._queue.get()
            try:
                await self._apply(old, new)
            except Exception:  # noqa: BLE001 - a change kept must not be lost to its effects
                logger.exception("group: putting the change in force failed")
            finally:
                self._queue.task_done()

    def _spawn(self, coro) -> None:
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _tell(self, record: Record, also=()) -> None:
        """Every member of `record` but this player, and `also` (members
        taken out, or a player joining), sent `record` at once."""
        me = self.me
        targets: dict[str, Member] = {}
        for member in (*record.members, *[m for m in also if m is not None]):
            if member.id != me:
                targets[member.id] = member
        await asyncio.gather(*(self._deliver(m, record) for m in targets.values()))

    async def _deliver(self, member: Member, record: Record) -> bool:
        try:
            ok = await self._send(member, record)
        except Exception as exc:  # noqa: BLE001 - one member's failure is not the change's
            logger.info("group: %s did not take the change: %s", member.name, exc)
            ok = False
        if ok:
            self._owed.pop(member.id, None)
        else:
            self._owed[member.id] = record
        return ok


class GroupError(Exception):
    """A change that cannot be made; said to whoever asked."""


def _member_of(status: dict) -> Member:
    host = str(status.get("host") or "")
    return Member(id=str(status.get("id")), name=str(status.get("name") or host), host=host,
                  port=int(status.get("port") or 8090))


def member_of(status: dict) -> Member | None:
    """A player as `/player/status` describes it, as a member; None for a
    player with no id or no group API (older than multiroom)."""
    if not status.get("id") or int(status.get("multiroom") or 0) < PROTOCOL:
        return None
    return _member_of(status)


class Peers:
    """**Every other member's `/state`, live** (D5, D6): a WebSocket to each,
    made again when it drops. `address(member)` gives where to reach it -
    the address the network search found, else its name."""

    def __init__(self, on_change: Callable[[], None],
                 address: Callable[[Member], tuple[str, int]], *, retry_s: float = 3.0) -> None:
        self._on_change = on_change
        self._address = address
        self._retry_s = retry_s
        self._tasks: dict[str, asyncio.Task] = {}
        self.states: dict[str, dict] = {}
        self.reachable: dict[str, bool] = {}
        self._session: aiohttp.ClientSession | None = None

    def follow(self, members: list[Member]) -> None:
        wanted = {m.id: m for m in members}
        for player_id in list(self._tasks):
            if player_id not in wanted:
                self._tasks.pop(player_id).cancel()
                self.states.pop(player_id, None)
                self.reachable.pop(player_id, None)
        for player_id, member in wanted.items():
            if player_id not in self._tasks:
                self._tasks[player_id] = asyncio.create_task(self._watch(member))

    def stop(self) -> None:
        self.follow([])

    async def _watch(self, member: Member) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        while True:
            host, port = self._address(member)
            try:
                async with self._session.ws_connect(f"http://{host}:{port}/state", heartbeat=20,
                                                    timeout=aiohttp.ClientWSTimeout(ws_close=5)) as ws:
                    async for msg in ws:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            continue
                        try:
                            self.states[member.id] = json.loads(msg.data)
                        except ValueError:
                            continue
                        if not self.reachable.get(member.id):
                            self.reachable[member.id] = True
                            logger.info("group: following %s", member.name)
                        self._on_change()
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                logger.debug("group: %s not reachable: %s", member.name, exc)
            if self.reachable.get(member.id, True):
                self.reachable[member.id] = False
                self._on_change()
            await asyncio.sleep(self._retry_s)


@dataclass
class Live:
    """What this player knows of itself, for the group's view."""

    id: str
    state: dict = field(default_factory=dict)
    screen: bool = True


def _volume_of(state: dict) -> tuple[int | None, bool, bool, bool | None]:
    """(percent, muted, fixed, fixed mute) from a player's `/state`."""
    volume = state.get("volume") or {}
    fixed = bool(state.get("fixed_output"))
    fixed_mute = state.get("fixed_mute")
    if fixed:
        return None, bool(fixed_mute), True, fixed_mute
    percent = volume.get("percent")
    return (int(percent) if percent is not None else None), bool(volume.get("muted")), False, None


def source_of(state: dict) -> dict | None:
    """What a player's `/state` says it plays: its active source's id and
    name, from its own list of sources."""
    active = state.get("active")
    if not active:
        return None
    entry = next((s for s in state.get("sources") or [] if s.get("id") == active), None)
    return {"id": active, "name": (entry or {}).get("name") or active,
            "accent": (entry or {}).get("accent")}


def view(record: Record | None, me: Live, peers: Peers, *, mode: str, joining: set[str],
         screens: dict[str, bool], urls: dict[str, str], names: dict[str, str] | None = None) -> dict | None:
    """**The group as `/state` publishes it** (design/data-contract.md,
    Phase 22): the members leader first, each with its level, mute, Fixed,
    whether it is reachable and whether it is catching up; the group's level
    (the mean of its Variable members) and mute (all muted); what plays."""
    if record is None:
        return None
    states = {**peers.states, me.id: me.state}
    reachable = {**peers.reachable, me.id: True}
    ordered = sorted(record.members, key=lambda m: m.id != record.leader)
    members = []
    for member in ordered:
        state = states.get(member.id) or {}
        percent, muted, fixed, fixed_mute = _volume_of(state)
        up = bool(reachable.get(member.id))
        members.append({
            # A rename shows without joining again: the name as it says it now.
            "id": member.id, "name": (names or {}).get(member.id) or member.name, "url": urls.get(member.id),
            "me": member.id == me.id, "leads": member.id == record.leader,
            "reachable": up, "joining": up and member.id in joining,
            "screen": screens.get(member.id, True) if member.id != me.id else me.screen,
            "volume": percent if up else None, "muted": muted, "fixed": fixed,
            "fixed_mute": fixed_mute,
        })
    live = [m for m in members if m["reachable"]]
    variable = [m for m in live if not m["fixed"] and m["volume"] is not None]
    leader_state = states.get(record.leader) or {}
    leader_up = bool(reachable.get(record.leader))
    metadata = leader_state.get("metadata") or {}
    return {
        "id": record.id, "revision": record.revision, "leader": record.leader, "me": me.id,
        "mode": mode, "silent": not leader_up,
        "members": members,
        "level": round(sum(m["volume"] for m in variable) / len(variable)) if variable else None,
        "muted": bool(live) and all(m["muted"] for m in live),
        "source": source_of(leader_state) if leader_up else None,
        "transport": metadata.get("transport") if leader_up else None,
        "title": metadata.get("title") if leader_up else None,
        # The stream's rate, as the leader feeds it (its own view says).
        "rate": (leader_state.get("group") or {}).get("rate") if leader_up else None,
    }


def summary(record: Record | None) -> dict | None:
    """What this player says of its group in `/player/status`, for the other
    players' lists (*In a group with Office and Garage*) and their
    reconciling."""
    if record is None:
        return None
    return {"id": record.id, "revision": record.revision, "changed": record.changed,
            "leader": record.leader, "members": [{"id": m.id, "name": m.name} for m in record.members]}


def step_levels(levels: dict[str, int], target: float) -> dict[str, int]:
    """**The *All* slider** (D6: *the same step, as a share of its own
    travel*). From the members' levels when the drag began - their mean is
    where the slider stood - every Variable member moves the same share of
    its own way: up, of its way to 100; down, of its way to 0. So the mean
    lands where the finger is, everyone reaches 100 at the top and 0 at the
    bottom, nothing is cut at either end, and a drag back to where it began
    gives the levels back as they were (sofapi and the bar, 2026-10-28: with
    the same step for all, a member at 100 held the mean below the finger,
    and the slider jumped back)."""
    if not levels:
        return {}
    mean = sum(levels.values()) / len(levels)
    target = max(0.0, min(100.0, float(target)))
    if target >= mean:
        share = 0.0 if mean >= 100 else (target - mean) / (100 - mean)
        moved = {k: level + share * (100 - level) for k, level in levels.items()}
    else:
        share = 0.0 if mean <= 0 else (mean - target) / mean
        moved = {k: level - share * level for k, level in levels.items()}
    return {k: max(0, min(100, round(v))) for k, v in moved.items()}


def follow_level(level: int, before: int, after: int) -> int:
    """A member's level when the leader's source moved its own from `before`
    to `after` (D6): the same share of its own way, as `step_levels`."""
    if after > before:
        moved = level + (after - before) / (100 - before) * (100 - level)
    elif after < before:
        moved = level - (before - after) / before * level
    else:
        moved = level
    return max(0, min(100, round(moved)))
