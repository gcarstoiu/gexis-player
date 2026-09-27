#!/bin/bash -e
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ADR-0096: letterbox the 1280x720 animated packs into this 1280x800 panel.
# Runs inside the target because it needs python3 and Pillow (python3-pil is
# in this stage's 00-packages); 01-run.sh fetched and verified the packs and
# left them in skins-letterbox/<name>.

PEPPY=/opt/gexis-peppy
for staged in "${PEPPY}"/skins-letterbox/*/; do
	name="$(basename "${staged}")"
	out="${PEPPY}/skins/${name}/templates/1280x800"
	mkdir -p "$(dirname "${out}")"
	python3 "${PEPPY}/letterbox.py" "${staged}" "${out}"
	# A letterboxed pack is 1280x800 in every full-frame picture: say so, or
	# the script's own check is the only one there is.
	if [ ! -f "${out}/meters.txt" ]; then
		echo "ERROR: ${name} was not letterboxed" >&2
		exit 1
	fi
done
rm -rf "${PEPPY}/skins-letterbox"
for name in g5-turntables g5-tape g5-cassette t1800; do
	if [ ! -f "${PEPPY}/skins/${name}/templates/1280x800/meters.txt" ]; then
		echo "ERROR: ${name} is not installed" >&2
		exit 1
	fi
done
