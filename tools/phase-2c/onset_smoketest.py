"""One-off smoke test for the spectrum-FIFO onset detector (spectrum_fifo.py).

Plays a WAV with a known silence-then-tone boundary through `output`,
reads the real ALSA hardware trigger time + the known silent-sample count
to compute the *true* expected onset (independent of the FIFO mechanism -
grounded in the same CLOCK_MONOTONIC domain via /proc's trigger_time and
Python's time.monotonic(), both clock_gettime(CLOCK_MONOTONIC) on Linux),
and compares it against when the FIFO reader first reports nonzero energy.

Not a full calibration across renderers/rates - a sanity check that the
mechanism (source-read in spectrum_fifo.py's docstring) behaves as
expected on real hardware, run once manually. Run directly on gexis (the
proc path and FIFO are both local to it).
"""

import re
import subprocess
import sys
import threading
import time

sys.path.insert(0, "/tmp")
from spectrum_fifo import wait_for_onset  # noqa: E402

WAV = "/tmp/onset-test.wav"
STATUS_PATH = "/proc/asound/card5/pcm0p/sub0/status"
SILENCE_S = 3.0  # must match the generator in the parent commit's message


def read_trigger_time():
    with open(STATUS_PATH) as f:
        text = f.read()
    m = re.search(r"trigger_time:\s*([\d.]+)", text)
    return float(m.group(1)) if m else None


def wait_for_running_and_trigger_time(poll_timeout=5.0):
    start = time.monotonic()
    while time.monotonic() - start < poll_timeout:
        try:
            with open(STATUS_PATH) as f:
                text = f.read()
        except FileNotFoundError:
            time.sleep(0.005)
            continue
        if "state: RUNNING" in text:
            m = re.search(r"trigger_time:\s*([\d.]+)", text)
            if m:
                return float(m.group(1))
        time.sleep(0.005)
    raise TimeoutError("PCM never reached RUNNING with a trigger_time")


onset_result = {}


def fifo_thread():
    onset_result["fifo_onset"] = wait_for_onset(timeout=15)


t = threading.Thread(target=fifo_thread, daemon=True)
t.start()
time.sleep(0.2)  # let the reader attach to the FIFO before playback starts

proc = subprocess.Popen(["aplay", "-D", "output", WAV], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

trigger_time = wait_for_running_and_trigger_time()
# trigger_time and time.monotonic() are both CLOCK_MONOTONIC on Linux -
# directly comparable, no offset translation needed (an earlier version
# of this script computed a "boot_offset" here that algebraically
# cancelled trigger_time out entirely - caught before running for real).
expected_onset_monotonic = trigger_time + SILENCE_S

t.join(timeout=15)
proc.wait(timeout=15)

fifo_onset = onset_result.get("fifo_onset")
if fifo_onset is None:
    print("FAIL: FIFO never reported an onset")
    sys.exit(1)

lag_ms = (fifo_onset - expected_onset_monotonic) * 1000
print(f"trigger_time (proc, s-since-boot): {trigger_time:.6f}")
print(f"expected true onset (monotonic):   {expected_onset_monotonic:.6f}")
print(f"FIFO-reported onset (monotonic):   {fifo_onset:.6f}")
print(f"measured lag: {lag_ms:.1f} ms")
