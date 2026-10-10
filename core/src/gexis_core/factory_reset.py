"""**Reset to factory settings** (ADR-0132).

Confirming in Settings writes `REQUEST` and restarts. At the start of the next
boot `gexis-factory-reset.service` runs this module, before NetworkManager,
Bluetooth, the renderers and the core, so nothing holds a file it removes, and
the player is back to a freshly flashed card: the same boot ends in setup.

`wipe()` takes a `root` so the tests can run it on a folder.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

from gexis_core import board_apply, journal, screen_apply

logger = logging.getLogger("gexis_core.factory_reset")

#: Written by Settings; its presence at boot is the request.
REQUEST = Path("/var/lib/gexis/factory-reset")

#: Removed outright, files or folders, relative to the root (ADR-0132 §3).
REMOVED = (
    # Settings and what was built from them.
    "var/lib/gexis-core/settings.db", "var/lib/gexis-core/settings.db-wal", "var/lib/gexis-core/settings.db-shm",
    "var/lib/gexis-core/enrichment.db", "var/lib/gexis-core/enrichment.db-wal", "var/lib/gexis-core/enrichment.db-shm",
    "var/cache/gexis-core",
    # The backups kept on the player (George: deleted).
    "var/lib/gexis-core/backups",
    # The name.
    "etc/gexis/device-name.env", "etc/machine-info",
    # Network share passwords; kept debug logs.
    "etc/gexis/shares", "etc/systemd/journald.conf.d/60-gexis-debug-logs.conf",
    # Setup comes back (ADR-0104): no marker, no answers, nothing settling.
    "var/lib/gexis/setup-done", "var/lib/gexis/setup-answers.json", "var/lib/gexis/setup-backup.tgz",
    "var/lib/gexis/settling.json",
    # The screen and the sound card board.
    "etc/gexis/screen.env", "var/lib/gexis/screen.json", "var/lib/gexis/screen-seen.json",
    "var/lib/gexis/board.json",
    # Downloads and plugins.
    "var/lib/gexis/components", "var/lib/gexis/plugins", "var/lib/gexis/plugins-known.json",
    "var/lib/gexis/updates/pack.json", "var/lib/gexis-uploaded", "var/lib/private/gexis-uploaded",
    # The downloaded wallpapers: Pixabay's and Space pictures (ADR-0133).
    "var/lib/gexis-core/wallpapers", "var/lib/gexis-core/space",
    "home/pi/plexamp",
    # Identities.
    "var/lib/go-librespot/state.json", "var/lib/beszel-agent", "var/lib/beszel-hub",
    "home/pi/.local/share/Plexamp",
    # The Lyrion Server's settings and library.
    "var/lib/squeezeboxserver/prefs", "var/lib/squeezeboxserver/cache",
    "var/lib/gexis/lyrion-addons.done", "var/lib/gexis/lyrion-scan-stopped.json",
    "var/lib/gexis/lyrion-usb-seen.json",
)
#: Emptied, the folder itself kept (its owner and mode belong to the image).
#: Never the music folder (`/var/lib/gexis-music`, with Lyrion's playlists)
#: or the Pictures share (`/var/lib/gexis-core/pictures`): what the owner put
#: there stays (George, 2026-10-09, amending ADR-0132).
EMPTIED = (
    "etc/NetworkManager/system-connections",
    "var/lib/bluetooth",
    "var/log/journal",
)
#: The image's own name and time zone (pi-gen's defaults; ADR-0132 §3).
HOSTNAME = "raspberrypi"
TIMEZONE = "Europe/London"
#: What Spotify is called on a fresh card (go-librespot-config.yml).
SPOTIFY_NAME = "gexis"
#: `cmdline.txt` entries the player adds: the Wi-Fi country.
ADDED_TO_CMDLINE = ("cfg80211.ieee80211_regdom=",)


def request(path: Path = REQUEST) -> None:
    """What Settings does: ask for the reset at the next boot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ\n", time.gmtime()))


def _remove(target: Path) -> bool:
    if target.is_symlink() or target.is_file():
        target.unlink()
        return True
    if target.is_dir():
        shutil.rmtree(target)
        return True
    return False


def _empty(folder: Path) -> int:
    count = 0
    if folder.is_dir():
        for child in folder.iterdir():
            if _remove(child):
                count += 1
    return count


def _cmdline(text: str) -> str:
    words = [w for w in text.split() if not w.startswith(ADDED_TO_CMDLINE)]
    return " ".join(words)


def wipe(root: Path = Path("/"), run=subprocess.run) -> list[str]:
    """Everything back to a freshly flashed card. Returns what was done, for
    the log. Never raises for a single step: a reset that stops halfway is
    worse than one that goes on and says what it could not do."""
    done: list[str] = []

    def step(what: str, action) -> None:
        try:
            if action():
                done.append(what)
        except Exception as exc:  # noqa: BLE001 - one step must not stop the rest
            logger.warning("factory reset: %s failed: %s", what, exc)

    for rel in REMOVED:
        step(rel, lambda rel=rel: _remove(root / rel))
    for rel in EMPTIED:
        step(f"{rel}/*", lambda rel=rel: _empty(root / rel) > 0)

    def hostname() -> bool:
        (root / "etc/hostname").write_text(HOSTNAME + "\n")
        hosts = root / "etc/hosts"
        if hosts.exists():
            lines = [f"127.0.1.1\t{HOSTNAME}" if line.startswith("127.0.1.1") else line
                     for line in hosts.read_text().splitlines()]
            hosts.write_text("\n".join(lines) + "\n")
        if root == Path("/"):
            # The kernel took the old name from /etc/hostname earlier in this
            # boot; setup would advertise it until the next start.
            run(["hostname", HOSTNAME], capture_output=True, text=True, check=False)
        return True
    step("hostname", hostname)

    def spotify_name() -> bool:
        config = root / "var/lib/go-librespot/config.yml"
        if not config.exists():
            return False
        lines = [f"device_name: {SPOTIFY_NAME}" if line.startswith("device_name:") else line
                 for line in config.read_text().splitlines()]
        config.write_text("\n".join(lines) + "\n")
        return True
    step("Spotify's name", spotify_name)

    def timezone() -> bool:
        zone = root / "usr/share/zoneinfo" / TIMEZONE
        localtime = root / "etc/localtime"
        if localtime.is_symlink() or localtime.exists():
            localtime.unlink()
        localtime.symlink_to(Path("/usr/share/zoneinfo") / TIMEZONE if root == Path("/") else zone)
        (root / "etc/timezone").write_text(TIMEZONE + "\n")
        return True
    step("time zone", timezone)

    def cmdline() -> bool:
        path = root / "boot/firmware/cmdline.txt"
        if not path.exists():
            return False
        before = path.read_text()
        after = _cmdline(screen_apply.with_video(before.strip(), None)) + "\n"
        if after != before:
            path.write_text(after)
            return True
        return False
    step("cmdline.txt", cmdline)

    def config_txt() -> bool:
        path = root / "boot/firmware/config.txt"
        if not path.exists():
            return False
        before = path.read_text()
        after = board_apply.with_block(before, None)
        if after != before:
            path.write_text(after)
            return True
        return False
    step("config.txt", config_txt)

    def skin_packs() -> bool:
        if root != Path("/"):
            return False
        listed = run(["dpkg-query", "-W", "-f", "${Package} ${Status}\\n", "gexis-skins*"],
                     capture_output=True, text=True, check=False)
        packs = [line.split()[0] for line in listed.stdout.splitlines()
                 if line.strip().endswith("installed") and " not-installed" not in line]
        if not packs:
            return False
        run(["dpkg", "--purge", *packs], capture_output=True, text=True, check=False)
        return True
    step("skin packs", skin_packs)

    def keep_this_boots_log() -> bool:
        # TEMPORARY - remove before the first public release (journal.AFTER_RESET).
        dropin = root / journal.AFTER_RESET.relative_to("/")
        dropin.parent.mkdir(parents=True, exist_ok=True)
        dropin.write_text(journal.AFTER_RESET_CONTENT)
        if root == Path("/"):
            # journald read its settings before this ran; the restart takes
            # the new one, and the flush ordered after this unit then moves the
            # boot's log so far onto the card.
            run(["systemctl", "restart", "systemd-journald"], capture_output=True, text=True, check=False)
        return True
    step("this boot's log kept (temporary)", keep_this_boots_log)
    return done


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(name)s: %(message)s")
    if not REQUEST.exists():
        return 0
    logger.info("factory reset: requested %s; wiping", REQUEST.read_text().strip())
    done = wipe()
    logger.info("factory reset: done - %s", ", ".join(done) or "nothing to remove")
    REQUEST.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
