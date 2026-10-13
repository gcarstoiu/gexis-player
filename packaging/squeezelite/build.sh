#!/bin/sh
# ADR-0145: gexis-squeezelite, Lyrion's player, built by us so that a file of
# more than two channels is folded down to stereo instead of losing channels
# (FLAC), not playing (WAV/AIFF) or keeping only two (DSD) - Finding 121.
# Runs inside gexis-deb-builder (arm64 trixie), with the repository at /src
# and the output in /out.
#
# The source Debian trixie builds its own `squeezelite` from - upstream's
# commit 262994a, which Debian's orig tarball matches file for file (checked
# 2026-10-13) - with Debian's build options (its debian/rules: DSD FFMPEG
# RESAMPLE VISEXPORT LINKALL IR USE_SSL OPUS, hardening=+all, -Wall) and
# Debian applies no patches of its own. **PATCHED**: squeezelite-downmix.patch
# beside this script adds the fold-down (downmix.c) and calls it from flac.c,
# pcm.c and dsd.c. The version says so with its "+git<commit>" and the
# Description names the patch by sha256.
#
# Replaces Debian's package: same binary path (/usr/bin/squeezelite), and the
# unit stays gexis-system's squeezelite.service. Debian's package carried
# only a SysV script and /etc/default file besides the binary, which the
# native unit has always overridden.
set -eu

VERSION_ARG="$1"   # the repository's version: unused, Squeezelite has its own
COMMIT=262994a989dc29ce3be4390c57c6a43373dfdca2
# The commit's own date, so a later pin sorts later. Checked below.
COMMIT_DATE=20241227
# Upstream's own version (squeezelite.h: 2.0, 0, 1517), with the hyphen a dot
# so the Debian revision below is the only one.
UPSTREAM=2.0.0.1517
# sha256 of every tracked file, sorted by name (as peppyalsa's pin).
SOURCE_SHA256=e7f2eaf0765ebd79214d8cf00aa06fc22de222b2cf9bf75b18517d6804aad645
PATCH=/src/packaging/squeezelite/squeezelite-downmix.patch
PATCH_SHA256=$(sha256sum "$PATCH" | cut -d' ' -f1)
SHORT=$(printf '%s' "$COMMIT" | cut -c1-7)
# The revision is ours: raised with every change to the patch or the build,
# or apt keeps the old binary (LESSONS 53).
VERSION="${UPSTREAM}+git${COMMIT_DATE}.${SHORT}-2"
PKG=gexis-squeezelite
# Staged where dpkg-shlibdeps expects a package's files: debian/<package>.
STAGE=/tmp/pkg/debian/$PKG
# Built at a fixed path: it is recorded through -ffile-prefix-map.
SRC=/tmp/squeezelite

rm -rf "$SRC" /tmp/pkg
git clone -q https://github.com/ralph-irving/squeezelite.git "$SRC"
cd "$SRC"
git checkout -q "$COMMIT"
[ "$(git rev-parse HEAD)" = "$COMMIT" ] || { echo "ERROR: HEAD is not $COMMIT" >&2; exit 1; }
got_date=$(TZ=UTC git log -1 --format=%cd --date=format-local:%Y%m%d)
[ "$got_date" = "$COMMIT_DATE" ] || { echo "ERROR: $COMMIT is dated $got_date, the pin says $COMMIT_DATE" >&2; exit 1; }
have=$(git ls-files -z | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)
if [ "$have" != "$SOURCE_SHA256" ]; then
	echo "ERROR: squeezelite $COMMIT source is $have, pinned $SOURCE_SHA256" >&2
	exit 1
fi

# `git apply`, which fails loudly on a mismatch.
git apply --verbose "$PATCH"
grep -q 'downmix_init_default' flac.c || { echo "ERROR: the downmix patch did not apply" >&2; exit 1; }

# Debian's debian/rules, as dh would run it: its build flags, hardening on,
# -Wall first, and its OPTS.
export DEB_BUILD_MAINT_OPTIONS=hardening=+all
export DEB_CFLAGS_MAINT_PREPEND=-Wall
eval "$(dpkg-buildflags --export=sh)"
make -j"$(nproc)" EXECUTABLE=squeezelite \
	OPTS="-DDSD -DFFMPEG -DRESAMPLE -DVISEXPORT -DLINKALL -DIR -DUSE_SSL -DOPUS -I/usr/include/opus"

# What dh_strip does to a binary (its debug symbols are not kept).
strip --remove-section=.comment --remove-section=.note --strip-unneeded squeezelite
# The build options it reports must be Debian's.
opts=$(./squeezelite -? 2>&1 | sed -n 's/^Build options: *//p' | tr -s ' ' | sed 's/ *$//')
[ "$opts" = "LINUX ALSA EVENTFD RESAMPLE FFMPEG OPUS VISEXPORT IR DSD SSL LINKALL" ] \
	|| { echo "ERROR: build options are '$opts', not Debian's" >&2; exit 1; }

install -D -m 755 squeezelite "$STAGE/usr/bin/squeezelite"
install -d -m 755 "$STAGE/usr/share/man/man1"
gzip -9n < doc/squeezelite.1 > "$STAGE/usr/share/man/man1/squeezelite.1.gz"
chmod 644 "$STAGE/usr/share/man/man1/squeezelite.1.gz"

# ADR-0099: the licence notice at the path the others use (GPL-3.0 section
# 5a: modified), the licence itself, and dsd2pcm's notice, which its licence
# asks to be carried with a binary.
DOC="$STAGE/usr/share/doc/gexis-player/licenses/squeezelite"
install -d -m 755 "$DOC"
printf '%s\n' "Squeezelite is licensed under the GNU General Public License, version 3 or later (LICENSE.txt)." \
	"It is MODIFIED by Gexis Player: a file of more than two channels is folded down to stereo." \
	"The change is packaging/squeezelite/squeezelite-downmix.patch in Gexis Player's repository," \
	"applied to upstream commit $COMMIT. See ../../SOURCE.md." \
	"Source: https://github.com/ralph-irving/squeezelite" \
	"dsd2pcm, part of it, is under the licence in dsd2pcm-LICENSE." \
	> "$DOC/README"
install -m 644 LICENSE.txt "$DOC/LICENSE.txt"
sed -n '1,/^ *\*\//p' dsd2pcm/dsd2pcm.h > "$DOC/dsd2pcm-LICENSE"
grep -q 'Sebastian Gesemann' "$DOC/dsd2pcm-LICENSE" || { echo "ERROR: dsd2pcm's notice not found" >&2; exit 1; }
chmod 644 "$DOC/README" "$DOC/dsd2pcm-LICENSE"
find "$STAGE" -type d -exec chmod 755 {} +

# Runtime dependencies as dpkg-shlibdeps reads them from the binary. It finds
# the package's root by its DEBIAN folder, so that exists first.
mkdir -p "$STAGE/DEBIAN"
printf 'Source: %s\n\nPackage: %s\nArchitecture: arm64\n' "$PKG" "$PKG" > /tmp/pkg/debian/control
DEPENDS=$(cd /tmp/pkg && dpkg-shlibdeps -O "debian/$PKG/usr/bin/squeezelite" | sed -n 's/^shlibs:Depends=//p')
[ -n "$DEPENDS" ] || { echo "ERROR: dpkg-shlibdeps found no dependencies" >&2; exit 1; }

# A device updated from a release with Debian's squeezelite: the binary is
# replaced under the running player, so it is restarted - only if running
# (the core stops it while another source plays). No enable: the unit and
# its enablement are gexis-system's.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && [ -d /run/systemd/system ]; then
	systemctl try-restart squeezelite.service || true
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
Provides: squeezelite
Conflicts: squeezelite
Replaces: squeezelite
Section: sound
Priority: optional
Homepage: https://github.com/ralph-irving/squeezelite
Description: Squeezelite, Lyrion's player, patched for Gexis Player
 Built as Debian trixie builds squeezelite, with its options. PATCHED
 (ADR-0145): a file of more than two channels - FLAC, WAV, AIFF, DSD - is
 folded down to stereo. Upstream commit $COMMIT
 (source sha256 over its tracked files $SOURCE_SHA256)
 with squeezelite-downmix.patch applied (sha256 $PATCH_SHA256).
CTL
chmod 644 "$STAGE/DEBIAN/control"
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_arm64.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_arm64.deb"
