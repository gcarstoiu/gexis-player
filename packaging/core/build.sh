#!/bin/sh
# ADR-0107: gexis-core as a Debian package. Runs inside gexis-deb-builder
# (arm64 trixie), with the repository at /src and the output in /out.
#
# The environment is built at its real path, /opt/gexis-core/venv, because a
# venv is not relocatable: its scripts name that path in their first line.
# Every file pip installs is checked against packaging/core/*.lock, the core
# itself included only as a wheel built here from /src/core.
set -eu

VERSION="$1"
VENV=/opt/gexis-core/venv
STAGE=/tmp/stage/gexis-core

rm -rf "$VENV" /tmp/stage /tmp/wheels /tmp/buildenv
python3 -m venv /tmp/buildenv
/tmp/buildenv/bin/pip install -q --no-cache-dir --require-hashes \
	-r /src/packaging/core/build-requirements.lock
# The core's own wheel, with the locked build backend and nothing fetched.
cp -r /src/core /tmp/core-src
rm -rf /tmp/core-src/.pytest_cache /tmp/core-src/build
find /tmp/core-src -name __pycache__ -type d -prune -exec rm -rf {} +
/tmp/buildenv/bin/pip wheel -q --no-cache-dir --no-deps --no-build-isolation \
	-w /tmp/wheels /tmp/core-src

python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --no-cache-dir --require-hashes --no-deps \
	-r /src/packaging/core/requirements.lock
"$VENV/bin/pip" install -q --no-cache-dir --no-deps /tmp/wheels/gexis_core-*.whl
# pip is the one thing in the venv nobody runs on the device; it stays so a
# developer can inspect the environment, and costs ~10 MB.

mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/gexis-core"
cp -a "$VENV" "$STAGE/opt/gexis-core/"

# What the core stage installs besides the environment (image/stage-gexis/
# 03-core), from the same files - one source of truth until the stages go.
F=/src/image/stage-gexis/03-core/files
U="$STAGE/usr/lib/systemd/system"
for unit in gexis-core.service gexis-meter.service gexis-park.service gexis-screen-check.service \
	gexis-uploaded-renderer@.service gexis-uploaded-service@.service gexis-fetch@.service; do
	install -D -m 644 "$F/$unit" "$U/$unit"
done
install -D -m 755 "$F/gexis-run-uploaded" "$STAGE/usr/lib/gexis/gexis-run-uploaded"
install -D -m 755 "$F/gexis-fetch-component" "$STAGE/usr/lib/gexis/gexis-fetch-component"
for plugin in "$F"/plugins/*/; do
	id=$(basename "$plugin")
	install -D -m 644 "${plugin}plugin.json" "$STAGE/usr/share/gexis/plugins/$id/plugin.json"
	[ -f "${plugin}mark.png" ] && install -D -m 644 "${plugin}mark.png" "$STAGE/usr/share/gexis/plugins/$id/mark.png"
done
# The updater (ADR-0105 section 4): standalone, on the system's Python, so it
# outlives the environment it replaces. Its key in both forms: armoured for
# apt's signed-by, binary for gpgv, which checks the channel file.
install -D -m 755 /src/core/updater/gexis-update "$STAGE/usr/lib/gexis/gexis-update"
for unit in gexis-update-check.service gexis-update-check.timer gexis-update-install.service; do
	install -D -m 644 "/src/core/updater/units/$unit" "$U/$unit"
done
install -D -m 644 /src/packaging/keys/gexis-release.asc "$STAGE/usr/share/gexis/keys/gexis-release.asc"
gpg --dearmor < /src/packaging/keys/gexis-release.asc > "$STAGE/usr/share/gexis/keys/gexis-release.gpg"
chmod 644 "$STAGE/usr/share/gexis/keys/gexis-release.gpg"

# A default, placed once: setup, a restore and first boot all write this file.
install -D -m 644 "$F/core.toml" "$STAGE/usr/share/gexis/defaults/core.toml"

cat > "$STAGE/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
# ADR-0107: gexis-core. Idempotent; never overwrites what the device wrote.
set -e
[ "$1" = configure ] || exit 0

# The default config, only where there is none (setup, restore and first
# boot write it; an update must not undo them).
if [ ! -e /etc/gexis/core.toml ]; then
	install -D -m 644 /usr/share/gexis/defaults/core.toml /etc/gexis/core.toml
fi

# The group that may connect to the plugin socket (ADR-0084 as amended).
getent group gexis-plugins >/dev/null || addgroup --system gexis-plugins
if getent passwd pi >/dev/null; then adduser pi gexis-plugins >/dev/null; fi

# The pictures and backups shares (ADR-0049, ADR-0083), the stock user's.
install -d -o 1000 -g 1000 -m 2775 /var/lib/gexis-core/pictures /var/lib/gexis-core/backups

if [ -z "$2" ]; then
	# First install: on at boot, as the image has always had them. An update
	# leaves the enable state alone.
	# Not `|| true`: an enable that fails must fail the install, not leave a
	# device that does not start its core. Only a system without systemctl
	# at all (a test container) skips it, and says so.
	if command -v systemctl >/dev/null; then
		systemctl enable gexis-core.service gexis-meter.service gexis-park.service
	else
		echo "gexis-core: no systemctl here; units not enabled" >&2
	fi
fi
# The daily check only reads the channel and reports (installing is a separate
# unit, ADR-0105 section 4), so it is on for every device - one updating from
# a release that had none included, which a first-install-only enable missed.
# Started too, on a running system: enabled alone waits for the next boot, and a
# device that updates rather than reboots had no nightly check (found on
# sofa-pi, 2026-09-30: enabled, inactive, no next run). A timer starting is
# harmless - it only schedules.
# ADR-0109 as amended 2026-10-04: a new screen is switched to before the
# panel starts. On for every device, an updated one included - it only acts
# at a start.
if command -v systemctl >/dev/null; then
	systemctl enable gexis-screen-check.service
	systemctl enable gexis-update-check.timer
	if [ -d /run/systemd/system ]; then systemctl start gexis-update-check.timer; fi
fi
# Restarts are the updater's (the core may be the one running it); only tell
# a running systemd the unit files changed.
if [ -d /run/systemd/system ]; then systemctl daemon-reload || true; fi
POSTINST
chmod 755 "$STAGE/DEBIAN/postinst"
PYV=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
NEXT=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1] + 1}")')
cat > "$STAGE/DEBIAN/control" <<EOF
Package: gexis-core
Version: $VERSION
Architecture: arm64
Maintainer: Gexis Player <noreply@github.com>
Depends: python3 (>= $PYV), python3 (<< $NEXT), adduser, gpgv
Section: sound
Priority: optional
Description: Gexis Player's core, in its own Python environment
 Arbitration, the state and settings API, and the panel's server, with every
 Python dependency pinned by hash (ADR-0107).
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-core_${VERSION}_arm64.deb" >/dev/null
echo "/out/gexis-core_${VERSION}_arm64.deb"
