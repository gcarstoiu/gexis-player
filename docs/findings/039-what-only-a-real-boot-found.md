# Finding 039 — Five defects in the boot splash, none visible to the build

**Date:** 2026-09-19
**Question:** ADR-0043 was built with build-time assertions and shipped in an
image. What did booting it actually find?
**System:** `gexis`, the 2026-09-19 image
(`v0.2.1-287-ge59654c-dirty`) flashed to a second SD card, then patched over
SSH between attempts. Kernel 6.18.50+rpt-rpi-v8, Chromium 153.0.8010.47,
labwc on Wayland.
**Scope:** one device, one afternoon, four reboots and a dozen kiosk
restarts. Timings below are from `journalctl -o short-monotonic` and
`systemd-analyze` on that device.

## The point

**The build asserted a great deal about the initramfs and nothing about
whether anything could take the screen afterwards.** Every assertion in
`06-splash` passed on the image that produced four of these five defects.
Three of them left the panel black or frozen; a fourth silently broke boot
measurement; the fifth is cosmetic and is parked.

A stage that verifies its own outputs is not the same as a device that
works, and the distance between them was four reboots.

## 1. The splash and the compositor waited for each other

**Symptom:** the animation played, then the panel went black and stayed
black. `gexis-core` was healthy throughout.

**Cause:** plymouth is DRM master for as long as it runs. ADR-0043 §3 held
the splash until the panel reported a painted frame - and the panel cannot
paint, because labwc cannot open `/dev/dri/card1` while plymouth has it.

```
labwc: [libseat] Could not take device: Device or resource busy
labwc: Failed to open device: '/dev/dri/card1': Resource temporarily unavailable
labwc: Found 0 GPUs, cannot create backend
gexis-kiosk.service: Main process exited, code=exited, status=1/FAILURE
```

labwc exited at 24.5s. The 90s backstop then freed the device, by which time
the kiosk had already failed and `Restart=no` meant nothing retried.

**Fix:** `gexis-kiosk.service` quits plymouth itself, with
`--retain-splash`, as `ExecStartPre` - before labwc, not after Chromium
paints.

**What the ADR got wrong is worth naming.** It listed "whether the handover
is actually seamless" as unverified. The real question was whether the
handover could work at all. The wrong risk was written down as the risk.

## 2. The quit was refused, silently

**Symptom:** second boot, same black screen. George: *"Seems stuck with
logo"* - which was accurate: plymouth was still looping its pulse, because
nothing had successfully told it to stop.

**Cause:** `gexis-kiosk.service` runs `User=pi`, and `ExecStartPre` inherits
it. The plymouth client needs root to command `plymouthd`, so the quit was
refused and nothing said so. `plymouthd` was still running as PID 183 after
the boot completed.

**Fix:** `ExecStartPre=-+/bin/plymouth quit --retain-splash`. The `+` runs
that one line as root regardless of `User=`.

## 3. The backstop held the boot open for 90 seconds

**Symptom:** `systemd-analyze` refused to answer - "Bootup is not yet
finished" - while the panel had been up and usable for over a minute.
`systemctl list-jobs` showed one job: `gexis-splash-backstop.service`.

**Cause:** it was `Type=oneshot` with `ExecStartPre=/bin/sleep 90`, wanted by
`multi-user.target`. A oneshot unit in the boot transaction keeps that
transaction open until it exits.

**Measured, after replacing it:**

```
Startup finished in 5.185s (kernel) + 1min 28.757s (userspace) = 1min 33.942s
multi-user.target reached after 16.681s in userspace
```

**This is the one that would have done lasting damage.** Phase 9 tunes this
panel against measured numbers. An instrument that cannot answer for the
first 90 seconds of every boot is not an instrument, and nothing would have
failed - the numbers would simply have been wrong.

**Fix:** a timer with `OnBootSec=90` and a service that only runs the quit.
Nothing sleeps inside the boot transaction.

## 4. The console appeared between the animation and the panel

**Symptom:** George, watching a boot: the text console was visible between
the animation ending and the still image appearing.

**Cause:** `getty@tty1`'s login prompt is still in tty1's framebuffer. The
splash covers it; the instant plymouth quits there is nothing over it until
labwc draws. `--retain-splash` does not survive the modeset here (George:
it went straight to black, nothing froze), so what it reveals is the
console.

**Fix:** clear the VT *before* the splash goes -
`ExecStartPre=-+/bin/sh -c 'printf "\033c" > /dev/tty1'`, ordered ahead of
the quit. Deployed 2026-09-19 and **not yet seen on a boot.**

## 5. A white flash, ~1s, parked

**Symptom:** white between the still image and the UI appearing.

**Cause:** Blink's initial empty document, before any document exists for CSS
to colour. The inline `#101a21` added to `index.html` cannot reach it, and
neither can the wallpaper, which is on the background layer beneath
Chromium's window.

**Two Chromium switches were tried and both are ignored by this build**, on
Wayland/ozone:

- `--default-background-color=FF101A21`. Tested decisively by setting it to
  bright blue: the flash stayed white, so the switch is not honoured rather
  than wrongly valued.
- `--force-dark-mode`. No change.

Both were removed rather than left in as unexplained decoration.

**How long it lasts**, from the last clean boot:

| moment | monotonic |
|---|---|
| `gexis-kiosk.service` started (splash quits here) | 21.9s |
| Chromium requests the page | 34.6s |
| panel reports its first painted frame | 35.6s |

So Chromium takes **~12.8s from unit start to asking for the page**, then
~1s more to paint. On a warm restart: 2.6s then 0.6s. **The white is the
last ~1s of that**, and the animation covers everything before it.

**Parked by George, 2026-09-19**, with the fix understood but not built: an
overlay showing the artwork *above* Chromium's window, removed when the
panel reports its first painted frame at `POST /panel/painted`. That needs a
layer-shell image client, a labwc rule to keep it on top, a kill path in the
daemon, and a timeout - four moving parts to remove a one-second flash, and
it introduces a failure mode of its own: something that covers the panel and
must be told to go away.

## The number nobody was looking at

**Chromium takes 12.8s from `gexis-kiosk.service` starting to requesting the
page.** The panel is not actually usable until ~35.6s, on a machine that
reaches `multi-user.target` at 16.7s. The animation hides all of it, which
is what an animation is for - but it is the difference between a panel ready
at 22s and one ready at 35s, and it has never been investigated.

## What this does not say

- **Nothing here has been re-verified from an image.** Every fix was
  installed over SSH onto a running device. The image that produced these
  findings still contains four of the five defects.
- **Fix 4 has not been seen on a boot**, only deployed.
- **Whether the intro-once-then-pulse sequence reads correctly** was not
  judged in this pass; the reboots were spent on failures.
- **Nothing was measured about memory.** Whether plymouth holds all 100
  frames - ~400MB decompressed if it does - remains the open question it was.
