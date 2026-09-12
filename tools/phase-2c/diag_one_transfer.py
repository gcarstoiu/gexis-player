"""One-off diagnostic: fires a single LMS-to-Spotify transfer and prints a
merged, timestamped view of pcm_holder polling alongside what happened, to
pin down exactly when go-librespot attempts its ALSA open relative to LMS's
actual release. Not part of the permanent harness - throwaway, for Finding
013 follow-up.
"""

import subprocess
import threading
import time

import lms_cli
import pcm_holder
import spotify_api

events = []
lock = threading.Lock()


def log(msg):
    with lock:
        events.append((time.monotonic(), msg))


def poll_holders(stop_evt):
    last = None
    while not stop_evt.is_set():
        holders = tuple(sorted(label for _, label in pcm_holder.current_holders()))
        if holders != last:
            log(f"pcm_holder -> {holders}")
            last = holders
        time.sleep(0.05)


def main():
    stop_evt = threading.Event()
    t = threading.Thread(target=poll_holders, args=(stop_evt,), daemon=True)
    t.start()

    cli = lms_cli.LmsCli()
    log("calling cli.play()")
    cli.play()

    # wait for lms to show up
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if any(l == "lms" for _, l in pcm_holder.current_holders()):
            break
        time.sleep(0.05)
    log("lms confirmed holding (or timed out)")

    time.sleep(1.5)
    log("calling spotify_api.transfer_to_gexis(play=True)")
    try:
        spotify_api.transfer_to_gexis(play=True)
        log("transfer_to_gexis call returned")
    except Exception as e:
        log(f"transfer_to_gexis raised: {e!r}")

    time.sleep(20)
    stop_evt.set()
    t.join(timeout=2)
    cli.close()

    t0 = events[0][0]
    for ts, msg in events:
        print(f"+{ts - t0:6.3f}s  {msg}")


if __name__ == "__main__":
    main()
