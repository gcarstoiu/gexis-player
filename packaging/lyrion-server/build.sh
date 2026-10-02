#!/bin/sh
# ADR-0115: gexis-lyrion-server, Lyrion Music Server as upstream built it,
# repackaged so it ships switched off. Runs inside gexis-deb-builder (arm64
# trixie), with the repository at /src, the download cache at /cache and the
# output in /out.
#
# **Upstream's files, unchanged; our install scripts.** Upstream's postinst
# enables and starts the server on a fresh install (dh_systemd_enable), and an
# image cannot ship a server running that nobody switched on. So its data tree
# is taken as it is, and the maintainer scripts are ours: make its user and
# folders, never enable it. The Plugins screen switches it.
#
# Versioned by Lyrion's own version (ADR-0107); the git version given as $1
# is ignored.
set -eu
STAGE_DIR=/src/image/stage-gexis/10-lyrion
. /src/packaging/lyrion-server/pins.sh
: "${LYRION_VERSION:?} ${LYRION_ASSET:?} ${LYRION_URL:?} ${LYRION_SHA256:?}"
VERSION="${LYRION_VERSION}-1"
PKG=gexis-lyrion-server
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"
. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$LYRION_URL" "$LYRION_SHA256" "$WORK/$LYRION_ASSET"
dpkg-deb -x "$WORK/$LYRION_ASSET" "$STAGE"
dpkg-deb -e "$WORK/$LYRION_ASSET" "$WORK/upstream-control"
# The SysV script would be a second way to start it: systemd's unit is the one.
rm -f "$STAGE/etc/init.d/lyrionmusicserver"
# Our part: the drop-in, the plugin manifest, the share, the first prefs.
install -D -m 644 "$STAGE_DIR/files/gexis.conf" \
	"$STAGE/etc/systemd/system/lyrionmusicserver.service.d/gexis.conf"
install -D -m 644 "$STAGE_DIR/files/plugin.json" \
	"$STAGE/usr/share/gexis/plugins/lyrion-server/plugin.json"
install -D -m 644 "$STAGE_DIR/files/gexis-music.conf" \
	"$STAGE/etc/samba/smb.conf.d/gexis-music.conf"
install -D -m 644 "$STAGE_DIR/files/server.prefs" \
	"$STAGE/usr/share/gexis/defaults/lyrion-server.prefs"
# Upstream's conffiles, less the SysV script removed above.
grep -v '^/etc/init.d/lyrionmusicserver$' "$WORK/upstream-control/conffiles" > "$STAGE/DEBIAN/conffiles" || true

cat > "$STAGE/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
[ "$1" = configure ] || exit 0
# Upstream's user, made as upstream makes it.
if ! getent passwd squeezeboxserver > /dev/null; then
	adduser --system --home /usr/share/squeezeboxserver --no-create-home \
		--gecos "Lyrion Music Server" squeezeboxserver
fi
usermod -a -G audio squeezeboxserver || true
for d in /var/lib/squeezeboxserver /var/lib/squeezeboxserver/prefs /var/log/squeezeboxserver; do
	install -d -o squeezeboxserver -g nogroup "$d"
done
chown -R squeezeboxserver:nogroup /etc/squeezeboxserver /var/lib/squeezeboxserver
# ADR-0115: the device's Music folder and its Playlists folder, Lyrion's.
install -d -m 755 -o squeezeboxserver -g nogroup /var/lib/gexis-music /var/lib/gexis-music/Playlists
# The first prefs, once: Lyrion's own file from then on.
if [ ! -e /var/lib/squeezeboxserver/prefs/server.prefs ]; then
	install -m 644 -o squeezeboxserver -g nogroup /usr/share/gexis/defaults/lyrion-server.prefs \
		/var/lib/squeezeboxserver/prefs/server.prefs
fi
# The Music share, beside Pictures and Backups (ADR-0049).
SMB=/etc/samba/smb.conf
if [ -f "$SMB" ] && ! grep -q "smb.conf.d/gexis-music.conf" "$SMB"; then
	printf '\n# ADR-0115: the Lyrion server'"'"'s music share.\ninclude = /etc/samba/smb.conf.d/gexis-music.conf\n' >> "$SMB"
fi
# **Never enabled here** (ADR-0115 decision 1): off until switched on.
if [ -d /run/systemd/system ]; then
	systemctl daemon-reload || true
	systemctl try-reload-or-restart smbd.service 2>/dev/null || true
	[ -n "$2" ] && systemctl try-restart lyrionmusicserver.service || true
fi
exit 0
POST
chmod 755 "$STAGE/DEBIAN/postinst"

DEPENDS=$(sed -n 's/^Depends: //p' "$WORK/upstream-control/control")
cat > "$STAGE/DEBIAN/control" <<CTL
Package: $PKG
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: $DEPENDS
Conflicts: lyrionmusicserver, logitechmediaserver, squeezeboxserver
Section: sound
Priority: optional
Description: Lyrion Music Server, Gexis Player's server plugin
 Lyrion Music Server $LYRION_VERSION as upstream built it, pinned by checksum,
 with a unit drop-in that keeps playback first, its plugin manifest and the
 device's Music share. The server is left switched off: the Plugins screen
 switches it (ADR-0115, ADR-0107).
CTL
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_all.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_all.deb"
