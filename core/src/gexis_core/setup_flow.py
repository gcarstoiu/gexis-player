# SPDX-License-Identifier: GPL-3.0-or-later
"""**The answers setup collects, and applying them** (ADR-0104 §4).

**The core holds the answers, not the page.** The phone loses the page the
moment the device leaves the setup network, and Finding 099 saw the page's
connection drop once without that. So each step is saved here as it is
completed, and a page that reopens resumes from what is here.

**Applying** writes the settings first, through `Settings.set`, so each one
does exactly what it does from Settings (the name reaches its four places,
Headless stops the panel's units, and so on). Then the Wi-Fi country, from the
time zone. Then the network, last, because it is the step that loses the page.

**A join that fails keeps every answer but the password** (ADR-0031 amendment
5), with the reason, and the setup network comes back.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from gexis_core import discovery, setup_network

logger = logging.getLogger(__name__)

ANSWERS = setup_network.STATE_DIR / "setup-answers.json"
#: How long the panel shows where the device went, before its own screens.
DONE_S = 10.0

#: Answer -> the setting it becomes. The Wi-Fi is not a setting; it is a
#: NetworkManager profile, made last.
SETTINGS = {
    "name": "device_name",
    "timezone": "timezone",
    "clock": "clock_format",
    "output": "output_device",
    "lms": "lms_server",
    "spotify": "spotify_enabled",
    "bluetooth": "bt_enabled",
    "headless": "headless",
}
TEXT = ("ssid", "password", "name", "timezone", "clock", "output", "lms")
#: George, 2026-09-29: a server nobody asked for must not appear. The Music
#: step asks: find it once on the network, this address, or not at all.
LMS_MODES = ("find", "address", "off")
FLAGS = ("hidden", "spotify", "bluetooth", "headless")


class SetupFlow:
    def __init__(
        self,
        network: setup_network.SetupNetwork,
        settings,
        *,
        reboot=None,
        answers: Path = ANSWERS,
        marker: Path = setup_network.DONE_MARKER,
        set_country=None,
        find_servers=None,
        sleep=asyncio.sleep,
    ) -> None:
        self._network = network
        self._settings = settings
        self._reboot = reboot
        self._path = answers
        self._marker = marker
        self._set_country = set_country or _raspi_config_country
        self._find_servers = find_servers or discovery.find_servers
        self._sleep = sleep
        self._task: asyncio.Task | None = None

    # -- the answers ---------------------------------------------------------

    def _read(self) -> dict:
        try:
            data = json.loads(self._path.read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        """Atomic, and `0600` from the first byte: the Wi-Fi password is in
        it until the join succeeds or fails."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump(data, out)
        tmp.replace(self._path)

    def answers(self) -> dict:
        """What the page resumes from. **Never the password**: whether there
        is one, so the page can say so, and the last join's error."""
        data = self._read()
        public = {k: v for k, v in data.items() if k != "password"}
        public["has_password"] = bool(data.get("password"))
        return public

    def save(self, changes: dict) -> dict:
        if not isinstance(changes, dict):
            raise ValueError("answers must be an object")
        data = self._read()
        for key, value in changes.items():
            if key in TEXT:
                if value is not None and not isinstance(value, str):
                    raise ValueError(f"{key} must be text")
                data[key] = value
            elif key in FLAGS:
                if not isinstance(value, bool):
                    raise ValueError(f"{key} must be true or false")
                data[key] = value
            elif key == "lms_mode":
                if value is not None and value not in LMS_MODES:
                    raise ValueError(f"lms_mode must be one of {', '.join(LMS_MODES)}")
                data[key] = value
            elif key == "step":
                if not isinstance(value, str):
                    raise ValueError("step must be text")
                data[key] = value
            else:
                raise ValueError(f"unknown answer {key}")
        # A new password for the network, or another network, is a new try:
        # the last one's error no longer describes anything.
        if "password" in changes or "ssid" in changes:
            data.pop("error", None)
        self._write(data)
        return self.answers()

    # -- finishing ---------------------------------------------------------

    @property
    def finishing(self) -> bool:
        return self._task is not None and not self._task.done()

    def finish(self) -> None:
        """Start applying. Returns at once: the phone is told, and the
        network step happens `HANDOVER_S` later so that answer arrives."""
        if self.finishing:
            return
        data = self._read()
        # On Ethernet the Wi-Fi is optional (ADR-0031 amendment 8); without a
        # network at all, it is the one answer setup cannot finish without.
        if not data.get("ssid") and self._network.status()["network"] != "online":
            raise ValueError("no network chosen")
        self._task = asyncio.ensure_future(self._apply(data))

    async def _apply(self, data: dict) -> None:
        old_name = self._settings.value("device_name")
        mode = data.get("lms_mode")
        for answer, key in SETTINGS.items():
            if answer not in data or data[answer] in (None, ""):
                continue
            # The typed address only counts when "Enter an address" is the
            # answer; a field left filled under another choice is not one.
            if answer == "lms" and mode not in (None, "address"):
                continue
            try:
                if self._settings.value(key) != data[answer]:
                    self._settings.set(key, data[answer])
                    logger.info("setup: %s set", key)
            except Exception as exc:
                # One setting refusing must not strand the device on the setup
                # network; it is reported and the rest go on.
                logger.warning("setup: %s not set: %s", key, exc)
        country = setup_network.country_for(data.get("timezone"))
        if country:
            await self._set_country(country)

        ssid = data.get("ssid")
        if ssid:
            joined, reason = await self._network.join_new(ssid, data.get("password"), bool(data.get("hidden")))
        else:
            joined, reason = True, None
        if not joined:
            data.pop("password", None)
            data["error"] = {"ssid": ssid, "reason": reason}
            data["step"] = "wifi"
            self._write(data)
            return
        self._marker.parent.mkdir(parents=True, exist_ok=True)
        self._marker.touch()
        self._path.unlink(missing_ok=True)
        library = await self._library(data)
        # ADR-0048: a rename takes effect at a restart, and the page's last
        # screen has already sent the phone to the new name.
        renaming = bool(data.get("name") and data["name"] != old_name and self._reboot is not None)
        self._network.finished(ssid, library, renaming, data.get("name") or old_name)
        logger.info("setup: finished; library %s", library)
        await self._sleep(DONE_S)
        if renaming:
            # **Straight from setup to the restart** (George, 2026-09-29: the
            # home screen blinked in between). The panel keeps the last setup
            # screen, "Restarting to take its new name", until the restart
            # takes it down; the next boot starts as a configured device.
            logger.info("setup: the name changed; restarting to take it")
            await self._reboot()
            return
        self._network.done()

    async def _library(self, data: dict) -> dict:
        """**Lyrion, once the device is on the home network** (George,
        2026-09-29: *"If we can stop and start the WiFi to check the network,
        why can't we do the same for the Lms server?"*). Over the setup
        network there is nothing to find (amendment 4); after the join there
        is. An address typed in setup is kept as it is. Without one: exactly
        one server found is used; several are named and left to Settings;
        none is said."""
        mode = data.get("lms_mode") or ("address" if data.get("lms") else None)
        if mode == "off":
            self._set_quietly("lms_enabled", False)
            return {"state": "off"}
        if mode == "address" and data.get("lms"):
            self._set_quietly("lms_enabled", True)
            return {"state": "given", "address": data["lms"]}
        if mode != "find":
            # No choice recorded (an answers file from before this): nothing
            # is looked for and nothing is changed.
            return {"state": "unchanged"}
        try:
            servers = await self._find_servers()
        except Exception as exc:  # the search is a courtesy, never a failure
            logger.warning("setup: Lyrion search failed: %s", exc)
            servers = []
        if len(servers) == 1:
            server = servers[0]
            try:
                self._settings.set("lms_server", server["address"])
            except Exception as exc:
                logger.warning("setup: lms_server not set: %s", exc)
                return {"state": "none"}
            self._set_quietly("lms_enabled", True)
            return {"state": "found", "name": server.get("name") or server["address"], "address": server["address"]}
        if servers:
            return {"state": "several", "names": [s.get("name") or s["address"] for s in servers]}
        return {"state": "none"}


    def _set_quietly(self, key: str, value) -> None:
        try:
            if self._settings.value(key) != value:
                self._settings.set(key, value)
        except Exception as exc:
            logger.warning("setup: %s not set: %s", key, exc)


async def _raspi_config_country(country: str) -> None:
    """The OS's own mechanism: `cmdline.txt` for the next boot and `iw reg
    set` for now."""
    process = await asyncio.create_subprocess_exec(
        "raspi-config", "nonint", "do_wifi_country", country,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await process.communicate()
    if process.returncode:
        logger.warning("setup: Wi-Fi country %s not set: %s", country, err.decode(errors="replace").strip())
    else:
        logger.info("setup: Wi-Fi country %s", country)
