#!/bin/sh
# ADR-0107: gexis-ui, the panel's and the phone's built pages. Built by
# `make ui` on the build machine (ADR-0023: no Node on the device); this only
# packs ui/dist. Runs inside gexis-deb-builder with the repository at /src.
set -eu

VERSION="$1"
STAGE=/tmp/stage/gexis-ui
[ -f /src/ui/dist/index.html ] || { echo "ui/dist/index.html missing: run 'make ui' first" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/gexis-ui"
cp -r /src/ui/dist/. "$STAGE/opt/gexis-ui/"
cat > "$STAGE/DEBIAN/control" <<CTL
Package: gexis-ui
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Section: sound
Priority: optional
Description: Gexis Player's panel and phone pages
 The built Svelte application the core serves at /, with the licences of
 what it bundles (ADR-0107).
CTL
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-ui_${VERSION}_all.deb" >/dev/null
echo "/out/gexis-ui_${VERSION}_all.deb"
