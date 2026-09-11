"""Criterion 8: "time from stop of renderer A to first sample of renderer
B", same-rate and cross-rate, distribution over >=20 runs (DEVELOPMENT.md;
also matches tier 3's >=20-runs rule for anything snd-aloop-adjacent,
Finding 004).

Both T0 ("stop of renderer A" - last real audible frame) and T1 ("first
sample of renderer B") are read from the *same* instrument in one pass
(spectrum_fifo.measure_takeover_gap) - not T0 from pcm_holder and T1 from
the FIFO separately, which would mix two different measurement mechanisms
with their own relative timing quirks. pcm_holder is used only as a
precondition/postcondition sanity check (A really was holding the device
beforehand, B really holds it after), not as the timing source.

onset_smoketest.py validated the FIFO mechanism's own detection lag
against real hardware at 19.5-40ms, small next to the gaps this measures
(hundreds of ms to several seconds per HANDOFF's own prior findings) -
the same lag applies symmetrically to both the silence and onset edges
here, so it mostly cancels in the gap (T1 - T0), not just bounds each
side independently.

Only automates the LMS<->Spotify pairs (no phone needed). Bluetooth pairs
need a live audio source - not attempted here.
"""

import statistics
import sys
import threading
import time

import lms_cli
import pcm_holder
import spotify_api
from spectrum_fifo import SpectrumReader, measure_takeover_gap

SETTLE_S = 1.5  # after B acquires, let it play briefly before the next round
TIMEOUT_S = 15
FAILURE_COOLDOWN_S = 65  # see measure_one's docstring on why a failed round needs this


def _wait_for_release(label, timeout=TIMEOUT_S):
    """Blocks until `label` is no longer among the PCM holders; returns
    the monotonic timestamp of that transition."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        holders = pcm_holder.current_holders()
        if not any(holder_label == label for _, holder_label in holders):
            return time.monotonic()
        time.sleep(0.005)
    raise TimeoutError(f"{label} still held PCM after {timeout}s")


def _wait_for_acquire(label, timeout=TIMEOUT_S):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        holders = pcm_holder.current_holders()
        if any(holder_label == label for _, holder_label in holders):
            return
        time.sleep(0.005)
    raise TimeoutError(f"{label} never acquired PCM within {timeout}s")


def measure_one(reader, outgoing_label, incoming_action, incoming_label, timeout=TIMEOUT_S):
    """Triggers incoming_action() once (expected to cause `outgoing_label`
    to release and `incoming_label` to acquire) and returns the gap in
    seconds, measured entirely from the spectrum FIFO (see module
    docstring for why both edges come from one instrument).

    Deliberately a single attempt, no internal retry loop - Finding 013 §3:
    an earlier version retried the trigger every ~12s on failure, which
    is close enough to go-librespot's own observed ~56s retry-then-reauth
    backoff after a failed track load that the two cadences interfered -
    every time go-librespot's own slow retry was about to land on a
    freshly-freed device, this harness's next attempt had already
    reclaimed it via a fresh LMS `play`, for 14 consecutive rounds (~13
    minutes) with zero real handoffs, confirmed via `journalctl` to stop
    completely the moment the harness stopped. A single clean attempt per
    round, with a long cooldown on failure (see run_pair), avoids ever
    re-triggering while go-librespot might still be mid-backoff from the
    previous round."""
    assert any(label == outgoing_label for _, label in pcm_holder.current_holders()), (
        f"precondition failed: {outgoing_label} isn't holding the PCM before the takeover"
    )

    result = {}
    t_trigger = time.monotonic()

    def gap_thread():
        try:
            result["t_last"], result["t_first"] = measure_takeover_gap(reader, timeout=timeout)
        except TimeoutError:
            pass

    t = threading.Thread(target=gap_thread, daemon=True)
    t.start()
    time.sleep(0.1)  # give the measurement loop a moment to start waiting

    incoming_action()
    t.join(timeout=timeout + 1)

    if "t_first" in result:
        to_last = result["t_last"] - t_trigger
        gap = result["t_first"] - result["t_last"]
        print(f"    (trigger->A's last frame: {to_last * 1000:.0f}ms, gap (A's last -> B's first): {gap * 1000:.0f}ms)")
        _wait_for_release(outgoing_label)
        _wait_for_acquire(incoming_label)
        return gap

    raise TimeoutError(f"no handoff observed within {timeout}s")


def run_pair(direction, n, cli, reader):
    """direction: 'lms-to-spotify' or 'spotify-to-lms'."""
    gaps = []
    skipped = 0
    for i in range(n):
        try:
            if direction == "lms-to-spotify":
                # get LMS playing first
                cli.play()
                _wait_for_acquire("lms")
                time.sleep(SETTLE_S)
                gap = measure_one(reader, "lms", lambda: spotify_api.transfer_to_gexis(play=True), "spotify")
            else:
                spotify_api.transfer_to_gexis(play=True)
                _wait_for_acquire("spotify")
                time.sleep(SETTLE_S)
                gap = measure_one(reader, "spotify", cli.play, "lms")
        except (TimeoutError, AssertionError) as e:
            print(f"  round {i}: SKIPPED ({e}) - cooling down {FAILURE_COOLDOWN_S}s before the next round")
            skipped += 1
            time.sleep(FAILURE_COOLDOWN_S)
            continue
        gaps.append(gap)
        print(f"  round {i}: {gap * 1000:.1f} ms")
        time.sleep(SETTLE_S)
    if skipped:
        print(f"  ({skipped} round(s) skipped out of {n} attempted)")
    return gaps


def report(direction, gaps):
    print(f"\n--- {direction}: n={len(gaps)} ---")
    print(f"  min:    {min(gaps) * 1000:.1f} ms")
    print(f"  max:    {max(gaps) * 1000:.1f} ms")
    print(f"  mean:   {statistics.mean(gaps) * 1000:.1f} ms")
    print(f"  median: {statistics.median(gaps) * 1000:.1f} ms")
    if len(gaps) > 1:
        print(f"  stdev:  {statistics.stdev(gaps) * 1000:.1f} ms")
    print(f"  all (ms): {[round(g * 1000, 1) for g in gaps]}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    direction = sys.argv[2] if len(sys.argv) > 2 else "both"

    cli = lms_cli.LmsCli()
    reader = SpectrumReader().start()
    try:
        if direction in ("both", "lms-to-spotify"):
            print("=== lms-to-spotify ===")
            gaps = run_pair("lms-to-spotify", n, cli, reader)
            report("lms-to-spotify", gaps)
        if direction in ("both", "spotify-to-lms"):
            print("=== spotify-to-lms ===")
            gaps = run_pair("spotify-to-lms", n, cli, reader)
            report("spotify-to-lms", gaps)
    finally:
        cli.close()
        reader.stop()


if __name__ == "__main__":
    main()
