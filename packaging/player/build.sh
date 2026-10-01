#!/bin/bash
# ADR-0107: gexis-player, the release. It carries the player's licence and
# source offer, and depends on the exact version of every one of our
# packages and of alsa-lib - so installing a release is installing exactly
# what was tested together. Runs inside gexis-deb-builder; the packages it
# names must already be in /out from the same build.
set -euo pipefail

VERSION="$1"
STAGE=/tmp/stage/gexis-player
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"

# The version of each of ours, read from the package built for it. Ours carry
# this build's version; the components their own. Two versions of one
# package in /out is refused rather than guessed at.
version_of() {
	local pkg="$1" found
	found=$(for f in /out/"$pkg"_*.deb; do [ -e "$f" ] && dpkg-deb -f "$f" Version; done | sort -u)
	[ -n "$found" ] || { echo "no $pkg in /out: build it first" >&2; exit 1; }
	[ "$(printf '%s\n' "$found" | wc -l)" -eq 1 ] || { echo "$pkg: several versions in /out ($found); clear packaging/out" >&2; exit 1; }
	printf '%s' "$found"
}
ours=""
for pkg in gexis-core gexis-ui gexis-system gexis-skins gexis-peppyalsa gexis-peppy-engines \
	gexis-go-librespot gexis-beszel-agent gexis-plexamp; do
	v=$(version_of "$pkg")
	ours="$ours, $pkg (= $v)"
done

# alsa-lib: the version Findings 002 and 003 measured the output against
# (ADR-0021 as amended 2026-09-12). An exact dependency holds it: apt cannot
# move it without removing the release.
ALSA="libasound2t64 (= 1.2.14-1+rpt1+deb13u1)"
# The operating system's packages the device runs (the stages' lists), minus
# the five that only compiled peppyalsa, which now arrives built.
OS="alsa-utils, bluez-alsa-utils, bluez-tools, chromium, grim, labwc, nodejs, plymouth, plymouth-themes, python3-pil, python3-pygame, rfkill, samba, squeezelite, swaybg, wlr-randr, wlrctl"

install -D -m 644 /src/image/stage-gexis/09-legal/files/COPYING "$STAGE/usr/share/doc/gexis-player/COPYING"
install -D -m 644 /src/image/stage-gexis/09-legal/files/SOURCE.md "$STAGE/usr/share/doc/gexis-player/SOURCE.md"

cat > "$STAGE/DEBIAN/control" <<CTL
Package: gexis-player
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: ${ours#, }, $ALSA, $OS
Section: sound
Priority: optional
Description: Gexis Player, one release
 Depends on the exact version of each of the player's packages and of
 alsa-lib, so a release installs exactly what was tested together
 (ADR-0105, ADR-0107).
CTL
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-player_${VERSION}_all.deb" >/dev/null
echo "/out/gexis-player_${VERSION}_all.deb"
