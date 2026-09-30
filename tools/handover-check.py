#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A takeover and a return through an uploaded renderer, checked on the device.

LMS plays, the sample renderer (`tools/sample-renderer`, installed as the
uploaded plugin `tone`) takes the card from it, and LMS is picked again. What
it checks is what broke on 2026-09-30 without anything saying so (LESSONS 47):

- the core sees the uploaded renderer **holding the card** while it plays -
  the production `alsa.device_held_by`, not a copy of it;
- LMS is released with its playing state recorded, and the tone released when
  LMS comes back;
- LMS **resumes** on return, as `restore_transport` = "Play only if playing"
  says.

**It makes sound**: LMS's current queue, and a 440 Hz tone at a tenth of full
scale for about three seconds. Run it only when that is fine in the room.

Run **on the device, as root**, with the core's own Python so the production
module answers:

    sudo /opt/gexis-core/venv/bin/python handover-check.py

Needs: nothing playing, LMS with something in its queue, and `tone` uploaded
(Settings -> Plugins -> Upload a plugin, with the package `package.sh` in
`tools/sample-renderer` builds). The tone plugin's switch is put back as it
was; LMS is left paused. Both finish a couple of seconds after the script
exits: squeezelite closes the card 1 s after a pause, and switching the tone
off took 1.7 s (2026-09-30).

First run, 2026-09-30 on `sofa-pi`: 9 of 9.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request

from gexis_core import alsa

CORE = "http://127.0.0.1:8090"
TONE_UNIT = "gexis-uploaded-renderer@tone.service"
STATUS = "/proc/asound/sndrpihifiberry/pcm0p/sub0/status"


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(CORE + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read() or b"{}")


def card_state() -> str:
    try:
        return open(STATUS).readline().split(":", 1)[-1].strip() or "closed"
    except OSError:
        return "closed"


def log_since(mark: str) -> str:
    return subprocess.run(["journalctl", "-u", "gexis-core", "--since", mark, "--no-pager", "-o", "cat"],
                          capture_output=True, text=True, check=False).stdout


def wait_for(mark: str, text: str, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if text in log_since(mark):
            return True
        time.sleep(0.5)
    return False


def tone_switch() -> bool | None:
    for group in call("GET", "/settings")["groups"]:
        for row in group["rows"]:
            if row.get("key") == "tone.enabled":
                return bool(row.get("value"))
    return None


def main() -> int:
    if card_state() != "closed":
        print("Something is playing (the card is open). Stop it first.")
        return 2
    was_on = tone_switch()
    if was_on is None:
        print("The sample renderer is not installed: upload tools/sample-renderer's package first.")
        return 2

    results: list[tuple[str, bool]] = []

    def check(name: str, ok: bool) -> None:
        results.append((name, ok))
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    mark = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        if not was_on:
            call("PUT", "/settings/tone.enabled", {"value": True})
        check("the tone renderer connects", was_on or wait_for(mark, "plugins: tone connected", 20))

        call("POST", "/renderer/lms/activate")
        time.sleep(3)
        call("POST", "/transport/play")
        time.sleep(5)
        check("LMS plays", card_state() == "RUNNING")

        step = time.strftime("%Y-%m-%d %H:%M:%S")
        call("POST", "/renderer/tone/activate")
        check("the tone takes the card from LMS",
              wait_for(step, "acquire: tone takes the device (was lms)", 8))
        check("LMS is released remembering it was playing",
              "(will resume playing: True)" in log_since(step))
        time.sleep(1)
        check("the core sees the uploaded renderer holding the card",
              alsa.device_held_by(TONE_UNIT))

        step = time.strftime("%Y-%m-%d %H:%M:%S")
        call("POST", "/renderer/lms/activate")
        check("LMS takes the card back", wait_for(step, "acquire: lms takes the device (was tone)", 8))
        check("the tone is released", wait_for(step, "release[tone]:", 8))
        check("LMS resumes playing", wait_for(step, "lms: resumed playback", 8))
        time.sleep(2)
        check("the card is playing after the return", card_state() == "RUNNING")
    finally:
        try:
            call("POST", "/transport/pause")
        finally:
            if not was_on:
                call("PUT", "/settings/tone.enabled", {"value": False})

    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)} of {len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
