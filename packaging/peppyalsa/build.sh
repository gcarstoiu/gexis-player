#!/bin/sh
# ADR-0107: gexis-peppyalsa, the ALSA scope plugin that feeds the Peppy
# screen, as a Debian package. Runs inside gexis-deb-builder (arm64 trixie),
# with the repository at /src and the output in /out.
#
# The same build image/stage-gexis/00-alsa/01-run-chroot.sh does in the
# image's chroot: the same repository and pinned commit, the same patch, the
# same autotools sequence and --prefix=/usr, so the library lands at
# /usr/lib/libpeppyalsa.so, the path output.conf names. Built in
# /tmp/peppyalsa as the stage does, because that path is recorded in the
# library's debug information.
#
# **PATCHED**: this is not upstream peppyalsa. Finding 052's one write per
# spectrum frame is applied (image/stage-gexis/00-alsa/files/
# peppyalsa-one-write-per-frame.patch); the version says so with its
# "+git<commit>" and the Description names the patch by sha256.
set -eu

VERSION_ARG="$1"   # the repository's version: unused, peppyalsa has its own
COMMIT=7dcb0c5e783e0c86315a0f655684613affd3e9d2
# The commit's own date, so a later pin sorts later (ADR-0107: a version made
# of the ID alone does not - 3a1f... can compare below 7dcb...). Checked
# against the clone below. 0.44 is upstream's own version (configure.ac).
COMMIT_DATE=20260726
UPSTREAM=0.44
# A checksum of the checked-out source, independent of git: sha256 of every
# tracked file, sorted by name. The commit hash already names the content,
# but through SHA-1; this pins it by sha256 as every download here is pinned.
SOURCE_SHA256=a2e9fc0d0ea6b9cbb52bb9a959899c0bb9568a20d0e44d1b11afe5012960ba23
PATCH=/src/image/stage-gexis/00-alsa/files/peppyalsa-one-write-per-frame.patch
PATCH_SHA256=$(sha256sum "$PATCH" | cut -d' ' -f1)
SHORT=$(printf '%s' "$COMMIT" | cut -c1-7)
VERSION="${UPSTREAM}+git${COMMIT_DATE}.${SHORT}-1"
# Staged where dpkg-shlibdeps expects a package's files: debian/<package>.
STAGE=/tmp/pkg/debian/gexis-peppyalsa

rm -rf /tmp/peppyalsa /tmp/pkg
git clone -q https://github.com/project-owner/peppyalsa.git /tmp/peppyalsa
cd /tmp/peppyalsa
git checkout -q "$COMMIT"
[ "$(git rev-parse HEAD)" = "$COMMIT" ] || { echo "ERROR: HEAD is not $COMMIT" >&2; exit 1; }
got_date=$(TZ=UTC git log -1 --format=%cd --date=format-local:%Y%m%d)
[ "$got_date" = "$COMMIT_DATE" ] || { echo "ERROR: $COMMIT is dated $got_date, the pin says $COMMIT_DATE" >&2; exit 1; }
have=$(git ls-files -z | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)
if [ "$have" != "$SOURCE_SHA256" ]; then
	echo "ERROR: peppyalsa $COMMIT source is $have, pinned $SOURCE_SHA256" >&2
	exit 1
fi

# `git apply` and not `patch`: it fails loudly on a mismatch (the stage's
# reason, kept).
git apply --verbose "$PATCH"
grep -q 'frame_buffer' src/spectrum.c || { echo "ERROR: the peppyalsa patch did not apply" >&2; exit 1; }

aclocal
libtoolize
autoconf
automake --add-missing
./configure --prefix=/usr
make
make install DESTDIR="$STAGE"

# Everything make install put there, as the image has it today: the shared
# library and its two links, and the .a and .la beside them.
for f in libpeppyalsa.so libpeppyalsa.so.0; do
	[ -L "$STAGE/usr/lib/$f" ] || { echo "ERROR: /usr/lib/$f is not a link" >&2; exit 1; }
done
[ -f "$STAGE/usr/lib/libpeppyalsa.so.0.0.0" ] || { echo "ERROR: libpeppyalsa.so.0.0.0 not installed" >&2; exit 1; }
chmod 755 "$STAGE/usr/lib/libpeppyalsa.so.0.0.0" "$STAGE/usr/lib/libpeppyalsa.la"
chmod 644 "$STAGE/usr/lib/libpeppyalsa.a"

# ADR-0099: the licence notice image/stage-gexis/09-legal/00-run.sh writes,
# at the path it writes it to (GPL-3.0 section 5a: modified).
DOC="$STAGE/usr/share/doc/gexis-player/licenses/peppyalsa"
install -d -m 755 "$DOC"
printf '%s\n' "peppyalsa is licensed under the GNU General Public License, version 3." \
	"It is MODIFIED by Gexis Player: one write per frame. See ../../SOURCE.md." \
	"Source: https://github.com/project-owner/peppyalsa" \
	> "$DOC/README"
chmod 644 "$DOC/README"
find "$STAGE" -type d -exec chmod 755 {} +

# Runtime dependencies as dpkg-shlibdeps reads them from the library. It
# finds the package's root by its DEBIAN folder, so that exists first.
mkdir -p "$STAGE/DEBIAN"
printf 'Source: gexis-peppyalsa\n\nPackage: gexis-peppyalsa\nArchitecture: arm64\n' > /tmp/pkg/debian/control
DEPENDS=$(cd /tmp/pkg && dpkg-shlibdeps -O debian/gexis-peppyalsa/usr/lib/libpeppyalsa.so.0.0.0 | sed -n 's/^shlibs:Depends=//p')
[ -n "$DEPENDS" ] || { echo "ERROR: dpkg-shlibdeps found no dependencies" >&2; exit 1; }

# A shared library in /usr/lib: refresh the linker cache, as Debian's own
# library packages do. alsa-lib loads it by full path, so this is hygiene.
echo "activate-noawait ldconfig" > "$STAGE/DEBIAN/triggers"
cat > "$STAGE/DEBIAN/control" <<CTL
Package: gexis-peppyalsa
Version: $VERSION
Architecture: arm64
Maintainer: Gexis Player <noreply@github.com>
Depends: $DEPENDS
Section: sound
Priority: optional
Homepage: https://github.com/project-owner/peppyalsa
Description: peppyalsa ALSA scope plugin, patched for Gexis Player
 The level and spectrum plugin the Peppy screen reads (ADR-0107). PATCHED:
 upstream commit $COMMIT
 (source sha256 over its tracked files $SOURCE_SHA256)
 with peppyalsa-one-write-per-frame.patch applied
 (sha256 $PATCH_SHA256, Finding 052).
CTL
chmod 644 "$STAGE/DEBIAN/control" "$STAGE/DEBIAN/triggers"
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-peppyalsa_${VERSION}_arm64.deb" >/dev/null
echo "/out/gexis-peppyalsa_${VERSION}_arm64.deb"
