#!/bin/bash -e

# The built UI comes from the Makefile's third bind-mount
# (/pi-gen/gexis-ui-dist -> repo root's ui/dist), compiled on the host by
# the `ui` target. ADR-0023's stated cost: "Node is already on the dev
# machine; the image pipeline needs it at build time, not at runtime" - so
# no Node, npm or toolchain ships on the device, and no npm install runs
# under QEMU emulation.
UI_DIST="/pi-gen/gexis-ui-dist"
if [ ! -f "${UI_DIST}/index.html" ]; then
	echo "ERROR: ${UI_DIST}/index.html not found - did 'make ui' run, and is the ui/dist bind-mount wired up in the Makefile?" >&2
	exit 1
fi

install -d -m 755 "${ROOTFS_DIR}/opt/gexis-ui"
rm -rf "${ROOTFS_DIR}/opt/gexis-ui/"*
cp -r "${UI_DIST}/." "${ROOTFS_DIR}/opt/gexis-ui/"

install -D -m 644 files/kiosk.env "${ROOTFS_DIR}/etc/gexis/kiosk.env"
install -D -m 755 files/gexis-kiosk-start \
	"${ROOTFS_DIR}/usr/local/bin/gexis-kiosk-start"
# The page-cache warm-up (ADR-0043's Open, measured 2026-09-19): Chromium
# takes ~15s cold and ~2.7s warm, and the boot spends ~17s blocked on the
# network with the disk idle. This spends that window on reads that have to
# happen anyway.
install -D -m 755 files/gexis-panel-warmup \
	"${ROOTFS_DIR}/usr/local/bin/gexis-panel-warmup"
install -D -m 644 files/gexis-panel-warmup.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-panel-warmup.service"
ln -sf /etc/systemd/system/gexis-panel-warmup.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-panel-warmup.service"

install -D -m 644 files/gexis-kiosk.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-kiosk.service"
install -D -m 644 files/labwc-rc.xml \
	"${ROOTFS_DIR}/home/pi/.config/labwc/rc.xml"

# pi's own config has to belong to pi. The uid/gid are the stock Raspberry
# Pi OS values and are not looked up here, because this runs on the host
# where those names mean the *host's* users, not the image's.
chown -R 1000:1000 "${ROOTFS_DIR}/home/pi/.config"

install -d -m 755 -o 1000 -g 1000 "${ROOTFS_DIR}/var/lib/gexis-kiosk"
