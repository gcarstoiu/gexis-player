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
install -m 644 files/theme/still.png "${THEME_DIR}/"

# A still, not an animation (George, 2026-09-20). The 100-frame sequence and
# the assertion that exactly 100 of them landed are both gone; what has to be
# true now is smaller and is checked here rather than discovered on a panel.
if [ ! -s "${THEME_DIR}/still.png" ]; then
	echo "ERROR: the splash still is missing or empty" >&2
	exit 1
fi

# 1280x800 exactly, or plymouth letterboxes it and the seam with swaybg's
# wallpaper - the same file - becomes visible. Read from the PNG's IHDR
# rather than trusting the filename: bytes 16-23 are width and height, big
# endian. `od` is on the Lite image; `xxd` is not (see HANDOFF).
dims="$(od -An -tu4 -j16 -N8 --endian=big "${THEME_DIR}/still.png" | tr -s ' ')"
if [ "${dims}" != " 1280 800" ]; then
	echo "ERROR: the splash still is${dims} px, expected 1280 800" >&2
	exit 1
fi

# The kernel console moves off the VT the panel owns. This is the fix that
# actually works, found 2026-09-19 after clearing tty1 did not: the image
# ships `console=tty1`, so the kernel - and anything inheriting the console -
# writes to the very screen plymouth and labwc are using. George saw daemon
# output ("comet", from the LMS CometD connection) appear the moment the
# splash released the screen. Clearing tty1 cannot help, because whatever
# writes next lands straight back on it.
#
# tty3 is a VT nothing ever displays. `console=serial0` stays first, so a
# serial cable remains the real diagnostic path.
sed -i 's/\bconsole=tty1\b/console=tty3/' "${CMDLINE}"

# The rest of the text has its own switch each; see ADR-0043's table.
# `splash` is what tells plymouth to show a theme at all.
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
install -D -m 644 files/gexis-splash-backstop.timer \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-splash-backstop.timer"

# The helper that holds the boot screen across the gap between plymouth
# releasing the GPU and labwc drawing (ADR-0043's amendment, part 1). It sets
# the VT's graphics mode and paints the still into the framebuffer;
# gexis-kiosk.service calls it from ExecStartPre and puts the console back
# from ExecStopPost.
install -D -m 755 files/gexis-splash-fb \
	"${ROOTFS_DIR}/usr/local/bin/gexis-splash-fb"

# It is Python and it runs in the boot path, so a syntax error would show up
# as a silently missing boot screen. Compile it here instead.
if command -v python3 >/dev/null; then
	python3 -m py_compile "${ROOTFS_DIR}/usr/local/bin/gexis-splash-fb" || {
		echo "ERROR: gexis-splash-fb does not compile" >&2
		exit 1
	}
	rm -rf "${ROOTFS_DIR}/usr/local/bin/__pycache__"
fi

# The compositor's wallpaper, for the gap between the splash ending and
# Chromium's first paint (ADR-0043's Open). `--retain-splash` does not
# survive labwc's modeset on this hardware - George watched it go straight
# to black on 2026-09-19 - so something has to be behind the compositor or
# the gap is black.
#
# **It is the same file as the splash.** Before 2026-09-20 the splash was a
# 100-frame animation and this was its rest frame, chosen because it was what
# the screen showed for most of a boot. Now that the splash is a still, the
# wallpaper and the splash are one image, and the handover cannot show a cut
# between two different pictures - only, still, a gap where neither is drawn.
install -D -m 644 files/theme/still.png \
	"${ROOTFS_DIR}/usr/share/gexis/panel-background.png"

# The two must not drift apart. They are installed from one source file, so
# this can only fail if somebody edits one of the destinations - which is
# exactly the kind of thing that gets done on a device and then forgotten.
if ! cmp -s "${THEME_DIR}/still.png" \
	"${ROOTFS_DIR}/usr/share/gexis/panel-background.png"; then
	echo "ERROR: the splash still and the panel wallpaper differ" >&2
	exit 1
fi

# Build-time assertions. A boot that shows text is a defect nobody will
# report as one - they will just see it - so fail here instead.
grep -q 'console=tty3' "${CMDLINE}" || {
	echo "ERROR: the kernel console is still on the panel's VT" >&2
	exit 1
}
grep -q 'console=tty1' "${CMDLINE}" && {
	echo "ERROR: console=tty1 survived; the panel would show kernel output" >&2
	exit 1
}

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
