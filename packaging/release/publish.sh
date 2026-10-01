#!/bin/bash
# ADR-0108 (as amended): put a built release on GitHub, and move a channel. The
# one step here that reaches outside R2D2 - run on George's say-so, never by a
# build.
#
#   packaging/release/publish.sh <tag>                     upload the release only
#   packaging/release/publish.sh <tag> --channel testing   upload, then point testing at it
#   packaging/release/publish.sh --promote <tag>           point stable at it, with its image
#
# **A release is parts, named by content**: a part already on GitHub is not
# uploaded again. A typical release uploads its `ours` part and its page.
#
# **Paced for GitHub's limits** (2026-09-30: two whole releases in an hour hit
# the secondary rate limit, and then the API refused everything for a while).
# GitHub documents about 500 content-creating requests an hour: 10 files, then
# a pause, keeps under it; a refusal waits minutes, never hammers.
set -euo pipefail
cd "$(dirname "$0")/../.."

REPO=gcarstoiu/gexis-player
export GNUPGHOME="${GEXIS_RELEASE_GNUPGHOME:-$HOME/.gnupg-gexis-release}"
SIGNER='B6643AE345702FBA!'
BASE="https://github.com/$REPO/releases/download"
BATCH=10
PAUSE=80

gh_retry() {  # a gh call that waits out a refusal: 5, 10, 15 ... minutes
	local tries=0
	until "$@"; do
		tries=$((tries + 1))
		[ "$tries" -le 6 ] || { echo "ERROR: gh kept refusing: $*" >&2; exit 1; }
		echo "  GitHub refused; waiting $((tries * 5)) min" >&2
		sleep $((tries * 300))
	done
}

exists() {  # whether a release exists - asked once: "no" is an answer, not a refusal
	gh release view "$1" --repo "$REPO" >/dev/null 2>&1
}

upload_all() {  # release-tag directory: upload what is not there yet, packages first
	local rel="$1" dir="$2" have f
	have=$(gh_retry gh release view "$rel" --repo "$REPO" --json assets --jq '.assets[] | select(.state == "uploaded") | .name')
	local debs=() idx=()
	for f in "$dir"/*; do
		grep -qxF "$(basename "$f")" <<<"$have" && continue
		case "$f" in *.deb) debs+=("$f");; *) idx+=("$f");; esac
	done
	# The indexes last: a part is not usable until every package it lists is up.
	local todo=("${debs[@]}" "${idx[@]}")
	# GitHub renames what it does not like (`~` became `.`, 2026-10-01); a
	# name it would change is never "there", and apt would ask for the name
	# the index gives. release/build.sh names them safely; refuse otherwise.
	for f in "${todo[@]}"; do
		case "$(basename "$f")" in *[!A-Za-z0-9._+-]*) echo "ERROR: GitHub would rename $(basename "$f"); rebuild the release" >&2; exit 1;; esac
	done
	echo "$rel: ${#todo[@]} of $(ls "$dir" | wc -l) files to upload"
	while [ "${#todo[@]}" -gt 0 ]; do
		gh_retry gh release upload "$rel" --repo "$REPO" --clobber "${todo[@]:0:$BATCH}" >/dev/null
		todo=("${todo[@]:$BATCH}")
		[ "${#todo[@]}" -eq 0 ] || sleep "$PAUSE"
	done
	# Every file there under its own name, or the part is not usable.
	have=$(gh_retry gh api --paginate "repos/$REPO/releases/tags/$rel" --jq '.id' | head -1 \
		| xargs -I{} gh api --paginate "repos/$REPO/releases/{}/assets?per_page=100" --jq '.[] | select(.state == "uploaded") | .name')
	for f in "$dir"/*; do
		grep -qxF "$(basename "$f")" <<<"$have" || { echo "ERROR: $rel has no $(basename "$f") after upload" >&2; exit 1; }
	done
}

channel_file() {  # channel tag -> writes, signs and uploads channels/<channel>
	local channel="$1" tag="$2" work serial version parts
	work=$(mktemp -d)
	# The serial only increases (ADR-0108): read what is published, add one.
	if curl -fsSL -o "$work/current" "$BASE/channels/$channel" 2>/dev/null; then
		gpg --batch --verify "$work/current" 2>/dev/null || { echo "ERROR: the published $channel file does not verify; not moving it" >&2; exit 1; }
		serial=$(( $(sed -n 's/^Serial: //p' "$work/current") + 1 ))
	else
		serial=1
	fi
	curl -fsSL -o "$work/parts" "$BASE/$tag/parts" || { echo "ERROR: $tag has no parts file" >&2; exit 1; }
	gpg --batch --verify "$work/parts" 2>/dev/null || { echo "ERROR: $tag's parts file does not verify" >&2; exit 1; }
	version=$(gpg --batch --decrypt "$work/parts" 2>/dev/null | sed -n 's/^Release: //p')
	parts=$(gpg --batch --decrypt "$work/parts" 2>/dev/null | sed -n 's/^Parts: //p')
	cat > "$work/$channel.txt" <<EOF
Channel: $channel
Format: 2
Serial: $serial
Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Release: $version
Repositories: $parts
Notes: https://github.com/$REPO/releases/tag/$tag
EOF
	gpg --batch --yes -u "$SIGNER" --clearsign -o "$work/$channel" "$work/$channel.txt"
	exists channels \
		|| gh_retry gh release create channels --repo "$REPO" --target main --title "Update channels" \
			--notes "The signed files devices read to find their channel's release (ADR-0108). Not a release of the player."
	gh_retry gh release upload channels "$work/$channel" --repo "$REPO" --clobber
	echo "$channel -> $tag (serial $serial): $parts"
	rm -rf "$work"
}

if [ "${1:-}" = --promote ]; then
	tag="${2:?usage: publish.sh --promote <tag>}"
	gh_retry gh release view "$tag" --repo "$REPO" >/dev/null
	# **The image a new device starts from** (ADR-0105 as amended 2026-09-30,
	# George: "A now with B later"): the one this release was built from,
	# compressed, with its checksum and a signature by the release key. Fixed
	# names, and the release page marked GitHub's latest (parts never are), so
	# .../releases/latest/download/gexis-player.img.xz is always stable's image.
	DEST=packaging/release/out/$tag
	[ -f "$DEST/image.txt" ] || { echo "ERROR: $DEST/image.txt does not name the release's image" >&2; exit 1; }
	img=$(cat "$DEST/image.txt"); [ -f "$img" ] || { echo "ERROR: $img is not here" >&2; exit 1; }
	work=$(mktemp -d)
	xz -T0 -6 -c "$img" > "$work/gexis-player.img.xz"
	(cd "$work" && sha256sum gexis-player.img.xz > gexis-player.img.xz.sha256)
	gpg --batch --yes -u "$SIGNER" -abs -o "$work/gexis-player.img.xz.asc" "$work/gexis-player.img.xz"
	gh_retry gh release upload "$tag" --repo "$REPO" --clobber "$work"/gexis-player.img.xz "$work"/gexis-player.img.xz.sha256 "$work"/gexis-player.img.xz.asc
	rm -rf "$work"
	channel_file stable "$tag"
	gh_retry gh release edit "$tag" --repo "$REPO" --prerelease=false --latest
	exit 0
fi

tag="${1:?usage: publish.sh <tag> [--channel testing]}"
DEST=packaging/release/out/$tag
[ -f "$DEST/parts" ] || { echo "ERROR: $DEST has no parts file; build it with packaging/release/build.sh" >&2; exit 1; }
# **Its notes** (2026-10-01, George): a few plain sentences - what is new,
# what is fixed, whether it restarts - drafted from the commits and approved
# by George before this runs. The device shows them under Settings' Release
# row; the release page carries the same text.
[ -s "$DEST/notes.txt" ] || { echo "ERROR: $DEST/notes.txt is missing: write the release's notes, approved, first" >&2; exit 1; }
gpg --batch --yes -u "$SIGNER" --clearsign -o "$DEST/notes" "$DEST/notes.txt"
gpg --batch --verify "$DEST/parts" 2>/dev/null || { echo "ERROR: $DEST/parts does not verify" >&2; exit 1; }
version=$(gpg --batch --decrypt "$DEST/parts" 2>/dev/null | sed -n 's/^Release: //p')
# **A release has a number** (ADR-0110 §1): built from a commit tagged
# v<x.y.z>, so gexis-player is exactly x.y.z. A build between tags is not
# published.
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: $version is not a release number: tag the commit v<x.y.z> (approved with the notes) and build from it" >&2; exit 1; }

# The parts: each a pre-release of its own, never GitHub's "latest".
for part in "$DEST"/repos/*/; do
	name=$(basename "$part")
	gpg --batch --verify "$part/InRelease" 2>/dev/null || { echo "ERROR: $name's InRelease does not verify" >&2; exit 1; }
	exists "$name" \
		|| gh_retry gh release create "$name" --repo "$REPO" --target main --prerelease --latest=false \
			--title "Part $name" \
			--notes "A part of Gexis Player releases: a signed apt repository, named by its content (ADR-0108). Shared by every release whose part is the same."
	upload_all "$name" "$part"
done

# The release's page: its notes and its signed list of parts.
exists "$tag" \
	|| gh_retry gh release create "$tag" --repo "$REPO" --target main --prerelease --latest=false \
		--title "gexis-player $version" \
		--notes-file "$DEST/notes.txt"
gh_retry gh release edit "$tag" --repo "$REPO" --notes-file "$DEST/notes.txt" >/dev/null
gh_retry gh release upload "$tag" --repo "$REPO" --clobber "$DEST/parts" "$DEST/notes"
if [ "${2:-}" = --channel ]; then
	channel_file "${3:?--channel needs testing or stable}" "$tag"
fi
