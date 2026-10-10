#!/bin/sh
# ADR-0133: gexis-wallpapers - the player's own pictures (wallpapers/), for
# the Gexis wallpapers background and Space pictures' built-in set, with
# credits.json beside them: the screens draw each picture's credit from it.
# Runs inside gexis-deb-builder with the repository at /src.
#
# Its version is the last commit that changed wallpapers/ or this folder
# (packaging/build.sh), and the package is cached like the skins: 26 MB that
# change rarely are not downloaded again with every release.
set -eu

VERSION="$1"
STAGE=/tmp/stage/gexis-wallpapers
SRC=/src/wallpapers
[ -f "$SRC/credits.json" ] || { echo "wallpapers/credits.json missing" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/share/gexis/wallpapers"
cp -r "$SRC/." "$STAGE/usr/share/gexis/wallpapers/"
rm -f "$STAGE/usr/share/gexis/wallpapers/README.md"
# Where every licence the player ships is read (ADR-0099): the README says
# what the licences are, credits.json says whose each picture is.
install -D -m 644 "$SRC/README.md" "$STAGE/usr/share/doc/gexis-player/licenses/wallpapers/README.md"
install -D -m 644 "$SRC/credits.json" "$STAGE/usr/share/doc/gexis-player/licenses/wallpapers/credits.json"

# Every picture listed, and every listed picture there: a picture without its
# credit must not ship, and a credit without its picture is a broken list.
python3 - "$STAGE/usr/share/gexis/wallpapers" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
listed = {c["file"] for c in json.load(open(root / "credits.json"))}
present = {str(p.relative_to(root)) for p in root.glob("*/*.webp")}
missing, unlisted = listed - present, present - listed
if missing or unlisted:
    sys.exit(f"credits and pictures disagree: missing {sorted(missing)}, unlisted {sorted(unlisted)}")
print(f"{len(present)} pictures, each with its credit")
PY

cat > "$STAGE/DEBIAN/control" <<CTL
Package: gexis-wallpapers
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Section: sound
Priority: optional
Description: Gexis Player's own wallpapers
 Public-domain and CC0 photographs for the Gexis wallpapers background, and
 a built-in set of space pictures, with each picture's credit (ADR-0133).
CTL
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-wallpapers_${VERSION}_all.deb" >/dev/null
echo "/out/gexis-wallpapers_${VERSION}_all.deb"
