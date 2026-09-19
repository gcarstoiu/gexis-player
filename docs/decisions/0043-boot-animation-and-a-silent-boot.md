# ADR-0043 — A boot animation, and no text at any point

**Status:** Accepted — George, 2026-09-19. Built the same day; never
booted (see Unverified)
**Date:** 2026-09-19
**Raised by:** George, 2026-09-19: *"I don't want to see any text during
booting, only the animation I would provide."*
**Evidence:**
[Finding 038](../findings/038-what-the-panel-shows-while-it-boots.md) (the
boot budget),
[Finding 039](../findings/039-what-only-a-real-boot-found.md) (the five
defects booting it found, four of which the build asserted nothing about)
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

### 3. It ends before the compositor starts

> **Corrected 2026-09-19, on the first device that ever booted this.** This
> section originally said the splash is torn down "when the UI has painted,
> not when a unit has started", and argued that was the careful choice. **It
> cannot work.** Plymouth is DRM master for as long as it runs, so labwc
> cannot open the GPU while the splash is up, so the panel can never paint.
> Each waits for the other. Measured on `gexis`: `Could not take device:
> Device or resource busy`, `Found 0 GPUs, cannot create backend`, labwc
> exits 1 at 24s, and with `Restart=no` the panel stays black until somebody
> connects over SSH.

`gexis-kiosk.service` runs `plymouth quit --retain-splash` as `ExecStartPre`,
before labwc. That ends plymouth — releasing the device — and leaves the last
frame in the framebuffer for the compositor to draw over.

**`--retain-splash` does not survive labwc's modeset on this hardware**
(George, 2026-09-19: the screen went straight to black, nothing froze). So
there is a real gap between the splash ending and Chromium's first paint,
rather than the seam this section originally worried about. Covering it is an
open question below.

The panel still reports its first painted frame to `POST /panel/painted`, and
the daemon still answers by quitting any splash that is somehow still up. It
is a backstop now, not the mechanism.

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

## Built

`image/stage-gexis/06-splash`, 2026-09-19. The theme is 100 frames at 25 fps
(a 4.0 s loop) drawn by a Plymouth script theme whose every text callback is
deliberately empty — an undefined callback is not enough, because Plymouth
falls back to its own rendering for one a theme does not take.

The handover is `POST /panel/painted`, reported by the panel from a double
`requestAnimationFrame` in `App.svelte`'s `onMount` — the earliest point at
which a pixel of the app has actually been presented. `gexis_core/splash.py`
answers it with `plymouth quit --retain-splash`, once, and treats "there is
no plymouth" as normal rather than as an error. Plymouth's own
`plymouth-quit` units are masked, or they would end the animation at
`multi-user.target` while the panel is still ~2 s from drawing.

`gexis-splash-backstop.service` drops the splash 90 s in regardless. Without
it, a panel that never paints would loop the animation forever on a device
with no keyboard, hiding the failure somebody needs to see.

## Unverified

> **Booted 2026-09-19, four times.** Five defects, in
> [Finding 039](../findings/039-what-only-a-real-boot-found.md): the splash
> and the compositor waiting for each other, a quit refused for want of
> root, a backstop that held the boot transaction open for 90s, the console
> revealed when the splash went, and a ~1s white flash that is **parked**.
> All are fixed on the device except the flash; **none has been re-verified
> from an image**, because every fix was installed over SSH.
>
> What remains unverified below was written before any of that.

**Nothing here has been booted.** The stage is written and its build-time
assertions are in place, but no image has been built from it and no device
has run it. In particular:

- **The initramfs rebuild is the part that can stop a device booting.** It
  is asserted after the fact (something was written, it is not empty, it
  contains the plymouth hook) but assertions in a build are not a boot.
- **Whether Plymouth holds all 100 frames in memory** — roughly 400 MB
  decompressed if it does, regardless of the 6.5 MB on disk. 36 of the 100
  frames are exact duplicates, so there is cheap headroom if this turns out
  to matter.
- **Whether the handover is actually seamless.** The gap it exists to close
  was never measured, only reasoned about.

## Open

- ~~What covers the gap between the splash ending and the panel painting.~~
  **Answered 2026-09-19 (George: "i want it").** Two different gaps, and they
  needed different answers. The compositor's own emptiness is covered by
  `swaybg` showing a frame from the animation's held section, started by the
  kiosk session before Chromium. Chromium's first paint was separately white,
  because `index.html` set no background at all until a stylesheet loaded;
  it now carries the ground colour inline. **Neither is measured yet.**
- **What to do about the ~1s white flash.** Parked by George on
  2026-09-19 with the fix understood: an overlay above Chromium's window,
  removed on `POST /panel/painted`. Four moving parts, and it introduces
  something that covers the panel and must be told to go away.
- **Why Chromium takes 12.8s** from `gexis-kiosk.service` starting to
  requesting the page. The panel is not usable until ~35.6s on a machine
  that reaches `multi-user.target` at 16.7s. The animation hides it; nobody
  has looked at it.
- **Whether `Restart=no` on `gexis-kiosk.service` is still right.** Phase 4
  criterion 1 chose it deliberately - "a compositor that respawns in a loop
  after a real failure hides the failure behind a flicker" - and this failure
  is the argument on the other side: one lost race at boot left a black panel
  that only SSH could recover. George's call, not amended here.

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
