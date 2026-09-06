#!/bin/bash -e

# go-librespot has no Debian package (verified against packages.debian.org
# - empty search result) and ships only as a GitHub release tarball. Pinned
# the same way peppyalsa is pinned: an exact version and a checksum
# verified independently before trusting it, not just copied from the API.
#
# Downloaded and verified on the host, not inside the chroot: this is a
# plain HTTPS GET and a sha256sum, native x86_64 work with nothing to gain
# from doing it under qemu emulation.
GO_LIBRESPOT_VERSION="v0.9.0"
GO_LIBRESPOT_ASSET="go-librespot_linux_arm64.tar.gz"
GO_LIBRESPOT_URL="https://github.com/devgianlu/go-librespot/releases/download/${GO_LIBRESPOT_VERSION}/${GO_LIBRESPOT_ASSET}"
GO_LIBRESPOT_SHA256="79b80bb3723b7973165d2d94c428676b8582780aeca7c54694589206ab741e91"

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

curl -fsSL -o "${WORK}/${GO_LIBRESPOT_ASSET}" "${GO_LIBRESPOT_URL}"

echo "${GO_LIBRESPOT_SHA256}  ${WORK}/${GO_LIBRESPOT_ASSET}" | sha256sum -c -

tar -xzf "${WORK}/${GO_LIBRESPOT_ASSET}" -C "${WORK}" go-librespot

install -D -m 755 "${WORK}/go-librespot" "${ROOTFS_DIR}/usr/local/bin/go-librespot"

# go-librespot: config under systemd's StateDirectory= (/var/lib/go-
# librespot), not ~/.config - see go-librespot.service for why. systemd
# (re-)chowns this to User=/Group= on every start regardless of what
# ownership this install leaves it at, so -o/-g here is defence in depth,
# not load-bearing.
install -D -m 644 -o 1000 -g 1000 files/go-librespot-config.yml \
	"${ROOTFS_DIR}/var/lib/go-librespot/config.yml"
install -D -m 644 files/go-librespot.service \
	"${ROOTFS_DIR}/etc/systemd/system/go-librespot.service"

# squeezelite: package ships a SysV init script, not a systemd unit -
# criterion 2's ExecStartPre guard needs a real one, written from scratch.
install -D -m 644 files/squeezelite.service \
	"${ROOTFS_DIR}/etc/systemd/system/squeezelite.service"
install -D -m 755 files/squeezelite-mixer-check.sh \
	"${ROOTFS_DIR}/usr/local/lib/gexis/squeezelite-mixer-check.sh"

# bluealsa-aplay: bluez-alsa-utils already ships and auto-enables this
# unit (WantedBy=bluetooth.target); override its ExecStart rather than
# replace the unit, per upstream's own documented customisation path.
install -D -m 644 files/bluealsa-aplay-override.conf \
	"${ROOTFS_DIR}/etc/systemd/system/bluealsa-aplay.service.d/override.conf"

# bluealsa (the daemon): same override pattern, dropping the a2dp-source
# profile its shipped default advertises unasked (see the override's own
# comment - confirmed running on gexis, not something we configured).
install -D -m 644 files/bluealsa-override.conf \
	"${ROOTFS_DIR}/etc/systemd/system/bluealsa.service.d/override.conf"

# BlueZ's adapter name defaults to the system hostname (already "gexis"
# via firstrun.sh) unless main.conf's Name= is set - but relying on that
# implicitly is exactly the kind of thing ADR-0022 wants made explicit
# everywhere a device name shows up (mDNS, Spotify, Bluetooth). Set
# explicitly here rather than trusted as an implicit side effect.
# Targeted sed on the vendor-shipped file, not a full replacement - it's
# ~250 lines of reference documentation for settings this project
# doesn't otherwise touch, and replacing it wholesale would bury that
# for no gain here.
sed -i 's/^#Name = BlueZ$/Name = gexis/' "${ROOTFS_DIR}/etc/bluetooth/main.conf"

# Bluetooth pairing setup (ADR-0024): unblock the rfkill soft-block
# main.conf can't override on its own, power on, and register a
# PIN-free pairing agent. See the two units' own comments.
install -D -m 755 files/gexis-bluetooth-setup.sh \
	"${ROOTFS_DIR}/usr/local/lib/gexis/bluetooth-setup.sh"
install -D -m 644 files/gexis-bluetooth-setup.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-bluetooth-setup.service"
install -D -m 644 files/gexis-bt-agent.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-bt-agent.service"

# Enable our own units. Symlinked directly rather than via systemctl -
# there is no running systemd inside this chroot to talk to.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
ln -sf /etc/systemd/system/go-librespot.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/go-librespot.service"
ln -sf /etc/systemd/system/squeezelite.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/squeezelite.service"
ln -sf /etc/systemd/system/gexis-bluetooth-setup.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bluetooth-setup.service"
ln -sf /etc/systemd/system/gexis-bt-agent.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bt-agent.service"

# Build-time assertion: every file this stage installs actually landed
# where the systemd units expect it, and pi owns what it needs to own.
for f in \
	"${ROOTFS_DIR}/usr/local/bin/go-librespot" \
	"${ROOTFS_DIR}/var/lib/go-librespot/config.yml" \
	"${ROOTFS_DIR}/etc/systemd/system/go-librespot.service" \
	"${ROOTFS_DIR}/etc/systemd/system/squeezelite.service" \
	"${ROOTFS_DIR}/usr/local/lib/gexis/squeezelite-mixer-check.sh" \
	"${ROOTFS_DIR}/etc/systemd/system/bluealsa-aplay.service.d/override.conf" \
	"${ROOTFS_DIR}/etc/systemd/system/bluealsa.service.d/override.conf" \
	"${ROOTFS_DIR}/usr/local/lib/gexis/bluetooth-setup.sh" \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-bluetooth-setup.service" \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-bt-agent.service"
do
	if [ ! -e "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done
# The sed above must have actually matched - a missed pattern (e.g. if
# the vendor file's default comment text ever changes upstream) fails
# silently otherwise, leaving the adapter name on whatever bluetoothd's
# hostname-derived fallback happens to be.
if ! grep -q "^Name = gexis$" "${ROOTFS_DIR}/etc/bluetooth/main.conf"; then
	echo "ERROR: main.conf's Name= substitution did not take - pattern may have changed upstream" >&2
	exit 1
fi
# These two are symlinks to an absolute path (/etc/systemd/system/...)
# that only resolves once ${ROOTFS_DIR} is the real root, i.e. after boot -
# not from here. -e follows the link and fails against the build host's
# filesystem; -L only checks the link itself exists, which is what's
# actually verifiable at build time.
#
# -L is weaker than it looks: it confirms the symlink is there, not that
# it points anywhere real. A typo'd target would still pass this. The
# full check - does this symlink actually resolve - is only completable
# on a booted system (tier 3, gexis), not here. Do not "fix" this back
# to -e; that's the exact failure this comment exists to prevent.
for f in \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/go-librespot.service" \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/squeezelite.service" \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bluetooth-setup.service" \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bt-agent.service"
do
	if [ ! -L "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done
if [ ! -x "${ROOTFS_DIR}/usr/local/bin/go-librespot" ]; then
	echo "ERROR: go-librespot binary not executable" >&2
	exit 1
fi
if [ ! -x "${ROOTFS_DIR}/usr/local/lib/gexis/bluetooth-setup.sh" ]; then
	echo "ERROR: gexis bluetooth-setup.sh not executable" >&2
	exit 1
fi
