#!/bin/sh
# ADR-0107: gexis-ui, the panel's and the phone's built pages. Built by
# `make ui` on the build machine (ADR-0023: no Node on the device); this only
# packs ui/dist. Runs inside gexis-deb-builder with the repository at /src.
set -eu

VERSION="$1"
STAGE=/tmp/stage/gexis-ui
[ -f /src/ui/dist/index.html ] || { echo "ui/dist/index.html missing: run 'make ui' first" >&2; exit 1; }
# **A build older than the sources is refused** (2026-10-14): ui/dist built
# before a last edit was packed under the version of the commit after it, and
# sofapi ran the earlier outline code while its version named the fix.
stale=$(find /src/ui/src /src/ui/index.html /src/ui/package.json /src/ui/vite.config.js \
	-newer /src/ui/dist/index.html -type f 2>/dev/null | head -1)
[ -z "$stale" ] || { echo "ui/dist is older than $stale: run 'make ui' first" >&2; exit 1; }

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
