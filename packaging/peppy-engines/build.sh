#!/bin/sh
# ADR-0107: gexis-peppy-engines - PeppyMeter, PeppySpectrum and the DSEG
# font the skins lay remaining time out in - as a Debian package. Runs inside
# gexis-deb-builder with the repository at /src and the output in /out.
#
# The same downloads, checksums and unpacking as
# image/stage-gexis/05-peppy/01-run.sh. The pins are repeated here, not
# sourced from it: that script is a pi-gen stage and cannot be sourced. If one
# moves, move both (the checksum makes a mismatch fail rather than drift).
#
# **Not shipped here: the two engines' config.txt.** Both upstream tarballs
# carry one at the top level; the image replaces them with ours
# (05-peppy/files/peppy-meter.txt, peppy-spectrum.txt), which belong to
# gexis-system - the spectrum one is rewritten by the driver at runtime. The
# upstream copies are removed after unpacking, so this package never owns
# /opt/gexis-peppy/{peppymeter,spectrum}/config.txt.
set -eu

PEPPYMETER_COMMIT="ee2de2882669f62604ce568f4aa3959501b313d6"
PEPPYMETER_SHA256="ce4bddb4a7fa33469411a463505c92fab0bd894d0017373d957c0a092c42a4f9"
PEPPYSPECTRUM_COMMIT="c8be00dcacf9d27b0b0dc254a440a1b86ea89f6e"
PEPPYSPECTRUM_SHA256="e0c4c27ac21dc6d1175cbe80ddc9edd28f9274a90b9b84c39df1c7ee5bc84c6b"
DSEG_URL="https://github.com/keshikan/DSEG/releases/download/v0.46/fonts-DSEG_v046.zip"
DSEG_SHA256="a6c2f43520971ca8067262e78d49025e605f749bf716ec5394bad9a0ee1c238c"

VERSION_ARG="$1"   # the repository's version: unused, the engines have their own pins
M=$(printf '%s' "$PEPPYMETER_COMMIT" | cut -c1-7)
S=$(printf '%s' "$PEPPYSPECTRUM_COMMIT" | cut -c1-7)
VERSION="0.0.0+git${M}.${S}-1"
STAGE=/tmp/stage/gexis-peppy-engines
PEPPY_DIR="$STAGE/opt/gexis-peppy"
WORK=/tmp/work-engines

. /src/image/stage-gexis/fetch-cached.sh

rm -rf "$STAGE" "$WORK"
mkdir -p "$WORK"
fetch_cached "https://codeload.github.com/foonerd/PeppyMeter/tar.gz/${PEPPYMETER_COMMIT}" \
	"${PEPPYMETER_SHA256}" "${WORK}/peppymeter.tar.gz"
fetch_cached "https://codeload.github.com/foonerd/PeppySpectrum/tar.gz/${PEPPYSPECTRUM_COMMIT}" \
	"${PEPPYSPECTRUM_SHA256}" "${WORK}/peppyspectrum.tar.gz"
fetch_cached "${DSEG_URL}" "${DSEG_SHA256}" "${WORK}/dseg.zip"

install -d -m 755 "$PEPPY_DIR" "$PEPPY_DIR/peppymeter" "$PEPPY_DIR/spectrum"
# The archives' own modes (0664 files, 0775 folders), as the stage's tar
# running as root keeps them; owners are root through --root-owner-group.
tar -xzf "${WORK}/peppymeter.tar.gz" -C "$PEPPY_DIR/peppymeter" \
	--strip-components=1 --no-same-owner --same-permissions
tar -xzf "${WORK}/peppyspectrum.tar.gz" -C "$PEPPY_DIR/spectrum" \
	--strip-components=1 --no-same-owner --same-permissions
for engine in peppymeter spectrum; do
	if [ -e "$PEPPY_DIR/$engine/config.txt" ]; then
		rm "$PEPPY_DIR/$engine/config.txt"
		echo "excluded upstream $engine/config.txt (gexis-system ships ours)"
	fi
done

mkdir -p "${WORK}/dseg"
bsdtar -xf "${WORK}/dseg.zip" -C "${WORK}/dseg"
install -d -m 755 "$PEPPY_DIR/fonts"
install -m 644 "${WORK}/dseg/fonts-DSEG_v046/DSEG7-Classic/DSEG7Classic-Italic.ttf" "$PEPPY_DIR/fonts/"
install -m 644 "${WORK}/dseg/fonts-DSEG_v046/DSEG-LICENSE.txt" "$PEPPY_DIR/fonts/"

# The stage's own assertions that apply to what this package carries.
for required in "$PEPPY_DIR/peppymeter/peppymeter.py" "$PEPPY_DIR/spectrum/spectrum.py"; do
	[ -s "$required" ] || { echo "ERROR: ${required#$STAGE} missing or empty" >&2; exit 1; }
done

mkdir -p "$STAGE/DEBIAN"
cat > "$STAGE/DEBIAN/control" <<CTL
Package: gexis-peppy-engines
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: python3, python3-pygame, python3-pil
Section: sound
Priority: optional
Description: PeppyMeter and PeppySpectrum engines and the DSEG font
 The Peppy screen's two engines as foonerd's forks ship them, and the DSEG7
 font the skins lay remaining time out in (ADR-0107). Pinned:
 PeppyMeter $PEPPYMETER_COMMIT
 (tarball sha256 $PEPPYMETER_SHA256),
 PeppySpectrum $PEPPYSPECTRUM_COMMIT
 (tarball sha256 $PEPPYSPECTRUM_SHA256),
 DSEG v0.46 (zip sha256 $DSEG_SHA256).
 The engines' config.txt files are not here: gexis-system ships them.
CTL
chmod 644 "$STAGE/DEBIAN/control"
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-peppy-engines_${VERSION}_all.deb" >/dev/null
echo "/out/gexis-peppy-engines_${VERSION}_all.deb"
