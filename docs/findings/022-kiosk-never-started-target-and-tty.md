# Finding 022 — the kiosk never started: two defects, both invisible

**Date:** 2026-09-14
**Machine:** `gexis` (Pi 4), freshly flashed with
`2026-09-13-gexis-player-v0.2.1-98-gfec5067-dirty.img` — the first image
carrying `stage-gexis/04-ui`
**Reported by:** George — the panel showed an IP address and boot messages
instead of the UI
**Scope:** first boot of this image only. Covers why the panel did not appear
and what fixes it. Does **not** cover whether the UI is correct, whether the
kiosk survives long uptime, or anything about `04-ui` beyond starting it.

## Symptom

The screen showed a console getty. `gexis-kiosk.service` was `enabled` and
`inactive (dead)`, with nothing in its journal.

## Defect 1 — `default.target` is overwritten on first boot

`04-ui/01-run.sh` wrote `default.target -> graphical.target` at build time and
asserted it. Verified still correct in the build's own rootfs:

```
/pi-gen/work/gexis-player/stage-gexis/rootfs/etc/systemd/system/default.target
    -> /lib/systemd/system/graphical.target
```

On the booted device it was `-> /usr/lib/systemd/system/multi-user.target`,
mtime equal to boot time. `pi-gen`'s `export-image` does not touch it. The
chain is **our own**:

```
firstrun.sh → userconf pi ""        (cancels the setup wizard, deliberately)
  userconf  → /usr/bin/cancel-rename pi
  cancel-rename → raspi-config nonint do_boot_behaviour B1
  B1        → systemctl set-default multi-user.target
```

Confirmed by reading `/usr/bin/cancel-rename` on the device and by
`raspi-config nonint get_boot_cli` returning `0`, which selects that branch.
`graphical.target` was therefore never reached, and a unit installed into
`graphical.target.wants` never ran.

The same script also explains the sibling files touched at the same second —
it runs `systemctl enable getty@tty1` and reloads ssh.

## Defect 2 — `getty@tty1` owns the VT, and losing it is silent

Starting the unit by hand with the getty running produced:

```
Started gexis-kiosk.service …
gexis-kiosk.service: Deactivated successfully.
```

`labwc` exited **0**, immediately. Chromium printed nothing. There is no error
anywhere: `StandardInput=tty-fail` could not take `/dev/tty1`, and the failure
surfaced as a clean exit.

Stopping `getty@tty1` and starting the same unit, unchanged, gave a working
panel — so this is the whole of defect 2.

**This would have bitten even with defect 1 fixed.** `getty@tty1` is pulled in
by `multi-user.target`, which `graphical.target` requires. Fixing only the
target would have produced the same blank screen with the same empty journal.

## What was already correct

Once started, everything downstream worked first time, so `04-ui` is sound
apart from its trigger:

```
session 22  pi  seat0  tty1            PAMName=login grants the seat
labwc + chromium running
GET / 200, index-*.js 200, index-*.css 200
wsserver: client connected (1 total)
card1-HDMI-A-1: connected  mode=1280x800
```

This also gives ADR-0026 its first real evidence that labwc runs on this
hardware, though **not** that it can hand the screen to PeppyMeter — that
mechanism is still unverified.

## Fix

1. **`WantedBy=multi-user.target`**, and the stage no longer writes
   `default.target` at all. Re-asserting the target after `firstrun` would
   only move the fight: `raspi-config` owns that setting and resets it on
   every provisioning run. Nothing is lost — `graphical.target` on this image
   has no display manager behind it, so it is multi-user plus this unit.
2. **`Conflicts=getty@tty1.service` and `After=getty@tty1.service`** — what
   display managers do. Starting the kiosk stops the getty; stopping it hands
   the VT back.

Both are asserted at build time in `04-ui/01-run.sh`: the `Conflicts=` line
must be present, and `default.target` must **not** be written. Each failure is
invisible without a screen, so checking costs nothing where it is cheap.

## Verified

Applied to `gexis` by hand, getty re-enabled, then rebooted unattended:

```
readlink default.target   → /usr/lib/systemd/system/multi-user.target   (platform's)
gexis-kiosk.service       → active
getty@tty1.service        → inactive        (stopped by Conflicts=)
labwc pid 946, 10 chromium processes
loginctl                  → pi  seat0  tty1
gexis-core                → wsserver: client connected (1 total)
```

**Not yet verified in an image.** The fix is proven on a running device; the
build carrying it has not been produced or reflashed.

## Why this was not caught earlier

`04-ui` was written from documentation and validated by a build that ran the
stage without error — which it did, correctly. The stage's assertions checked
that the symlinks it wrote existed, and they did. Both defects live entirely
in what happens *after* the build: one in a platform script we invoke
ourselves, one in a resource conflict that only exists on a booted system.

This is `docs/LESSONS.md`'s shape again — the check ran against the build's
filesystem, which resembled the booted one closely enough that the difference
was invisible. Case 1 in that file is the same file, the same stage and the
same class of mistake.
