#!/bin/sh
# ADR-0162 D1, ADR-0107: gexis-camilladsp, the equaliser's engine, as upstream
# built it. Runs inside gexis-deb-builder (arm64 trixie), with the repository
# at /src, the download cache at /cache and the output in /out.
#
# Versioned by CamillaDSP's own version, not the repository's (ADR-0107: one
# package per third-party component), so the git version this script is
# given as $1 is deliberately ignored. The pin is packaging/camilladsp/pins.sh.
set -eu

STAGE_DIR=/src/image/stage-gexis/11-equaliser
. /src/packaging/camilladsp/pins.sh
: "${CAMILLADSP_VERSION:?} ${CAMILLADSP_ASSET:?} ${CAMILLADSP_URL:?} ${CAMILLADSP_SHA256:?}"
# The revision after the dash is ours: raise it whenever what this package
# carries besides CamillaDSP changes (its unit), or apt keeps the old one.
# Back to -1 with each new CamillaDSP version.
VERSION="${CAMILLADSP_VERSION#v}-1"

PKG=gexis-camilladsp
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"

. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$CAMILLADSP_URL" "$CAMILLADSP_SHA256" "$WORK/$CAMILLADSP_ASSET"
tar -xzf "$WORK/$CAMILLADSP_ASSET" -C "$WORK" camilladsp

install -D -m 755 "$WORK/camilladsp" "$STAGE/usr/bin/camilladsp"
install -D -m 644 "$STAGE_DIR/files/gexis-equaliser.service" \
	"$STAGE/usr/lib/systemd/system/gexis-equaliser.service"
# ADR-0099: GPL-3.0, whose text the player ships already (upstream's archive
# carries none).
install -d -m 755 "$STAGE/usr/share/doc/gexis-player/licenses/camilladsp"
printf '%s\n' "CamillaDSP is licensed under the GNU General Public License, version 3." \
	"The licence text is ../../COPYING. Source: https://github.com/HEnquist/camilladsp" \
	> "$STAGE/usr/share/doc/gexis-player/licenses/camilladsp/README"
chmod 644 "$STAGE/usr/share/doc/gexis-player/licenses/camilladsp/README"

# **The unit is never enabled** (ADR-0162): the core starts it while the
# equaliser is on for the output in use, and stops it when it is not.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && [ -d /run/systemd/system ]; then
	systemctl daemon-reload || true
	if [ -n "$2" ]; then
		systemctl try-restart gexis-equaliser.service || true
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
Description: CamillaDSP, Gexis Player's equaliser engine
 The upstream arm64 release of CamillaDSP ($CAMILLADSP_VERSION), pinned by
 checksum, with the unit the player starts while its equaliser is on
 (ADR-0162, ADR-0107).
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_arm64.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_arm64.deb"
