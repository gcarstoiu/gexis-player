#!/bin/bash -e

# The build stamp (the image, not the release: the release is gexis-player's
# version, which an update changes and this does not).
install -d -m 755 "${ROOTFS_DIR}/etc/gexis"
printf 'version=%s\nbuilt=%s\n' "${IMG_SUFFIX#-}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
	> "${ROOTFS_DIR}/etc/gexis/image.info"
chmod 644 "${ROOTFS_DIR}/etc/gexis/image.info"

# What gexis-system's postinst must have done to the boot files.
CMDLINE="${ROOTFS_DIR}/boot/firmware/cmdline.txt"
for option in cgroup_enable=memory console=tty3 quiet splash logo.nologo; do
	grep -qw -- "${option}" "${CMDLINE}" || { echo "ERROR: ${option} missing from cmdline.txt" >&2; exit 1; }
done
if grep -qw 'console=tty1' "${CMDLINE}"; then
	echo "ERROR: console=tty1 survived; the panel would show kernel output" >&2; exit 1
fi
grep -q '^disable_splash=1' "${ROOTFS_DIR}/boot/firmware/config.txt" \
	|| { echo "ERROR: disable_splash=1 missing from config.txt" >&2; exit 1; }
