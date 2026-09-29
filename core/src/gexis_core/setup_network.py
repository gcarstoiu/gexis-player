# SPDX-License-Identifier: GPL-3.0-or-later
"""**Setup mode and the setup network** (ADR-0031, ADR-0104).

Two questions, kept apart (ADR-0104 §1). *Does the device need setup* is a fact
about its configuration: no saved Wi-Fi and no `setup-done` marker. *Does it
need the setup network* is a fact about the radio right now: a configured
device that cannot reach its Wi-Fi at boot needs the network and not setup, and
a new device on Ethernet needs setup and not the network.

**At boot only.** A device that loses its Wi-Fi while running stays as it is
until it is restarted (George, 2026-09-28: *"Restarting is the way"*).

**One radio.** The setup network takes `wlan0` from the home Wi-Fi, so it
opens only when there is no home Wi-Fi to take it from, and a retry every five
minutes gives it back when a saved network comes into range - only while no
phone is on it, so nobody's setup is cut off (ADR-0031 amendment 7).

**A trial on a configured device** (gexis has no Ethernet, ADR-0031's
Testing): `/run/gexis-setup-trial` present at startup opens the setup network
whatever the radio is doing. It is read once and deleted, it is in `/run` so a
reboot forgets it anyway, and the retry is what gives the home Wi-Fi back. A line `retry=<seconds>` in it
shortens the retry for the trial.
"""
from __future__ import annotations

import asyncio
import logging
import secrets
import time
from pathlib import Path

from gexis_core import wifi

logger = logging.getLogger(__name__)

SSID = "gexis-setup"
#: The profile's name, which is also the network's. One name to look for when
#: a crash leaves it behind.
PROFILE = SSID
#: A player without a panel: nothing can show a made-up password, so it is the
#: network's own name, which WPA2's 8-63 characters allow (amendment 1).
HEADLESS_PASSWORD = "gexis-setup"
#: Read off a screen and typed on a phone: no `0 o 1 l`, no capitals.
PASSWORD_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"
PASSWORD_LENGTH = 8
#: NetworkManager's shared mode hands this address to the device.
ADDRESS = "10.42.0.1"

STATE_DIR = Path("/var/lib/gexis")
DONE_MARKER = STATE_DIR / "setup-done"
PASSWORD_FILE = STATE_DIR / "setup-password"
TRIAL_FILE = Path("/run/gexis-setup-trial")
DRM = Path("/sys/class/drm")
IFACE = "wlan0"

#: George, 2026-09-28: 90 s at boot for a configured device.
CONFIGURED_WAIT_S = 90.0
#: A new device has nothing to wait for but a cable's link (ADR-0104 §3).
NEW_WAIT_S = 15.0
#: While open and nobody is on it, look for the saved networks this often.
RETRY_S = 300.0
POLL_S = 2.0
#: After switching the radio on: how long to wait for NetworkManager to call
#: `wlan0` usable before asking it for the hotspot anyway.
WLAN_READY_S = 20.0
#: A setup network that did not start is tried again this soon, not at the
#: five-minute retry: nobody can set the device up until it is up.
FAILED_RETRY_S = 15.0
#: How often the panel's step follows the phones on the setup network.
PHONES_EVERY_S = 2.0
RFKILL = Path("/sys/class/rfkill")
#: NetworkManager's dnsmasq writes the setup network's leases here.
LEASES = Path("/var/lib/NetworkManager/dnsmasq-wlan0.leases")


def needs_setup(saved_wifi: int, marker: Path = DONE_MARKER) -> bool:
    """ADR-0104 §2: no saved Wi-Fi and no marker. Either one means somebody
    configured this device, and a provisioned card has `preconfigured`."""
    return saved_wifi == 0 and not marker.exists()


def panel_attached(drm: Path = DRM) -> bool:
    """A screen on an HDMI connector. The panel is on `HDMI-A-1` on gexis;
    whichever one it is on, a connected status is what counts."""
    try:
        connectors = list(drm.glob("card*-HDMI-A-*"))
    except OSError:
        return False
    for connector in connectors:
        try:
            if (connector / "status").read_text().strip() == "connected":
                return True
        except OSError:
            continue
    return False


#: Between the phone being told setup is finishing and the radio leaving it,
#: so the page's last screen - where to go next - arrives before the page
#: can no longer be reached.
HANDOVER_S = 3.0


def join_reason(rc: int, err: str) -> str:
    """NetworkManager's refusal, as the page and the panel say it."""
    text = (err or "").lower()
    if rc == 124:
        return "It took too long. The network may be out of range."
    if "secrets were required" in text or "no secrets" in text:
        return "The password was not accepted."
    if "no network with ssid" in text or "not found" in text or "could not be found" in text:
        return "No network with that name is in range."
    # The `Error:` line, not the last one: NetworkManager follows it with a
    # `Hint: use 'journalctl -xe ...'` line, which reached the panel as the
    # reason on the first scripted trial.
    for line in (err or "").splitlines():
        if line.startswith("Error:"):
            said = line.removeprefix("Error:").strip().removeprefix("Connection activation failed:").strip()
            if said:
                return said[0].upper() + said[1:].rstrip(".") + "."
    return "The network refused the connection."


def country_for(timezone: str | None, zone_tab: Path = Path("/usr/share/zoneinfo/zone.tab")) -> str | None:
    """The Wi-Fi country for a time zone, from tzdata's own table (ADR-0104
    §4). `zone.tab`, not `zone1970.tab`: the latter lists several countries
    for one zone (`Europe/Berlin` is `DE,DK,NO,SE,SJ` there)."""
    if not timezone:
        return None
    try:
        lines = zone_tab.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 3 and parts[2] == timezone:
            return parts[0]
    return None


async def _rfkill_unblock_wifi() -> None:
    """`rfkill unblock wifi`, logged when it had anything to do. Never fatal:
    a device without rfkill has nothing blocked."""
    try:
        process = await asyncio.create_subprocess_exec(
            "rfkill", "unblock", "wifi",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await asyncio.wait_for(process.communicate(), 10)
    except (OSError, asyncio.TimeoutError) as exc:
        logger.info("setup: rfkill unblock not run: %s", exc)
        return
    if process.returncode:
        logger.warning("setup: rfkill unblock wifi: %s", err.decode(errors="replace").strip())


def leased_macs(path: Path, now: float) -> set[str]:
    """MACs with a lease that has not expired. dnsmasq's line is `expiry mac
    ip hostname client-id`; an expiry of 0 means infinite."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return set()
    found = set()
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            expiry = int(parts[0])
        except ValueError:
            continue
        if expiry == 0 or expiry > now:
            found.add(parts[1].lower())
    return found


def rfkill_state(root: Path = RFKILL) -> str:
    """The Wi-Fi radio's rfkill switches, as `rfkill soft=1 hard=0`."""
    try:
        for entry in sorted(root.iterdir()):
            if (entry / "type").read_text().strip() == "wlan":
                soft = (entry / "soft").read_text().strip()
                hard = (entry / "hard").read_text().strip()
                return f"rfkill soft={soft} hard={hard}"
    except OSError:
        pass
    return "rfkill unknown"


def make_password() -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_LENGTH))


def password(panel: bool, path: Path = PASSWORD_FILE) -> str:
    """With a panel, one made up once and kept, so the password on the screen
    does not change under someone who read it before a restart. Without one,
    the fixed password."""
    if not panel:
        return HEADLESS_PASSWORD
    try:
        kept = path.read_text().strip()
        if len(kept) >= 8:
            return kept
    except OSError:
        pass
    made = make_password()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(made + "\n")
        path.chmod(0o600)
    except OSError as exc:
        logger.warning("setup: cannot keep the password (%s); it will change on restart", exc)
    return made


def read_trial(path: Path = TRIAL_FILE) -> float | None:
    """The retry for a trial, or None when there is no trial. A trial file
    without a `retry=` line keeps the real five minutes."""
    try:
        text = path.read_text()
    except OSError:
        return None
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "retry":
            try:
                return max(30.0, float(value))
            except ValueError:
                break
    return RETRY_S


def parse_devices(out: str) -> list[tuple[str, str, str, str]]:
    """`nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device` as tuples."""
    rows = []
    for line in out.splitlines():
        parts = wifi._fields(line)
        if len(parts) >= 4:
            rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


def online(devices: list[tuple[str, str, str, str]]) -> str | None:
    """The device that gives this player a network, or None. `connected` is
    NetworkManager's word for an address and a route; the setup network's own
    connection is not a network to anyone but the phone on it."""
    for device, kind, state, connection in devices:
        if kind not in ("ethernet", "wifi"):
            continue
        if state.startswith("connected") and connection != PROFILE:
            return device
    return None


def ethernet_address(devices: list[tuple[str, str, str, str]]) -> bool:
    return any(k == "ethernet" and s.startswith("connected") for _, k, s, _ in devices)


def carrier(iface_root: Path = Path("/sys/class/net")) -> bool:
    """A cable with a link on any Ethernet port. Read from the kernel rather
    than NetworkManager: a link comes up before an address does."""
    try:
        ports = [p for p in iface_root.iterdir() if p.name.startswith(("eth", "en"))]
    except OSError:
        return False
    for port in ports:
        try:
            if (port / "carrier").read_text().strip() == "1":
                return True
        except OSError:
            continue
    return False


class SetupNetwork:
    """The decision at boot, the setup network while it is needed, and the
    five-minute retry. `status()` is what the panel and the phone read."""

    def __init__(
        self,
        *,
        run=None,
        clock=time.monotonic,
        sleep=asyncio.sleep,
        marker: Path = DONE_MARKER,
        password_file: Path = PASSWORD_FILE,
        trial_file: Path = TRIAL_FILE,
        drm: Path = DRM,
        net_root: Path = Path("/sys/class/net"),
        stations=None,
        on_change=None,
        unblock=None,
        ready=None,
    ) -> None:
        self._nmcli = run or wifi._run
        self._count_stations = stations or self._stations
        #: Phones the panel counts as joined. A test that fakes the stations
        #: fakes these too.
        self._count_ready = ready or (stations if stations is not None else self._ready_phones)
        self._leases = LEASES
        self._unblock = unblock or _rfkill_unblock_wifi
        self._rfkill = RFKILL
        self._clock = clock
        self._sleep = sleep
        self._marker = marker
        self._password_file = password_file
        self._trial_file = trial_file
        self._drm = drm
        self._net_root = net_root
        self._needed = False
        self._state = "starting"
        self._password: str | None = None
        self._panel = False
        self._reason: str | None = None
        self._opened_at: float | None = None
        #: ADR-0031 amendment 8: a new device on Ethernet is set up over it,
        #: at this address, and there is no setup network.
        self._lan_address: str | None = None
        #: The network a join is going for, shown on the panel while it runs.
        self._target: str | None = None
        #: The network the last join failed on; `_reason` says why. Apart,
        #: so the panel can put the name in its title and the reason under it.
        self._failed: str | None = None
        #: A join from setup is running: the retry keeps its hands off.
        self._busy = False
        #: Phones on the setup network, and whether one has opened the setup
        #: page: the panel's steps follow these (George, 2026-09-29: "We know
        #: once an user connects so we can show a success join briefly and
        #: move to the next step").
        self._phones = 0
        self._page_opened = False
        #: The last word, shown on the panel for a few seconds after a
        #: successful join: where the device went and what it found.
        self._finished: dict | None = None
        #: Called with `public_status()` whenever it changes: the state
        #: broadcast, which every phone reads too, so never the password.
        self._on_change = on_change
        self._published: dict | None = None

    # -- what the panel and the phone read ---------------------------------

    def status(self) -> dict:
        """ADR-0104 §5's inputs, the password among them while the network is
        open. **For the panel only**: `/setup/status` hands this to a loopback
        caller and `public_status` to anyone else."""
        open_ = self._state == "open"
        if open_:
            address = f"http://{ADDRESS}:8090/"
        elif self._needed and self._state == "online" and self._lan_address:
            address = f"http://{self._lan_address}:8090/"
        else:
            address = None
        return {
            "needed": self._needed,
            "network": self._state,
            "ssid": SSID if open_ else None,
            "password": self._password if open_ else None,
            "address": address,
            "panel": self._panel,
            "reason": self._reason,
            "failed": self._failed,
            "target": self._target if self._state == "joining" else None,
            "phones": self._phones if open_ else 0,
            "finished": self._finished if self._state == "done" else None,
            "page_opened": self._page_opened and open_,
        }

    def public_status(self) -> dict:
        return {**self.status(), "password": None}

    def _publish(self) -> None:
        if self._on_change is None:
            return
        now = self.public_status()
        if now != self._published:
            self._published = now
            self._on_change(now)

    @property
    def needed(self) -> bool:
        return self._needed

    # -- NetworkManager ----------------------------------------------------

    async def _devices(self) -> list[tuple[str, str, str, str]]:
        rc, out, _ = await self._nmcli("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device")
        return parse_devices(out) if rc == 0 else []

    async def _saved_wifi(self) -> dict[str, str]:
        """SSID -> saved connection, less the setup network's own profile."""
        saved = await wifi.saved_ssids(run=self._nmcli)
        return {ssid: name for ssid, name in saved.items() if ssid != SSID and name != PROFILE}

    async def _in_range(self) -> set[str]:
        """What a scan sees, read while hosting (Finding 099: the phone stays
        on). The setup network sees itself, which is not a way home."""
        rc, out, _ = await self._nmcli(
            "-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes",
            timeout=wifi.SCAN_TIMEOUT_S,
        )
        if rc != 0:
            return set()
        return {wifi._fields(l)[0] for l in out.splitlines()} - {SSID, ""}

    async def _stations(self) -> int:
        """Phones associated with the setup network. `iw`, not the neighbour
        table, which saw a phone 5 s late (Finding 099)."""
        try:
            process = await asyncio.create_subprocess_exec(
                "iw", "dev", IFACE, "station", "dump",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await asyncio.wait_for(process.communicate(), 10)
        except (OSError, asyncio.TimeoutError):
            # Unknown counts as somebody there: a retry that cuts off a phone
            # is worse than one that waits another five minutes.
            return 1
        return sum(1 for line in out.decode("utf-8", "replace").splitlines() if line.startswith("Station"))

    async def _station_macs(self) -> set[str] | None:
        try:
            process = await asyncio.create_subprocess_exec(
                "iw", "dev", IFACE, "station", "dump",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await asyncio.wait_for(process.communicate(), 10)
        except (OSError, asyncio.TimeoutError):
            return None
        return {line.split()[1].lower() for line in out.decode("utf-8", "replace").splitlines()
                if line.startswith("Station") and len(line.split()) > 1}

    async def _ready_phones(self) -> int:
        """**Phones that are associated and have been given an address.**
        Association alone came too early (George, 2026-09-29: "we show phone
        connected before the phone itself shows that it's connected", and a
        fast user would open the page before the phone could reach it). The
        lease is the setup network's own dnsmasq answering the phone, the
        step after which the phone can open the page."""
        macs = await self._station_macs()
        if not macs:
            return 0
        return len(macs & leased_macs(self._leases, time.time()))

    async def _address_of(self, device: str) -> str | None:
        """The IPv4 address a phone on the same network would open, without
        its prefix length."""
        rc, out, _ = await self._nmcli("-g", "IP4.ADDRESS", "device", "show", device)
        first = out.strip().split("|")[0].strip() if rc == 0 else ""
        return first.split("/")[0] or None

    async def delete_leftover(self) -> None:
        """A profile a crash left behind. It is `autoconnect no`, but a profile
        nobody meant to keep is one nobody will think to look for."""
        rc, out, _ = await self._nmcli("-t", "-f", "NAME", "connection", "show")
        if rc == 0 and PROFILE in [wifi._fields(l)[0] for l in out.splitlines()]:
            await self._nmcli("connection", "delete", PROFILE)
            logger.info("setup: deleted a %s profile left from before", PROFILE)

    async def open(self) -> bool:
        """Raise the setup network: the command Finding 099 measured, then
        `autoconnect no` so the profile can never come up by itself at boot in
        place of the home Wi-Fi."""
        self._panel = panel_attached(self._drm)
        self._password = password(self._panel, self._password_file)
        await self.delete_leftover()
        # **The radio may be off.** Raspberry Pi OS starts every radio blocked
        # (`rfkill.default_state=0`) and pi-gen ships NetworkManager with
        # `WirelessEnabled=false` when the build sets no country, "to prevent
        # radiating on 5GHz bands until the WLAN regulatory domain is set". A
        # provisioned card lifts both by setting a country; a new one has
        # none, and the setup network failed with "device is not available"
        # on the first blank card (2026-09-29). Lifted here for the setup
        # network only, on 2.4 GHz, under the world domain; setup's Finish
        # sets the real country, which lifts it for good.
        await self._unblock()
        await self._nmcli("radio", "wifi", "on")
        # **Then wait for it.** Unblocking is not the chip being ready: on the
        # second blank card the hotspot was still refused with "device is
        # not available" (2026-09-29).
        ready = await self._wait_for_wlan()
        rc, _, err = await self._nmcli(
            "device", "wifi", "hotspot", "ifname", IFACE, "con-name", PROFILE,
            "ssid", SSID, "band", "bg", "password", self._password,
            timeout=wifi.JOIN_TIMEOUT_S,
        )
        await self._nmcli("connection", "modify", PROFILE, "connection.autoconnect", "no")
        # Read back rather than trusted: this is the line that keeps the home
        # Wi-Fi from losing the radio to a leftover at boot.
        _, autoconnect, _ = await self._nmcli("-g", "connection.autoconnect", "connection", "show", PROFILE)
        if rc != 0:
            self._state = "failed"
            said = err.splitlines()[-1] if err else f"nmcli exited {rc}"
            # What the radio was doing goes with the reason: on a blank card
            # the panel is the only place anyone can read it.
            self._reason = f"{said} [wlan0 {ready}; {rfkill_state(self._rfkill)}]"
            logger.warning("setup: the setup network did not come up: %s", self._reason)
            self._publish()
            return False
        self._state = "open"
        self._opened_at = self._clock()
        self._publish()
        logger.info(
            "setup: %s is open at %s (%s password; autoconnect %s)",
            SSID, ADDRESS, "the panel's" if self._panel else "the fixed",
            autoconnect.strip() or "unknown",
        )
        return True

    def page_opened(self) -> None:
        """A phone loaded the setup page (`/setup/answers`): the panel moves
        from "open the page" to "carry on on your phone"."""
        if not self._page_opened:
            self._page_opened = True
            self._publish()

    async def _watch_phones(self) -> None:
        """Keep `phones` current while the setup network is open. The last
        phone leaving takes the panel back to the first step."""
        while True:
            if self._state == "open":
                count = await self._count_ready()
                if count != self._phones:
                    self._phones = count
                    if count == 0:
                        self._page_opened = False
                    logger.info("setup: %d phone(s) on %s", count, SSID)
                    self._publish()
            elif self._phones:
                self._phones, self._page_opened = 0, False
            await self._sleep(PHONES_EVERY_S)

    def finished(self, ssid: str | None, library: dict, restarting: bool, name: str | None = None) -> None:
        """The panel's last setup screen (George, 2026-09-29): the network it
        joined, what became of Lyrion, and whether it is restarting."""
        self._state = "done"
        self._finished = {"ssid": ssid, "library": library, "restarting": restarting, "name": name}
        self._publish()

    def done(self) -> None:
        """Setup finished (ADR-0104 §2): the marker is written by the caller;
        this device no longer needs setup."""
        self._needed = False
        self._lan_address = None
        self._state = "online"
        self._finished = None
        self._publish()

    async def join_new(self, ssid: str, password: str | None, hidden: bool = False) -> tuple[bool, str | None]:
        """Save the network typed on the phone and join it (ADR-0104 §4).

        With one radio the setup network comes down first, so the phone loses
        the page here; the pause lets its last screen arrive. **A join that
        fails deletes what it saved** - a wrong password kept would be retried
        by NetworkManager for ever - and brings the setup network back, with
        the reason on the panel and the page (ADR-0031 amendment 5).
        """
        self._busy = True
        try:
            hosting = self._state == "open"
            self._state, self._target = "joining", ssid
            self._reason = self._failed = None
            self._publish()
            await self._sleep(HANDOVER_S)
            if hosting:
                await self.close()
            # A profile named after the network is ours to replace. Any other
            # profile for the same network is left alone: on a configured
            # device it may hold the right password while this one is wrong.
            await self._nmcli("connection", "delete", ssid)
            args = ["connection", "add", "type", "wifi", "ifname", IFACE,
                    "con-name", ssid, "ssid", ssid, "connection.autoconnect", "yes"]
            if hidden:
                args += ["802-11-wireless.hidden", "yes"]
            if password:
                args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
            rc, _, err = await self._nmcli(*args)
            if rc == 0:
                rc, _, err = await self._nmcli("connection", "up", ssid, timeout=wifi.JOIN_TIMEOUT_S)
            if rc == 0:
                self._state, self._target = "online", None
                logger.info("setup: joined %s", ssid)
                self._publish()
                return True, None
            reason = join_reason(rc, err)
            logger.warning("setup: could not join %s: %s (%s)", ssid, reason, err or rc)
            await self._nmcli("connection", "delete", ssid)
            self._target = None
            self._failed, self._reason = ssid, reason
            if hosting or self._needed:
                await self.open()
            else:
                self._state = "online"
            self._publish()
            return False, reason
        finally:
            self._busy = False

    async def _wait_for_wlan(self) -> str:
        """Poll NetworkManager until `wlan0` is out of `unavailable`, for at
        most `WLAN_READY_S`. Returns the state it last saw."""
        start, state = self._clock(), "missing"
        while True:
            state = next((st for dev, kind, st, _ in await self._devices() if dev == IFACE), "missing")
            if state not in ("unavailable", "unmanaged", "missing"):
                waited = self._clock() - start
                if waited > 0:
                    logger.info("setup: %s became %s after %.1f s", IFACE, state, waited)
                return state
            if self._clock() - start >= WLAN_READY_S:
                logger.warning("setup: %s still %s after %.0f s", IFACE, state, WLAN_READY_S)
                return state
            await self._sleep(1.0)

    async def close(self) -> None:
        await self._nmcli("connection", "down", PROFILE)
        await self._nmcli("connection", "delete", PROFILE)
        self._opened_at = None

    # -- the decision and the retry ----------------------------------------

    async def run(self) -> None:
        try:
            await self._run()
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - a watcher must not die silently
            logger.exception("setup: the setup network's task failed")

    async def _run(self) -> None:
        retry = read_trial(self._trial_file)
        trial = retry is not None
        retry = retry or RETRY_S
        if trial:
            # Read once. A core that restarts mid-trial comes up as it would
            # after a reboot, which deletes the profile and lets the home
            # Wi-Fi reconnect.
            self._trial_file.unlink(missing_ok=True)
        saved = await self._saved_wifi()
        self._needed = needs_setup(len(saved), self._marker)
        self._panel = panel_attached(self._drm)
        if not trial:
            await self.delete_leftover()
        logger.info(
            "setup: %s; %d saved Wi-Fi network(s)%s",
            "needed" if self._needed else "not needed", len(saved),
            "; a trial, retry every %ds" % retry if trial else "",
        )

        if not trial:
            self._state = "waiting"
            self._publish()
            where = await self._wait_for_network()
            if where is not None:
                self._state = "online"
                if self._needed:
                    self._lan_address = await self._address_of(where)
                self._publish()
                logger.info("setup: on the network through %s; no setup network", where)
                return
        await self.open()
        phones = asyncio.ensure_future(self._watch_phones())
        try:
            await self._hold(retry)
        finally:
            phones.cancel()

    async def _wait_for_network(self) -> str | None:
        """ADR-0104 §3. A configured device gets 90 s. A new one gets 15 s for
        a cable's link, and if a link came up, the 90 s for its address."""
        start = self._clock()
        while True:
            where = online(await self._devices())
            if where is not None:
                return where
            waited = self._clock() - start
            if self._needed and waited >= NEW_WAIT_S and not carrier(self._net_root):
                return None
            if waited >= CONFIGURED_WAIT_S:
                return None
            await self._sleep(POLL_S)

    async def _hold(self, retry: float) -> None:
        """While open: every `retry` seconds with nobody on it, look for a
        saved network and go back to it. A join that fails brings the setup
        network back.

        **Until the device is online, not while the network is open**: a
        join from setup takes the network down and may bring it back, and a
        loop that ended when it went down would never retry again."""
        while self._state != "online":
            await self._sleep(FAILED_RETRY_S if self._state == "failed" else retry)
            if self._busy or self._state not in ("open", "failed"):
                continue
            if self._state == "failed":
                await self.open()
                continue
            if await self._count_stations() > 0:
                logger.info("setup: a phone is on %s; not looking for other networks", SSID)
                continue
            saved = await self._saved_wifi()
            if not saved:
                continue
            in_range = await self._in_range()
            found = next((ssid for ssid in saved if ssid in in_range), None)
            if found is None:
                logger.info("setup: none of %d saved network(s) in range", len(saved))
                continue
            logger.info("setup: %s is in range; leaving %s to join it", found, SSID)
            await self.close()
            self._state = "joining"
            self._target = found
            self._publish()
            rc, _, err = await self._nmcli("connection", "up", saved[found], timeout=wifi.JOIN_TIMEOUT_S)
            if rc == 0:
                self._state = "online"
                self._reason = self._failed = None
                self._publish()
                logger.info("setup: back on %s", found)
                return
            self._failed, self._reason = found, join_reason(rc, err)
            logger.warning("setup: could not join %s: %s (%s); opening %s again", found, self._reason, err or rc, SSID)
            await self.open()
