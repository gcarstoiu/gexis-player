#!/bin/bash -e

# ADR-0107: the image is built from our packages - the same bytes an update
# brings. `make image` builds them into packaging/out/, mounted here.
DEBS=/pi-gen/gexis-debs
players=( "${DEBS}"/gexis-player_*.deb )
if [ "${#players[@]}" -ne 1 ] || [ ! -f "${players[0]}" ]; then
	echo "ERROR: expected exactly one gexis-player package in ${DEBS}, found ${#players[@]} - run 'make packages' from a clean packaging/out" >&2
	exit 1
fi
rm -rf "${ROOTFS_DIR}/tmp/gexis-debs"
install -d "${ROOTFS_DIR}/tmp/gexis-debs"
cp "${DEBS}"/*.deb "${ROOTFS_DIR}/tmp/gexis-debs/"
