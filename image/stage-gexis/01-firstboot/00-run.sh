#!/bin/bash -e

CMDLINE="${ROOTFS_DIR}/boot/firmware/cmdline.txt"
FIRSTRUN="${ROOTFS_DIR}/boot/firmware/firstrun.sh"

install -D -m 755 files/firstrun.sh "${FIRSTRUN}"

if ! grep -q 'systemd.run=' "${CMDLINE}"; then
	sed -i '$ s#$# systemd.run=/boot/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target#' "${CMDLINE}"
fi

# Build-time assertion: a card with no working first-boot path is exactly
# the defect that shipped undetected in the first Phase 0 build (found only
# by hand-inspecting a flashed card). Fail here, not on someone's SD card.
if [ ! -s "${FIRSTRUN}" ]; then
	echo "ERROR: ${FIRSTRUN} missing or empty" >&2
	exit 1
fi
if ! grep -q 'systemd.run=/boot/firstrun.sh' "${CMDLINE}"; then
	echo "ERROR: cmdline.txt does not invoke firstrun.sh" >&2
	exit 1
fi
for stale in meta-data network-config user-data; do
	if [ -e "${ROOTFS_DIR}/boot/firmware/${stale}" ]; then
		echo "ERROR: stale cloud-init template '${stale}' present on boot partition" >&2
		echo "       (ENABLE_CLOUD_INIT should be 0 in image/config)" >&2
		exit 1
	fi
done
