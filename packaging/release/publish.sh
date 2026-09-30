#!/bin/bash
# ADR-0108: put a built release on GitHub, and move a channel. The one step
# here that reaches outside R2D2 - run on George's say-so, never by a build.
#
#   packaging/release/publish.sh <tag>                 upload the release only
#   packaging/release/publish.sh <tag> --channel testing   upload, then point testing at it
#   packaging/release/publish.sh --promote <tag>       point stable at a release already up
set -euo pipefail
cd "$(dirname "$0")/../.."

REPO=gcarstoiu/gexis-player
export GNUPGHOME="${GEXIS_RELEASE_GNUPGHOME:-$HOME/.gnupg-gexis-release}"
SIGNER='B6643AE345702FBA!'
BASE="https://github.com/$REPO/releases/download"

channel_file() {  # channel tag -> writes, signs and uploads channels/<channel>
	local channel="$1" tag="$2" work serial version
	work=$(mktemp -d)
	# The serial only increases (ADR-0108): read what is published, add one.
	if curl -fsSL -o "$work/current" "$BASE/channels/$channel" 2>/dev/null; then
		gpg --batch --verify "$work/current" 2>/dev/null || { echo "ERROR: the published $channel file does not verify; not moving it" >&2; exit 1; }
		serial=$(( $(sed -n 's/^Serial: //p' "$work/current") + 1 ))
	else
		serial=1
	fi
	version=$(gh release view "$tag" --repo "$REPO" --json name --jq .name | sed 's/^gexis-player //')
	cat > "$work/$channel.txt" <<EOF
Channel: $channel
Serial: $serial
Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Release: $version
Repositories: $tag $tag-debian
Notes: https://github.com/$REPO/releases/tag/$tag
EOF
	gpg --batch --yes -u "$SIGNER" --clearsign -o "$work/$channel" "$work/$channel.txt"
	gh release view channels --repo "$REPO" >/dev/null 2>&1 \
		|| gh release create channels --repo "$REPO" --target main --title "Update channels" \
			--notes "The signed files devices read to find their channel's release (ADR-0108). Not a release of the player."
	gh release upload channels "$work/$channel" --repo "$REPO" --clobber
	echo "$channel -> $tag (serial $serial)"
	rm -rf "$work"
}

if [ "${1:-}" = --promote ]; then
	tag="${2:?usage: publish.sh --promote <tag>}"
	gh release view "$tag" --repo "$REPO" >/dev/null || { echo "ERROR: $tag is not published" >&2; exit 1; }
	channel_file stable "$tag"
	gh release edit "$tag" --repo "$REPO" --prerelease=false
	gh release edit "$tag-debian" --repo "$REPO" --prerelease=false
	exit 0
fi

tag="${1:?usage: publish.sh <tag> [--channel testing]}"
DEST=packaging/release/out/$tag
[ -f "$DEST/main/InRelease" ] && [ -f "$DEST/debian/InRelease" ] || { echo "ERROR: $DEST is not a built release" >&2; exit 1; }
for half in main debian; do
	gpg --batch --verify "$DEST/$half/InRelease" 2>/dev/null || { echo "ERROR: $half's InRelease does not verify" >&2; exit 1; }
done
version=$(sed -n 's/^gexis-player_\(.*\)_all\.deb$/\1/p' <(ls "$DEST/main"))
# Published as pre-releases: stable is what a promotion makes of them.
gh release create "$tag" --repo "$REPO" --target main --prerelease \
	--title "gexis-player $version" \
	--notes "Gexis Player $version: our packages and the Raspberry Pi part of the tested set, as a signed apt repository (ADR-0108). The Debian part is $tag-debian." \
	"$DEST"/main/*
gh release create "$tag-debian" --repo "$REPO" --target main --prerelease \
	--title "gexis-player $version (Debian packages)" \
	--notes "The Debian part of $tag's tested set, as a signed apt repository (ADR-0108)." \
	"$DEST"/debian/*
if [ "${2:-}" = --channel ]; then
	channel_file "${3:?--channel needs testing or stable}" "$tag"
fi
