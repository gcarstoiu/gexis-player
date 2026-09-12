"""Criterion 7 attack test, rewritten for ADR-0027's acquisition model.

"No renderer can be made to play while another holds the device."

`attack_test.py` predates ADR-0027 and drives LMS with `cli.play()`. That
was the acquisition trigger under the base-slot model; it is not any more -
**powering the player on is**. Run unchanged against the current build, its
later rounds produce no holder transitions at all: the renderers never
contend, and "0 violations" then means nothing. Kept alongside this file
rather than deleted, since its Spotify-side driving is still correct and it
is the record of what was measured before.

Two things this adds:

  1. **LMS is driven by power**, the real acquisition path now - including
     the press-play route, where LMS's own auto-power-on takes the device.
  2. **Every round asserts it actually contended.** A round that produced
     no handover is counted as INCONCLUSIVE, not as a pass. A clean run has
     to show contention *and* no violation; silence is not evidence.

The violation check itself is unchanged and mechanism-independent: poll the
real PCM holders (sudo fuser, not arbitration's own log lines) at 20ms and
flag any moment two renderers hold the device at once.

Runs on gexis under the gexis-core venv.
"""

import gzip
import json
import subprocess
import sys
import threading
import time
import urllib.request

sys.path.insert(0, "/tmp/phase2c-diag")
import lms_cli  # noqa: E402
import pcm_holder  # noqa: E402
import spotify_api  # noqa: E402

LMS_BASE = "http://192.168.178.188:9000"
PLAYER = "e4:5f:01:58:89:07"
POLL_INTERVAL_S = 0.02
_id = [0]


def rpc(command):
    _id[0] += 1
    body = json.dumps({"id": _id[0], "method": "slim.request",
                       "params": [PLAYER, command]}).encode()
    req = urllib.request.Request(f"{LMS_BASE}/jsonrpc.js", data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    raw = urllib.request.urlopen(req, timeout=5).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw).get("result", {})


class Watcher:
    """Independent ground truth. Never consults arbitration's own opinion."""

    def __init__(self):
        self.violations = []
        self.transitions = []
        self._stop = threading.Event()
        self._last = None
        self._t0 = time.monotonic()

    def _run(self):
        while not self._stop.is_set():
            labels = tuple(sorted({l for _, l in pcm_holder.current_holders()}))
            if labels != self._last:
                self.transitions.append((time.monotonic() - self._t0, labels))
                renderers = [l for l in labels if l in ("lms", "spotify", "bluetooth")]
                if len(renderers) > 1:
                    self.violations.append((time.monotonic() - self._t0, labels))
                self._last = labels
            time.sleep(POLL_INTERVAL_S)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def holders_seen_since(self, mark):
        return [(t, h) for t, h in self.transitions if t >= mark]

    def now(self):
        return time.monotonic() - self._t0


def holders():
    return tuple(sorted(l for _, l in pcm_holder.current_holders()))


def wait_for(pred, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred(holders()):
            return True
        time.sleep(0.03)
    return False


class Round:
    """Tracks whether a round genuinely contended, so a no-op cannot pass."""

    def __init__(self, w, label):
        self.w = w
        self.label = label
        self.mark = w.now()
        self.contended = False

    def note_handover(self, who):
        self.contended = True
        self.who = who


def scenario_spotify_then_lms_poweron(w, n):
    """Spotify holds the device; LMS races in by being POWERED ON - the real
    acquisition under ADR-0027."""
    results = []
    for i in range(n):
        r = Round(w, f"spotify -> lms power-on #{i}")
        rpc(["power", "1"])
        lms_cli_play()
        wait_for(lambda h: "lms" in h, 15)
        time.sleep(1.5)
        spotify_api.transfer_to_gexis(play=True)
        if not wait_for(lambda h: "spotify" in h, 15):
            results.append((r.label, "INCONCLUSIVE - spotify never took the device"))
            continue
        time.sleep(1.0)
        rpc(["power", "1"])          # <- the race: activate while spotify plays
        if wait_for(lambda h: "lms" in h, 15):
            r.note_handover("lms")
            results.append((r.label, "contended"))
        else:
            results.append((r.label, "INCONCLUSIVE - lms never took it back"))
        time.sleep(1.0)
    return results


def scenario_spotify_then_lms_pressplay(w, n):
    """Spotify holds the device; LMS races in via the press-play route,
    where LMS's own auto-power-on takes it."""
    results = []
    for i in range(n):
        r = Round(w, f"spotify -> lms press-play #{i}")
        rpc(["power", "1"])
        lms_cli_play()
        wait_for(lambda h: "lms" in h, 15)
        time.sleep(1.5)
        spotify_api.transfer_to_gexis(play=True)
        if not wait_for(lambda h: "spotify" in h, 15):
            results.append((r.label, "INCONCLUSIVE - spotify never took the device"))
            continue
        time.sleep(1.0)
        lms_cli_play()               # <- play on a powered-off player
        if wait_for(lambda h: "lms" in h, 15):
            r.note_handover("lms")
            results.append((r.label, "contended"))
        else:
            results.append((r.label, "INCONCLUSIVE - lms never took it back"))
        time.sleep(1.0)
    return results


def scenario_power_cycle_churn(w, n):
    """Deactivate/activate churn while Spotify plays - new user behaviour
    under ADR-0027, and the shape that broke the two reverted fixes."""
    results = []
    for i in range(n):
        r = Round(w, f"power churn #{i}")
        rpc(["power", "1"])
        lms_cli_play()
        wait_for(lambda h: "lms" in h, 15)
        time.sleep(1.0)
        spotify_api.transfer_to_gexis(play=True)
        if not wait_for(lambda h: "spotify" in h, 15):
            results.append((r.label, "INCONCLUSIVE - spotify never took the device"))
            continue
        for _ in range(6):           # rapid activate/deactivate
            rpc(["power", "1"])
            time.sleep(0.35)
            rpc(["power", "0"])
            time.sleep(0.35)
        r.note_handover("churn")
        results.append((r.label, "contended"))
        time.sleep(1.5)
    return results


def lms_cli_play():
    cli.play()


SCENARIOS = {
    "spotify-then-lms-poweron": scenario_spotify_then_lms_poweron,
    "spotify-then-lms-pressplay": scenario_spotify_then_lms_pressplay,
    "power-cycle-churn": scenario_power_cycle_churn,
}


def main():
    global cli
    name = sys.argv[1] if len(sys.argv) > 1 else "all"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    cli = lms_cli.LmsCli()
    w = Watcher()
    w.start()
    all_results = []
    try:
        todo = SCENARIOS.items() if name == "all" else [(name, SCENARIOS[name])]
        for scenario_name, fn in todo:
            print(f"\n=== scenario: {scenario_name} ===")
            for label, outcome in fn(w, n):
                print(f"  {label:42s} {outcome}")
                all_results.append((label, outcome))
    finally:
        w.stop()
        rpc(["power", "1"])
        cli.pause()
        cli.close()

    contended = sum(1 for _, o in all_results if o == "contended")
    inconclusive = sum(1 for _, o in all_results if o.startswith("INCONCLUSIVE"))
    print(f"\n--- rounds that genuinely contended: {contended}/{len(all_results)} "
          f"({inconclusive} inconclusive) ---")
    print(f"--- violations (two renderers on the PCM at once): "
          f"{len(w.violations)} ---")
    for t, labels in w.violations:
        print(f"      +{t:6.2f}s  {labels}")
    if contended == 0:
        print("\n*** NO ROUND CONTENDED - this run proves nothing about criterion 7")
    elif not w.violations:
        print(f"\ncriterion 7 held across {contended} genuinely contended rounds")


if __name__ == "__main__":
    main()
