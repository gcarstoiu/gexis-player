#!/bin/bash -e

# Raspberry Pi OS normally grants the default user passwordless sudo via
# /etc/sudoers.d/010_pi-nopasswd - created by the interactive first-boot
# wizard / userconfig.service, which this image never triggers. firstrun.sh
# (00-run.sh) calls userconf directly instead, with a deliberately empty
# password (SSH-key-only) - so nothing in this image's actual boot path
# ever creates this file.
#
# Verified empirically, not assumed, that this file was never there rather
# than removed by something in this stage: neither this image nor a
# completely stock, unmodified pi-gen Raspberry Pi OS Lite build (the
# -lite artefact stage2/EXPORT_IMAGE always produces alongside ours) ships
# it. Checked both rootfs partitions directly (dd + debugfs) before
# writing this fix.
#
# Unfixable once a card is flashed and running: fixing "the pi user has no
# way to become root" needs the root it lacks. Has to ship in the image.
SUDOERS="${ROOTFS_DIR}/etc/sudoers.d/010_pi-nopasswd"

install -D -m 440 -o 0 -g 0 files/010_pi-nopasswd "${SUDOERS}"

# sudo silently ignores a sudoers.d file with the wrong permissions or
# invalid syntax - it does not error, it just does not grant the access.
# That is exactly the class of failure this investigation started from
# (a locked, password-less account with no other path to root), so it
# gets asserted explicitly rather than trusted because install exited 0.
if [ ! -e "${SUDOERS}" ]; then
	echo "ERROR: ${SUDOERS} missing after install" >&2
	exit 1
fi

ACTUAL_MODE="$(stat -c '%a' "${SUDOERS}")"
if [ "${ACTUAL_MODE}" != "440" ]; then
	echo "ERROR: ${SUDOERS} is mode ${ACTUAL_MODE}, must be 440 - sudo" \
		"silently ignores sudoers.d files with any other permissions" >&2
	exit 1
fi

# Syntax check, not architecture-dependent (sudoers grammar doesn't vary
# by arch or, for a line this simple, by version). Runs inside the target
# chroot, not the host: the pi-gen build container has no visudo/sudo
# package installed on the host side, only in the rootfs being built.
# Verified against both a valid and a deliberately broken file before
# trusting it, rather than assumed from visudo's man page.
if ! on_chroot << EOF
visudo -cf /etc/sudoers.d/010_pi-nopasswd >/dev/null
EOF
then
	echo "ERROR: ${SUDOERS} failed visudo syntax check" >&2
	exit 1
fi
