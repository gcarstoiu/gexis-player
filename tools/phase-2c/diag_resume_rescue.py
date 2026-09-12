"""One-off: after a Mode A busy failure (Finding 014), try the local
POST /player/resume endpoint instead of a second Spotify Web API call, to
see if it can nudge go-librespot to retry the ALSA open without needing
Spotify account credentials at all. Throwaway diagnostic.
"""

import sys
import time
import urllib.request

import lms_cli
import pcm_holder
import spotify_api

GO_LIBRESPOT_BASE = "http://127.0.0.1:3678"


def local_resume():
    req = urllib.request.Request(f"{GO_LIBRESPOT_BASE}/player/resume", method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status


def wait_for(label, present, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        holders = pcm_holder.current_holders()
        has_it = any(l == label for _, l in holders)
        if has_it == present:
            return True
        time.sleep(0.05)
    return False


def main():
    cli = lms_cli.LmsCli()
    cli.play()
    if not wait_for("lms", True, timeout=10):
        print("lms never acquired the device - aborting this attempt")
        return 2
    print("lms confirmed holding:", pcm_holder.current_holders())
    time.sleep(1.5)

    spotify_api.transfer_to_gexis(play=True)
    print("transfer call returned")

    # give go-librespot's own immediate attempt a moment to happen/fail
    time.sleep(1.0)
    print("holders right after transfer+1s:", pcm_holder.current_holders())

    if not wait_for("lms", False, timeout=8):
        print("lms never released - can't tell mode A from mode B here, aborting")
        return 2

    print("lms confirmed released. holders now:", pcm_holder.current_holders())
    print("calling local /player/resume ...")
    try:
        status = local_resume()
        print("resume http status:", status)
    except Exception as e:
        print("resume call raised:", repr(e))
        return 1

    for i in range(8):
        time.sleep(1)
        h = pcm_holder.current_holders()
        print(f"+{i+1}s holders:", h)
        if any(l == "spotify" for _, l in h):
            print("RESCUED: spotify holding the PCM after local /player/resume alone")
            return 0

    print("NOT rescued: spotify never took the PCM within 8s of /player/resume")
    return 1


if __name__ == "__main__":
    cli = None
    sys.exit(main())
