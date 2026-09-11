"""Criterion 8: Bluetooth-involving takeover-gap measurement. Unlike
takeover_gap.py's LMS<->Spotify pairs, Bluetooth's own acquisition can't be
scripted - it needs a live phone. This runs ONE round at a time; whichever
side is Bluetooth's own action is left for a human to trigger while this
process is already waiting (the FIFO reader is timestamp-driven by real
frame arrivals, not by when this script happens to be invoked, so there's
no measurement-corrupting cost to it sitting idle for a while first - see
spectrum_fifo.measure_takeover_gap's own docstring).

Usage: bt_takeover_gap.py <direction> [timeout_s]
  direction one of: bluetooth-to-lms, bluetooth-to-spotify,
                    lms-to-bluetooth, spotify-to-bluetooth
"""

import sys
import time

import lms_cli
import pcm_holder
import spotify_api
from spectrum_fifo import SpectrumReader, measure_takeover_gap

TIMEOUT_S_DEFAULT = 120


def holder_is(label):
    return any(l == label for _, l in pcm_holder.current_holders())


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    direction = sys.argv[1]
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else TIMEOUT_S_DEFAULT

    reader = SpectrumReader().start()
    time.sleep(0.2)
    cli = lms_cli.LmsCli() if "lms" in direction else None

    try:
        if direction == "bluetooth-to-lms":
            if not holder_is("bluetooth"):
                print(f"PRECONDITION FAILED: bluetooth is not holding the PCM (holders: {pcm_holder.current_holders()}) - connect and play on your phone first")
                sys.exit(1)
            print("bluetooth confirmed holding - triggering LMS play now")
            t_last, t_first = _measure(reader, timeout, lambda: cli.play())
        elif direction == "bluetooth-to-spotify":
            if not holder_is("bluetooth"):
                print(f"PRECONDITION FAILED: bluetooth is not holding the PCM (holders: {pcm_holder.current_holders()}) - connect and play on your phone first")
                sys.exit(1)
            print("bluetooth confirmed holding - triggering Spotify transfer now")
            t_last, t_first = _measure(reader, timeout, lambda: spotify_api.transfer_to_gexis(play=True))
        elif direction == "lms-to-bluetooth":
            if not holder_is("lms"):
                print("lms not currently holding - calling play to set it up")
                cli.play()
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not holder_is("lms"):
                    time.sleep(0.1)
            print(f"lms holding: {holder_is('lms')} - NOW connect/play Bluetooth on your phone (waiting up to {timeout:.0f}s)")
            t_last, t_first = _measure(reader, timeout, None)
        elif direction == "spotify-to-bluetooth":
            if not holder_is("spotify"):
                print("spotify not currently holding - transferring to set it up")
                spotify_api.transfer_to_gexis(play=True)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not holder_is("spotify"):
                    time.sleep(0.1)
            print(f"spotify holding: {holder_is('spotify')} - NOW connect/play Bluetooth on your phone (waiting up to {timeout:.0f}s)")
            t_last, t_first = _measure(reader, timeout, None)
        else:
            print(f"unknown direction {direction!r}")
            sys.exit(2)
    except TimeoutError as e:
        print(f"TIMEOUT: {e}")
        sys.exit(1)
    finally:
        reader.stop()
        if cli:
            cli.close()

    gap = t_first - t_last
    print(f"gap: {gap * 1000:.1f} ms")
    print(f"holders after: {pcm_holder.current_holders()}")


def _measure(reader, timeout, trigger):
    """If trigger is given, calls it right after starting to wait (the
    scriptable-incoming-side case); if trigger is None, the wait itself
    is what gives a human time to act (the manual-incoming-side case)."""
    import threading

    result = {}

    def gap_thread():
        result["t_last"], result["t_first"] = measure_takeover_gap(reader, timeout=timeout)

    t = threading.Thread(target=gap_thread, daemon=True)
    t.start()
    time.sleep(0.1)
    if trigger is not None:
        trigger()
    t.join(timeout=timeout + 2)
    if "t_first" not in result:
        raise TimeoutError(f"no handoff observed within {timeout}s")
    return result["t_last"], result["t_first"]


if __name__ == "__main__":
    main()
