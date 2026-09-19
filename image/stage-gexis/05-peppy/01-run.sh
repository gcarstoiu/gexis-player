#!/bin/bash -e

# The Peppy screen's engines and skins (ADR-0026, Phase 5).
#
# Vendored by fetch-and-verify on the host, like go-librespot and peppyalsa:
# an exact commit and a checksum, never a floating branch. The Volumio
# wrapper (foonerd/peppy_screensaver) is deliberately NOT installed - it
# reads Volumio's API and assumes X (ADR-0026's amendment). Only its 1280x800
# skin templates are taken from it.
#
# Everything here is a plain HTTPS GET plus sha256sum: host work, nothing to
# gain from doing it under qemu.

PEPPYMETER_COMMIT="ee2de2882669f62604ce568f4aa3959501b313d6"
PEPPYMETER_SHA256="ce4bddb4a7fa33469411a463505c92fab0bd894d0017373d957c0a092c42a4f9"
PEPPYSPECTRUM_COMMIT="c8be00dcacf9d27b0b0dc254a440a1b86ea89f6e"
PEPPYSPECTRUM_SHA256="e0c4c27ac21dc6d1175cbe80ddc9edd28f9274a90b9b84c39df1c7ee5bc84c6b"
SCREENSAVER_COMMIT="efbd0adf7d527dfed1aeb04fe1541c85b6d3175e"
SCREENSAVER_SHA256="9513bc5e43d38cc5a04b06c166de161604847da449e8db1859b6b299cd6c30b3"

# Gelo5's 84 skins, 1280x800 - the corpus ADR-0015 is written against. Only
# the config files are in this repository (skins/, 97 KB); the 82 MB of
# images come from here. See skins/README.md for provenance and licence.
GELO5_URL="https://github.com/project-owner/PeppyMeter.doc/releases/download/2024.03.02/Gelo5_1280x800.84skins.zip"
GELO5_SHA256="3a0a99b1584915bc375bc6a2d137a22cbb29a45230ffb6e04a8ccb0bab466997"

# The seven-segment face the skins lay remaining time out for (the wrapper's
# "digi" font). Upstream's own release, OFL-1.1; measured identical to the
# copy foonerd's wrapper bundles at the skins' sizes (2026-09-16).
DSEG_URL="https://github.com/keshikan/DSEG/releases/download/v0.46/fonts-DSEG_v046.zip"
DSEG_SHA256="a6c2f43520971ca8067262e78d49025e605f749bf716ec5394bad9a0ee1c238c"

PEPPY_DIR="${ROOTFS_DIR}/opt/gexis-peppy"
for tool in curl sha256sum bsdtar; do
	command -v "${tool}" >/dev/null || { echo "ERROR: ${tool} is not in the build container" >&2; exit 1; }
done

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

# Content-addressed cache first, network on a miss (ADR-0042). The cache is
# optional: with nothing mounted at CACHE_DIR this is the plain fetch-and-
# verify it replaced.
# shellcheck source=../fetch-cached.sh
. /pi-gen/stage-gexis/fetch-cached.sh

fetch() {  # url sha256 dest
	fetch_cached "$1" "$2" "$3"
}

fetch "https://codeload.github.com/foonerd/PeppyMeter/tar.gz/${PEPPYMETER_COMMIT}" \
	"${PEPPYMETER_SHA256}" "${WORK}/peppymeter.tar.gz"
fetch "https://codeload.github.com/foonerd/PeppySpectrum/tar.gz/${PEPPYSPECTRUM_COMMIT}" \
	"${PEPPYSPECTRUM_SHA256}" "${WORK}/peppyspectrum.tar.gz"
fetch "https://codeload.github.com/foonerd/peppy_screensaver/tar.gz/${SCREENSAVER_COMMIT}" \
	"${SCREENSAVER_SHA256}" "${WORK}/screensaver.tar.gz"
fetch "${GELO5_URL}" "${GELO5_SHA256}" "${WORK}/gelo5.zip"
fetch "${DSEG_URL}" "${DSEG_SHA256}" "${WORK}/dseg.zip"

install -d -m 755 "${PEPPY_DIR}"
rm -rf "${PEPPY_DIR}/peppymeter" "${PEPPY_DIR}/spectrum" "${PEPPY_DIR}/skins"

mkdir -p "${PEPPY_DIR}/peppymeter" "${PEPPY_DIR}/spectrum"
tar -xzf "${WORK}/peppymeter.tar.gz" -C "${PEPPY_DIR}/peppymeter" --strip-components=1
tar -xzf "${WORK}/peppyspectrum.tar.gz" -C "${PEPPY_DIR}/spectrum" --strip-components=1

# Both skin corpora, side by side (George, 2026-09-16: keep the stock ones).
mkdir -p "${WORK}/screensaver" "${WORK}/gelo5"
tar -xzf "${WORK}/screensaver.tar.gz" -C "${WORK}/screensaver" --strip-components=1
# bsdtar, not unzip: the pi-gen build container has no unzip and no python3
# (checked 2026-09-16, after a build failed here on exactly that).
bsdtar -xf "${WORK}/gelo5.zip" -C "${WORK}/gelo5"

# Both engines demand a folder whose NAME is the resolution: it must start
# with a digit and parse as WIDTHxHEIGHT, or they print one line and call
# os._exit(0) (configfileparser.py:222-225). Hence the 1280x800 level.
install -d -m 755 "${PEPPY_DIR}/skins/stock/templates/1280x800" \
	"${PEPPY_DIR}/skins/stock/templates_spectrum/1280x800"
cp -r "${WORK}/screensaver/templates/1280x800_custom_4/." \
	"${PEPPY_DIR}/skins/stock/templates/1280x800/"
cp -r "${WORK}/screensaver/templates_spectrum/1280x800_custom_4/." \
	"${PEPPY_DIR}/skins/stock/templates_spectrum/1280x800/"

# Gelo5 ships six template folders; four are the same 71 skins split into
# groups of twenty (verified 2026-09-16 by comparing section names). Only the
# two distinct ones are installed - see skins/README.md.
install -d -m 755 "${PEPPY_DIR}/skins/gelo5/templates/1280x800" \
	"${PEPPY_DIR}/skins/gelo5/templates_spectrum/1280x800"
cp -r "${WORK}/gelo5/template/1280x800_Gelo5 00-99 Skin_400/." \
	"${PEPPY_DIR}/skins/gelo5/templates/1280x800/"
cp -r "${WORK}/gelo5/template/1280x800_Gelo5 Spec&Met_420/." \
	"${PEPPY_DIR}/skins/gelo5/templates_spectrum/1280x800/"
cp -r "${WORK}/gelo5/template_spectrum/1280x800_Gelo5 Spec&Met_420/." \
	"${PEPPY_DIR}/skins/gelo5/templates_spectrum/1280x800/"

# The corpus this repository validates (make skins) must be the corpus that
# ships: the fetched pack's config files have to match ours byte for byte,
# or the validator proved nothing about what is installed.
for pair in \
	"/pi-gen/gexis-skins/templates/meters.txt:${PEPPY_DIR}/skins/gelo5/templates/1280x800/meters.txt" \
	"/pi-gen/gexis-skins/templates_spectrum/meters.txt:${PEPPY_DIR}/skins/gelo5/templates_spectrum/1280x800/meters.txt" \
	"/pi-gen/gexis-skins/templates_spectrum/spectrum.txt:${PEPPY_DIR}/skins/gelo5/templates_spectrum/1280x800/spectrum.txt"
do
	ours="${pair%%:*}"
	theirs="${pair##*:}"
	# cmp alone cannot tell "differs" from "missing": the first build after
	# the 1280x800 level was added failed here on a path that no longer
	# existed, reported as a difference (2026-09-16).
	if [ ! -f "${theirs}" ]; then
		echo "ERROR: ${theirs} was not installed" >&2
		exit 1
	fi
	if ! cmp -s "${ours}" "${theirs}"; then
		echo "ERROR: ${theirs} differs from the validated ${ours}" >&2
		echo "       the pack changed, or the wrong folder was installed" >&2
		exit 1
	fi
done

# PeppyMeter has no --config option: it reads ./config.txt relative to the
# working directory (configfileparser.py:174-176), so the file goes in the
# engine's own folder and the launcher cds there.
install -D -m 644 files/peppy-meter.txt "${PEPPY_DIR}/peppymeter/config.txt"
install -D -m 644 files/peppy-spectrum.txt "${PEPPY_DIR}/spectrum/config.txt"
install -D -m 755 files/gexis-peppy-driver.py "${PEPPY_DIR}/driver.py"
install -D -m 644 files/gexis_peppy_render.py "${PEPPY_DIR}/gexis_peppy_render.py"
mkdir -p "${WORK}/dseg"
bsdtar -xf "${WORK}/dseg.zip" -C "${WORK}/dseg"
install -d -m 755 "${PEPPY_DIR}/fonts"
install -m 644 "${WORK}/dseg/fonts-DSEG_v046/DSEG7-Classic/DSEG7Classic-Italic.ttf" "${PEPPY_DIR}/fonts/"
install -m 644 "${WORK}/dseg/fonts-DSEG_v046/DSEG-LICENSE.txt" "${PEPPY_DIR}/fonts/"
install -d -m 755 "${PEPPY_DIR}/icons"
install -m 644 files/icons/* "${PEPPY_DIR}/icons/"
install -D -m 644 files/gexis-peppy.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-peppy.service"
install -D -m 755 files/gexis-peppy-start "${ROOTFS_DIR}/usr/local/bin/gexis-peppy-start"

# Enabled by symlink, the same way 04-ui enables the kiosk: `systemctl
# enable` cannot run in a chroot with no running systemd.
# multi-user.target, NOT graphical.target: firstrun.sh reaches raspi-config
# do_boot_behaviour, which resets default.target away from graphical - a unit
# wanted by graphical.target then never starts (Finding 022, the defect that
# shipped in the first flashed image).
install -d -m 755 "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
ln -sf /etc/systemd/system/gexis-peppy.service \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-peppy.service"
rm -f "${ROOTFS_DIR}/etc/systemd/system/graphical.target.wants/gexis-peppy.service"

# What must be true of the *running* system, asserted here because the build
# cannot observe it (docs/LESSONS.md case 5).
if ! grep -q "^WantedBy=multi-user.target$" files/gexis-peppy.service; then
	echo "ERROR: gexis-peppy.service must be WantedBy=multi-user.target (Finding 022)" >&2
	exit 1
fi
if ! grep -q "python3 -u" files/gexis-peppy-start; then
	echo "ERROR: the launcher must run python3 -u, or a config failure is a silent exit 0" >&2
	exit 1
fi

# Assertions: what the build can check about what it just installed. The
# running system is checked separately (docs/LESSONS.md case 5).
for required in \
	"${PEPPY_DIR}/peppymeter/peppymeter.py" \
	"${PEPPY_DIR}/spectrum/spectrum.py" \
	"${PEPPY_DIR}/skins/gelo5/templates/1280x800/meters.txt" \
	"${PEPPY_DIR}/skins/stock/templates/1280x800/meters.txt" \
	"${PEPPY_DIR}/peppymeter/config.txt"
do
	if [ ! -s "${required}" ]; then
		echo "ERROR: ${required} missing or empty after install" >&2
		exit 1
	fi
done

# The skins name images that must be beside their meters.txt; a config-only
# install would parse and then render black (the reference document's
# symptom B, from a different cause).
for corpus in gelo5 stock; do
	count=$(find "${PEPPY_DIR}/skins/${corpus}/templates/1280x800" -maxdepth 1 -type f \
		\( -name '*.png' -o -name '*.jpg' \) | wc -l)
	if [ "${count}" -lt 10 ]; then
		echo "ERROR: ${corpus} templates hold only ${count} images - the pack did not unpack as expected" >&2
		exit 1
	fi
done
