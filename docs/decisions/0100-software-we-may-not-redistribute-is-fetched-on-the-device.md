# ADR-0100 — Software we may not redistribute is fetched on the device, when it is switched on

**Status:** **Accepted and built** — George, 2026-09-27: *"1A"*, on Plexamp
being included in the image with no established right to redistribute it.
**Amends [ADR-0090](0090-plexamp-ships-the-way-beszel-does.md)**, which put
Plexamp in the image.
**Date:** 2026-09-27
**Raised by:** the inventory behind [ADR-0099](0099-legal-and-credits-in-settings.md).
The Plexamp stage copied Plex's proprietary tarball, with Un4seen's BASS
libraries, into `/home/pi/plexamp`. It carries no licence or EULA, and no
record here held Plex's terms.

## Decision

1. **The image carries a pin, not the software.**
   `/usr/share/gexis/components/<name>.env` names the maker's URL, the pinned
   sha256, the archive format, where the software lives, and its owner.
2. **`gexis-fetch@<name>.service` fetches it before the unit that needs it
   starts.** That unit `Requires=` and `After=` it. The helper,
   `/usr/local/lib/gexis/gexis-fetch-component`, works like this:
   - It downloads the archive and refuses anything that fails the checksum.
   - It unpacks to a temporary directory and swaps the tree in whole.
   - It records the installed checksum. Every later start is a 0.04 s
     comparison.
   - A new pin means one new download.
3. **Switching the software on is the consent.** For Plexamp that is the
   existing Plugins switch: turning it on starts `plexamp.service`, which pulls
   the fetch in. The core does not change. A plugin whose manifest carries a
   `notice` has it confirmed in front of the switch.
4. **The image build checks both ways.** `verify-image.sh` fails if
   `/home/pi/plexamp` is in the image, and fails if `plexamp.service` does not
   require the fetch. `core/tests/test_notices.py` accounts for every URL in a
   pin, as it does for the stages' own downloads.

## Measured on gexis (2026-09-27)

- The image's copy of Plexamp was moved aside and `plexamp.service` started.
  The fetch downloaded 4.13.2 from `plexamp.plex.tv`, verified it, and installed
  a tree **identical (`diff -r`) to the one the image had shipped**, owned by
  `pi:pi`. Plexamp and its plugin came up.
- The no-op path on a later start takes 0.04 s.
- A pin with a wrong checksum was refused: exit 1, nothing unpacked.

## Costs

- **The first switch-on needs the network**, and takes as long as a 14 MB
  download. Plexamp needs Plex's servers anyway.
- **A restore brings Plexamp's claim back, not Plexamp.** The next start fetches
  it again.

## Amended 2026-09-27: the user is told what is happening, all the way

George, before he would try it: *"Even if it's extremely fast, feedback is a
must. Also retry in case of failure and a general status. This goes for all
plugins which require a download."* So it is built into the mechanism, not
into Plexamp:

- **The helper reports every step** to `/run/gexis/components/<name>.json`:
  preparing, downloading (bytes of total, attempt n of 3), retrying (with the
  reason and the wait), verifying, installing, installed, failed (with a
  sentence a person can read). **A failed download is tried three times**, 5 s
  and then 10 s apart, before it gives up.
- **The core publishes it live** as `components` in the state the panel already
  subscribes to. It polls twice a second while a download is busy, and every
  2 s otherwise. It says *preparing* the moment the switch goes on, before
  systemd has started anything.
- **A pin names its plugin** (`PLUGIN=`), its label and its source. The plugin
  gets a row under its switch, with the status, a progress bar with megabytes
  while downloading, and **Retry** with the reason when it failed. At rest it
  reads *"Not installed · downloaded from Plex when you switch it on"* or
  *"Installed · Plexamp 4.13.2"*.
- Switching off stops the finished download unit, so the next switch-on checks
  what is on disk again.

**Measured on gexis**, recording the state the panel receives while Plexamp was
switched on:

| Time | Status |
|---|---|
| 1.0 s | Switch flipped; *preparing* at the same instant |
| 3.2 s | 0 % of 14.6 MB |
| 3.7 s | 1 % |
| 4.2 s | 31 % |
| 4.7 s | 77 % |
| 5.2 s | Verifying |
| 5.7 s | Installing (unpacking takes 6 s) |
| 11.8 s | Installed |

An unreachable test component failed three times, at 5 s and then 10 s apart,
and ended *"Could not download from Nowhere: Could not resolve host"*. Retry
through the API restarted it.

**Amended again the same day (George):** *"The status and the download need
to be part of the pill itself otherwise it floats and the connection is not
clear."* The status line, the progress bar and Retry now sit inside the
plugin's own switch row. Retry is a hidden action row the API keeps. *"Let's
group the plugins based on the area they operate in"*: the Plugins page lists
switches under *Sources* (renderers) and *System* (services). Every state was
drawn in Plexamp's row on the panel and photographed: starting, downloading,
interrupted, installing, failed with Retry, installed.

## Amended 2026-09-28: switching off stops it; removing is a separate action

Switching a plugin off stopped its software and left the download where it
was, and nothing removed it. **Decided (George,
2026-09-28), option C of three:** *"Option C that you recommended for turning
it off and deleting separately. This should be reflected in the legal text
too."* The other two were leaving it as it was, and deleting on every switch-off.

- **Off stops the software.** The download stays, so switching back on is
  immediate, with no second download.
- **Remove** appears inside the plugin's own row, beside the status line, where
  Retry sits. It is shown only while the plugin is **off** and its software is
  **installed**. It asks first, in a sheet that says what goes and what stays.
- **What Remove deletes:** the downloaded software (the pin's `DEST`, and any
  `DEST.old`), its installed-version stamp, and its status. The row then reads
  *Not installed*, and switching on downloads it again.
- **What it keeps:** the plugin's settings and whatever the software wrote
  outside `DEST`: Plexamp's sign-in (its claim). George's principle
  was about code that could get the player into trouble, and a sign-in is not
  code. Keeping it means a re-download carries on where it was, where losing it
  would mean claiming Plexamp again. *This is Claude's call and easy to reverse.
  It is put to George with the change.*
- **Refused while the plugin is on**, in the core as well as on the screen. The
  core runs as root and deletes directly. It deletes only a path the image's own
  pin names, and never one shorter than four parts: `/home/pi/plexamp` is, and
  `/opt/x` is refused.
- A hidden action row, `<plugin>.remove`, beside `<plugin>.download` (Retry).
  It is an action, not a setting, so it adds no ADR-0022 row.
- **The Legal page says it** for Plexamp.

