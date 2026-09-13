#!/bin/bash -e

# No running systemd inside this chroot to talk to (same reasoning as
# 02-renderers/01-run.sh and 03-core/01-run.sh) - symlinked directly
# rather than via systemctl.
#
# graphical.target, not multi-user.target, and the default target is moved
# to match: this is the one unit on the image that needs a graphical
# session, and hanging it off multi-user would mean either starting it
# before seats exist or inventing an ordering dependency that
# graphical.target already expresses.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system/graphical.target.wants"
ln -sf /etc/systemd/system/gexis-kiosk.service \
	"${ROOTFS_DIR}/etc/systemd/system/graphical.target.wants/gexis-kiosk.service"
ln -sf /lib/systemd/system/graphical.target \
	"${ROOTFS_DIR}/etc/systemd/system/default.target"

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
for f in \
	"${ROOTFS_DIR}/etc/systemd/system/graphical.target.wants/gexis-kiosk.service" \
	"${ROOTFS_DIR}/etc/systemd/system/default.target"
do
	if [ ! -L "${f}" ]; then
		echo "ERROR: ${f} missing after install" >&2
		exit 1
	fi
done
