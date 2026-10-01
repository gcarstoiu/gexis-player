#!/bin/sh
# ADR-0107: gexis-go-librespot, the Spotify Connect renderer as upstream built
# it. Runs inside gexis-deb-builder (arm64 trixie), with the repository at
# /src, the download cache at /cache and the output in /out.
#
# Versioned by go-librespot's own version, not the repository's (ADR-0107:
# one package per third-party component), so the git version this script is
# given as $1 is deliberately ignored.
#
# The pin is read from the image stage that installs it today, so there is
# one place that names the version and its checksum.
set -eu

STAGE_DIR=/src/image/stage-gexis/02-renderers
. /src/packaging/go-librespot/pins.sh
: "${GO_LIBRESPOT_VERSION:?} ${GO_LIBRESPOT_ASSET:?} ${GO_LIBRESPOT_URL:?} ${GO_LIBRESPOT_SHA256:?}"
VERSION="${GO_LIBRESPOT_VERSION#v}-1"

PKG=gexis-go-librespot
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"

. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$GO_LIBRESPOT_URL" "$GO_LIBRESPOT_SHA256" "$WORK/$GO_LIBRESPOT_ASSET"
tar -xzf "$WORK/$GO_LIBRESPOT_ASSET" -C "$WORK" go-librespot

install -D -m 755 "$WORK/go-librespot" "$STAGE/usr/bin/go-librespot"
install -D -m 644 "$STAGE_DIR/files/go-librespot.service" \
	"$STAGE/usr/lib/systemd/system/go-librespot.service"
# The player rewrites /var/lib/go-librespot/config.yml at runtime (device
# name, sign-in), so the package ships the default and postinst places it
# only where there is none (ADR-0107, files the player rewrites).
install -D -m 644 "$STAGE_DIR/files/go-librespot-config.yml" \
	"$STAGE/usr/share/gexis/defaults/go-librespot/config.yml"
# ADR-0099: the same notice at the same path 09-legal writes today.
install -d -m 755 "$STAGE/usr/share/doc/gexis-player/licenses/go-librespot"
printf '%s\n' "go-librespot is licensed under the GNU General Public License, version 3." \
	"The licence text is ../../COPYING. Source: https://github.com/devgianlu/go-librespot" \
	> "$STAGE/usr/share/doc/gexis-player/licenses/go-librespot/README"
chmod 644 "$STAGE/usr/share/doc/gexis-player/licenses/go-librespot/README"

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
	# Placed once: the player owns this file after the first install.
	if [ ! -e /var/lib/go-librespot/config.yml ]; then
		install -d -m 755 /var/lib/go-librespot
		install -m 644 -o 1000 -g 1000 \
			/usr/share/gexis/defaults/go-librespot/config.yml \
			/var/lib/go-librespot/config.yml
	fi
	# Enabled on the first install only; after that the core switches it at
	# runtime and an upgrade must leave that choice alone.
	# Not `|| true`: a failed enable fails the install rather than leaving a
	# device with no Spotify (as gexis-core's). Only a system without
	# systemctl at all - a test container - skips it, and says so.
	if [ -z "$2" ]; then
		if command -v systemctl >/dev/null; then
			systemctl enable go-librespot.service
		else
			echo "gexis-go-librespot: no systemctl here; not enabled" >&2
		fi
	fi
	if [ -d /run/systemd/system ]; then
		systemctl daemon-reload || true
		if [ -n "$2" ]; then
			systemctl try-restart go-librespot.service || true
		fi
	fi
fi
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: arm64
Maintainer: Gexis Player <noreply@github.com>
Section: sound
Priority: optional
Description: go-librespot, Gexis Player's Spotify Connect renderer
 The upstream arm64 release of go-librespot ($GO_LIBRESPOT_VERSION), pinned by
 checksum, with its unit and the player's default configuration (ADR-0107).
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_arm64.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_arm64.deb"
