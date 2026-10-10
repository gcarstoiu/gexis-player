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

from gexis_core import backups, device_name, discovery, screen_apply, screen_detect, screens, settling, \
    settings_migrations, setup_network, skin_packs

logger = logging.getLogger(__name__)

ANSWERS = setup_network.STATE_DIR / "setup-answers.json"
#: ADR-0131: a backup uploaded in setup, until setup finishes or another
#: replaces it. Root's only: it holds Bluetooth keys and sign-ins.
BACKUP = setup_network.STATE_DIR / "setup-backup.tgz"
#: Larger than any backup measured (guestpi's: 2 MB), small enough that a
#: wrong file is stopped before it fills the card.
BACKUP_MAX_BYTES = 1024 * 1024 * 1024
#: ADR-0131 §1: after Network, a new player or a backup.
STARTS = ("new", "restore")
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
    #: ADR-0109: the Screen step's model, as Settings stores it ("Maker/Model").
    #: After `headless`, so a device leaving Headless is then given its screen.
    "screen": "screen",
    #: ADR-0111 decision 4. Setting it starts the pack's download, which waits
    #: for the home network (the core retries every five minutes).
    "visualiser": "visualiser_skins",
}
TEXT = ("ssid", "password", "name", "timezone", "clock", "output", "lms", "screen")
#: George, 2026-09-29: a server nobody asked for must not appear. The Music
#: step asks: find it once on the network, this address, or not at all.
LMS_MODES = ("find", "address", "off")
FLAGS = ("hidden", "spotify", "bluetooth", "headless", "visualiser", "second_player")



#: **What the phone is told, in words** (George, 2026-10-04, on the setup copy
#: review: "This needs fixing. Human readable errors."). The core's own text
#: goes to the log; the phone gets one of these. Matched on how the text
#: starts, since some carry the value that was refused.
SAID = (
    ("no network chosen", "Choose a Wi-Fi network first, or connect the player by cable."),
    ("setup is not running", "Setup has already finished. Open the player at its address instead."),
    ("unknown screen", "That screen isn't on the list. Choose another, or Headless."),
    ("choose a screen or headless, not both", "Choose a screen or Headless, not both."),
    ("no backup", "Choose the backup file first."),
)
#: Everything else is a request the page itself got wrong - nothing a person
#: can act on but trying again.
SAID_OTHERWISE = "Something went wrong saving that. Try again."


def said(raw: str) -> str:
    """The sentence the phone shows for a setup error."""
    for start, sentence in SAID:
        if raw.startswith(start):
            return sentence
    return SAID_OTHERWISE

class SetupFlow:
    def __init__(
        self,
        network: setup_network.SetupNetwork,
        settings,
        *,
        reboot=None,
        answers: Path = ANSWERS,
        backup: Path = BACKUP,
        restore_root: Path = Path("/"),
        apply_name=None,
        rename=None,
        marker: Path = setup_network.DONE_MARKER,
        set_country=None,
        find_servers=None,
        sleep=asyncio.sleep,
        plugins=None,
        settling_path: Path = settling.PATH,
    ) -> None:
        self._network = network
        self._settings = settings
        self._reboot = reboot
        self._path = answers
        self._backup = backup
        self._restore_root = restore_root
        self._apply_name = apply_name or device_name.apply_restored
        self._rename = rename or device_name.apply
        self._marker = marker
        self._set_country = set_country or _raspi_config_country
        self._find_servers = find_servers or discovery.find_servers
        self._sleep = sleep
        #: ADR-0128: what the Plugins step offers - every plugin the release
        #: ships beyond the built-in sources, as `offered()` describes them.
        self._plugins = plugins or (lambda: [])
        self._settling_path = settling_path
        self._task: asyncio.Task | None = None

    def offered(self) -> list[dict]:
        """ADR-0128 decision 1: every plugin the release ships (George: "All")."""
        return list(self._plugins())

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
            elif key == "plugins":
                ids = {p["id"] for p in self.offered()}
                if not isinstance(value, list) or not all(isinstance(v, str) and v in ids for v in value):
                    raise ValueError("plugins must be a list of offered plugins")
                data[key] = sorted(set(value))
            elif key == "start":
                if value is not None and value not in STARTS:
                    raise ValueError(f"start must be one of {', '.join(STARTS)}")
                data[key] = value
            elif key == "step":
                if not isinstance(value, str):
                    raise ValueError("step must be text")
                data[key] = value
            else:
                raise ValueError(f"unknown answer {key}")
        # ADR-0109's Screen step: a screen and Headless are one choice. A
        # model must be one gexis knows and ends Headless; Headless drops it.
        screen = changes.get("screen")
        if screen:
            if screens.by_label(screen) is None:
                raise ValueError(f"unknown screen {screen}")
            if changes.get("headless") is True:
                raise ValueError("choose a screen or headless, not both")
            data["headless"] = False
        if changes.get("headless") is True:
            data.pop("screen", None)
            # No screen, no visualiser: its step is passed over (ADR-0111).
            data.pop("visualiser", None)
        # A new password for the network, or another network, is a new try:
        # the last one's error no longer describes anything.
        if "password" in changes or "ssid" in changes:
            data.pop("error", None)
        self._write(data)
        return self.answers()

    # -- a backup (ADR-0131) -------------------------------------------------

    def upload_path(self) -> Path:
        """Where an upload is written while it arrives, beside the kept one."""
        return self._backup.with_name(self._backup.name + ".part")

    def take_backup(self, upload: Path, filename: str | None = None) -> dict:
        """Check an uploaded file and keep it for finishing. Raises
        `backups.Refused` with the sentence for the phone; a refused file is
        deleted, and one kept before it stays."""
        # Read under the name it came with, which carries when it was made.
        named = upload
        if filename and backups.NAME.match(Path(filename).name) and backups.SAFE.match(Path(filename).name):
            named = upload.with_name(Path(filename).name)
            upload.replace(named)
        try:
            seen = backups.inspect(named, len(settings_migrations.MIGRATIONS))
        except backups.Refused:
            named.unlink(missing_ok=True)
            raise
        self._backup.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(named, 0o600)
        named.replace(self._backup)
        data = self._read()
        data["backup"] = {**seen, "file": (filename or "")[:120] or None}
        data["start"] = "restore"
        self._write(data)
        logger.info("setup: backup from %s taken (%s)", seen.get("name"), ", ".join(seen["brings"]) or "settings only")
        return self.answers()

    def forget_backup(self) -> dict:
        self._backup.unlink(missing_ok=True)
        data = self._read()
        data.pop("backup", None)
        self._write(data)
        return self.answers()

    def _restoring(self, data: dict) -> bool:
        return data.get("start") == "restore" and bool(data.get("backup")) and self._backup.is_file()

    # -- finishing ---------------------------------------------------------

    @property
    def finishing(self) -> bool:
        return self._task is not None and not self._task.done()

    def finish(self) -> dict:
        """Start applying. Returns at once: the phone is told, and the
        network step happens `HANDOVER_S` later so that answer arrives.
        Tells the phone whether the restart will ask *Keep this screen?*
        (ADR-0109 as amended 2026-10-02), which it says before you leave."""
        if self.finishing:
            return {"keep_question": False}
        data = self._read()
        # On Ethernet the Wi-Fi is optional (ADR-0031 amendment 8); without a
        # network at all, it is the one answer setup cannot finish without.
        if not data.get("ssid") and self._network.status()["network"] != "online":
            raise ValueError("no network chosen")
        if data.get("start") == "restore":
            if not self._restoring(data):
                raise ValueError("no backup")
            values, _ = self._restore_values(data)
            self._task = asyncio.ensure_future(self._apply_restore(data))
            return {"keep_question": self._keep_question(values)}
        self._task = asyncio.ensure_future(self._apply(data))
        return {"keep_question": self._keep_question(data)}

    def _keep_question(self, data: dict) -> bool:
        """`data` is setup's answers, or a backup's settings by their keys."""
        label = data.get("screen")
        model = screens.by_label(label) if label and not data.get("headless") else None
        if model is None:
            return False
        try:
            turn = screen_apply.parse_rotation(self._settings.value("rotation"))
            return screen_apply.would_ask(screen_apply.Applied(model.id, turn))
        except Exception as exc:  # a guess for the phone's wording, never a failure
            logger.info("setup: cannot tell whether Keep will be asked: %s", exc)
            return True

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
            joined, reason = await self._network.join_new(ssid, data.get("password"), bool(data.get("hidden")), hold=True)
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
        self._plugins_and_settling(data)
        # ADR-0048: a rename takes effect at a restart, and the page's last
        # screen has already sent the phone to the new name.
        renaming = bool(data.get("name") and data["name"] != old_name and self._reboot is not None)
        # ADR-0109: a screen chosen here was written for the next start, and
        # the restart is where *Keep this screen?* is asked.
        screening = bool(data.get("screen") and self._reboot is not None)
        restart_for = "name" if renaming and not screening else "screen" if screening and not renaming else \
            "both" if renaming else None
        self._network.finished(ssid, library, restart_for, data.get("name") or old_name)
        logger.info("setup: finished; library %s", library)
        await self._sleep(DONE_S)
        if restart_for:
            # **Straight from setup to the restart** (George, 2026-09-29: the
            # home screen blinked in between). The panel keeps the last setup
            # screen, "Restarting to take its new name", until the restart
            # takes it down; the next boot starts as a configured device.
            logger.info("setup: the name or the screen changed; restarting")
            await self._reboot()
            return
        self._network.done()

    def _restore_values(self, data: dict) -> tuple[dict, set]:
        """**The backup's settings, with what was changed in setup over them**
        (ADR-0131 as amended; George, 2026-10-08: *"from the overview have the
        ability to change for example the Device name"*). A step's answer is
        there only when the step was opened and continued from, so what the
        owner left alone stays the backup's. Returns the values and the keys
        setup changed."""
        values = dict(data["backup"]["settings"])
        changed = set()
        for answer, key in SETTINGS.items():
            if answer == "lms" or answer not in data or data[answer] in (None, ""):
                continue
            values[key] = data[answer]
            changed.add(key)
        if data.get("headless") is True:
            values.pop("screen", None)
            changed.discard("screen")
        mode = data.get("lms_mode")
        if mode == "off":
            values["lms_enabled"] = False
            changed.add("lms_enabled")
        elif mode == "address" and data.get("lms"):
            values.update(lms_server=data["lms"], lms_enabled=True)
            changed |= {"lms_server", "lms_enabled"}
        return values, changed

    async def _apply_restore(self, data: dict) -> None:
        """**ADR-0131 §5, as amended**: the join; the backup's files put back;
        what was changed in setup written over them; then everything that
        lives outside the store (the screen, the time zone, the name) applied
        through Settings, as setup applies its own; what to wait for; the
        restart. A failed join keeps the backup and goes back to Network."""
        values, changed = self._restore_values(data)
        country = setup_network.country_for(values.get("timezone"))
        if country:
            await self._set_country(country)
        ssid = data.get("ssid")
        if ssid:
            joined, reason = await self._network.join_new(ssid, data.get("password"), bool(data.get("hidden")), hold=True)
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
        if values.get("headless"):
            values.pop("screen", None)
        elif values.get("screen") and screens.by_label(values["screen"]) is None:
            # A model this version does not know - a newer backup's.
            logger.warning("setup: the backup's screen %s is not known here; left to Settings", values["screen"])
            values.pop("screen")
            changed.discard("screen")
        # The plugins: the Plugins step's answer when it was changed, else the
        # backup's own.
        offered = self.offered()
        if "plugins" in data:
            enabled = set(data["plugins"])
        else:
            # On unless the backup switched it off: a switch's default is on.
            off = set(data["backup"].get("disabled") or [])
            enabled = {p["id"] for p in offered if p["id"] not in off}
        writes = {key: values[key] for key in changed if key in values}
        if "plugins" in data:
            writes.update({p["row"]: p["id"] in enabled for p in offered})
        if data.get("lms_mode") == "find":
            library = await self._library(data, apply=False)
            if library.get("state") == "found":
                writes.update(lms_server=library["address"], lms_enabled=True)
        # **What lives outside the store first, through Settings as setup's
        # own answers** - the screen, the time zone, the name. Before the
        # files go back, not after: once the settings file is replaced, the
        # store the core holds open refuses every write ("attempt to write a
        # readonly database"), and 0.9.5's restore lost the name, the time
        # zone and the screen to it (2026-10-08: a renamed backup on a new
        # card came up as raspberrypi).
        for key in backups.APPLIED:
            if key in values and values[key] is not None:
                self._set_quietly(key, values[key])
        # **A second player** (ADR-0131 as amended): a backup given another
        # name leaves the first player's identities behind, unless the owner
        # said it is the same player.
        renamed = (values.get("device_name") or "").strip() != (data["backup"]["settings"].get("device_name") or "").strip()
        second = renamed and data.get("second_player") is not False
        leave = tuple(prefix for prefix, _ in backups.IDENTITIES) if second else ()
        if second:
            logger.info("setup: restoring as another player; leaving behind %s",
                        ", ".join(label for _, label in backups.IDENTITIES))
        try:
            await asyncio.to_thread(backups.restore_file, self._backup, self._restore_root, leave)
            if second:
                # Before setup's own answers, so a plugin switched on in the
                # review still is.
                await asyncio.to_thread(backups.forget_settings, backups.IDENTITY_SETTINGS, self._restore_root)
            await asyncio.to_thread(backups.write_settings, writes, self._restore_root)
            if "device_name" in changed and values.get("device_name"):
                # The backup's own name file just came back with the files:
                # the name changed in setup goes over it again, everywhere.
                await asyncio.to_thread(self._rename, values["device_name"])
            else:
                # The backup's name in all four places, as Settings' restore
                # does.
                await asyncio.to_thread(self._apply_name)
        except Exception as exc:  # noqa: BLE001 - the restart still comes
            logger.error("setup: the backup did not go back: %s", exc)
        finally:
            self._backup.unlink(missing_ok=True)
        wait = []
        if values.get("visualiser_skins") and not values.get("headless"):
            wait.append({"id": "skins", "name": "The visualiser's skins"})
        for plugin in offered:
            if plugin["id"] in enabled and plugin.get("component"):
                wait.append({"id": plugin["component"], "name": plugin["name"]})
        try:
            settling.begin(wait, self._settling_path)
        except OSError as exc:
            logger.warning("setup: cannot record what to wait for: %s", exc)
        name = values.get("device_name") or data["backup"].get("name")
        self._network.finished(ssid, {"state": "unchanged"}, "restore", name)
        logger.info("setup: finished by restoring a backup (%d setting(s) changed in setup); restarting",
                    len(writes))
        await self._sleep(DONE_S)
        if self._reboot is not None:
            await self._reboot()
        else:
            self._network.done()

    async def _library(self, data: dict, apply: bool = True) -> dict:
        """**Lyrion, once the device is on the home network** (George,
        2026-09-29: *"If we can stop and start the WiFi to check the network,
        why can't we do the same for the Lms server?"*). Over the setup
        network there is nothing to find (amendment 4); after the join there
        is. An address typed in setup is kept as it is. Without one: exactly
        one server found is used; several are named and left to Settings;
        none is said. `apply=False` (a restore, ADR-0131) only says what was
        found: the restore writes it into the settings it puts back."""
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
            if apply:
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


    def _plugins_and_settling(self, data: dict) -> None:
        """ADR-0128: the plugins chosen switched on - after the join, since
        each downloads from the internet - and every other one offered
        switched off, explicitly (a switch's default is not a choice). Then
        what the first start waits for: the skin pack, if one was chosen,
        and each chosen plugin that downloads its software."""
        chosen = set(data.get("plugins") or [])
        wait = []
        if data.get("visualiser") and not data.get("headless"):
            wait.append({"id": "skins", "name": "The visualiser's skins"})
        for plugin in self.offered():
            on = plugin["id"] in chosen
            self._set_quietly(plugin["row"], on)
            if on and plugin.get("component"):
                wait.append({"id": plugin["component"], "name": plugin["name"]})
        try:
            settling.begin(wait, self._settling_path)
        except OSError as exc:
            logger.warning("setup: cannot record what to wait for: %s", exc)

    def _set_quietly(self, key: str, value) -> None:
        try:
            if self._settings.value(key) != value:
                self._settings.set(key, value)
        except Exception as exc:
            logger.warning("setup: %s not set: %s", key, exc)


def _screen_json(screen: screens.Screen) -> dict:
    return {
        "id": screen.id,
        "label": screen.label,
        "maker": screen.maker,
        "model": screen.model,
        "width": screen.width,
        "height": screen.height,
        "family": screen.family,
        "tested": screen.tested,
        #: ADR-0111: the skin pack this screen gets, which the Visualiser
        #: step names ("1280x800"), or None if no pack fits it.
        "skins": _pack_name(screen.width, screen.height),
        "skin_count": skin_packs.COUNTS.get(_pack_name(screen.width, screen.height) or ""),
    }


def _pack_name(width: int, height: int) -> str | None:
    size = skin_packs.for_screen(width, height)
    return f"{size[0]}x{size[1]}" if size else None


def screen_choices(report: screen_detect.Seen) -> dict:
    """**The Screen step's page** (ADR-0109): what the screen reports, the
    tested model that suggests (or nothing), and every model. The page tells
    its three states apart from this: a suggestion is *recognised*, a screen
    connected without one is *uncertain*, nothing connected is *none*."""
    suggested = screen_detect.suggest(report)
    return {
        "seen": report.to_json(),
        "suggested": _screen_json(suggested) if suggested else None,
        "models": [_screen_json(s) for s in screens.all_screens()],
    }


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
