#!/bin/bash
# ADR-0107: gexis-skins - the stock, Gelo5 and animated skins, the animated
# 1280x720 packs letterboxed here at package build - as a Debian package.
# Runs inside gexis-deb-builder with the repository at /src and the output in
# /out. bash, not sh: the pack list is read with `read` from a here-document
# exactly as the stage reads it.
#
# The same downloads, checksums, folders and checks as
# image/stage-gexis/05-peppy/01-run.sh, and the letterboxing of
# 05-peppy/02-run-chroot.sh, run here with the builder's python3-pil (Debian
# trixie's 11.1.0, the image's own). The pins are repeated, not sourced: the
# stage script cannot be sourced. If one moves, move both - the checksums and
# the cmp against skins/ make a mismatch fail rather than drift.
#
# letterbox.py ships too, at /opt/gexis-peppy/letterbox.py where the image
# has it today, read from 05-peppy/files/ - the same file this build runs.
set -euo pipefail

VERSION="$1"   # the skins are our selection: the repository's version
SCREENSAVER_COMMIT="efbd0adf7d527dfed1aeb04fe1541c85b6d3175e"
SCREENSAVER_SHA256="9513bc5e43d38cc5a04b06c166de161604847da449e8db1859b6b299cd6c30b3"
GELO5_URL="https://github.com/project-owner/PeppyMeter.doc/releases/download/2024.03.02/Gelo5_1280x800.84skins.zip"
GELO5_SHA256="3a0a99b1584915bc375bc6a2d137a22cbb29a45230ffb6e04a8ccb0bab466997"
TEMPLATES_COMMIT="f80c166a"
TEMPLATES_RAW="https://raw.githubusercontent.com/foonerd/peppy_templates/${TEMPLATES_COMMIT}/template_peppy"
TEMPLATES_LICENSE_SHA256="32f33fd11a3263acf22e759fc4482c21cc9296f9d2e3a402639a0fb3a7b3a654"

FILES=/src/image/stage-gexis/05-peppy/files
SKINS_SRC=/src/skins
STAGE=/tmp/stage/gexis-skins
PEPPY_DIR="$STAGE/opt/gexis-peppy"
LICENSES="$STAGE/usr/share/doc/gexis-player/licenses"
WORK=/tmp/work-skins

. /src/image/stage-gexis/fetch-cached.sh
fetch() { fetch_cached "$1" "$2" "$3"; }

rm -rf "$STAGE" "$WORK"
mkdir -p "$WORK"
fetch "https://codeload.github.com/foonerd/peppy_screensaver/tar.gz/${SCREENSAVER_COMMIT}" \
	"${SCREENSAVER_SHA256}" "${WORK}/screensaver.tar.gz"
fetch "${GELO5_URL}" "${GELO5_SHA256}" "${WORK}/gelo5.zip"

install -d -m 755 "$PEPPY_DIR" "$PEPPY_DIR/skins"
mkdir -p "${WORK}/screensaver" "${WORK}/gelo5"
tar -xzf "${WORK}/screensaver.tar.gz" -C "${WORK}/screensaver" --strip-components=1 --no-same-owner
# ADR-0099: the MIT notice travels with the stock skins.
install -D -m 644 "${WORK}/screensaver/LICENSE" "$LICENSES/peppy_screensaver/LICENSE"
bsdtar -xf "${WORK}/gelo5.zip" -C "${WORK}/gelo5"

# The 1280x800 level: both engines demand a folder named for the resolution.
install -d -m 755 "$PEPPY_DIR/skins/stock/templates/1280x800" \
	"$PEPPY_DIR/skins/stock/templates_spectrum/1280x800"
cp -r "${WORK}/screensaver/templates/1280x800_custom_4/." "$PEPPY_DIR/skins/stock/templates/1280x800/"
cp -r "${WORK}/screensaver/templates_spectrum/1280x800_custom_4/." "$PEPPY_DIR/skins/stock/templates_spectrum/1280x800/"

# Gelo5: the two distinct folders of the six (skins/README.md).
install -d -m 755 "$PEPPY_DIR/skins/gelo5/templates/1280x800" \
	"$PEPPY_DIR/skins/gelo5/templates_spectrum/1280x800"
cp -r "${WORK}/gelo5/template/1280x800_Gelo5 00-99 Skin_400/." "$PEPPY_DIR/skins/gelo5/templates/1280x800/"
cp -r "${WORK}/gelo5/template/1280x800_Gelo5 Spec&Met_420/." "$PEPPY_DIR/skins/gelo5/templates_spectrum/1280x800/"
cp -r "${WORK}/gelo5/template_spectrum/1280x800_Gelo5 Spec&Met_420/." "$PEPPY_DIR/skins/gelo5/templates_spectrum/1280x800/"

# The corpus `make skins` validates must be the corpus that ships.
for pair in \
	"$SKINS_SRC/templates/meters.txt:$PEPPY_DIR/skins/gelo5/templates/1280x800/meters.txt" \
	"$SKINS_SRC/templates_spectrum/meters.txt:$PEPPY_DIR/skins/gelo5/templates_spectrum/1280x800/meters.txt" \
	"$SKINS_SRC/templates_spectrum/spectrum.txt:$PEPPY_DIR/skins/gelo5/templates_spectrum/1280x800/spectrum.txt"
do
	ours="${pair%%:*}"
	theirs="${pair##*:}"
	[ -f "$theirs" ] || { echo "ERROR: ${theirs#$STAGE} was not installed" >&2; exit 1; }
	if ! cmp -s "$ours" "$theirs"; then
		echo "ERROR: ${theirs#$STAGE} differs from the validated ${ours#/src/}" >&2
		exit 1
	fi
done

# Finding 050: two meter sections name the spectrum panel as their meter
# background. The same sed, and the same checks, as the stage.
sm="$PEPPY_DIR/skins/gelo5/templates_spectrum/1280x800/meters.txt"
sed -i \
	-e '/\[111G5_Teletronix S+M\]/,/\[112G5/ s/Teletronix_bgr\.png/Teletronix.jpg/' \
	-e '/\[107G5_Marantz S+M\]/,/\[108G5/ s/Marantz_bgr\.png/Marantz.jpg/' \
	"$sm"
for want in "bgr.filename = Teletronix.jpg" "bgr.filename = Marantz.jpg"; do
	grep -qF "$want" "$sm" || { echo "ERROR: the meter background correction did not apply ($want)" >&2; exit 1; }
done
for want in "Teletronix_bgr.png" "Marantz_bgr.png"; do
	grep -qF "$want" "$PEPPY_DIR/skins/gelo5/templates_spectrum/1280x800/spectrum.txt" \
		|| { echo "ERROR: $want is no longer a spectrum background - see Finding 050" >&2; exit 1; }
done
for pack in gelo5 stock; do
	specs=$(find "$PEPPY_DIR/skins/$pack" -name spectrum.txt)
	[ -n "$specs" ] || continue
	# Paths with no spaces in them (the 1280x800 level is ours), so the
	# stage's word splitting is safe here as it is there.
	for meters in $(find "$PEPPY_DIR/skins/$pack" -name meters.txt); do
		# shellcheck disable=SC2086
		if ! awk -f "$FILES/meter-background-check.awk" $specs "$meters"; then
			echo "       ${meters#$STAGE}: a meter draws a spectrum panel - see Finding 050" >&2
			exit 1
		fi
	done
done

# The animated packs (ADR-0096), each held to skins/animated byte for byte.
LETTERBOX="$WORK/letterbox"
mkdir -p "$LETTERBOX"
while read -r path pack sha name; do
	fetch "${TEMPLATES_RAW}/${path}/${pack}.zip" "$sha" "${WORK}/${pack}.zip"
	mkdir -p "${WORK}/anim/${pack}"
	bsdtar -xf "${WORK}/${pack}.zip" -C "${WORK}/anim/${pack}"
	src="${WORK}/anim/${pack}/${pack}"
	[ -f "$src/meters.txt" ] || { echo "ERROR: ${pack}.zip has no ${pack}/meters.txt" >&2; exit 1; }
	if ! cmp -s "$SKINS_SRC/animated/${pack}/meters.txt" "$src/meters.txt"; then
		echo "ERROR: ${pack}'s meters.txt differs from the validated skins/animated copy" >&2
		exit 1
	fi
	case "$pack" in
	1280x800_*)
		install -d -m 755 "$PEPPY_DIR/skins/${name}/templates/1280x800"
		cp -r "$src/." "$PEPPY_DIR/skins/${name}/templates/1280x800/"
		;;
	*)
		cp -r "$src" "$LETTERBOX/${name}"
		;;
	esac
done <<'PACKS'
1280/720 1280x720_g5_710_Turntables e134e35c0f13ffa62d19f476ffe6ee90de185ae63128830f73f34a23e34c913e g5-turntables
1280/720 1280x720_g5_711_Tape_Recorder 9c0d0161efd3d1886d29f2d185d06f4ec11b45cecc323a2bfc95a10dd10a52fc g5-tape
1280/720 1280x720_g5_712_Cassette 8e2d79fce2eb55cfea8628dc0c466226181495b7d3939b1923b7afcf2a85f798 g5-cassette
1280/800 1280x800_t1800_pack7 d3874b563a44406ece770ab1278cb785b92c787f46e1d0ef122ef515173cb8ec t1800
PACKS
fetch "https://raw.githubusercontent.com/foonerd/peppy_templates/f80c166a9682467f0631c374b6ed4eb088fc6e3c/LICENSE" \
	"$TEMPLATES_LICENSE_SHA256" "${WORK}/templates-LICENSE"
install -D -m 644 "${WORK}/templates-LICENSE" "$LICENSES/peppy_templates/LICENSE"

# 05-peppy/02-run-chroot.sh, at package build instead of in the image.
for staged in "$LETTERBOX"/*/; do
	name="$(basename "$staged")"
	out="$PEPPY_DIR/skins/${name}/templates/1280x800"
	mkdir -p "$(dirname "$out")"
	python3 "$FILES/letterbox.py" "$staged" "$out"
	[ -f "$out/meters.txt" ] || { echo "ERROR: ${name} was not letterboxed" >&2; exit 1; }
done
for name in g5-turntables g5-tape g5-cassette t1800; do
	[ -f "$PEPPY_DIR/skins/${name}/templates/1280x800/meters.txt" ] \
		|| { echo "ERROR: ${name} is not installed" >&2; exit 1; }
done
install -m 644 "$FILES/letterbox.py" "$PEPPY_DIR/letterbox.py"

# The stage's closing assertions, for the parts this package carries.
for required in "$PEPPY_DIR/skins/gelo5/templates/1280x800/meters.txt" \
	"$PEPPY_DIR/skins/stock/templates/1280x800/meters.txt"; do
	[ -s "$required" ] || { echo "ERROR: ${required#$STAGE} missing or empty" >&2; exit 1; }
done
for corpus in gelo5 stock; do
	count=$(find "$PEPPY_DIR/skins/${corpus}/templates/1280x800" -maxdepth 1 -type f \
		\( -name '*.png' -o -name '*.jpg' \) | wc -l)
	if [ "$count" -lt 10 ]; then
		echo "ERROR: ${corpus} templates hold only ${count} images - the pack did not unpack as expected" >&2
		exit 1
	fi
done

# Explicit modes, as the image has them: every folder 0755, every file 0644.
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +

mkdir -p "$STAGE/DEBIAN"
cat > "$STAGE/DEBIAN/control" <<CTL
Package: gexis-skins
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Section: sound
Priority: optional
Description: Gexis Player's Peppy screen skins
 The stock skins, Gelo5's 84-skin corpus (Finding 050's two meter backgrounds
 corrected) and the animated packs, the 1280x720 ones letterboxed to 1280x800
 at package build (ADR-0096, ADR-0107). Upstream pins:
 foonerd/peppy_screensaver $SCREENSAVER_COMMIT
 (tarball sha256 $SCREENSAVER_SHA256);
 Gelo5_1280x800.84skins.zip from project-owner/PeppyMeter.doc 2024.03.02
 (sha256 $GELO5_SHA256);
 foonerd/peppy_templates $TEMPLATES_COMMIT, four packs each by the sha256 of
 its own catalogue (skins/README.md).
CTL
chmod 644 "$STAGE/DEBIAN/control"
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-skins_${VERSION}_all.deb" >/dev/null
echo "/out/gexis-skins_${VERSION}_all.deb"
