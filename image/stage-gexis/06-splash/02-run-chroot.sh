#!/bin/bash -e

# Selecting the theme and rebuilding the initramfs, in the target (ADR-0043).
#
# Both halves have to happen here rather than on the host: the alternatives
# system and update-initramfs are the target's, and the initramfs has to be
# built against the target's own kernel modules.
#
# Plymouth is started FROM the initramfs on purpose. This image sets
# auto_initramfs=1 and ships one (Finding 038 - which corrects an earlier
# claim in this session that Raspberry Pi OS has no initramfs), so the
# animation can begin a second or two after power rather than after the root
# mount at ~3.97s.

plymouth-set-default-theme gexis

selected="$(plymouth-set-default-theme)"
if [ "${selected}" != "gexis" ]; then
	echo "ERROR: default plymouth theme is '${selected}', not gexis" >&2
	exit 1
fi

# Plymouth ships units that quit the splash as soon as the system is up.
# They must not run: the panel is still ~2s from painting then, and plymouth
# has to be ended in a controlled place - gexis-kiosk.service does it, just
# before labwc, because plymouth holds DRM until it goes. The backstop timer
# is the net for a kiosk that never starts at all.
systemctl mask plymouth-quit.service
systemctl mask plymouth-quit-wait.service
systemctl enable gexis-splash-backstop.timer

# Rebuild every initramfs so the plymouth hook is in it. -k all rather than a
# version we guessed: this image carries two kernels, `+rpt-rpi-v8` for the
# Pi 4 and `+rpt-rpi-2712` for the Pi 5, and the raspi-firmware post-update
# hook copies each to /boot/firmware/initramfs8 and initramfs_2712.
#
# **Raspberry Pi OS ships `update_initramfs=no`**, so update-initramfs prints
# "Not updating initramfs." and does nothing at all. Found on 2026-09-19 by
# this stage's own assertion, on the first build after it was written: the
# rebuild appeared to succeed and the initramfs was still the one stage2
# produced, without plymouth in it.
#
# The setting is deliberate upstream - it stops an apt kernel upgrade
# rebuilding the initramfs behind the raspi-firmware hook's back - so it is
# turned on for this one rebuild and put back exactly as it was found.
CONF=/etc/initramfs-tools/update-initramfs.conf
ORIGINAL="$(grep '^update_initramfs=' "${CONF}" || echo 'update_initramfs=no')"

sed -i 's/^update_initramfs=.*/update_initramfs=all/' "${CONF}"
update-initramfs -u -k all
sed -i "s/^update_initramfs=.*/${ORIGINAL}/" "${CONF}"

grep -q "^${ORIGINAL}\$" "${CONF}" || {
	echo "ERROR: failed to restore ${CONF} to '${ORIGINAL}'" >&2
	exit 1
}

# An initramfs that is missing, empty or missing its plymouth hook does not
# fail the build on its own - it produces a device that shows no animation,
# or does not boot at all. Both are worth failing here instead.
shopt -s nullglob
built=(/boot/firmware/initramfs*)
if [ ${#built[@]} -eq 0 ]; then
	echo "ERROR: no initramfs was produced; the splash could not start early" >&2
	exit 1
fi

for image in "${built[@]}"; do
	if [ ! -s "${image}" ]; then
		echo "ERROR: ${image} is empty after update-initramfs" >&2
		exit 1
	fi
	# lsinitramfs comes with initramfs-tools, which is what just ran - but
	# the check is skipped rather than failed if it is somehow absent, since
	# a missing tool is not evidence of a missing hook.
	if command -v lsinitramfs >/dev/null; then
		if ! lsinitramfs "${image}" 2>/dev/null | grep -q plymouth; then
			echo "ERROR: plymouth is not in ${image}; the splash would start late" >&2
			exit 1
		fi
	fi
done
