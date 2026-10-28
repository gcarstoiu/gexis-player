#!/bin/sh
# ADR-0167 T1: gexis-nqptp, the timing daemon Shairport Sync needs for
# AirPlay 2. Not in Debian trixie (forky and sid carry 1.2.6, older than the
# shared-memory interface 11 Shairport Sync 5.6 needs), so built here from
# upstream's tag. Runs inside gexis-deb-builder (arm64 trixie), with the
# repository at /src and the output in /out.
#
# The binary and its licence only: the unit is gexis-airplay's.
set -eu

VERSION_ARG="$1"   # the repository's version: unused, NQPTP has its own
TAG=1.2.9
COMMIT=ab8fb67483411640fd7f1e193889482f2421c37c
COMMIT_DATE=20261014
# sha256 of every tracked file, sorted by name (as Squeezelite's pin).
SOURCE_SHA256=4ccb3f3fd8e6810b168177d9f9c0797842889b098834ac30adde7d5e03a2aba2
# The revision is ours: raised with every change to the build (LESSONS 53).
VERSION="${TAG}-1"
PKG=gexis-nqptp
STAGE=/tmp/pkg/debian/$PKG
SRC=/tmp/nqptp

rm -rf "$SRC" /tmp/pkg
git clone -q https://github.com/mikebrady/nqptp.git "$SRC"
cd "$SRC"
git checkout -q "$COMMIT"
[ "$(git rev-parse HEAD)" = "$COMMIT" ] || { echo "ERROR: HEAD is not $COMMIT" >&2; exit 1; }
[ "$(git rev-parse "refs/tags/$TAG^{commit}")" = "$COMMIT" ] || { echo "ERROR: tag $TAG is not $COMMIT" >&2; exit 1; }
got_date=$(TZ=UTC git log -1 --format=%cd --date=format-local:%Y%m%d)
[ "$got_date" = "$COMMIT_DATE" ] || { echo "ERROR: $COMMIT is dated $got_date, the pin says $COMMIT_DATE" >&2; exit 1; }
have=$(git ls-files -z | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)
if [ "$have" != "$SOURCE_SHA256" ]; then
	echo "ERROR: nqptp $COMMIT source is $have, pinned $SOURCE_SHA256" >&2
	exit 1
fi

export DEB_BUILD_MAINT_OPTIONS=hardening=+all
eval "$(dpkg-buildflags --export=sh)"
autoreconf -fi >/dev/null
./configure --prefix=/usr >/dev/null
make -j"$(nproc)" >/dev/null
strip --remove-section=.comment --remove-section=.note --strip-unneeded nqptp
# The version it reports, and the shared-memory interface Shairport Sync 5.6
# needs (smi11; its release notes).
said=$(./nqptp -V 2>&1)
[ "$said" = "Version: $TAG. Shared Memory Interface Version: smi11." ] \
	|| { echo "ERROR: nqptp -V says '$said'" >&2; exit 1; }

install -D -m 755 nqptp "$STAGE/usr/bin/nqptp"
install -d -m 755 "$STAGE/usr/share/man/man8"
gzip -9n < nqptp.8 > "$STAGE/usr/share/man/man8/nqptp.8.gz"
chmod 644 "$STAGE/usr/share/man/man8/nqptp.8.gz"

# ADR-0099 and ADR-0167 T8: GPL-2.0-only, so the notice says where the exact
# source is.
DOC="$STAGE/usr/share/doc/gexis-player/licenses/nqptp"
install -d -m 755 "$DOC"
printf '%s\n' "NQPTP is licensed under the GNU General Public License, version 2 (LICENSE)." \
	"Built unmodified from upstream tag $TAG, commit $COMMIT." \
	"Source: https://github.com/mikebrady/nqptp/tree/$COMMIT" \
	> "$DOC/README"
install -m 644 LICENSE "$DOC/LICENSE"
chmod 644 "$DOC/README"
find "$STAGE" -type d -exec chmod 755 {} +

mkdir -p "$STAGE/DEBIAN"
printf 'Source: %s\n\nPackage: %s\nArchitecture: arm64\n' "$PKG" "$PKG" > /tmp/pkg/debian/control
DEPENDS=$(cd /tmp/pkg && dpkg-shlibdeps -O "debian/$PKG/usr/bin/nqptp" | sed -n 's/^shlibs:Depends=//p')
[ -n "$DEPENDS" ] || { echo "ERROR: dpkg-shlibdeps found no dependencies" >&2; exit 1; }

# Upstream (5.6): NQPTP first, then Shairport Sync - restarting the receiver
# restarts both, in that order (gexis-nqptp is PartOf it), only if running.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && [ -n "$2" ] && [ -d /run/systemd/system ]; then
	systemctl try-restart gexis-shairport-sync.service || true
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/control" <<CTL
Package: $PKG
Version: $VERSION
Architecture: arm64
Maintainer: Gexis Player <noreply@github.com>
Depends: $DEPENDS
Provides: nqptp
Conflicts: nqptp
Replaces: nqptp
Section: sound
Priority: optional
Homepage: https://github.com/mikebrady/nqptp
Description: NQPTP, the timing daemon for AirPlay 2, for Gexis Player
 Built unmodified from upstream tag $TAG (commit $COMMIT, source sha256
 over its tracked files $SOURCE_SHA256), for Shairport Sync (ADR-0167).
CTL
chmod 644 "$STAGE/DEBIAN/control"
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_arm64.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_arm64.deb"
