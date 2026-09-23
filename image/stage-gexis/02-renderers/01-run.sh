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

# Content-addressed cache first, network on a miss (ADR-0042). Still
# verified either way; the cache is optional and absent by default.
# shellcheck source=../fetch-cached.sh
. /pi-gen/stage-gexis/fetch-cached.sh

fetch_cached "${GO_LIBRESPOT_URL}" "${GO_LIBRESPOT_SHA256}" \
	"${WORK}/${GO_LIBRESPOT_ASSET}"

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

# The unit reads the player's name from here (ADR-0048 §1). Shipped with the
# build-time name rather than left to the unit's fallback, so the file the
# settings screen rewrites always exists and one place holds the answer.
install -d -m 755 "${ROOTFS_DIR}/etc/gexis"
printf 'GEXIS_DEVICE_NAME=gexis\n' \
	> "${ROOTFS_DIR}/etc/gexis/device-name.env"
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

# BlueZ's adapter name comes from /etc/machine-info's PRETTY_HOSTNAME,
# which is where the settings screen writes it (ADR-0048 §4a).
#
# **main.conf's `Name =` does nothing**, and this stage set it for months.
# The shipped file says so two lines above the setting itself - "The plugin
# 'hostname' is loaded by default and overides the Name set here so consider
# modifying /etc/machine-info with variable PRETTY_HOSTNAME=<NewName>
# instead" - and the check below asserted only that the sed had matched,
# which it always had. It looked right because the hostname was the same
# string. Verified on the device 2026-09-21: with `Name = SofaPi` in
# main.conf and no PRETTY_HOSTNAME, the adapter reported `sofapi`; with
# PRETTY_HOSTNAME it reported `SofaPi`. See docs/LESSONS.md.
install -d -m 755 "${ROOTFS_DIR}/etc"
printf 'PRETTY_HOSTNAME=gexis\n' > "${ROOTFS_DIR}/etc/machine-info"

# Bluetooth pairing setup (ADR-0024): unblock the rfkill soft-block
# main.conf can't override on its own, power on, and register a
# PIN-free pairing agent. See the two units' own comments.
install -D -m 755 files/gexis-bluetooth-setup.sh \
	"${ROOTFS_DIR}/usr/local/lib/gexis/bluetooth-setup.sh"
install -D -m 644 files/gexis-bluetooth-setup.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-bluetooth-setup.service"
# `gexis-bt-agent.service` is gone (ADR-0045). It ran `bt-agent
# --capability=NoInputNoOutput` from bluez-tools, which answers the pairing
# handshake on its own console and has no route to a screen - so pairing
# could never be confirmed by anyone. `gexis_core.bluetooth_agent` registers
# an `org.bluez.Agent1` of our own with `DisplayYesNo`, which is what makes
# BlueZ produce a six-digit code at all.

# Enable our own units. Symlinked directly rather than via systemctl -
# there is no running systemd inside this chroot to talk to.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
ln -sf /etc/systemd/system/go-librespot.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/go-librespot.service"
ln -sf /etc/systemd/system/squeezelite.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/squeezelite.service"
ln -sf /etc/systemd/system/gexis-bluetooth-setup.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bluetooth-setup.service"

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
	"${ROOTFS_DIR}/etc/gexis/device-name.env"
do
	if [ ! -e "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done
# ADR-0048 §1: the name lives in the env file, and a unit that stopped
# reading it would silently pin every device to one name again - visible
# only as "the rename did nothing", which is the hardest kind to trace.
if ! grep -q 'EnvironmentFile=-/etc/gexis/device-name.env' \
	"${ROOTFS_DIR}/etc/systemd/system/squeezelite.service"; then
	echo "ERROR: squeezelite.service no longer reads /etc/gexis/device-name.env" >&2
	exit 1
fi
if ! grep -q -- '-n \${GEXIS_DEVICE_NAME}' \
	"${ROOTFS_DIR}/etc/systemd/system/squeezelite.service"; then
	echo "ERROR: squeezelite.service's -n is not the device name variable" >&2
	exit 1
fi

# The name BlueZ will actually use. Checked as a value, not as a
# substitution: the line this replaced asserted that main.conf said
# `Name = gexis`, which was true and meant nothing (docs/LESSONS.md).
if ! grep -q "^PRETTY_HOSTNAME=gexis$" "${ROOTFS_DIR}/etc/machine-info"; then
	echo "ERROR: /etc/machine-info does not carry the device name" >&2
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
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bluetooth-setup.service"
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
