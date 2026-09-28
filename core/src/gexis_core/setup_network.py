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
    ) -> None:
        self._nmcli = run or wifi._run
        self._count_stations = stations or self._stations
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

    # -- what the panel and the phone read ---------------------------------

    def status(self) -> dict:
        """ADR-0104 §5's inputs. The password only while the network is open:
        it is on the panel for anyone in the room, and nowhere else."""
        open_ = self._state == "open"
        return {
            "needed": self._needed,
            "network": self._state,
            "ssid": SSID if open_ else None,
            "password": self._password if open_ else None,
            "address": f"http://{ADDRESS}:8090/" if open_ else None,
            "panel": self._panel,
            "reason": self._reason,
        }

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
        rc, _, err = await self._nmcli(
            "device", "wifi", "hotspot", "ifname", IFACE, "con-name", PROFILE,
            "ssid", SSID, "password", self._password,
            timeout=wifi.JOIN_TIMEOUT_S,
        )
        await self._nmcli("connection", "modify", PROFILE, "connection.autoconnect", "no")
        # Read back rather than trusted: this is the line that keeps the home
        # Wi-Fi from losing the radio to a leftover at boot.
        _, autoconnect, _ = await self._nmcli("-g", "connection.autoconnect", "connection", "show", PROFILE)
        if rc != 0:
            self._state = "failed"
            self._reason = err.splitlines()[-1] if err else f"nmcli exited {rc}"
            logger.warning("setup: the setup network did not come up: %s", self._reason)
            return False
        self._state = "open"
        self._opened_at = self._clock()
        logger.info(
            "setup: %s is open at %s (%s password; autoconnect %s)",
            SSID, ADDRESS, "the panel's" if self._panel else "the fixed",
            autoconnect.strip() or "unknown",
        )
        return True

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
            where = await self._wait_for_network()
            if where is not None:
                self._state = "online"
                logger.info("setup: on the network through %s; no setup network", where)
                return
        await self.open()
        await self._hold(retry)

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
        network back."""
        while self._state in ("open", "failed"):
            await self._sleep(retry)
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
            rc, _, err = await self._nmcli("connection", "up", saved[found], timeout=wifi.JOIN_TIMEOUT_S)
            if rc == 0:
                self._state = "online"
                self._reason = None
                logger.info("setup: back on %s", found)
                return
            self._reason = f"Could not join {found}: " + (err.splitlines()[-1] if err else f"exit {rc}")
            logger.warning("setup: %s; opening %s again", self._reason, SSID)
            await self.open()
