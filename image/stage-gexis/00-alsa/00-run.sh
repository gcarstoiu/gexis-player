#!/bin/bash -e
# 01-run-chroot.sh builds peppyalsa *inside* the chroot, where this stage's
# own files/ directory is not mounted. Put the patch somewhere it can reach.
# Runs before it: pi-gen orders by filename, and "00-run.sh" sorts before
# "01-run-chroot.sh".
install -D -m 644 files/peppyalsa-one-write-per-frame.patch \
	"${ROOTFS_DIR}/tmp/peppyalsa-one-write-per-frame.patch"
