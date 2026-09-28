#!/bin/bash -e
# SPDX-License-Identifier: GPL-3.0-or-later
# ADR-0099: every Debian and Raspberry Pi OS package in the image, with the
# source package and version SOURCE.md's offer refers to.
dpkg-query -W -f='${Package}\t${Version}\t${source:Package}\t${source:Version}\n' \
	| sort > /usr/share/doc/gexis-player/packages.txt
