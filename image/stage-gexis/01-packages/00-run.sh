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
# **No skins in the image** (ADR-0111 decision 9): nothing is installed
# without consent, so neither the per-size packs (gexis-skins-<W>x<H>) nor the
# old gexis-skins go in. The release carries the packs; a device installs its
# own once the user agrees. Devices that already have gexis-skins keep it
# (decision 10) - nothing here touches them.
for deb in "${DEBS}"/*.deb; do
	case "$(basename "${deb}")" in
		gexis-skins_*|gexis-skins-*) echo "not in the image (ADR-0111): $(basename "${deb}")" ;;
		*) cp "${deb}" "${ROOTFS_DIR}/tmp/gexis-debs/" ;;
	esac
done
