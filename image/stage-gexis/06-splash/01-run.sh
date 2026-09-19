#!/bin/bash -e

# The boot animation, and a boot with no text at all (ADR-0043).
#
# Host-side half: install the theme and edit the two boot files. The chroot
# half (02-run-chroot.sh) selects the theme and rebuilds the initramfs,
# because both need the target's own plymouth and initramfs tooling.
#
# Finding 038 measured what this covers: 19.7s from power to
# multi-user.target, with gexis-kiosk.service starting at 18.26s.

THEME_DIR="${ROOTFS_DIR}/usr/share/plymouth/themes/gexis"
CMDLINE="${ROOTFS_DIR}/boot/firmware/cmdline.txt"
CONFIG="${ROOTFS_DIR}/boot/firmware/config.txt"

install -d -m 755 "${THEME_DIR}"
install -m 644 files/theme/gexis.plymouth "${THEME_DIR}/"
install -m 644 files/theme/gexis.script "${THEME_DIR}/"
install -m 644 files/theme/boot-*.png "${THEME_DIR}/"

frames="$(find "${THEME_DIR}" -name 'boot-*.png' | wc -l)"
if [ "${frames}" -ne 100 ]; then
	echo "ERROR: expected 100 animation frames, installed ${frames}" >&2
	exit 1
fi

# The text has six sources and each needs its own switch; see ADR-0043's
# table. `splash` is what tells plymouth to show a theme at all.
#
# console=tty1 is deliberately left alone: the serial and VT consoles stay
# for diagnosis over SSH and a cable. What changes is that nothing writes to
# the panel while it boots.
for option in \
	quiet \
	loglevel=0 \
	logo.nologo \
	vt.global_cursor_default=0 \
	systemd.show_status=false \
	plymouth.ignore-serial-consoles \
	splash
do
	if ! grep -qw -- "${option}" "${CMDLINE}"; then
		sed -i "$ s#\$# ${option}#" "${CMDLINE}"
	fi
done

# The firmware's rainbow square, drawn before the kernel is even running -
# the one thing plymouth cannot cover.
if ! grep -q '^disable_splash=1' "${CONFIG}"; then
	printf '\n# ADR-0043: no rainbow square before the boot animation.\ndisable_splash=1\n' \
		>> "${CONFIG}"
fi

# Plymouth normally tears itself down when multi-user.target is reached,
# which is ~2s before the panel has anything to show. It is masked in the
# chroot half, and gexis-kiosk.service quits it itself with
# `--retain-splash` just before labwc starts (ADR-0043 §3, corrected
# 2026-09-19: plymouth is DRM master, so holding it any longer than that
# stops the compositor opening the GPU at all).
#
# The backstop unit stays for the case where the kiosk never starts: without
# it the animation would loop forever on a device with no keyboard.
install -D -m 644 files/gexis-splash-backstop.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-splash-backstop.service"

# The compositor's wallpaper, for the gap between the splash ending and
# Chromium's first paint (ADR-0043's Open). `--retain-splash` does not
# survive labwc's modeset on this hardware - George watched it go straight
# to black on 2026-09-19 - so something has to be behind the compositor or
# the gap is black.
#
# The pulse's rest state (its last frame, which is pixel-identical to its
# first): that is what is on screen for almost all of a boot, so the
# wallpaper continues the picture rather than cutting to a different moment
# of it.
STILL=boot-0100.png
install -D -m 644 "files/theme/${STILL}" \
	"${ROOTFS_DIR}/usr/share/gexis/panel-background.png"

# Build-time assertions. A boot that shows text is a defect nobody will
# report as one - they will just see it - so fail here instead.
for option in quiet splash logo.nologo; do
	grep -qw -- "${option}" "${CMDLINE}" || {
		echo "ERROR: ${option} missing from cmdline.txt" >&2
		exit 1
	}
done
grep -q '^disable_splash=1' "${CONFIG}" || {
	echo "ERROR: disable_splash=1 missing from config.txt" >&2
	exit 1
}
