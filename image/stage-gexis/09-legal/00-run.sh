#!/bin/bash -e
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ADR-0099: the player's licence, the source offer, and the licences the other
# stages placed, together in /usr/share/doc/gexis-player. Last, so the package
# list it records is the image's final one.
DOC="${ROOTFS_DIR}/usr/share/doc/gexis-player"
install -D -m 644 files/COPYING "${DOC}/COPYING"
install -D -m 644 files/SOURCE.md "${DOC}/SOURCE.md"

# go-librespot is GPL-3.0 and its release carries no licence text; the text is
# the same as the player's, so it points there rather than duplicating it.
install -d "${DOC}/licenses/go-librespot"
printf '%s\n' "go-librespot is licensed under the GNU General Public License, version 3." \
	"The licence text is ../../COPYING. Source: https://github.com/devgianlu/go-librespot" \
	> "${DOC}/licenses/go-librespot/README"
# peppyalsa, GPL-3.0, modified here (GPL-3.0 section 5a).
install -d "${DOC}/licenses/peppyalsa"
printf '%s\n' "peppyalsa is licensed under the GNU General Public License, version 3." \
	"It is MODIFIED by Gexis Player: one write per frame. See ../../SOURCE.md." \
	"Source: https://github.com/project-owner/peppyalsa" \
	> "${DOC}/licenses/peppyalsa/README"
