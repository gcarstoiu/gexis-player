# Finding 038 — What the panel shows while it boots, and for how long

**Date:** 2026-09-19
**Question:** George wants a boot animation and no text at all. Before
designing one: how long is a boot, where does the text come from, and when
could an animation start and have to stop?
**System:** `gexis`, the running Phase 8 image, measured over SSH with
`systemd-analyze`. No reboot was performed — these are the timings of the
boot it was already running, so nothing interrupted the panel.
**Scope:** one device, one boot, warm SD card, network present. A first boot
differs (see below) and was not measured.

## The budget

```
Startup finished in 2.352s (kernel) + 17.368s (userspace) = 19.721s
multi-user.target reached after 15.937s in userspace
```

**`gexis-kiosk.service` starts at 18.26s** into the boot, and that is the
unit starting — labwc and Chromium then take their own time before the panel
paints anything. **The animation therefore has to cover roughly 2s to 20s+,
and its end is not a fixed moment**: it is whenever the UI first paints.

Where the userspace time goes, from `systemd-analyze blame`:

| service | cost |
|---|---|
| `NetworkManager-wait-online` | 5.981s |
| `NetworkManager` | 2.942s |
| `apt-daily-upgrade` | 2.664s |
| `apt-daily` | 2.582s |
| `go-librespot` | 2.141s |
| `cloud-init-main` | 1.833s |

**Nearly 11 of the 17 userspace seconds are network waiting and apt
timers.** An animation would be covering that rather than the device doing
anything a user wants. Shortening it is a separate question from drawing it,
and is not decided here.

## An initramfs already exists — correcting what was said earlier

**Claude told George on 2026-09-19 that "Raspberry Pi OS ships no initramfs
by default, so Plymouth starts only after the root filesystem is mounted".
That is wrong on this image**, and the device says so plainly:

```
config.txt:  auto_initramfs=1
/boot/firmware/initramfs8        (and initramfs_2712 for the Pi 5)
```

So Plymouth **can** be started from the initramfs and the animation can
begin early, rather than only after the root mount at ~3.97s. The claim was
made from general knowledge and not checked against the device before being
said, which is the failure `docs/LESSONS.md` exists for.

## Where the text comes from

`cmdline.txt` as shipped carries none of the quieting options:

```
console=serial0,115200 console=tty1 root=PARTUUID=7fb7163b-02 rootfstype=ext4
fsck.repair=yes rootwait cfg80211.ieee80211_regdom=DE
```

No `quiet`, no `splash`, no `logo.nologo`, no `vt.global_cursor_default=0`.
`config.txt` has no `disable_splash`. **`getty@tty1.service` is enabled** —
deliberately, by [Finding 022](022-kiosk-never-started-target-and-tty.md),
whose defect George reported as *"the panel showed an IP address and boot
messages"*. That getty is the login prompt, and `gexis-kiosk.service`
already orders itself `After=getty@tty1.service` so the VT is free when
labwc opens.

**Plymouth is not installed** (`dpkg -l | grep plymouth` is empty).

## What this does not cover

- **A first boot.** `firstrun.sh` runs and then reboots, so the sequence
  happens twice and the first pass is a differently configured machine.
  Never measured.
- **A cold card.** This was measured on a device that had been running; an
  SD card's read speed after a power cut is not the same.
- **When Chromium actually paints.** Only the unit's start at 18.26s was
  measured. The gap between that and the first frame on the glass is the
  part the handover has to cover, and it is unmeasured.
