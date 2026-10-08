# SPDX-License-Identifier: GPL-3.0-or-later
"""**The cable** (ADR-0123): its state, and its address - automatic or manual.

A player on a cable works without any of this: NetworkManager makes a profile
for the port (*Wired connection 1*) and takes an address by DHCP. This reads
what that gives, and lets the owner fix the address by hand. Changing it is
the one setting that can lock the owner out of Settings, so a change is
**kept only once it is shown to work** - confirmed from the new address within
`KEEP_S`, or put back as it was (the shape of ADR-0109's *Keep this screen?*).

IPv4 only; IPv6 stays automatic (ADR-0123, Consequences).
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from gexis_core import wifi

logger = logging.getLogger(__name__)

DEVICE = "eth0"
SYS_NET = Path("/sys/class/net")
#: How long a new address waits for *Keep* before the old one comes back.
KEEP_S = 60.0
#: How long the port is given to take its address after a change.
UP_TIMEOUT_S = 30.0

#: The sentences the phone shows for an address that does not work out.
BAD_ADDRESS = "Type the address with its prefix, for example 192.168.1.20/24."
BAD_GATEWAY = "The gateway has to be an address in the same network as the player's."
BAD_DNS = "Each DNS server is an address, for example 192.168.1.1. One or two."


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def has_port(device: str = DEVICE, sys_net: Path = SYS_NET) -> bool:
    return (sys_net / device).is_dir()


def link(device: str = DEVICE, sys_net: Path = SYS_NET) -> tuple[bool, int | None]:
    """Whether a cable carries a link, and its speed in Mb/s - from the
    kernel, cheap enough for every settings request."""
    carrier = _read(sys_net / device / "carrier") == "1"
    speed = None
    if carrier:
        try:
            speed = int(_read(sys_net / device / "speed") or "")
        except ValueError:
            speed = None
        if speed is not None and speed <= 0:
            speed = None
    return carrier, speed


@dataclass
class Manual:
    """A manual address as checked: `address` with its prefix, `gateway`,
    and one or two `dns` servers."""
    address: str
    gateway: str
    dns: list[str] = field(default_factory=list)

    @property
    def host(self) -> str:
        return self.address.split("/")[0]


def check(address: str, gateway: str, dns: list[str] | str) -> Manual:
    """**Checked as typed** (ADR-0123): an address with its prefix, a gateway
    inside that network, one or two DNS servers. Raises ValueError with the
    sentence the phone shows."""
    try:
        interface = ipaddress.IPv4Interface((address or "").strip())
    except ValueError:
        raise ValueError(BAD_ADDRESS) from None
    if "/" not in (address or "") or interface.network.prefixlen > 30 or interface.ip in (
            interface.network.network_address, interface.network.broadcast_address):
        raise ValueError(BAD_ADDRESS)
    try:
        gate = ipaddress.IPv4Address((gateway or "").strip())
    except ValueError:
        raise ValueError(BAD_GATEWAY) from None
    if gate not in interface.network or gate == interface.ip:
        raise ValueError(BAD_GATEWAY)
    servers = dns.split() if isinstance(dns, str) else [d for d in (dns or []) if d]
    servers = [s.strip().strip(",") for s in servers if s.strip().strip(",")]
    if not 1 <= len(servers) <= 2:
        raise ValueError(BAD_DNS)
    try:
        servers = [str(ipaddress.IPv4Address(s)) for s in servers]
    except ValueError:
        raise ValueError(BAD_DNS) from None
    return Manual(str(interface), str(gate), servers)


def _lines(out: str) -> list[str]:
    return out.splitlines()


async def profile(device: str = DEVICE, run=wifi._run) -> str | None:
    """The NetworkManager connection on the port - *Wired connection 1*, as a
    rule - or None when there is none."""
    rc, out, _ = await run("-t", "-f", "GENERAL.CONNECTION", "device", "show", device)
    if rc != 0:
        return None
    for line in _lines(out):
        value = wifi._fields(line)[-1]
        if value and value != "--":
            return value
    return None


async def settings_of(name: str, run=wifi._run) -> dict:
    """The profile's own IPv4 settings - what a change is put back to."""
    rc, out, _ = await run("-g", "ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns", "connection", "show", name)
    values = (_lines(out) + ["", "", "", ""])[:4] if rc == 0 else ["auto", "", "", ""]
    method, addresses, gateway, dns = (v.strip() for v in values)
    return {"method": method or "auto", "addresses": addresses, "gateway": gateway,
            "dns": dns.replace(",", " ").split()}


async def status(device: str = DEVICE, run=wifi._run, sys_net: Path = SYS_NET) -> dict:
    """What the Cable row and its sheet show."""
    carrier, speed = link(device, sys_net)
    name = await profile(device, run)
    method = (await settings_of(name, run))["method"] if name else "auto"
    address = gateway = None
    dns: list[str] = []
    rc, out, _ = await run("-t", "-f", "IP4.ADDRESS,IP4.GATEWAY,IP4.DNS", "device", "show", device)
    for line in _lines(out) if rc == 0 else ():
        key, _, value = line.partition(":")
        value = value.strip()
        if not value or value == "--":
            continue
        if key.startswith("IP4.ADDRESS") and address is None:
            address = value
        elif key == "IP4.GATEWAY":
            gateway = value
        elif key.startswith("IP4.DNS"):
            dns.append(value)
    return {
        "port": has_port(device, sys_net),
        "link": carrier,
        "speed": speed,
        "profile": name,
        "method": "manual" if method == "manual" else "auto",
        "address": address,
        "gateway": gateway,
        "dns": dns,
    }


def summary(state: dict) -> str:
    """The row's line: *Connected · 1000 Mb/s · 192.168.1.20*, or *No link*."""
    if not state.get("link"):
        return "No link"
    parts = ["Connected"]
    if state.get("speed"):
        parts.append(f"{state['speed']} Mb/s")
    if state.get("address"):
        parts.append(state["address"].split("/")[0])
    return " · ".join(parts)


async def _set(name: str, wanted: dict, device: str, run) -> tuple[bool, str | None]:
    if wanted["method"] == "manual":
        args = ["ipv4.method", "manual", "ipv4.addresses", wanted["addresses"],
                "ipv4.gateway", wanted["gateway"], "ipv4.dns", " ".join(wanted["dns"])]
    else:
        args = ["ipv4.method", "auto", "ipv4.addresses", "", "ipv4.gateway", "", "ipv4.dns", ""]
    rc, _, err = await run("connection", "modify", name, *args)
    if rc != 0:
        return False, err or "NetworkManager refused the address"
    rc, _, err = await run("connection", "up", name, "ifname", device, timeout=UP_TIMEOUT_S)
    if rc != 0:
        return False, err or "The port did not come up with it"
    return True, None


@dataclass
class Pending:
    profile: str
    before: dict
    address: str | None
    until: float


class Cable:
    """The cable's address, changed and kept - or put back."""

    def __init__(self, device: str = DEVICE, run=wifi._run, sys_net: Path = SYS_NET,
                 keep_s: float = KEEP_S, on_change=None, sleep=asyncio.sleep, clock=time.time) -> None:
        self._device = device
        self._run = run
        self._sys_net = sys_net
        self._keep_s = keep_s
        self._on_change = on_change or (lambda pending: None)
        self._sleep = sleep
        self._clock = clock
        self.pending: Pending | None = None
        self._timer: asyncio.Task | None = None
        #: Whether the profile holds a manual address - read at each status,
        #: so the row can stay shown without a cable (ADR-0123).
        self.manual = False
        #: The last status read, for the row's line between reads.
        self.last: dict = {}

    async def status(self) -> dict:
        state = await status(self._device, self._run, self._sys_net)
        self.manual = state["method"] == "manual"
        self.last = dict(state)
        if self.pending is not None:
            state["pending"] = {"address": self.pending.address, "until": self.pending.until}
        return state

    def note(self) -> str | None:
        """The row's line, the link read live and the address as last read."""
        if not has_port(self._device, self._sys_net):
            return None
        carrier, speed = link(self._device, self._sys_net)
        line = summary({**self.last, "link": carrier, "speed": speed})
        if self.pending is not None:
            line += " · waiting to be kept"
        elif self.manual and carrier:
            line += " · manual"
        return line

    async def follow(self, every: float = 10.0) -> None:
        """Keeps `last` current, so the row says what the cable is now."""
        while True:
            if has_port(self._device, self._sys_net):
                try:
                    before = (self.last.get("address"), self.manual)
                    await self.status()
                    if (self.last.get("address"), self.manual) != before:
                        self._on_change(self.pending)
                except Exception as exc:  # noqa: BLE001 - a row, never the core
                    logger.info("cable: status not read: %s", exc)
            await asyncio.sleep(every)

    def shown(self) -> bool:
        """ADR-0123: while a cable is plugged in, or a manual address is set."""
        return has_port(self._device, self._sys_net) and (link(self._device, self._sys_net)[0] or self.manual)

    async def change(self, method: str, address: str = "", gateway: str = "", dns=()) -> dict:
        """Apply an address and start the wait for *Keep*. Raises ValueError
        with a sentence for the phone. Returns the pending change, with the
        address the phone opens to keep it."""
        if self.pending is not None:
            raise ValueError("A change is waiting to be kept. Keep it, or wait for it to go back.")
        name = await profile(self._device, self._run)
        if name is None:
            raise ValueError("The cable has no connection to change. Plug it in first.")
        before = await settings_of(name, self._run)
        if method == "manual":
            manual = check(address, gateway, dns)
            wanted = {"method": "manual", "addresses": manual.address, "gateway": manual.gateway, "dns": manual.dns}
        elif method == "auto":
            wanted = {"method": "auto"}
        else:
            raise ValueError("Choose Automatic or Manual.")
        ok, err = await _set(name, wanted, self._device, self._run)
        if not ok:
            logger.warning("cable: %s refused (%s); putting it back", wanted["method"], err)
            await _set(name, before, self._device, self._run)
            raise ValueError("The player could not take that address. Nothing was changed.")
        now = await status(self._device, self._run, self._sys_net)
        new = (now.get("address") or "").split("/")[0] or None
        self.pending = Pending(name, before, new, self._clock() + self._keep_s)
        logger.info("cable: %s address %s applied; kept only if confirmed within %.0f s",
                    wanted["method"], new, self._keep_s)
        self._timer = asyncio.ensure_future(self._expire())
        self._on_change(self.pending)
        return {"address": new, "until": self.pending.until}

    def keep(self, arrived_at: str | None, loopback: bool) -> bool:
        """*Keep*, accepted from the new address - which proves it works -
        or from the panel, which reaches the player whatever its address."""
        if self.pending is None:
            return False
        if not loopback and arrived_at != self.pending.address:
            return False
        logger.info("cable: the new address is kept")
        self.pending = None
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self._on_change(None)
        return True

    async def _expire(self) -> None:
        pending = self.pending
        await self._sleep(self._keep_s)
        if self.pending is not pending or pending is None:
            return
        logger.warning("cable: not kept within %.0f s; putting the address back", self._keep_s)
        ok, err = await _set(pending.profile, pending.before, self._device, self._run)
        if not ok:
            logger.error("cable: the old address did not come back: %s", err)
        self.pending = None
        self._on_change(None)
