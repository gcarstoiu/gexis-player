#!/bin/sh
# ADR-0167 T2: gexis-airplay, the plugin that makes Shairport Sync a Gexis
# renderer - the adapter from gcarstoiu/gexis-airplay's pinned release, its
# manifest and mark, and our units, configuration, hook and D-Bus policy
# (image/stage-gexis/13-airplay). Shairport Sync and NQPTP are their own
# packages. Runs inside gexis-deb-builder, with the repository at /src, the
# download cache at /cache and the output in /out.
#
# Versioned by the gexis-airplay release it carries, plus $1 - the commit of
# this repository's files it also carries (LESSONS 53: one version, one
# content).
set -eu

STAGE_DIR=/src/image/stage-gexis/13-airplay
. /src/packaging/airplay/pins.sh
: "${PLUGIN_VERSION:?} ${PLUGIN_ASSET:?} ${PLUGIN_URL:?} ${PLUGIN_SHA256:?}"
VERSION="${PLUGIN_VERSION}-1+${1:?usage: build.sh <version of our files>}"

PKG=gexis-airplay
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"

. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$PLUGIN_URL" "$PLUGIN_SHA256" "$WORK/$PLUGIN_ASSET"
tar -xzf "$WORK/$PLUGIN_ASSET" -C "$WORK"
PLUGIN_SRC="$WORK/gexis-airplay"
grep -q "^version = \"$PLUGIN_VERSION\"" "$PLUGIN_SRC/pyproject.toml" \
	|| { echo "ERROR: the release is not $PLUGIN_VERSION" >&2; exit 1; }

# The adapter's package only, not its tests. Modes set here.
mkdir -p "$STAGE/opt/gexis-airplay/src"
cp -r "$PLUGIN_SRC/src/gexis_airplay" "$STAGE/opt/gexis-airplay/src/gexis_airplay"
find "$STAGE/opt" -type d -exec chmod 755 {} +
find "$STAGE/opt" -type f -exec chmod 644 {} +

install -D -m 644 "$PLUGIN_SRC/gexis-airplay.service" "$STAGE/usr/lib/systemd/system/gexis-airplay.service"
install -D -m 644 "$STAGE_DIR/files/gexis-shairport-sync.service" "$STAGE/usr/lib/systemd/system/gexis-shairport-sync.service"
install -D -m 644 "$STAGE_DIR/files/gexis-nqptp.service" "$STAGE/usr/lib/systemd/system/gexis-nqptp.service"
install -D -m 644 "$STAGE_DIR/files/shairport-sync.conf" "$STAGE/usr/share/gexis/airplay/shairport-sync.conf"
install -D -m 755 "$STAGE_DIR/files/airplay-hook" "$STAGE/usr/lib/gexis/airplay-hook"
install -D -m 644 "$STAGE_DIR/files/gexis-airplay-dbus.conf" "$STAGE/usr/share/dbus-1/system.d/gexis-airplay.conf"
# ADR-0086: the manifest and its glyph, owned by the plugin's repository.
install -D -m 644 "$PLUGIN_SRC/plugin.json" "$STAGE/usr/share/gexis/plugins/airplay/plugin.json"
install -D -m 644 "$PLUGIN_SRC/mark.png" "$STAGE/usr/share/gexis/plugins/airplay/mark.png"
# ADR-0099: the adapter's own licence, beside the others.
install -D -m 644 "$PLUGIN_SRC/LICENSE" "$STAGE/usr/share/doc/gexis-player/licenses/gexis-airplay/LICENSE"

# **On for a player not set up yet, off for one that is** (ADR-0167
# decision 1 and Open 1, as proposed): a new image comes with AirPlay on, as
# Spotify and Bluetooth are; an update does not start announcing a new
# service on a network nobody chose it for. The switch is the unit's enabled
# state (ADR-0086), so this is the only place it is set; first use's presets
# and Settings change it afterwards. On an upgrade only the plugin restarts,
# for its new code: the receiver's restart would end a session that plays.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
	if [ -z "$2" ] && [ ! -e /var/lib/gexis/setup-done ]; then
		systemctl enable gexis-shairport-sync.service >/dev/null 2>&1 || true
	fi
	if [ -d /run/systemd/system ]; then
		systemctl daemon-reload || true
		systemctl reload dbus.service >/dev/null 2>&1 || true
		if [ -n "$2" ]; then
			systemctl try-restart gexis-airplay.service || true
		fi
	fi
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"
cat > "$STAGE/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = remove ] && [ -d /run/systemd/system ]; then
	systemctl stop gexis-shairport-sync.service gexis-airplay.service gexis-nqptp.service >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/prerm"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: python3, gexis-shairport-sync (>= 5.6.2), gexis-nqptp (>= 1.2.9), dbus
Recommends: python3-pil
Section: sound
Priority: optional
Description: AirPlay 2 as a Gexis Player plugin
 The gexis-airplay adapter (release $PLUGIN_VERSION), its manifest, and the
 units, configuration and hook that make Shairport Sync a Gexis renderer
 (ADR-0167). AirPlay is a trademark of Apple Inc., registered in the U.S.
 and other countries and regions.
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_all.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_all.deb"
