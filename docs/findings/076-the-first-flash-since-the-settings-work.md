# Finding 076 — The first flash since the settings work

**Date:** 2026-09-25
**Question:** Phase 9 was closed against a device running an rsynced tree. Does
it hold on an image? And does [ADR-0083](../decisions/0083-a-backup-leaves-the-device.md)'s
backup and restore work on hardware?
**Scope:** `gexis`, a **new SD card** flashed with
`2026-09-25-gexis-player-v0.2.1-513-g8cbff39.img`, the old card kept intact and
untouched as a fallback. The image carries all of Phase 9 and **none of
ADR-0083**, which landed one commit later — so the backup work was rsynced on
top and the samba share installed by hand exactly as the image stage will. That
half is verified as code, **not as an image**; the next build is what proves
the stage.

## 1. Phase 9 holds on a real flash

| check | fresh boot |
|---|---|
| rows served | 74 |
| **orange dots** (a decision still owed) | **none** |
| **visible and unwired rows** | **none** |
| `version` | **`v0.2.1-513-g8cbff39`** |
| `image_build` | `2026-09-25T11:18:08Z` |
| `handoff_threshold` | max 3, step 0.5 |
| units | `gexis-core`, kiosk, peppy, squeezelite, go-librespot, bluealsa-aplay, smbd — all active |

**`version` is the one worth pointing at.** It read `unknown` for the whole of
Phase 9 because `/etc/gexis/image.info` did not exist on any card ever flashed
— the stage that writes it was itself part of criterion 1. This is the first
device that can say which build it is.

**A fresh card holds nothing**: 0 stored settings, no pairings, an empty
enrichment cache. Which is correct, and is the closest anyone has come to
seeing what a stranger gets — criterion 0's revisit before Phase 13 is about
that state.

## 2. The restore

The hand copy taken before the flash went back on: **41 stored settings,
3,664 enrichment rows, 7,061 notes**, `core.toml` with its `idle_url`, and the
phone's pairing. `spectrum_smoothing` came back as **62**, not the registry's
90 — the tuned value, which is the point.

**Checked that it was usable and not merely present:** eight artist ids from
the library, **8 of 8 portraits served from the restored cache**. Roughly fifty
minutes of sweeps, intact.

**The check that said it had failed was wrong.** `sudo ls /var/lib/bluetooth/*/`
reported no paired devices — because the glob expands as `pi` *before* `sudo`
runs, and `pi` cannot read a root-only directory, so it matched nothing and the
count was zero. `bluetoothctl devices` showed the Pixel the whole time.
[LESSONS](../LESSONS.md) 1's shape again: the check measured the checker.

## 3. ADR-0083, round trip

```
POST /settings/backup            -> gexis-gexis-20260925-142928.tgz, 3.6 MB, pi:pi
GET  /settings/restore/items     -> 1 item, "25 Sep 2026, 14:29 · 3.6 MB"
```

The row carries the item **without the sheet being opened**, which is what
seeding it is for.

**The share answers a guest**, which is the whole point — a backup that cannot
leave the device does not survive the event it exists for:

```
$ smbclient -N -L //gexis.local
  pictures   Disk   Gexis idle screen pictures
  backups    Disk   Gexis backups
$ smbclient -N //gexis.local/backups -c ls
  gexis-gexis-20260925-142928.tgz    N  3761596
```

`testparm` reports `path = /var/lib/gexis-core/backups`, `read only = No`,
`guest ok = Yes` — the three things the image's own check asserts — and the
section list is `[pictures] [backups]` with everything else unavailable.

**And the restore reverted a real change.** `idle_timeout` was set to **42**,
then the archive restored: the device rebooted on its own and came back
reporting **5**, with 41 settings, the enrichment cache and the pairing intact.

> The notes table reads **7,066** afterwards, not 7,061. That is not drift: the
> archive restored here was taken at 14:29 from the running device, by which
> point the daemon had cached five more notes than the pre-flash copy held.

## What this does not tell us

- **Whether the image builds the share.** The samba config and the directory
  were installed by hand here. `01-run-chroot.sh` asserts both at build time
  and has not run yet.
- **Whether a restore survives a *different* image.** Both sides of this round
  trip were the same build. An archive carries a device name and an LMS
  address and nothing stops it being restored anywhere.
- **Anything about the panel's own buttons.** Both actions were driven over
  HTTP. The sheet, its confirm and its wording were not tapped.
- **Boot time, or anything else measured.** This was a functional pass.
