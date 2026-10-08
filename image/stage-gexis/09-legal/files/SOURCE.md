# Source code for Gexis Player

Gexis Player is free software under the GNU General Public License, version 3
or later. The full text is in `COPYING`, beside this file.

**The player's own source:** https://github.com/gcarstoiu/gexis-player, at the
version shown under Settings → System → Image build.

**The other free software in this image.** Each component and its licence are
listed under Settings → System → Legal, and in `THIRD-PARTY.md` in the
repository.

- Components fetched when the image is built are pinned to exact commits or
  releases, which are named in the build scripts under `image/stage-gexis/`.
  Their source is at those upstreams.
- **peppyalsa is modified here.** The changes are
  `image/stage-gexis/00-alsa/files/peppyalsa-one-write-per-frame.patch` and
  `image/stage-gexis/00-alsa/files/peppyalsa-spectrum-bands.patch`, applied in
  that order to the pinned upstream commit.
- Debian and Raspberry Pi OS packages are listed with their exact versions in
  `packages.txt`, beside this file. Their source is in the Debian and Raspberry
  Pi OS source archives at those versions.

**Written offer.** For at least three years after this image was published,
the complete corresponding source code for any GPL- or LGPL-licensed program in
it is available on request, for no more than the cost of providing it. Ask by
opening an issue at https://github.com/gcarstoiu/gexis-player/issues.
