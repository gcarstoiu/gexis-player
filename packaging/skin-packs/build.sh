#!/bin/bash
# ADR-0111: gexis-skins-<W>x<H>, one screen size's skins as a Debian package -
# Gelo5's set for that size and every foonerd/peppy_templates pack of it,
# previews and byte-identical repeats left out. Runs inside gexis-deb-builder
# with the repository at /src and the output in /out:
#
#     build.sh <version> <W>x<H>
#
# Every download is pinned by SHA256 (pins.json; the catalog's own
# catalog/index.json for each of its zips, the index itself pinned) and goes
# through fetch_cached. assemble.py decides what a skin is and what repeats;
# describe.py writes pack.json and the licence files.
set -euo pipefail
# Some archives name files outside ASCII (`... — kopia.png` in
# 1280x800_g5_420_meters.zip): bsdtar refuses those in the C locale.
export LC_ALL=C.UTF-8

VERSION="$1"
SIZE="$2"
case "$SIZE" in
	1920x1080|1280x400|1480x320|800x480|1280x800) ;;   # ADR-0111 decision 1
	*) echo "ERROR: $SIZE is not one of ADR-0111's sizes" >&2; exit 1 ;;
esac
PACKAGE="gexis-skins-$SIZE"
HERE=/src/packaging/skin-packs
FILES=/src/image/stage-gexis/05-peppy/files
STAGE="/tmp/stage/$PACKAGE"
WORK="/tmp/work-$PACKAGE"
# pin catalog commit -> pins.json's ["catalog"]["commit"]
pin() { python3 -c 'import json, sys
d = json.load(open(sys.argv[1]))
for k in sys.argv[2:]: d = d[k]
print(d)' "$HERE/pins.json" "$@"; }

. /src/image/stage-gexis/fetch-cached.sh
start=$(date +%s)
rm -rf "$STAGE" "$WORK"
mkdir -p "$WORK/zips" "$WORK/cat" "$WORK/gelo5"

COMMIT=$(pin catalog commit)
RAW="https://raw.githubusercontent.com/foonerd/peppy_templates/$COMMIT"
fetch_cached "$RAW/catalog/index.json" "$(pin catalog index_sha256)" "$WORK/index.json"
fetch_cached "$RAW/LICENSE" "$(pin catalog licence_sha256)" "$WORK/LICENSE.peppy_templates"
fetch_cached "$(pin gelo5 licence_url)" "$(pin gelo5 licence_sha256)" "$WORK/LICENSE.PeppyMeter.doc"
fetch_cached "$(pin gelo5 release)/$(pin gelo5 sets "$SIZE" file)" \
	"$(pin gelo5 sets "$SIZE" sha256)" "$WORK/gelo5.zip"
bsdtar -xf "$WORK/gelo5.zip" -C "$WORK/gelo5"

# The catalog's packs of this size (and, for 1280x800, the 1280x720 ones it
# letterboxes), each fetched by the SHA256 the pinned index gives it. A zip
# path holds a space (`1280x400_rose rs150.zip`), hence the URL quoting.
python3 - "$WORK/index.json" "$SIZE" > "$WORK/catalog.tsv" <<'PY'
import json, sys, urllib.parse
index, size = json.load(open(sys.argv[1])), sys.argv[2]
wanted = {size} | ({"1280x720"} if size == "1280x800" else set())
for t in sorted(index["templates"], key=lambda t: t["name"]):
    if f"{t['width']}x{t['height']}" in wanted:
        print(t["name"], t["sha256"], urllib.parse.quote(t["zip"]), sep="\t")
PY
[ -s "$WORK/catalog.tsv" ] || { echo "ERROR: the catalog has no $SIZE packs" >&2; exit 1; }
while IFS=$'\t' read -r name sha path; do
	fetch_cached "$RAW/$path" "$sha" "$WORK/zips/$sha.zip"
	mkdir -p "$WORK/cat/$name"
	bsdtar -xf "$WORK/zips/$sha.zip" -C "$WORK/cat/$name"
done < "$WORK/catalog.tsv"
rm -rf "$WORK/zips" "$WORK/gelo5.zip"

# The corpora the repository validates (`make skins`) must be what ships,
# as gexis-skins holds them: Gelo5's 1280x800 configuration files, and the
# four animated packs' meters.txt before letterboxing (skins/README.md).
if [ "$SIZE" = 1280x800 ]; then
	g="$WORK/gelo5/template"; gs="$WORK/gelo5/template_spectrum"
	for pair in \
		"/src/skins/templates/meters.txt:$g/1280x800_Gelo5 00-99 Skin_400/meters.txt" \
		"/src/skins/templates_spectrum/meters.txt:$g/1280x800_Gelo5 Spec&Met_420/meters.txt" \
		"/src/skins/templates_spectrum/spectrum.txt:$gs/1280x800_Gelo5 Spec&Met_420/spectrum.txt"
	do
		cmp -s "${pair%%:*}" "${pair#*:}" || { echo "ERROR: ${pair#*:} differs from the validated ${pair%%:*}" >&2; exit 1; }
	done
	for pack in /src/skins/animated/*/; do
		pack=$(basename "$pack")
		cmp -s "/src/skins/animated/$pack/meters.txt" "$WORK/cat/$pack/$pack/meters.txt" \
			|| { echo "ERROR: $pack's meters.txt differs from the validated skins/animated copy" >&2; exit 1; }
	done
fi

ROOT="$STAGE/opt/gexis-peppy/packs/$SIZE"
python3 "$HERE/assemble.py" --size "$SIZE" --index "$WORK/index.json" \
	--catalog "$WORK/cat" --gelo5 "$WORK/gelo5" --out "$ROOT" --work "$WORK/assemble" \
	--report "$WORK/report.json" --letterbox "$FILES/letterbox.py"
python3 "$HERE/describe.py" "$WORK/report.json" "$HERE/pins.json" "$STAGE"
install -m 644 "$WORK/LICENSE.peppy_templates" "$WORK/LICENSE.PeppyMeter.doc" "$STAGE/usr/share/doc/$PACKAGE/"

# The 1280x800 set holds what gexis-skins carried, folder for folder.
if [ "$SIZE" = 1280x800 ]; then
	for want in gelo5/templates gelo5-420/templates gelo5-420/templates_spectrum \
		1280x720_g5_710_Turntables/templates 1280x720_g5_711_Tape_Recorder/templates \
		1280x720_g5_712_Cassette/templates 1280x800_t1800_pack7/templates; do
		[ -s "$ROOT/$want/1280x800/meters.txt" ] || [ -s "$ROOT/$want/1280x800/spectrum.txt" ] \
			|| { echo "ERROR: $want is not in the 1280x800 pack" >&2; exit 1; }
	done
fi
if find "$ROOT" -iname preview.png | grep -q .; then
	echo "ERROR: a preview.png is in the pack (ADR-0111 decision 8)" >&2; exit 1
fi

# Explicit modes, as the image has them: every folder 0755, every file 0644.
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +

skins=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["skins"])' "$ROOT/pack.json")
letterboxed=""
[ "$SIZE" = 1280x800 ] && letterboxed=", the 1280x720 ones letterboxed"
mkdir -p "$STAGE/DEBIAN"
cat > "$STAGE/DEBIAN/control" <<CTL
Package: $PACKAGE
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Installed-Size: $(du -sk --apparent-size "$STAGE/opt" "$STAGE/usr" | awk '{s += $1} END {print s}')
Section: sound
Priority: optional
Description: Gexis Player's visualiser skins for a $SIZE screen
 $skins PeppyMeter skins drawn for $SIZE, under /opt/gexis-peppy/packs/$SIZE:
 Gelo5's set from project-owner/PeppyMeter.doc 2024.03.02 and every
 foonerd/peppy_templates pack of this size at
 $COMMIT$letterboxed (ADR-0111).
 Previews and byte-identical repeats are left out;
 /usr/share/doc/$PACKAGE/dropped.txt names them.
CTL
chmod 644 "$STAGE/DEBIAN/control"
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/${PACKAGE}_${VERSION}_all.deb" >/dev/null
rm -rf "$WORK"
echo "/out/${PACKAGE}_${VERSION}_all.deb ($skins skins, $(du -sm "$STAGE" | cut -f1) MB installed, $(( $(date +%s) - start ))s)"
