#!/bin/sh
# ADR-0114: gexis-beszel-hub, the Beszel hub as upstream built it, at the
# agent's pin. Runs inside gexis-deb-builder (arm64 trixie), with the
# repository at /src, the download cache at /cache and the output in /out.
#
# Versioned by Beszel's own version, then ours: $1 is the commit of this
# package's own files (packaging/build.sh), so a change to the unit or the
# manifest is a new version. "-2" sorts after the 0.20.0-1 that went out first.
set -eu
STAGE_DIR=/src/image/stage-gexis/07-beszel
. /src/packaging/beszel-hub/pins.sh
: "${BESZEL_HUB_VERSION:?} ${BESZEL_HUB_ASSET:?} ${BESZEL_HUB_URL:?} ${BESZEL_HUB_SHA256:?}"
VERSION="${BESZEL_HUB_VERSION#v}-2+${1:?the version of our files}"
PKG=gexis-beszel-hub
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"
. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$BESZEL_HUB_URL" "$BESZEL_HUB_SHA256" "$WORK/$BESZEL_HUB_ASSET"
tar -xzf "$WORK/$BESZEL_HUB_ASSET" -C "$WORK" beszel LICENSE
# Named for what it is beside the agent: upstream calls the hub `beszel`.
install -D -m 755 "$WORK/beszel" "$STAGE/usr/bin/beszel-hub"
install -D -m 644 "$STAGE_DIR/files/beszel-hub.service" \
	"$STAGE/usr/lib/systemd/system/beszel-hub.service"
install -D -m 644 "$STAGE_DIR/files/plugin-hub.json" \
	"$STAGE/usr/share/gexis/plugins/beszel-hub/plugin.json"
# ADR-0099: the MIT notice goes with the binary - the agent's, same licence.
install -D -m 644 "$WORK/LICENSE" \
	"$STAGE/usr/share/doc/gexis-player/licenses/beszel-hub/LICENSE"

# **The unit is never enabled here** (ADR-0114 decision 2): off until the
# Plugins screen switches it on.
cat > "$STAGE/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
	# The same system account as the agent's (gexis-beszel-agent makes it too).
	if ! getent passwd beszel > /dev/null; then
		adduser --system --group --no-create-home \
			--home /var/lib/beszel-agent --shell /usr/sbin/nologin beszel
	fi
	if [ -d /run/systemd/system ]; then
		systemctl daemon-reload || true
		if [ -n "$2" ]; then
			systemctl try-restart beszel-hub.service || true
		fi
	fi
fi
exit 0
POST
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/control" <<CTL
Package: $PKG
Version: $VERSION
Architecture: arm64
Maintainer: Gexis Player <noreply@github.com>
Depends: adduser
Section: admin
Priority: optional
Description: Beszel hub, Gexis Player's system-metrics history plugin
 The upstream arm64 release of the Beszel hub ($BESZEL_HUB_VERSION), pinned by
 checksum, with its unit (port 8095) and its plugin manifest. The unit is left
 disabled: the Plugins screen switches it (ADR-0114, ADR-0107).
CTL
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_arm64.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_arm64.deb"
