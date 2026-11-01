#!/bin/sh
# ADR-0172: gexis-roon, the plugin that makes the player a Roon device - the
# adapter from gcarstoiu/gexis-roon's pinned release and its manifest, and our
# unit for Roon Bridge, its user and its download pin
# (image/stage-gexis/14-roon). Roon Bridge itself is Roon Labs' and is never
# in the package: it is fetched on the device when Roon is switched on.
# Runs inside gexis-deb-builder, with the repository at /src, the download
# cache at /cache and the output in /out.
#
# Versioned by the gexis-roon release it carries, plus $1 - the commit of
# this repository's files it also carries (LESSONS 53: one version, one
# content).
set -eu

STAGE_DIR=/src/image/stage-gexis/14-roon
. /src/packaging/roon/pins.sh
: "${PLUGIN_VERSION:?} ${PLUGIN_ASSET:?} ${PLUGIN_URL:?} ${PLUGIN_SHA256:?}"
VERSION="${PLUGIN_VERSION}-1+${1:?usage: build.sh <version of our files>}"

PKG=gexis-roon
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"

. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$PLUGIN_URL" "$PLUGIN_SHA256" "$WORK/$PLUGIN_ASSET"
tar -xzf "$WORK/$PLUGIN_ASSET" -C "$WORK"
PLUGIN_SRC="$WORK/gexis-roon"
grep -q "^version = \"$PLUGIN_VERSION\"" "$PLUGIN_SRC/pyproject.toml" \
	|| { echo "ERROR: the release is not $PLUGIN_VERSION" >&2; exit 1; }

mkdir -p "$STAGE/opt/gexis-roon/src"
cp -r "$PLUGIN_SRC/src/gexis_roon" "$STAGE/opt/gexis-roon/src/gexis_roon"
find "$STAGE/opt" -type d -exec chmod 755 {} +
find "$STAGE/opt" -type f -exec chmod 644 {} +

install -D -m 644 "$PLUGIN_SRC/gexis-roon.service" "$STAGE/usr/lib/systemd/system/gexis-roon.service"
install -D -m 644 "$STAGE_DIR/files/gexis-roonbridge.service" "$STAGE/usr/lib/systemd/system/gexis-roonbridge.service"
install -D -m 644 "$STAGE_DIR/files/roonbridge-sysusers.conf" "$STAGE/usr/lib/sysusers.d/gexis-roonbridge.conf"
install -D -m 644 "$STAGE_DIR/files/components/roonbridge.env" "$STAGE/usr/share/gexis/components/roonbridge.env"
install -D -m 644 "$PLUGIN_SRC/plugin.json" "$STAGE/usr/share/gexis/plugins/roon/plugin.json"
install -D -m 644 "$PLUGIN_SRC/LICENSE" "$STAGE/usr/share/doc/gexis-player/licenses/gexis-roon/LICENSE"

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
set -e
if [ "$1" = configure ]; then
	systemd-sysusers gexis-roonbridge.conf >/dev/null 2>&1 || true
	if [ -d /run/systemd/system ]; then
		systemctl daemon-reload || true
		if [ -n "$2" ]; then
			systemctl try-restart gexis-roon.service || true
		fi
	fi
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"
cat > "$STAGE/DEBIAN/prerm" <<'EOF'
set -e
if [ "$1" = remove ] && [ -d /run/systemd/system ]; then
	systemctl stop gexis-roon.service gexis-roonbridge.service >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/prerm"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: python3, alsa-utils, curl, bzip2, libicu76
Section: sound
Priority: optional
Description: Roon as a Gexis Player plugin
 The gexis-roon adapter (release $PLUGIN_VERSION), its manifest, and the unit,
 user and download pin for Roon Bridge, which is fetched from Roon Labs on
 the device when the plugin is switched on (ADR-0172). Roon and Roon Bridge
 are Roon Labs' and under Roon's own terms.
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_all.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_all.deb"
