#!/bin/sh
# ADR-0107: gexis-beszel-agent, the Beszel monitoring agent (ADR-0087) as
# upstream built it. Runs inside gexis-deb-builder (arm64 trixie), with the
# repository at /src, the download cache at /cache and the output in /out.
#
# Versioned by Beszel's own version, not the repository's (ADR-0107: one
# package per third-party component), so the git version this script is
# given as $1 is deliberately ignored.
#
# The pin is read from the image stage that installs it today, so there is
# one place that names the version and its checksum.
set -eu

STAGE_DIR=/src/image/stage-gexis/07-beszel
. /src/packaging/beszel-agent/pins.sh
: "${BESZEL_VERSION:?} ${BESZEL_ASSET:?} ${BESZEL_URL:?} ${BESZEL_SHA256:?}"
# The revision after the dash is ours: raise it whenever what this package
# carries besides Beszel changes (its plugin.json), or apt keeps the old one -
# -2 for the manifest's `summary` (ADR-0128, 2026-10-07); -3 for the Hub
# public key's `pattern`.
VERSION="${BESZEL_VERSION#v}-3"

PKG=gexis-beszel-agent
STAGE=/tmp/stage/$PKG
WORK=/tmp/work/$PKG
rm -rf "$STAGE" "$WORK"
mkdir -p "$STAGE/DEBIAN" "$WORK"

. /src/image/stage-gexis/fetch-cached.sh
fetch_cached "$BESZEL_URL" "$BESZEL_SHA256" "$WORK/$BESZEL_ASSET"
tar -xzf "$WORK/$BESZEL_ASSET" -C "$WORK" beszel-agent LICENSE

install -D -m 755 "$WORK/beszel-agent" "$STAGE/usr/bin/beszel-agent"
install -D -m 755 "$STAGE_DIR/files/beszel-agent-listen-check.sh" \
	"$STAGE/usr/lib/gexis/beszel-agent-listen-check.sh"
install -D -m 644 "$STAGE_DIR/files/beszel-agent.service" \
	"$STAGE/usr/lib/systemd/system/beszel-agent.service"
install -D -m 644 "$STAGE_DIR/files/plugin.json" \
	"$STAGE/usr/share/gexis/plugins/beszel/plugin.json"
# ADR-0099: the MIT notice goes with the binary, at the path it has today.
install -D -m 644 "$WORK/LICENSE" \
	"$STAGE/usr/share/doc/gexis-player/licenses/beszel/LICENSE"

# **The unit is never enabled here** (ADR-0087): an unenrolled device runs
# nothing, and the core switches it at runtime.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
	# The agent's own system account, as 07-beszel/01-run-chroot.sh makes it.
	if ! getent passwd beszel > /dev/null; then
		adduser --system --group --no-create-home \
			--home /var/lib/beszel-agent --shell /usr/sbin/nologin beszel
	fi
	# StateDirectory= re-creates and re-chowns this on every start; this only
	# makes sure a first start does not have to.
	install -d -m 750 -o beszel -g beszel /var/lib/beszel-agent
	if [ -d /run/systemd/system ]; then
		systemctl daemon-reload || true
		if [ -n "$2" ]; then
			systemctl try-restart beszel-agent.service || true
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
Depends: adduser
Section: admin
Priority: optional
Description: Beszel agent, Gexis Player's system-metrics plugin
 The upstream arm64 release of beszel-agent ($BESZEL_VERSION), pinned by
 checksum, with its unit, its listen check and its plugin manifest. The unit
 is left disabled: the player's settings switch it (ADR-0087, ADR-0107).
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PKG}_${VERSION}_arm64.deb" >/dev/null
echo "/out/${PKG}_${VERSION}_arm64.deb"
