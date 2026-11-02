#!/bin/bash
# ADR-0173: sign a release's parts - on R2D2, the one place the release key
# is (ADR-0105 decision 1), never in a container or on GitHub. Each part's
# Release gets its InRelease and Release.gpg, and parts.plain becomes the
# signed `parts`. A part needs only its Release and Packages here, not its
# packages: what GitHub built is signed from a few kilobytes.
#
# Usage: packaging/release/sign.sh <release dir>    (packaging/release/out/rX)
set -euo pipefail
shopt -s nullglob   # a release whose parts were all signed before has none here
DEST="${1:?usage: packaging/release/sign.sh <release dir>}"
export GNUPGHOME="${GEXIS_RELEASE_GNUPGHOME:-$HOME/.gnupg-gexis-release}"
SIGNER='B6643AE345702FBA!'   # the release subkey (ADR-0105)

for part in "$DEST"/repos/*/; do
	# The Release lists its Packages by sha256: signing it signs every package.
	want=$(sed -n 's/^ \([0-9a-f]\{64\}\) \+[0-9]\+ Packages$/\1/p' "$part/Release")
	[ "$want" = "$(sha256sum "$part/Packages" | cut -c1-64)" ] \
		|| { echo "ERROR: $(basename "$part")'s Release does not list its Packages" >&2; exit 1; }
	gpg --batch --yes -u "$SIGNER" --clearsign -o "$part/InRelease" "$part/Release"
	gpg --batch --yes -u "$SIGNER" -abs -o "$part/Release.gpg" "$part/Release"
	gpg --batch --verify "$part/InRelease" 2>/dev/null || { echo "ERROR: $(basename "$part")'s InRelease does not verify" >&2; exit 1; }
done
gpg --batch --yes -u "$SIGNER" --clearsign -o "$DEST/parts" "$DEST/parts.plain"
rm "$DEST/parts.plain"
parts=( "$DEST"/repos/*/ )
echo "signed $DEST: ${#parts[@]} parts and its list of parts"
