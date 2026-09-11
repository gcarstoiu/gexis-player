"""Criterion 7 attack-test scenarios involving Bluetooth. Unlike
attack_test.py's LMS<->Spotify pairs, Bluetooth's *acquisition* (a real
A2DP stream from a phone) can't be scripted here - it needs a live phone.
This script only automates the "race LMS/Spotify in while Bluetooth is
already streaming" direction; getting Bluetooth to (re)acquire is manual
(see main()'s prompts) unless bluetoothctl's own reconnect-to-trusted-
device turns out to resume streaming on its own - tried, not assumed.
"""

import subprocess
import sys
import time

import lms_cli
import pcm_holder
import spotify_api
from attack_test import Watcher

BT_MAC = "64:9D:38:E3:E5:2A"


def bt_reconnect_attempt():
    """Best-effort: BlueZ can initiate a connection to an already-trusted
    device (ARCHITECTURE.md's own note on Bluetooth reconnection) - tries
    it, but whether the phone's OS resumes actual audio streaming on
    reconnect is unknown and phone/app-dependent, not assumed to work."""
    result = subprocess.run(
        ["bluetoothctl", "connect", BT_MAC],
        capture_output=True, text=True, timeout=10,
    )
    return result.returncode == 0, result.stdout + result.stderr


def race_in(w, label, action):
    w.mark(label)
    action()
    time.sleep(2.0)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    cli = lms_cli.LmsCli()
    w = Watcher()
    w.start()
    try:
        w.mark("=== scenario: bluetooth-then-lms ===")
        for i in range(n):
            holders = pcm_holder.current_holders()
            if not any(label == "bluetooth" for _, label in holders):
                w.mark(f"round {i}: bluetooth not currently holding - attempting reconnect")
                ok, out = bt_reconnect_attempt()
                w.mark(f"round {i}: bluetoothctl connect -> {ok}: {out.strip()[:200]}")
                time.sleep(2.0)
            race_in(w, f"round {i}: lms play (race in against bluetooth)", cli.play)

        w.mark("=== scenario: bluetooth-then-spotify ===")
        for i in range(n):
            holders = pcm_holder.current_holders()
            if not any(label == "bluetooth" for _, label in holders):
                w.mark(f"round {i}: bluetooth not currently holding - attempting reconnect")
                ok, out = bt_reconnect_attempt()
                w.mark(f"round {i}: bluetoothctl connect -> {ok}: {out.strip()[:200]}")
                time.sleep(2.0)
            race_in(w, f"round {i}: spotify transfer (race in against bluetooth)",
                    lambda: spotify_api.transfer_to_gexis(play=True))
    finally:
        time.sleep(0.5)
        w.stop()
        cli.close()

    ok = w.report()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
