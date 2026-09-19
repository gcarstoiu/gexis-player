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
# They must not run: the panel is still painting. gexis-core drops it when
# the UI reports its first frame, and gexis-splash-backstop.service is the
# safety net if that never arrives.
systemctl mask plymouth-quit.service
systemctl mask plymouth-quit-wait.service
systemctl enable gexis-splash-backstop.service

# Rebuild every initramfs so the plymouth hook and the theme are in it.
# -k all rather than a version we guessed: this image is built for more than
# one Pi and carries more than one kernel.
#
# -u updates an existing initramfs and fails when there is none; -c creates
# one and fails when there is. Which applies depends on whether stage2's
# kernel postinst already ran here, so try the update and fall back rather
# than assuming either.
update-initramfs -u -k all || update-initramfs -c -k all

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
