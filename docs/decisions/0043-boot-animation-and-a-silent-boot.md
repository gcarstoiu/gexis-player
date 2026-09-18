# ADR-0043 — A boot animation, and no text at any point

**Status:** Proposed — awaiting George
**Date:** 2026-09-19
**Raised by:** George, 2026-09-19: *"I don't want to see any text during
booting, only the animation I would provide."*
**Evidence:**
[Finding 038](../findings/038-what-the-panel-shows-while-it-boots.md)
**Relates to:** [Finding 022](../findings/022-kiosk-never-started-target-and-tty.md)
(the panel showing an IP address and boot messages — the same complaint,
answered differently), [ADR-0021](0021-deployment-flashable-image.md) (the
image this is built into), [ADR-0019](0019-peppy-screen-lifecycle.md) (the
panel never blanks)

## Context

The panel today shows the firmware's colour square, four raspberry logos,
kernel messages, systemd unit lines and a login prompt before the UI
appears. Measured on `gexis`: **19.7s from power to `multi-user.target`,
with `gexis-kiosk.service` starting at 18.26s** and Chromium painting some
unmeasured time after that.

**The text comes from six places, not one**, and nothing in the image
currently quiets any of them (Finding 038).

## Decision

**One animation covers the whole boot, and nothing else is ever drawn.**

### 1. Every source of text is silenced at its own source

| what | lever | where |
|---|---|---|
| firmware colour square | `disable_splash=1` | `config.txt` |
| four raspberry logos | `logo.nologo` | `cmdline.txt` |
| kernel messages | `quiet loglevel=0` | `cmdline.txt` |
| blinking cursor | `vt.global_cursor_default=0` | `cmdline.txt` |
| systemd unit lines | `systemd.show_status=false` | `cmdline.txt` |
| login prompt and IP | the getty is kept, its output kept off the panel's VT | see §4 |

`console=tty1` stays for the serial/diagnostic path; what changes is what is
allowed to write to the panel.

### 2. The animation is Plymouth, started from the initramfs

This image already builds an initramfs (`auto_initramfs=1`,
`/boot/firmware/initramfs8` — Finding 038 corrects an earlier claim that it
did not), so the splash can begin within a second or two of power rather
than after the root mount at ~3.97s.

**A PNG frame sequence, 1280x800, looped.** Plymouth's script theme animates
frames; it does not play video, and this is the format the artwork has to
arrive in.

### 3. It ends when the UI has painted, not when a unit has started

`plymouth quit --retain-splash` leaves the last frame on screen and the
kiosk draws over it. **The teardown is driven by the panel actually
painting**, not by `gexis-kiosk.service` reaching active at 18.26s — the gap
between those two is exactly where a flash of black would show.

### 4. The getty stays enabled

Finding 022 re-enabled it for a reason and `gexis-kiosk.service` already
orders itself `After=getty@tty1.service`. This record does not undo that; it
keeps the getty and keeps its output off the panel.

## Consequences

- **A failed boot becomes silent.** A filesystem check, emergency mode or a
  unit that never comes up will show an animation rather than a reason, on a
  device with no keyboard. **SSH becomes the only diagnostic path.** This is
  the cost of the requirement, and it is accepted knowingly rather than
  discovered later.
- **The animation covers mostly waiting.** 11 of the 17 userspace seconds
  are `NetworkManager-wait-online` and the apt timers (Finding 038).
  Shortening the boot is a separate decision; if it is ever taken, the
  animation's loop length is unaffected because it loops.
- **A first boot plays it twice.** `firstrun.sh` runs and reboots.

## Open

- **Whether to shorten the boot at all**, given that ~6s of it is waiting
  for a network the panel does not need to draw its first screen.
- **Whether the animation should be interruptible** — Plymouth can reveal
  the log on a keypress, which is worthless without a keyboard but free.
- **Whether this is a setting.** It is hardcoded as proposed; a "show boot
  animation" row is plausible and is not in ADR-0022's inventory today. Per
  this project's rule it goes in the inventory only if George says so.

## Alternatives considered

- **Quiet boot with no animation** — a black screen for 20s, which reads as
  a dead device rather than a starting one.
- **Starting Plymouth after the root mount** instead of from the initramfs —
  simpler, but leaves ~4s uncovered at exactly the moment someone is
  watching to see whether the thing turned on.
- **Letting the kiosk draw its own splash** — cannot work: Chromium is the
  thing we are waiting for.
