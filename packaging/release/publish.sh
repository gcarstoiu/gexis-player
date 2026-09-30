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
	# **The image a new device starts from** (ADR-0105 as amended 2026-09-30,
	# George: "A now with B later"): the one this release was built from,
	# compressed, with its checksum and a signature by the release key. Fixed
	# names, and this half marked GitHub's latest, so
	# .../releases/latest/download/gexis-player.img.xz is always stable's image.
	DEST=packaging/release/out/$tag
	[ -f "$DEST/image.txt" ] || { echo "ERROR: $DEST/image.txt does not name the release's image" >&2; exit 1; }
	img=$(cat "$DEST/image.txt"); [ -f "$img" ] || { echo "ERROR: $img is not here" >&2; exit 1; }
	work=$(mktemp -d)
	xz -T0 -6 -c "$img" > "$work/gexis-player.img.xz"
	(cd "$work" && sha256sum gexis-player.img.xz > gexis-player.img.xz.sha256)
	gpg --batch --yes -u "$SIGNER" -abs -o "$work/gexis-player.img.xz.asc" "$work/gexis-player.img.xz"
	gh release upload "$tag" --repo "$REPO" --clobber "$work"/gexis-player.img.xz "$work"/gexis-player.img.xz.sha256 "$work"/gexis-player.img.xz.asc
	rm -rf "$work"
	channel_file stable "$tag"
	gh release edit "$tag" --repo "$REPO" --prerelease=false --latest
	gh release edit "$tag-debian" --repo "$REPO" --prerelease=false --latest=false
	exit 0
fi

tag="${1:?usage: publish.sh <tag> [--channel testing]}"
DEST=packaging/release/out/$tag
[ -f "$DEST/main/InRelease" ] && [ -f "$DEST/debian/InRelease" ] || { echo "ERROR: $DEST is not a built release" >&2; exit 1; }
for half in main debian; do
	gpg --batch --verify "$DEST/$half/InRelease" 2>/dev/null || { echo "ERROR: $half's InRelease does not verify" >&2; exit 1; }
done
version=$(sed -n 's/^gexis-player_\(.*\)_all\.deb$/\1/p' <(ls "$DEST/main"))
# **Resumable and paced** (2026-09-30: the second release in an hour hit
# GitHub's secondary rate limit 150 files into its 1,031). A release that
# exists is completed rather than refused; files already up are skipped; the
# rest go in batches, and a rate-limit answer waits and tries again.
upload_all() {  # release-tag directory
	local rel="$1" dir="$2" have todo batch=() f tries
	have=$(gh release view "$rel" --repo "$REPO" --json assets --jq '.assets[].name')
	todo=()
	for f in "$dir"/*; do
		grep -qxF "$(basename "$f")" <<<"$have" || todo+=("$f")
	done
	echo "$rel: ${#todo[@]} of $(ls "$dir" | wc -l) files to upload"
	# The indexes last: a half is not usable until every package it lists is up.
	local debs=() idx=()
	for f in "${todo[@]}"; do case "$f" in *.deb) debs+=("$f");; *) idx+=("$f");; esac; done
	todo=("${debs[@]}" "${idx[@]}")
	while [ "${#todo[@]}" -gt 0 ]; do
		batch=("${todo[@]:0:20}")
		tries=0
		until gh release upload "$rel" --repo "$REPO" --clobber "${batch[@]}" >/dev/null 2>&1; do
			tries=$((tries + 1))
			[ "$tries" -le 8 ] || { echo "ERROR: $rel: upload kept failing" >&2; exit 1; }
			echo "  waiting $((tries * 60)) s (GitHub rate limit or network), then again"
			sleep $((tries * 60))
		done
		todo=("${todo[@]:20}")
		sleep 10
	done
}
# Published as pre-releases: stable is what a promotion makes of them.
gh release view "$tag" --repo "$REPO" >/dev/null 2>&1 || gh release create "$tag" --repo "$REPO" --target main --prerelease \
	--title "gexis-player $version" \
	--notes "Gexis Player $version: our packages and the Raspberry Pi part of the tested set, as a signed apt repository (ADR-0108). The Debian part is $tag-debian."
upload_all "$tag" "$DEST/main"
gh release view "$tag-debian" --repo "$REPO" >/dev/null 2>&1 || gh release create "$tag-debian" --repo "$REPO" --target main --prerelease \
	--title "gexis-player $version (Debian packages)" \
	--notes "The Debian part of $tag's tested set, as a signed apt repository (ADR-0108)."
upload_all "$tag-debian" "$DEST/debian"
if [ "${2:-}" = --channel ]; then
	channel_file "${3:?--channel needs testing or stable}" "$tag"
fi
