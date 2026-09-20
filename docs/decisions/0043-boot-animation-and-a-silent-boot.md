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
  decompressed if it does, regardless of the 3.2 MB on disk. **26** of the
  100 frames are exact duplicates, so there is cheap headroom if this turns
  out to matter.
  > Both numbers were stale and are corrected here, 2026-09-20. "6.5 MB" and
  > "36 duplicates" described the `b33da2e` set and survived two re-renders
  > unexamined; `HANDOFF.md` still carries them. Measured on the set
  > committed today: 3.2 MB, 74 distinct frames, 26 exact duplicates.
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

---

## Amendment, 2026-09-20 — the handover is ten seconds, not a seam

**Status: Accepted — George, 2026-09-20**, who also chose the order: start
by shrinking D1. Parts 1 and 2 are not implemented.
**Raised by:** George, 2026-09-20: *"The main aim is to have a continuous
animation until the player takes over (the white flash is fine for now)."*
**Evidence:** [Finding 041](../findings/041-the-ten-seconds-with-no-animation.md)

### What this record got wrong

§3 above, and Finding 039, both treat the end of the animation as a *seam* —
a moment to be joined cleanly. Measured on the 2026-09-20 boot, it is not a
moment:

| | from → to | length | what is drawn |
|---|---|---|---|
| **D1** | 25.64 → 31.55 s | **5.93 s** | nothing this project controls |
| **D2** | 31.55 → 34.76 s | **3.21 s** | a frozen frame (`swaybg`) |
| **D3** | 34.76 → 35.79 s | 1.01 s | white — parked |

**10.15 s with no animation**, on a boot whose animation only runs for about
twenty. Neither D1 nor D2 is named anywhere in this record or in Finding 039.
The open question above — *"what covers the gap between the splash ending and
the panel painting"* — was answered with `swaybg`, and `swaybg` cannot start
until labwc exists, so it covers the far side of a gap it cannot reach across.

### The constraint, stated plainly

Plymouth is DRM master until it exits, so it must exit before labwc opens the
GPU. labwc then needs its own start-up — ~2.0 s of PAM, logind and the user
manager, then ~3.9 s of labwc itself. **During that start-up the display is
owned by nothing that is drawing, and no amount of care in the handover
changes that.** D1 is the compositor's start-up time. It is also not
fixed-length: it tracks `NetworkManager-wait-online`, which moved it from
21.9 s (Finding 039) to 25.44 s here.

**So an animation cannot run across D1.** The best D1 can be is a held frame.
This amendment is about making that true, making it short, and making the
animation resume the instant a compositor exists.

### Decision, in three parts

**1. D1 shows the boot screen, not black and not a console. BUILT
2026-09-20.** `quit --retain-splash` was supposed to do this and does not.
Rather than diagnose the escrow, `gexis-kiosk.service` writes the image
itself, via `gexis-splash-fb`:

| step | what | why in this order |
|---|---|---|
| `ExecStartPre` | `printf "\033c" > /dev/tty1` | kept as the fallback if the helper is missing |
| `ExecStartPre` | `gexis-splash-fb graphics` | `KD_GRAPHICS` stops the console being drawn **at all** |
| `ExecStartPre` | `plymouth quit --retain-splash` | plymouth is DRM master and must go before labwc |
| `ExecStartPre` | `gexis-splash-fb paint …` | the boot screen into the framebuffer |
| `ExecStopPost` | `gexis-splash-fb text` | so a **failed** boot looks failed |

**This also answers the console**, and differently from every previous
attempt: `KD_GRAPHICS` removes the possibility of console output rather than
racing to clear what is already there. The `\033c` clear loses that race
about half the time, which is why George saw `160R` on some boots and not
others.

**Three things were measured on the device first**, because each would have
sunk it:

- **The framebuffer is the scanout when no DRM master holds the device.** A
  2,048,000-byte write to `/dev/fb0` reads back byte-identical and George
  confirmed the image reaches the panel. An earlier `/dev/fb0` capture read
  black 45 times out of 45 and was discarded as a blind instrument — it was
  blind only because labwc held the device throughout.
- **tty1 is already `KD_GRAPHICS` for the whole uptime**, put there by labwc.
  This moves the start of that state ~5 s earlier; it does not introduce it.
- **A `KD_GRAPHICS` set with no compositor persists indefinitely.** Nothing
  reclaims it, which is why `ExecStopPost` exists rather than trusting
  systemd's `TTYReset=yes`.

**What it does not do: cover all of D1.** The painted image holds until labwc
modesets, and where that falls inside labwc's ~5 s start-up is unmeasured.

**2. ~~D2 animates.~~ Overtaken 2026-09-20 — D2 is no longer a
discontinuity.** This said `swaybg`'s still should be replaced by a client
playing the pulse loop. George then removed the animation entirely, so the
splash and the wallpaper are one file and D2 shows the same image as D1.
There is nothing left to animate and no seam to hide. The layer-shell client
this proposed is not built and is not wanted.

**3. The target is D1 ≤ 2.0 s, and the reason is the artwork, not the
clock.** The pulse is a beat followed by a genuine rest, 2.0 s long. A held
rest frame is *indistinguishable from the animation between beats* — until
the beat that should have come does not. So a gap shorter than one pulse
period is not perceptible as a stop at all, and one of 5.93 s is three missed
beats. This turns "continuous" into something measurable.

Getting there means taking ~4 s off labwc's start-up. Three candidates, none
yet established as a cause:

- ~~**`gexis-panel-warmup` runs straight through D1.**~~ **Measured
  2026-09-20 and changed** (Finding 041 §7). It warmed Chromium's 482 MB
  first and `/usr/bin/labwc` last, 7.4 s after labwc had started — and
  `/usr/bin/labwc` is 515 KB, while what labwc actually reads is `dlopen`'d
  and so invisible to `ldd`: `libLLVM` 117 MB, `libgallium` 49 MB, `libz3`
  25 MB, ~196 MB in all, none of it warmed. The list now warms the
  compositor's set first and logs one line per target. **Whether that
  shrinks D1 is unmeasured until a boot says so.**
- **3.6 s of D1 produces no log output from anything at all** (27.91 →
  31.50 s). The ~196 MB above is the candidate explanation and is not yet
  confirmed as the whole of it.
- **~2.0 s before labwc's first line** is PAM, logind and the user manager.
  Untouched.

**If D1 ≤ 2.0 s turns out to be unreachable, the fallback is to say so and
accept a held frame**, rather than to add machinery that hides it.

### What this does not propose

- **Removing the network from the panel's critical path.** `gexis-kiosk` →
  `gexis-core` → `network-online.target` → `NetworkManager-wait-online`,
  5.996 s, is the single largest cost on `critical-chain` and the panel does
  not need a network to draw its first screen. It would make the whole boot
  shorter without making D1 shorter, and it is a separate decision about what
  `gexis-core` may start without. Named here so it is not re-derived.
- **Anything about D3.** Parked by George, 2026-09-19, unchanged.

### Rejected alternatives

- **A second KMS animator taking over from plymouth for D1.** It would have
  the identical problem: it is DRM master, so it must release before labwc
  starts, and the gap is exactly as long. It adds a process and moves nothing.
- **Holding plymouth until the panel paints.** This is what §3 above already
  corrected. It deadlocks: plymouth holds DRM, labwc cannot open the GPU, the
  panel never paints.
- **A longer animation, or a slower one, so the rest state is longer.** It
  would hide D1 by making the artwork worse, and it fails the moment D1 grows
  — which it already did, by 3.5 s, between two boots.
- **`--retain-splash` alone, without part 2.** It makes D1 and D2 both a
  frozen frame: 9.14 s of one image, more than four missed beats. It removes
  the console without meeting the requirement.

### Reversal condition

If the compositor ever draws its first frame fast enough that D1 falls below
one pulse period on its own, part 2 is still wanted but part 3 stops being
work. If labwc is ever replaced by something that can take DRM master from a
running plymouth, the whole shape of this changes and the amendment should be
re-read rather than patched.

### Still open after this

- ~~**The console George reported is not explained.**~~ **Answered
  2026-09-20**, by George looking at it rather than by any log: *"a couple of
  lines at the bottom"*. It is the echoed cursor-position replies
  (`^[[1;1R^[[50;160R`) sitting in tty1's buffer, revealed for the whole of
  D1 — not systemd output, not a getty, not an earlier boot (Finding 041 §4).
  **Part 1 removes it and part 3 shortens it, neither of which needs the
  emitter identified.** What writes `ESC[6n` to tty1 after the clear is a
  separate and unhurried question; the likeliest source is systemd's own
  terminal handling for `TTYPath=/dev/tty1` with `TTYReset=yes`,
  `TTYVHangup=yes` and `PAMName=login`.
- **Whether `systemd.show_status=false` should stay.** It is overridden every
  boot by plymouthd's `SIGRTMIN+20`, so it is doing nothing; what keeps that
  text off the panel is plymouth's interception and `console=tty3`
  (Finding 041 §3).
- **The unverified intro restart at ~9.1 s** —
  `plymouth-start.service`'s `ExecStartPost=-/usr/bin/plymouth show-splash`
  fires against the already-running initramfs daemon. If it resets the theme
  script, the intro replays seven seconds in. Not determinable from logs.
- **Whether any of this is a setting.** Unchanged: hardcoded as proposed, and
  a row goes into [ADR-0022](0022-settings-inventory.md)'s inventory only if
  George says so.
