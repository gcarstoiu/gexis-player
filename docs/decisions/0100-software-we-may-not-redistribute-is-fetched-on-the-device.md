# ADR-0100 — Software we may not redistribute is fetched on the device, when it is switched on

**Status:** **Accepted and built** — George, 2026-09-27: *"1A"*, on Plexamp
being included in the image with no established right to redistribute it.
**Amends [ADR-0090](0090-plexamp-ships-the-way-beszel-does.md)**, which put
Plexamp in the image. Qobuz's receiver
([ADR-0098](0098-qobuz-connect-is-installed-by-the-user.md)) will use the same
mechanism.
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
   the fetch in. The core does not change. For Qobuz, ADR-0098 puts a notice to
   confirm in front of the switch.
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
