#!/bin/bash -e

# No running systemd inside this chroot to talk to (same reasoning as
# 02-renderers/01-run.sh and 03-core/01-run.sh) - symlinked directly
# rather than via systemctl.
#
# multi-user.target, and the image's default target is left alone
# (changed 2026-09-14, Finding 022). This stage used to hang the unit off
# graphical.target and repoint default.target to match. It did not survive
# first boot: our own firstrun.sh calls `userconf` to cancel the setup
# wizard, userconf ends in `cancel-rename`, and cancel-rename runs
# `raspi-config nonint do_boot_behaviour B1` - which is
# `systemctl set-default multi-user.target`. The build wrote the symlink
# correctly and the platform overwrote it on the first boot, so the panel
# never started and the screen showed a console getty instead.
#
# Do not reinstate default.target here. raspi-config owns that setting and
# will reset it again; the unit's own [Install] section carries the full
# reasoning.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
ln -sf /etc/systemd/system/gexis-kiosk.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-kiosk.service"

# Build-time assertions, same discipline as 03-core: catch a stage that
# silently half-ran now, rather than on a panel that boots to nothing 35
# minutes and a reflash later.
for f in \
	"${ROOTFS_DIR}/opt/gexis-ui/index.html" \
	"${ROOTFS_DIR}/etc/gexis/kiosk.env" \
	"${ROOTFS_DIR}/usr/local/bin/gexis-kiosk-start" \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-kiosk.service" \
	"${ROOTFS_DIR}/home/pi/.config/labwc/rc.xml"
do
	if [ ! -e "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done

# The UI is hashed-asset based (vite): index.html is useless without the
# assets directory it references, and a half-copied dist would serve a
# blank page with a 404 in the console - visible only to whoever opens
# devtools on a kiosk.
if [ -z "$(ls -A "${ROOTFS_DIR}/opt/gexis-ui/assets" 2>/dev/null)" ]; then
	echo "ERROR: ${ROOTFS_DIR}/opt/gexis-ui/assets is missing or empty" >&2
	exit 1
fi

# Symlinks resolve only once ${ROOTFS_DIR} is the real root (after boot) -
# see 02-renderers/01-run.sh's comment on why this is -L, not -e.
if [ ! -L "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-kiosk.service" ]; then
	echo "ERROR: multi-user.target.wants/gexis-kiosk.service missing after install" >&2
	exit 1
fi

# Finding 022's second half, asserted rather than trusted: a unit that does
# not take tty1 away from the getty starts, logs "Deactivated successfully"
# and shows nothing. That failure is invisible without a screen, so it is
# checked here where it costs nothing instead of after a 35-minute build and
# a reflash.
if ! grep -q '^Conflicts=getty@tty1\.service$' \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-kiosk.service"; then
	echo "ERROR: gexis-kiosk.service must Conflicts= getty@tty1.service, or labwc exits 0 with tty1 taken" >&2
	exit 1
fi

# The stage no longer writes default.target, and must not: raspi-config
# resets it on every provisioning run (see the comment at the top). If a
# future edit reinstates it, this catches the regression at build time.
if [ -e "${ROOTFS_DIR}/etc/systemd/system/default.target" ] || \
   [ -L "${ROOTFS_DIR}/etc/systemd/system/default.target" ]; then
	echo "ERROR: this stage must not set default.target - raspi-config overwrites it at first boot (Finding 022)" >&2
	exit 1
fi
