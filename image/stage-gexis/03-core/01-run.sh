#!/bin/bash -e

# No running systemd inside this chroot to talk to (same reasoning as
# 02-renderers/01-run.sh) - symlinked directly rather than via systemctl.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
ln -sf /etc/systemd/system/gexis-core.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-core.service"
# Phase 5: without this the Peppy screen gets no levels on a fresh image -
# until 2026-09-16 it had only ever been started by hand.
ln -sf /etc/systemd/system/gexis-meter.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-meter.service"

# Build-time assertion: the venv actually landed and the src copy this
# stage used to install from didn't linger (00-run-chroot.sh's rm -rf
# ran, so this also catches that script silently failing to reach it).
#
# bin/pip, not bin/python: venv's bin/python is a *relative* symlink to
# bin/python3, which is itself an *absolute* symlink to
# /usr/bin/python3 - the same "resolves only once ${ROOTFS_DIR} is the
# real root" trap the symlink checks below already comment on, just one
# hop deeper and easy to miss on a first pass (found the hard way: this
# check failed a real, successful install). bin/pip is a plain text
# script, not a symlink, so -e on it means what it looks like it means.
for f in \
	"${ROOTFS_DIR}/opt/gexis-core/venv/bin/pip" \
	"${ROOTFS_DIR}/etc/gexis/core.toml" \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-core.service"
do
	if [ ! -e "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done
if [ -e "${ROOTFS_DIR}/opt/gexis-core/src" ]; then
	echo "ERROR: ${ROOTFS_DIR}/opt/gexis-core/src should have been removed after install" >&2
	exit 1
fi
# Symlinks resolve only once ${ROOTFS_DIR} is the real root (after boot) -
# see 02-renderers/01-run.sh's comment on why this is -L, not -e.
for f in \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-core.service"
do
	if [ ! -L "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done

# And the one that must NOT be there: ADR-0045 removed it, and a warm build
# keeps whatever an earlier one wrote until it is deleted.
for f in \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-bluetooth-trust.service" \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bluetooth-trust.service"
do
	if [ -e "${f}" ] || [ -L "${f}" ]; then
		echo "ERROR: ${f} still present; ADR-0045 removed it" >&2
		exit 1
	fi
done
mask_target="$(readlink "${ROOTFS_DIR}/etc/systemd/system/alsa-restore.service" 2>/dev/null || true)"
if [ "${mask_target}" != "/dev/null" ]; then
	echo "ERROR: alsa-restore.service mask missing or wrong (got '${mask_target}')" >&2
	exit 1
fi
