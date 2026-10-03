#!/bin/sh
# ADR-0107: gexis-plexamp, the plugin that makes Plexamp a Gexis renderer
# (ADR-0090). Plexamp itself is not in it: it stays fetched on the device
# (ADR-0100), by the pin this package ships in components/plexamp.env. Runs
# inside gexis-deb-builder, with the repository at /src, the download cache at
# /cache and the output in /out.
#
# Versioned by the gexis-plexamp release it carries (ADR-0107: one package
# per component), plus $1 - the commit of this repository's files it also
# carries, Plexamp's pin among them (ADR-0100, amended 2026-10-03).
#
# The pin is read from the image stage that installs it today, so there is
# one place that names the version and its checksum.
set -eu

STAGE_DIR=/src/image/stage-gexis/08-plexamp
. /src/packaging/plexamp/pins.sh
: "${PLUGIN_VERSION:?} ${PLUGIN_ASSET:?} ${PLUGIN_URL:?} ${PLUGIN_SHA256:?}"
# The plugin's version, plus the commit of the files of ours this package
# carries - the pin among them - so a new Plexamp pin is a new version
# (LESSONS 53: one version, one content).
VERSION="${PLUGIN_VERSION}-2+${1:?usage: build.sh <version of our files>}"

PKG=gexis-plexamp
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"

. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$PLUGIN_URL" "$PLUGIN_SHA256" "$WORK/$PLUGIN_ASSET"
tar -xzf "$WORK/$PLUGIN_ASSET" -C "$WORK"
PLUGIN_SRC="$WORK/gexis-plexamp"

# The plugin's source, as 08-plexamp copies it - its package only, not the
# release's egg-info or tests. Modes are set here rather than taken from the
# tarball, which carries group-writable ones.
mkdir -p "$STAGE/opt/gexis-plexamp/src"
cp -r "$PLUGIN_SRC/src/gexis_plexamp" "$STAGE/opt/gexis-plexamp/src/gexis_plexamp"
find "$STAGE/opt" -type d -exec chmod 755 {} +
find "$STAGE/opt" -type f -exec chmod 644 {} +

install -D -m 644 "$PLUGIN_SRC/gexis-plexamp.service" \
	"$STAGE/usr/lib/systemd/system/gexis-plexamp.service"
install -D -m 644 "$STAGE_DIR/files/plexamp.service" \
	"$STAGE/usr/lib/systemd/system/plexamp.service"
install -D -m 755 "$STAGE_DIR/files/plexamp-start-idle" \
	"$STAGE/usr/lib/gexis/plexamp-start-idle"
# ADR-0086: the manifest and its glyph, owned by the plugin's repository.
install -D -m 644 "$PLUGIN_SRC/plugin.json" \
	"$STAGE/usr/share/gexis/plugins/plexamp/plugin.json"
install -D -m 644 "$PLUGIN_SRC/mark.png" \
	"$STAGE/usr/share/gexis/plugins/plexamp/mark.png"
# ADR-0100: the pin gexis-fetch@plexamp uses to download Plexamp from Plex.
install -D -m 644 /src/image/stage-gexis/03-core/files/components/plexamp.env \
	"$STAGE/usr/share/gexis/components/plexamp.env"

# **Neither unit is enabled here** (ADR-0090): an unclaimed Plexamp cannot play
# anything, and the core switches the pair at runtime. On an upgrade only the
# plugin restarts, to pick up its new code; Plexamp's own process is not ours
# and restarting it would interrupt whatever it is playing.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && [ -d /run/systemd/system ]; then
	systemctl daemon-reload || true
	pinned=
	# **A new pin is fetched by the update that brings it** (ADR-0100,
	# amended 2026-10-03). gexis-fetch@ stays active once it has run, so
	# restarting the software alone never downloads again: stopped, it runs
	# at the next start - now, where the switch is on, without holding the
	# update for the download; at the next switch-on otherwise.
	want=$(sed -n 's/^SHA256=//p' /usr/share/gexis/components/plexamp.env)
	have=$(cat /var/lib/gexis/components/plexamp.sha256 2>/dev/null || true)
	if [ -n "$have" ] && [ "$have" != "$want" ]; then
		on=$(systemctl is-enabled plexamp.service 2>/dev/null || true)
		systemctl stop gexis-fetch@plexamp.service || true
		[ "$on" = enabled ] && systemctl start --no-block plexamp.service || true
		pinned=1
	fi
	if [ -n "$2" ]; then
		systemctl try-restart gexis-plexamp.service || true
	fi
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: python3, nodejs
Section: sound
Priority: optional
Description: Plexamp as a Gexis Player plugin
 The gexis-plexamp adapter (release $PLUGIN_VERSION), its manifest and units,
 and the pin the device uses to fetch Plexamp headless from Plex the first
 time it is switched on. Plexamp itself is not included (ADR-0100, ADR-0107).
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_all.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_all.deb"
