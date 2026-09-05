#!/bin/bash -e

install -D -m 644 files/output.conf "${ROOTFS_DIR}/etc/alsa/conf.d/output.conf"
