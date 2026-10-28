#!/bin/sh
# ADR-0167 T1: gexis-shairport-sync, the AirPlay 2 receiver. Debian trixie's
# shairport-sync 4.3.7 is classic AirPlay only (its debian/rules has no
# --with-airplay-2), so built here from upstream's tag, for AirPlay 2, with
# the metadata pipe and the D-Bus interface the adapter uses. Runs inside
# gexis-deb-builder (arm64 trixie), with the repository at /src and the
# output in /out.
#
# The binary and its licences only: the units and the configuration are
# gexis-airplay's.
set -eu

VERSION_ARG="$1"   # the repository's version: unused, Shairport Sync has its own
TAG=5.6.2
COMMIT=0a34fbda83724cc06266aadcf7c88acc8fef4e7d
COMMIT_DATE=20261025
# sha256 of every tracked file, sorted by name (as Squeezelite's pin).
SOURCE_SHA256=65568447b74493eeadaf6f897c9552007d968bf1b61155e1d22107bc3f0115a5
# The revision is ours: raised with every change to the build (LESSONS 53).
VERSION="${TAG}-1"
PKG=gexis-shairport-sync
STAGE=/tmp/pkg/debian/$PKG
SRC=/tmp/shairport-sync

# **Its build libraries are installed here, not in the builder image**
# (2026-10-28): the image's one layer would be rebuilt whole, about 1.4 GB on
# a build machine's `/` that had 1.9 GB free. Upstream's BUILD.md list for
# AirPlay 2, less what the image already has, plus GLib's for the D-Bus
# interface (gdbus-codegen).
apt-get update -qq
apt-get install -y -qq --no-install-recommends libpopt-dev libconfig-dev libavahi-client-dev \
	libplist-dev libplist-utils libsodium-dev uuid-dev libgcrypt20-dev xxd libglib2.0-dev >/dev/null

rm -rf "$SRC" /tmp/pkg
git clone -q https://github.com/mikebrady/shairport-sync.git "$SRC"
cd "$SRC"
git checkout -q "$COMMIT"
[ "$(git rev-parse HEAD)" = "$COMMIT" ] || { echo "ERROR: HEAD is not $COMMIT" >&2; exit 1; }
[ "$(git rev-parse "refs/tags/$TAG^{commit}")" = "$COMMIT" ] || { echo "ERROR: tag $TAG is not $COMMIT" >&2; exit 1; }
got_date=$(TZ=UTC git log -1 --format=%cd --date=format-local:%Y%m%d)
[ "$got_date" = "$COMMIT_DATE" ] || { echo "ERROR: $COMMIT is dated $got_date, the pin says $COMMIT_DATE" >&2; exit 1; }
have=$(git ls-files -z | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)
if [ "$have" != "$SOURCE_SHA256" ]; then
	echo "ERROR: shairport-sync $COMMIT source is $have, pinned $SOURCE_SHA256" >&2
	exit 1
fi

export DEB_BUILD_MAINT_OPTIONS=hardening=+all
eval "$(dpkg-buildflags --export=sh)"
autoreconf -fi >/dev/null
./configure --prefix=/usr --sysconfdir=/etc --with-airplay-2 --with-alsa --with-avahi \
	--with-ssl=openssl --with-soxr --with-metadata --with-metadata-pipe --with-dbus-interface >/dev/null
make -j"$(nproc)" >/dev/null
strip --remove-section=.comment --remove-section=.note --strip-unneeded shairport-sync

# What it was built with, as it reports itself: AirPlay 2 on NQPTP's
# interface 11, through ALSA and Avahi, with the metadata pipe and D-Bus.
said=$(./shairport-sync -V 2>&1)
for part in "$TAG" -AirPlay2 -smi11 -FFmpeg -OpenSSL -Avahi -ALSA -soxr -metadata -dbus; do
	case "$said" in *"$part"*) ;; *) echo "ERROR: shairport-sync -V says '$said', without $part" >&2; exit 1 ;; esac
done
echo "built $said"

install -D -m 755 shairport-sync "$STAGE/usr/bin/shairport-sync"
install -d -m 755 "$STAGE/usr/share/man/man1"
gzip -9n < man/shairport-sync.1 > "$STAGE/usr/share/man/man1/shairport-sync.1.gz"
chmod 644 "$STAGE/usr/share/man/man1/shairport-sync.1.gz"

# ADR-0099 and ADR-0167 T8: its own notice and the licences of the parts it
# carries (COPYING refers to each file; LICENSES lists them).
DOC="$STAGE/usr/share/doc/gexis-player/licenses/shairport-sync"
install -d -m 755 "$DOC"
printf '%s\n' "Shairport Sync is under the licences in COPYING and LICENSES: MIT-style for its own" \
	"files, BSD-3-Clause, MIT and ISC for parts it includes." \
	"Built unmodified from upstream tag $TAG, commit $COMMIT." \
	"Source: https://github.com/mikebrady/shairport-sync/tree/$COMMIT" \
	> "$DOC/README"
install -m 644 COPYING "$DOC/COPYING"
install -m 644 LICENSES "$DOC/LICENSES"
chmod 644 "$DOC/README"
find "$STAGE" -type d -exec chmod 755 {} +

mkdir -p "$STAGE/DEBIAN"
printf 'Source: %s\n\nPackage: %s\nArchitecture: arm64\n' "$PKG" "$PKG" > /tmp/pkg/debian/control
DEPENDS=$(cd /tmp/pkg && dpkg-shlibdeps -O "debian/$PKG/usr/bin/shairport-sync" | sed -n 's/^shlibs:Depends=//p')
[ -n "$DEPENDS" ] || { echo "ERROR: dpkg-shlibdeps found no dependencies" >&2; exit 1; }

cat > "$STAGE/DEBIAN/control" <<CTL
Package: $PKG
Version: $VERSION
Architecture: arm64
Maintainer: Gexis Player <noreply@github.com>
Depends: $DEPENDS, avahi-daemon, gexis-nqptp
Provides: shairport-sync
Conflicts: shairport-sync
Replaces: shairport-sync
Section: sound
Priority: optional
Homepage: https://github.com/mikebrady/shairport-sync
Description: Shairport Sync, an AirPlay 2 receiver, for Gexis Player
 Built unmodified from upstream tag $TAG (commit $COMMIT, source sha256
 over its tracked files $SOURCE_SHA256) for AirPlay 2, with the metadata
 pipe and the D-Bus interface (ADR-0167). Debian trixie's shairport-sync is
 classic AirPlay only.
CTL
chmod 644 "$STAGE/DEBIAN/control"
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_arm64.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_arm64.deb"
