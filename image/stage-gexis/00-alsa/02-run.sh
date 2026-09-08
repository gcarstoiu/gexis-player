#!/bin/bash -e

install -D -m 644 files/output.conf "${ROOTFS_DIR}/etc/alsa/conf.d/output.conf"

# B2, George's decision 2026-09-08: private snd-dummy mixer controls for
# LMS and Bluetooth (volume.py's DummyMixerBridge). Loaded at boot, not
# on demand - squeezelite.service and bluealsa-aplay's override both
# reference these cards by id unconditionally at their own startup.
install -D -m 644 files/gexis-dummy-mixers-load.conf \
	"${ROOTFS_DIR}/etc/modules-load.d/gexis-dummy-mixers.conf"
install -D -m 644 files/gexis-dummy-mixers-modprobe.conf \
	"${ROOTFS_DIR}/etc/modprobe.d/gexis-dummy-mixers.conf"
