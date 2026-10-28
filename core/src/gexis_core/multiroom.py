# SPDX-License-Identifier: GPL-3.0-or-later
"""**Multiroom on this player** (ADR-0166): what a group does here.

`group.Group` keeps the record and carries it between players; this puts it
in force, and answers the group's routes:

- **The chain** (D1): grouped, the renderers play into the group's loopback
  and the group's music comes back from the leader (`outputs.group_in_path`).
  Squeezelite keeps this player's own chain where every member uses one
  Lyrion server (`BUT_LYRION`, D2); elsewhere it plays into the loopback too
  (`ALL`, C3).
- **Snapcast** (D1): every member serves (`snapcast.Snapcast`), and plays
  from the leader - except while Lyrion plays here in Lyrion's own sync,
  when Squeezelite needs the card.
- **Lyrion's own sync** (D2, decision 10): the leader keeps Lyrion's sync as
  the group is; a sync made or undone in a Lyrion app groups or ungroups the
  players here too.
- **The leader moves with the source** (D4): a source started on a member
  makes it the leader; the old leader's own source stops (C1).
- **The group's Now Playing on a member** (D5): the leader's playback,
  mirrored into this player's state; its transport commands sent there.
- **The group volume** (D6): the *All* slider moves every Variable member by
  the same step; each member's own row is its own control.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urljoin

import aiohttp

from gexis_core import group as groups
from gexis_core import outputs
from gexis_core.adapters.base import TRANSPORT_COMMANDS, Capabilities
from gexis_core.group import Group, GroupError, Live, Member, Peers, Record, member_of
from gexis_core.model import Queue, TrackMetadata
from gexis_core.snapcast import sample_format_for

logger = logging.getLogger("gexis_core.multiroom")

#: The chain a group was last put in, so a start comes up with it before
#: the other members have been heard from.
CHAIN_PATH = Path("/var/lib/gexis/group-chain.json")
#: A sync seen in Lyrion this soon after one of ours is ours.
OWN_SYNC_S = 6.0
HTTP_TIMEOUT_S = 3.0


def read_chain(path: Path = CHAIN_PATH) -> str | None:
    try:
        value = json.loads(path.read_text()).get("chain")
    except (OSError, ValueError, AttributeError):
        return None
    return value if value in (outputs.BUT_LYRION, outputs.ALL) else None


def write_chain(value: str | None, path: Path = CHAIN_PATH) -> None:
    try:
        if value is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"chain": value}))
    except OSError as exc:
        logger.warning("multiroom: cannot keep the chain in %s: %s", path, exc)


def absolute(url: str | None, base: str) -> str | None:
    """A leader's picture, reachable from a member's page: a path on the
    leader's own server made into its full address."""
    if not url or "://" in url or url.startswith("data:"):
        return url
    return urljoin(base, url)


def mirror_of(state: dict, base: str) -> tuple | None:
    """**The leader's playback, as this player publishes it** (D5):
    (active, metadata, capabilities, source, queue), from its `/state`."""
    active = state.get("active")
    if not active:
        return None
    caps_json = (state.get("capabilities") or {}).get(active) or {}
    capabilities = Capabilities.from_json(caps_json)
    controls = state.get("controls") or {}
    declared = capabilities.controls & TRANSPORT_COMMANDS
    unavailable = declared - set(controls.get("available") or ())
    meta = dict(state.get("metadata") or {})
    for key in ("artwork", "artwork_small"):
        meta[key] = absolute(meta.get(key), base)
    metadata = TrackMetadata.from_json(meta, unavailable=unavailable,
                                       shuffle=controls.get("shuffle"), repeat=controls.get("repeat"))
    source = next((dict(s) for s in state.get("sources") or [] if s.get("id") == active), None)
    if source and source.get("mark"):
        source["mark"] = absolute(source["mark"], base)
    queue_json = state.get("queue")
    queue = None
    if isinstance(queue_json, dict):
        for item in queue_json.get("items") or []:
            if isinstance(item, dict):
                for key in ("artwork", "artwork_small"):
                    item[key] = absolute(item.get(key), base)
        queue = Queue.from_json(queue_json)
    return (active, metadata, capabilities, source, queue)


class Multiroom:
    def __init__(self, *, store, players, snap, me: Callable[[], Member | None],
                 local_active: Callable[[], str | None],
                 stop_source: Callable[[], Awaitable[object]],
                 rechain: Callable[[], Awaitable[None]],
                 chain_card: Callable[[], tuple[str | None, bool]],
                 set_own_volume: Callable[[float], Awaitable[bool]],
                 set_own_mute: Callable[[bool], Awaitable[bool]],
                 screen: Callable[[], bool],
                 lms=None, lms_on: Callable[[], bool] = lambda: False,
                 before_reload=None, after_reload=None,
                 group_path: Path = groups.PATH, chain_path: Path = CHAIN_PATH, peers=None) -> None:
        self._store = store
        self._players = players
        self.snap = snap
        self._me = me
        self._local_active = local_active
        self._stop_source = stop_source
        self._rechain = rechain
        self._chain_card = chain_card
        self._set_own_volume = set_own_volume
        self._set_own_mute = set_own_mute
        self._screen = screen
        self._lms = lms
        self._lms_on = lms_on
        self._before_reload = before_reload
        self._after_reload = after_reload
        self._chain_path = chain_path
        self.group = Group(me=me, send=self._send, apply=self._apply, path=group_path)
        self.peers = peers if peers is not None else Peers(self._changed, self._address)
        #: What `outputs.group_in_path` answers: None alone.
        self.chain: str | None = read_chain(chain_path) if self.group.record else None
        #: A source started here, its claim to lead on the way (D4).
        self._claiming = False
        #: The group ended while this player led and played: it plays on
        #: through its own server until the stream ends (*the music stays on
        #: the leader*), then plays alone.
        self._alone_when_idle = False
        self._lms_commanded = 0.0
        self._refresh_task: asyncio.Task | None = None
        self._session: aiohttp.ClientSession | None = None
        self._statuses: dict[str, dict] = {}
        snap.on_change = self._changed

    # -- what others ask about this player -------------------------------------

    def status(self) -> dict:
        """What this player adds to `/player/status` (ADR-0136): its group
        API, its group, its Lyrion, its level."""
        state = self._store.state
        lyrion = None
        if self._lms is not None and self._lms_on() and self._lms.player_id:
            lyrion = {"server": self._lms.server_id, "player": self._lms.player_id}
        volume = state.volume
        mine = self._me()
        return {"multiroom": groups.PROTOCOL, "port": mine.port if mine else 8090,
                "group": groups.summary(self.group.record),
                "lyrion": lyrion,
                "volume": {"percent": volume.percent, "muted": volume.muted} if volume else None,
                "fixed": state.fixed_output}

    @property
    def record(self) -> Record | None:
        return self.group.record

    async def relisten(self) -> None:
        """The client back as the group wants it, after the chain was
        rewritten under it (a change of output, of tuning)."""
        await self._listen()

    def mirroring(self) -> bool:
        return self._store.mirrored and self._local_active() is None

    # -- start -----------------------------------------------------------------------

    async def start(self) -> None:
        """At the core's start: a group kept from before is put back in force
        (decision 3). The chain was written with it already (`chain`)."""
        self._players.on_refresh = self._seen
        self._store.subscribe(lambda _state: self._changed())
        record = self.group.record
        if record is None:
            return
        logger.info("multiroom: in a group of %d, led by %s, since before this start",
                    len(record.members), record.leader)
        self.peers.follow(self._others(record))
        if self.chain is None:
            self.chain = outputs.ALL
            write_chain(self.chain, self._chain_path)
        await self.snap.ensure_card(self._before_reload, self._after_reload)
        await self.snap.serve(True)
        await self._listen()
        self._changed()

    # -- the group's routes -------------------------------------------------------------

    async def join(self, player_id: str) -> Record:
        member = self._member(player_id)
        if member is None:
            raise GroupError("that player cannot be grouped: it is not found, or older than multiroom")
        return await self.group.join(member)

    async def remove(self, player_id: str) -> Record:
        return await self.group.remove(player_id)

    async def leave(self) -> Record:
        record = self.group.record
        if record is not None and record.leader == self.group.me:
            raise GroupError("the leader cannot leave; undo the group instead")
        return await self.group.leave()

    async def undo(self) -> Record:
        return await self.group.undo()

    async def receive(self, data: dict) -> bool:
        try:
            record = Record.from_json(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise GroupError(f"not a group record: {exc}") from exc
        return await self.group.receive(record)

    def view(self) -> dict | None:
        return self._store.state.group

    async def group_volume(self, target: float, start: dict | None = None) -> dict[str, int]:
        """**The *All* slider** (D6): `start` holds the Variable members'
        levels when the drag began (the design's `_gBase`), so a drag down to
        nothing and back keeps the balance; without it, their levels now."""
        view = self.view() or {}
        variable = {m["id"]: m["volume"] for m in view.get("members") or []
                    if m["reachable"] and not m["fixed"] and m["volume"] is not None}
        if isinstance(start, dict):
            levels = {k: int(v) for k, v in start.items()
                      if k in variable and isinstance(v, (int, float)) and not isinstance(v, bool)}
        else:
            levels = variable
        moved = groups.step_levels(levels, target)
        muted = {m["id"] for m in view.get("members") or [] if m["muted"]}
        await asyncio.gather(*(self._member_volume(k, v, unmute=k in muted) for k, v in moved.items()))
        return moved

    async def group_mute(self, muted: bool) -> None:
        """Every reachable member muted or not - a Fixed one too, where its
        output has a control to silence (ADR-0165)."""
        view = self.view() or {}
        targets = [m["id"] for m in view.get("members") or []
                   if m["reachable"] and (not m["fixed"] or m["fixed_mute"] is not None)]
        await asyncio.gather(*(self.member_mute(k, muted) for k in targets))

    async def member_volume(self, player_id: str, percent: float) -> bool:
        return await self._member_volume(player_id, percent)

    async def member_mute(self, player_id: str, muted: bool) -> bool:
        if player_id == self.group.me:
            return await self._set_own_mute(muted)
        return await self._post(player_id, "/volume/mute", {"muted": muted})

    async def _member_volume(self, player_id: str, percent: float, unmute: bool = False) -> bool:
        if player_id == self.group.me:
            ok = await self._set_own_volume(percent)
            if unmute:
                await self._set_own_mute(False)
            return ok
        ok = await self._post(player_id, "/volume", {"percent": percent})
        if unmute:
            await self._post(player_id, "/volume/mute", {"muted": False})
        return ok

    async def forward_transport(self, command: str, argument=None) -> bool:
        """A member's play, pause, skip or seek, sent to the leader (D5)."""
        record = self.group.record
        if record is None:
            return False
        body = None
        if command == "seek":
            body = {"position": argument}
        elif command == "shuffle":
            body = {"on": argument}
        elif command == "repeat":
            body = {"mode": argument}
        return await self._post(record.leader, f"/transport/{command}", body)

    def on_source_volume(self, before: int, after: int) -> None:
        """**A source's own app moved the leader's level** (D6): Spotify's
        slider, a volume-handing plugin. The other Variable members move by
        the same step. Lyrion's apps set each player's own (its sync group
        has a volume of its own)."""
        record = self.group.record
        if record is None or record.leader != self.group.me or after == before:
            return
        if self._local_active() == "lms" and self.chain == outputs.BUT_LYRION:
            return
        view = self.view() or {}
        delta = after - before
        for m in view.get("members") or []:
            if m["me"] or not m["reachable"] or m["fixed"] or m["volume"] is None:
                continue
            level = max(0, min(100, m["volume"] + delta))
            asyncio.ensure_future(self._post(m["id"], "/volume", {"percent": level}))

    # -- what happens here ----------------------------------------------------------------

    def on_local_active(self, renderer_id: str | None) -> None:
        """This player's own source changed (the supervisor's `active`)."""
        record = self.group.record
        if record is None:
            return
        me = self.group.me
        if renderer_id is None:
            asyncio.ensure_future(self._listen())
            self._changed()
            return
        lyrion_here = renderer_id == "lms" and self.chain == outputs.BUT_LYRION
        if lyrion_here:
            # Squeezelite plays to this player's own card, in Lyrion's sync.
            asyncio.ensure_future(self.snap.listen(None))
            if record.leader == me:
                asyncio.ensure_future(self._lms_follow())
        if record.leader == me:
            return
        leader_state = self.peers.states.get(record.leader) or {}
        leader_up = self.peers.reachable.get(record.leader, False)
        if lyrion_here and leader_up and leader_state.get("active") == "lms":
            # The group plays Lyrion already: this is its sync.
            return
        self._claiming = True

        async def claim() -> None:
            try:
                await self.group.lead()
            finally:
                self._claiming = False
                self._changed()
        logger.info("multiroom: %s started here; this player leads the group", renderer_id)
        asyncio.ensure_future(claim())

    def on_lyrion_sync(self, master: str | None, others: tuple[str, ...]) -> None:
        """**A sync made or undone in Lyrion** (decision 10): Lyrion's groups
        are Gexis groups. Ours, made by the leader to follow the group, are
        known by their time."""
        if time.monotonic() - self._lms_commanded < OWN_SYNC_S:
            return
        asyncio.ensure_future(self._from_lyrion(master, others))

    # -- inside -----------------------------------------------------------------------

    def _others(self, record: Record) -> list[Member]:
        me = self.group.me
        return [m for m in record.members if m.id != me]

    def _member(self, player_id: str) -> Member | None:
        status = self._players.status_of(player_id) or self._statuses.get(player_id)
        return member_of(status) if status else None

    def _address(self, member: Member) -> tuple[str, int]:
        found = self._players.addresses.get(member.id)
        return found if found else (member.host, member.port)

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_S))
        return self._session

    async def _post(self, player_id: str, path: str, body: dict | None) -> bool:
        record = self.group.record
        member = (record.member(player_id) if record else None) or self._member(player_id)
        if member is None:
            return False
        host, port = self._address(member)
        try:
            session = await self._http()
            async with session.post(f"http://{host}:{port}{path}", json=body) as response:
                return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
            logger.info("multiroom: %s did not take %s: %s", member.name, path, exc)
            return False

    async def _send(self, member: Member, record: Record) -> bool:
        host, port = self._address(member)
        session = await self._http()
        async with session.post(f"http://{host}:{port}/group/record",
                                json={"record": record.to_json()}) as response:
            return response.status == 200

    async def _seen(self, statuses: dict[str, dict]) -> None:
        """The players found on the network, every half minute: kept for the
        Lyrion checks, and the group reconciled with them."""
        self._statuses = statuses
        await self.group.reconcile(statuses)
        record = self.group.record
        if record is not None:
            chain = self._chain_for(record)
            if chain != self.chain and not self._alone_when_idle:
                logger.info("multiroom: the group's chain is now %s", chain)
                await self._set_chain(chain)
            await self._lms_follow()
        self._changed()

    def _lyrion_of(self, player_id: str) -> dict | None:
        if player_id == self.group.me:
            return self.status().get("lyrion")
        status = self._statuses.get(player_id) or self._players.status_of(player_id) or {}
        return status.get("lyrion")

    def _chain_for(self, record: Record) -> str:
        """`BUT_LYRION` where every member plays Lyrion from one server, so
        Lyrion's own sync can carry it; else `ALL` (C3)."""
        servers = set()
        for member in record.members:
            lyrion = self._lyrion_of(member.id)
            if not lyrion or not lyrion.get("server"):
                return outputs.ALL
            servers.add(lyrion["server"])
        return outputs.BUT_LYRION if len(servers) == 1 else outputs.ALL

    async def _apply(self, old: Record | None, new: Record | None) -> None:
        me = self.group.me
        if new is not None:
            self.peers.follow(self._others(new))
        else:
            self.peers.stop()
        if old is None and new is not None:
            if new.leader != me:
                await self._stop_own("it joined a group")
            await self._enter(new)
        elif old is not None and new is not None:
            if old.leader == me and new.leader != me and self._local_active() is not None:
                await self._stop_own("another player leads the group now")
            chain = self._chain_for(new)
            if chain != self.chain:
                await self._set_chain(chain)
            await self._listen()
        elif old is not None and new is None:
            await self._leave(old)
        asyncio.ensure_future(self._lms_follow())
        self._changed()

    async def _stop_own(self, why: str) -> None:
        stopped = await self._stop_source()
        if stopped:
            logger.info("multiroom: %s stopped here - %s (C1)", stopped, why)

    async def _enter(self, record: Record) -> None:
        self._alone_when_idle = False
        await self.snap.ensure_card(self._before_reload, self._after_reload)
        await self._set_chain(self._chain_for(record))
        await self.snap.serve(True)
        await self._listen()

    async def _set_chain(self, chain: str | None) -> None:
        self.chain = chain
        write_chain(chain, self._chain_path)
        # The client lets go of the card first: the chain is asked of it.
        await self.snap.listen(None)
        await self._rechain()

    async def _leave(self, old: Record) -> None:
        if self._lms is not None and self._lms_on() and self._lms.sync_group[1]:
            self._lms_commanded = time.monotonic()
            await self._lms.unsync()
        if old.leader == self.group.me and self.snap.rate is not None:
            # The music stays on the leader: through its own server until the
            # stream ends, so nothing is cut.
            self._alone_when_idle = True
            logger.info("multiroom: the group is undone; playing on alone once this stream ends")
            return
        await self._alone()

    async def _alone(self) -> None:
        self._alone_when_idle = False
        await self.snap.listen(None)
        await self.snap.serve(False)
        self._store.set_mirror(None)
        self.chain = None
        write_chain(None, self._chain_path)
        await self._rechain()
        logger.info("multiroom: playing alone")

    async def _listen(self) -> None:
        record = self.group.record
        if record is None:
            if not self._alone_when_idle:
                await self.snap.listen(None)
            return
        if self._local_active() == "lms" and self.chain == outputs.BUT_LYRION:
            await self.snap.listen(None)
            return
        me = self.group.me or ""
        if record.leader == me:
            host = "127.0.0.1"
        else:
            leader = record.member(record.leader)
            host = self._address(leader)[0] if leader else None
        card, takes_32 = self._chain_card()
        await self.snap.listen(host, me, groups_format(card, takes_32))

    def _changed(self) -> None:
        """Something the group's view or this player's part in it depends on
        changed: looked at once, a moment later."""
        if self._refresh_task is not None and not self._refresh_task.done():
            return
        try:
            self._refresh_task = asyncio.get_running_loop().create_task(self._refresh())
        except RuntimeError:
            pass

    async def _refresh(self) -> None:
        await asyncio.sleep(0.05)
        record = self.group.record
        if self._alone_when_idle and self.snap.rate is None:
            await self._alone()
        self._publish(record)
        self._mirror(record)
        if record is not None and not self._claiming:
            await self._settle(record)

    def _publish(self, record: Record | None) -> None:
        me = self.group.me
        if record is None or me is None:
            self._store.set_group(None)
            return
        state = self._store.own()
        own = {"volume": state.volume.to_json() if state.volume else None,
               "fixed_output": state.fixed_output, "fixed_mute": state.fixed_mute,
               "active": state.active, "sources": [dict(s) for s in state.sources],
               "metadata": state.metadata.to_json()}
        joining: set[str] = set()
        if record.leader == me:
            if self.snap.rate is not None:
                joining = {m.id for m in record.members
                           if m.id != me and not self.snap.caught_up(m.id)}
        else:
            led = ((self.peers.states.get(record.leader) or {}).get("group") or {})
            joining = {m["id"] for m in led.get("members") or [] if m.get("joining")}
        screens = {pid: bool(s.get("screen", True)) for pid, s in self._statuses.items()}
        urls = {pid: s.get("url") for pid, s in self._statuses.items()}
        mine = self._me()
        if mine is not None:
            urls[me] = f"http://{mine.host}:{mine.port}/"
        mode = "lyrion" if (self.chain == outputs.BUT_LYRION and
                            ((self.peers.states.get(record.leader) or own).get("active") == "lms")) else "snapcast"
        view = groups.view(record, Live(me, own, self._screen()), self.peers, mode=mode,
                           joining=joining, screens=screens, urls=urls)
        if view is not None and record.leader == me:
            view["source"] = groups.source_of(own)
            view["transport"] = own["metadata"].get("transport")
            view["title"] = own["metadata"].get("title")
            view["silent"] = False
        self._store.set_group(view)

    def _mirror(self, record: Record | None) -> None:
        me = self.group.me
        if record is None or record.leader == me or self._local_active() is not None:
            self._store.set_mirror(None)
            return
        leader = record.member(record.leader)
        state = self.peers.states.get(record.leader)
        if leader is None or not state or not self.peers.reachable.get(record.leader):
            self._store.set_mirror(None)
            return
        host, port = self._address(leader)
        self._store.set_mirror(mirror_of(state, f"http://{host}:{port}/"))

    async def _settle(self, record: Record) -> None:
        """**Only the leader's source plays** (C1, D4): a member's own source
        still active after another took the lead is stopped - unless it is
        Lyrion playing in the group's own sync."""
        me = self.group.me
        active = self._local_active()
        if record.leader == me or active is None:
            return
        if active == "lms" and self.chain == outputs.BUT_LYRION:
            leader_state = self.peers.states.get(record.leader) or {}
            if leader_state.get("active") == "lms" or not self.peers.reachable.get(record.leader):
                return
        await self._stop_own("another player leads the group")

    # -- Lyrion's own sync (D2, decision 10) ------------------------------------------------

    async def _lms_follow(self) -> None:
        """The leader keeps Lyrion's sync as the group is: every member's
        player synced to its own, and switched on while Lyrion plays here."""
        record = self.group.record
        lms = self._lms
        if (record is None or lms is None or not self._lms_on() or lms.player_id is None
                or record.leader != self.group.me or self.chain != outputs.BUT_LYRION):
            return
        wanted = set()
        for member in self._others(record):
            lyrion = self._lyrion_of(member.id) or {}
            if lyrion.get("player"):
                wanted.add(lyrion["player"])
        current = set(lms.sync_group[1])
        missing = wanted - current
        known_gexis = {(s.get("lyrion") or {}).get("player") for s in self._statuses.values()}
        extra = (current - wanted) & known_gexis
        if self._local_active() == "lms":
            # Lyrion plays here: every member's player on, so it plays too.
            for player in sorted(wanted):
                await lms.power_on(player)
        if not missing and not extra:
            return
        self._lms_commanded = time.monotonic()
        for player in sorted(missing):
            await lms.sync_with(player)
        for player in sorted(extra):
            await lms.unsync(player)
        logger.info("multiroom: Lyrion's sync follows the group (%d in, %d out)", len(missing), len(extra))

    async def _from_lyrion(self, master: str | None, others: tuple[str, ...]) -> None:
        lms = self._lms
        if lms is None or not self._lms_on() or lms.player_id is None:
            return
        me = self.group.me
        by_player = {(s.get("lyrion") or {}).get("player"): pid for pid, s in self._statuses.items()
                     if (s.get("lyrion") or {}).get("player")}
        gexis = sorted(by_player[p] for p in others if p in by_player)
        record = self.group.record
        if not others:
            # Unsynced in Lyrion: out of the group here too.
            if record is not None and self.chain == outputs.BUT_LYRION:
                logger.info("multiroom: unsynced in Lyrion; leaving the group")
                if record.leader == me:
                    rest = [m.id for m in self._others(record)]
                    if rest:
                        record = await self.group.hand_over(rest[0])
                if record is not None and record.leader != me:
                    await self.group.leave()
            return
        # The one who acts: Lyrion's master, or the first of the Gexis
        # players synced when the master is not one.
        actor = by_player.get(master) if master in by_player or master == lms.player_id else None
        if master == lms.player_id:
            actor = me
        if actor is None:
            actor = min([me or "", *gexis])
        if actor != me:
            return
        for pid in gexis:
            record = self.group.record
            if record is None or not record.has(pid):
                member = self._member(pid)
                if member is not None:
                    logger.info("multiroom: synced in Lyrion with %s; grouped here too", member.name)
                    await self.group.join(member)


def groups_format(card: str | None, takes_32: bool) -> str | None:
    """The client's `--sampleformat` for this player's chain (snapcast)."""
    return sample_format_for(card, takes_32)
