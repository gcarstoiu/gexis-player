"""Independent ground truth for "who holds the ALSA playback device" -
criterion 7 must not trust arbitration's own self-reported acquire/release
log lines, since the whole point is checking whether the *system* (not
just the supervisor's opinion of it) ever has two renderers holding the
device at once.

Card index looked up by name at import time (never hardcoded) per this
project's own rule - Finding 005 measured it varying across builds and
even across rebuilds of the same image on the same hardware.
"""

import re
import subprocess

RENDERER_PROCESS_NAMES = {
    "squeezelite": "lms",
    "go-librespot": "spotify",
    "bluealsa-aplay": "bluetooth",
}


def _find_card_number(name="sndrpihifiberry"):
    with open("/proc/asound/cards") as f:
        for line in f:
            m = re.match(r"\s*(\d+)\s+\[([^\]]+)\]", line)
            if m and m.group(2).strip() == name:
                return int(m.group(1))
    raise RuntimeError(f"card '{name}' not found in /proc/asound/cards")


CARD_NUM = _find_card_number()
PCM_PATH = f"/dev/snd/pcmC{CARD_NUM}D0p"


def _process_name(pid):
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def current_holders():
    """Returns a list of (pid, renderer_label_or_raw_command) currently
    holding the playback PCM device. Empty list if nobody does.

    Deliberately parses only fuser's stdout (bare PIDs, one per matching
    process). `fuser -v`'s stderr table only lines up with those PIDs
    visually on a real terminal (both streams share a display, not a
    guaranteed positional correlation) - captured separately, as any
    subprocess call must, the stderr row doesn't repeat the PID at all,
    which silently produced an always-empty holder list until checked
    against real output rather than assumed from -v's man page framing.
    """
    # sudo is required: plain `fuser` as `pi` cannot see another process's
    # fds even under the same user (Yama ptrace_scope) - confirmed on
    # gexis, go-librespot holding the device was invisible to bare fuser
    # and visible only with sudo. sudo -n is passwordless here (Phase 0
    # criterion 3).
    result = subprocess.run(
        ["sudo", "-n", "fuser", PCM_PATH],
        capture_output=True,
        text=True,
    )
    holders = []
    for pid in result.stdout.split():
        command = _process_name(pid) or "?"
        holders.append((pid, RENDERER_PROCESS_NAMES.get(command, command)))
    return holders


if __name__ == "__main__":
    print(f"PCM path: {PCM_PATH}")
    print("holders:", current_holders())
