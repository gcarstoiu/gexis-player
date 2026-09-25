# ADR-0049 — The on-device pictures folder is an SMB share

**Status:** Accepted — George, 2026-09-21: *"Let's go with B. Simplest for
now as it should be."*
**Date:** 2026-09-21
**Raised by:** [ADR-0047](0047-the-idle-screen-gains-backgrounds-and-weather.md)'s
open question — *"Where on-device wallpapers live, and how they get there"* —
which `idle_background: Wallpapers on device` needs an answer to before it
is a option anyone can use.
**Relates to:** [ADR-0028](0028-ui-serving-and-command-channel.md) (the API is
unauthenticated on the LAN), [ADR-0031](0031-first-boot-setup-access-point.md)

## Context

The idle screen offers four backgrounds and one of them reads
`/var/lib/gexis-core/pictures`. **Nothing put anything there.** Today a
picture arrives over SSH, which is not an answer for an appliance: the row
says *"No pictures on this device yet"* and no screen this product has can
change that.

Four ways were put to George on 2026-09-21, with what each costs on this
device measured rather than guessed: an upload control on the phone, an SMB
share, a USB import, or leaving it at SSH. **He chose the share, on
simplicity.**

## Decision

**`/var/lib/gexis-core/pictures` is served over SMB as `pictures`, and
nothing else is.**

### 1. One directory, never a disk

The share's path is the pictures directory itself. Not the home directory,
not `/var/lib/gexis-core` — which holds the settings database, the
enrichment cache and the wallpaper cache — and not a parent of anything.
A share is a hole in a box: it should be exactly the size of the thing that
goes through it.

**The downloaded wallpaper cache stays out of it** even though it is also
pictures. That directory is ours to evict from and a person editing it would
be editing a cache.

### 2. Guest-writable, because the LAN already is

**No credentials.** Anyone who can reach the device can write pictures to
it. That is a real statement and it is not a new one: ADR-0028 leaves the
whole command API unauthenticated on the LAN, so anyone who can reach this
device can already change its volume, its settings and what it is playing.
A folder of wallpapers is the same class of exposure and a smaller one.

**What keeps it small:** one directory, no execute bit, and the daemon only
ever reads from it and only ever as an image. A file dropped there that is
not a picture is not shown; it is not run, parsed or trusted.

If that posture ever changes, it changes for ADR-0028 first and this follows
it. A password on the share while the API stays open would be a lock on the
window next to an open door.

### 3. Written as `pi`, read as root

`force user = pi` with `create mask = 0644`: every write lands as the same
owner whoever connected, so the directory cannot accumulate files the daemon
or the next writer cannot touch. The daemon runs as root and only reads.

### 4. Found by name, not by NetBIOS

`avahi` is already running on this device — it is how `gexis.local` resolves
— so an `_smb._tcp` service file is what makes the share appear in Finder's
sidebar and in Windows' network view. **`nmbd` stays disabled**: NetBIOS
name service is a second discovery protocol, from 1987, broadcasting on a
LAN that already has one that works.

### 4a. Folders inside it are pictures too

**Organise them however you like.** George asked whether it matters,
2026-09-21, and at that moment it did: the reader looked at the top level
only, so a picture inside `Holidays/` was on the disk and invisible to the
screen. It walks the tree now, and a name travels as its path relative to
the share - `Holidays/beach.png`.

**A symlink is the one thing in that folder that can name a file somewhere
else**, and the folder is writable by anyone on the LAN. Links out are
skipped when the tree is read, and the route that serves a picture resolves
the whole name and requires the result to still be inside the directory - so
`../../etc/shadow` and a link to it are refused the same way.

### 5. It is not the only way in, and nothing assumes it is

The daemon reads a directory. SSH still works, a USB copy would work, and if
the upload control is ever built (option A, not chosen today) it writes to
the same place. **Nothing in the reading path knows or cares how a file got
there** — which is what keeps this decision cheap to reverse.

## Consequences

- **A second service listens on this device**, on 445. It is the first thing
  on the image that is neither ours nor a renderer, and it is another package
  to keep updated.
- **The image gains `samba`** and a config file. `nmbd` is masked rather
  than left running.
- **The pictures directory must exist before the share does**, owned by `pi`,
  or the first connection sees nothing and the user cannot tell an empty
  folder from a broken one.
- **The settings row can stay as it is.** It lists what the directory holds
  and says so when it is empty; the sentence it says is now actionable,
  which it was not before.
- **`smb.conf` is a stock file we edit**, so the build asserts on what it
  wrote and the device is checked separately — `docs/LESSONS.md` case 9: a
  check on the file you wrote is a check on your own `sed`.

## Alternatives considered

- **Upload from the phone** (option A). The pieces mostly exist — the `list`
  mechanic, `/surface` to keep the file picker off the kiosk — and it needs
  no new service. Not chosen: George wanted the simplest thing, and this one
  is a route, caps, an image check and a new affordance the design does not
  draw. **Still the better answer for someone with no computer**, and it
  writes to the same directory if it is ever built.
- **USB import** (option C). The only one that needs no network at all, and
  the most machinery: nothing on this image handles removable media today.
- **SSH, documented** (option D). Free, and what happens now. It leaves the
  row unusable by anyone who is not already at a terminal.
