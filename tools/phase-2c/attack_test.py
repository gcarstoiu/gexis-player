"""Criterion 7 attack test: "no renderer can be made to play while another
holds the device."

Runs entirely on gexis (LMS's CLI and Spotify's Web API are both only
reachable from here or from gexis's own LAN; the PCM/FIFO checks are
inherently local). Independently polls the actual PCM holder (pcm_holder,
via sudo fuser - not arbitration's own acquire/release log lines) at high
frequency throughout each scenario and flags any moment more than one
renderer's process holds the device at once.

Bluetooth scenarios are separate (bt_attack_test.py) since they need a
live phone as the audio source - this file covers the fully-scriptable
LMS<->Spotify pairs.
"""

import sys
import threading
import time

import lms_cli
import pcm_holder
import spotify_api

POLL_INTERVAL_S = 0.02


class Watcher:
    def __init__(self):
        self.events = []  # (timestamp, holders)
        self.violations = []
        self._stop = threading.Event()
        self._last = None
        self._t0 = time.monotonic()

    def _mark(self, label):
        self.events.append((time.monotonic() - self._t0, "MARK", label))

    def mark(self, label):
        self._mark(label)

    def _run(self):
        while not self._stop.is_set():
            holders = pcm_holder.current_holders()
            labels = tuple(sorted({label for _, label in holders}))
            if labels != self._last:
                self.events.append((time.monotonic() - self._t0, "HOLDERS", labels))
                self._last = labels
                if len(labels) > 1:
                    self.violations.append((time.monotonic() - self._t0, labels))
            time.sleep(POLL_INTERVAL_S)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def report(self):
        print("\n--- timeline ---")
        for t, kind, val in self.events:
            print(f"{t:8.3f}s  {kind:8s} {val}")
        print(f"\n--- violations: {len(self.violations)} ---")
        for t, labels in self.violations:
            print(f"{t:8.3f}s  MULTIPLE HOLDERS: {labels}")
        return len(self.violations) == 0


def scenario_lms_then_spotify_race(w, cli, n=5):
    """LMS playing, then Spotify races in to acquire, repeated n times."""
    for i in range(n):
        w.mark(f"round {i}: lms play")
        cli.play()
        time.sleep(1.0)
        w.mark(f"round {i}: spotify transfer (race in)")
        spotify_api.transfer_to_gexis(play=True)
        time.sleep(1.5)


def scenario_spotify_then_lms_race(w, cli, n=5):
    """Spotify playing, then LMS races in to acquire, repeated n times."""
    for i in range(n):
        w.mark(f"round {i}: spotify transfer")
        spotify_api.transfer_to_gexis(play=True)
        time.sleep(1.0)
        w.mark(f"round {i}: lms play (race in)")
        cli.play()
        time.sleep(1.5)


def scenario_lms_reclaim_spam(w, cli, n=5):
    """Targets Finding 009/010's LMS-reclaim mystery: after Spotify has
    just taken over, spam LMS play commands rapidly to see whether
    arbitration bounces the device back without a genuine new user
    action."""
    for i in range(n):
        w.mark(f"round {i}: spotify transfer")
        spotify_api.transfer_to_gexis(play=True)
        time.sleep(0.8)
        w.mark(f"round {i}: LMS play-spam (5x, 100ms apart)")
        for _ in range(5):
            cli.play()
            time.sleep(0.1)
        time.sleep(1.5)


SCENARIOS = {
    "lms-then-spotify": scenario_lms_then_spotify_race,
    "spotify-then-lms": scenario_spotify_then_lms_race,
    "lms-reclaim-spam": scenario_lms_reclaim_spam,
}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "all"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    cli = lms_cli.LmsCli()
    w = Watcher()
    w.start()
    try:
        if name == "all":
            for scenario_name, fn in SCENARIOS.items():
                w.mark(f"=== scenario: {scenario_name} ===")
                fn(w, cli, n)
        else:
            SCENARIOS[name](w, cli, n)
    finally:
        time.sleep(0.5)
        w.stop()
        cli.close()

    ok = w.report()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
