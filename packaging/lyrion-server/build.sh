#!/bin/sh
# ADR-0115: gexis-lyrion-server, our half of the Lyrion server plugin. Runs
# inside gexis-deb-builder (arm64 trixie), with the repository at /src and the
# output in /out.
#
# **Nothing of Lyrion's is in it** (decision 11): its notice restricts
# redistributing parts of it, so the device fetches it from the Lyrion
# community when the server is switched on (the pin, lyrion.env, and
# gexis-fetch@lyrion, as Plexamp, ADR-0100). This package is the rest: the
# unit, the manifest, the Music share, the first prefs, Lyrion's user and
# folders, and the system packages Lyrion runs on.
#
# Versioned by the Lyrion version it fetches, then ours: $1 is the commit of
# this package's own files (packaging/build.sh), so a change of ours is a new
# version. "-3" sorts after the 9.1.1-2 that went out before this.
set -eu
STAGE_DIR=/src/image/stage-gexis/10-lyrion
. /src/packaging/lyrion-server/pins.sh
: "${LYRION_VERSION:?}"
VERSION="${LYRION_VERSION}-3+${1:?the version of our files}"
PKG=gexis-lyrion-server
STAGE=/tmp/stage/$PKG
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"
# The pin names the version this package was built for: one place for it.
grep -q "LyrionMusicServer_v${LYRION_VERSION}/" "$STAGE_DIR/files/lyrion.env" \
	|| { echo "ERROR: lyrion.env does not fetch ${LYRION_VERSION}" >&2; exit 1; }
install -D -m 644 "$STAGE_DIR/files/lyrion.env" "$STAGE/usr/share/gexis/components/lyrion.env"
install -D -m 644 "$STAGE_DIR/files/gexis-lyrion.service" \
	"$STAGE/usr/lib/systemd/system/gexis-lyrion.service"
install -D -m 644 "$STAGE_DIR/files/plugin.json" \
	"$STAGE/usr/share/gexis/plugins/lyrion-server/plugin.json"
install -D -m 644 "$STAGE_DIR/files/gexis-music.conf" \
	"$STAGE/etc/samba/smb.conf.d/gexis-music.conf"
install -D -m 644 "$STAGE_DIR/files/server.prefs" \
	"$STAGE/usr/share/gexis/defaults/lyrion-server.prefs"
install -D -m 644 "$STAGE_DIR/files/90-gexis-usb-music.rules" \
	"$STAGE/usr/lib/udev/rules.d/90-gexis-usb-music.rules"

cat > "$STAGE/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
[ "$1" = configure ] || exit 0
# Lyrion's user, made as its own package makes it.
if ! getent passwd squeezeboxserver > /dev/null; then
	adduser --system --home /var/lib/squeezeboxserver --no-create-home \
		--gecos "Lyrion Music Server" squeezeboxserver
fi
usermod -a -G audio squeezeboxserver || true
for d in /var/lib/squeezeboxserver /var/lib/squeezeboxserver/prefs \
	/var/lib/squeezeboxserver/cache /var/log/squeezeboxserver; do
	install -d -o squeezeboxserver -g nogroup "$d"
done
# ADR-0115 decision 10: the device's Music folder and its Playlists folder.
install -d -m 755 -o squeezeboxserver -g nogroup /var/lib/gexis-music /var/lib/gexis-music/Playlists
if [ ! -e /var/lib/squeezeboxserver/prefs/server.prefs ]; then
	install -m 644 -o squeezeboxserver -g nogroup /usr/share/gexis/defaults/lyrion-server.prefs \
		/var/lib/squeezeboxserver/prefs/server.prefs
fi
SMB=/etc/samba/smb.conf
if [ -f "$SMB" ] && ! grep -q "smb.conf.d/gexis-music.conf" "$SMB"; then
	printf '\n# ADR-0115: the Lyrion server'"'"'s music share.\ninclude = /etc/samba/smb.conf.d/gexis-music.conf\n' >> "$SMB"
fi
# **Never enabled here**: off until the Plugins screen switches it on.
if [ -d /run/systemd/system ]; then
	systemctl daemon-reload || true
	systemctl try-reload-or-restart smbd.service 2>/dev/null || true
	pinned=
	# **A new pin is fetched by the update that brings it** (ADR-0100,
	# amended 2026-10-03). gexis-fetch@ stays active once it has run, so
	# restarting the software alone never downloads again: stopped, it runs
	# at the next start - now, where the switch is on, without holding the
	# update for the download; at the next switch-on otherwise.
	want=$(sed -n 's/^SHA256=//p' /usr/share/gexis/components/lyrion.env)
	have=$(cat /var/lib/gexis/components/lyrion.sha256 2>/dev/null || true)
	if [ -n "$have" ] && [ "$have" != "$want" ]; then
		on=$(systemctl is-enabled gexis-lyrion.service 2>/dev/null || true)
		systemctl stop gexis-fetch@lyrion.service || true
		[ "$on" = enabled ] && systemctl start --no-block gexis-lyrion.service || true
		pinned=1
	fi
	[ -n "$2" ] && [ -z "$pinned" ] && systemctl try-restart gexis-lyrion.service || true
fi
exit 0
POST
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/control" <<CTL
Package: $PKG
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: adduser, perl (>= 5.14.0), libio-socket-ssl-perl, libcrypt-openssl-rsa-perl, ca-certificates, procps, psmisc, samba, cifs-utils, nfs-common, smbclient, avahi-utils
Section: sound
Priority: optional
Description: Gexis Player's Lyrion server plugin
 Fetches Lyrion Music Server $LYRION_VERSION from the Lyrion community when the
 server is switched on, and runs it with playback first; the device's Music
 share and its Playlists folder. Lyrion itself is not in this package
 (ADR-0115).
CTL
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_all.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_all.deb"
