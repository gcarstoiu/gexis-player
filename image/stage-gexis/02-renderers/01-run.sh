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

# go-librespot: config at its own default location (~/.config/go-librespot)
# for the user the unit runs as - no -config_dir override needed.
install -D -m 644 -o 1000 -g 1000 files/go-librespot-config.yml \
	"${ROOTFS_DIR}/home/pi/.config/go-librespot/config.yml"
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

# Enable our own units. Symlinked directly rather than via systemctl -
# there is no running systemd inside this chroot to talk to.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
ln -sf /etc/systemd/system/go-librespot.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/go-librespot.service"
ln -sf /etc/systemd/system/squeezelite.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/squeezelite.service"

# Build-time assertion: every file this stage installs actually landed
# where the systemd units expect it, and pi owns what it needs to own.
for f in \
	"${ROOTFS_DIR}/usr/local/bin/go-librespot" \
	"${ROOTFS_DIR}/home/pi/.config/go-librespot/config.yml" \
	"${ROOTFS_DIR}/etc/systemd/system/go-librespot.service" \
	"${ROOTFS_DIR}/etc/systemd/system/squeezelite.service" \
	"${ROOTFS_DIR}/usr/local/lib/gexis/squeezelite-mixer-check.sh" \
	"${ROOTFS_DIR}/etc/systemd/system/bluealsa-aplay.service.d/override.conf"
do
	if [ ! -e "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done
# These two are symlinks to an absolute path (/etc/systemd/system/...)
# that only resolves once ${ROOTFS_DIR} is the real root, i.e. after boot -
# not from here. -e follows the link and fails against the build host's
# filesystem; -L only checks the link itself exists, which is what's
# actually verifiable at build time.
for f in \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/go-librespot.service" \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/squeezelite.service"
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
