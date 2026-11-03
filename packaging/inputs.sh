#!/bin/bash
# ADR-0173: the `inputs` mirror, the build's downloads (ADR-0042) kept on
# GitHub under their sha256, as packaging/inputs.tsv lists them.
#
#   packaging/inputs.sh publish           upload what the mirror lacks, from $GEXIS_BUILD_CACHE
#   packaging/inputs.sh fill <dir>        put every listed file the mirror has into a build cache
#   packaging/inputs.sh unlisted <dir>    name a build cache's files the list lacks
#
# Every file is checked against its name before it is uploaded or kept.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO=gcarstoiu/gexis-player
TAG=inputs
LIST=packaging/inputs.tsv
listed() { grep -v '^#' "$LIST" | cut -f1; }
good() { echo "$1  $2" | sha256sum -c - >/dev/null 2>&1; }

case "${1:-}" in
publish)
	CACHE="${GEXIS_BUILD_CACHE:?set GEXIS_BUILD_CACHE to the cache holding the files}"
	gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1 \
		|| gh release create "$TAG" --repo "$REPO" --target main --prerelease --latest=false \
			--title "Build inputs" \
			--notes "The files the build downloads, each named by its sha256, so a release still builds if an upstream removes one (ADR-0042, ADR-0173). Each file's origin and licence: packaging/inputs.tsv. Not a release of the player."
	have=$(gh release view "$TAG" --repo "$REPO" --json assets --jq '.assets[] | select(.state == "uploaded") | .name')
	todo=()
	for sum in $(listed); do
		grep -qxF "$sum" <<<"$have" && continue
		[ -f "$CACHE/$sum" ] || { echo "ERROR: $sum is listed but not in $CACHE" >&2; exit 1; }
		good "$sum" "$CACHE/$sum" || { echo "ERROR: $CACHE/$sum is not what its name says" >&2; exit 1; }
		todo+=("$CACHE/$sum")
	done
	echo "$TAG: ${#todo[@]} of $(listed | wc -l) to upload"
	# Paced as publish.sh is: 10 files, then a pause (GitHub's secondary limit).
	while [ "${#todo[@]}" -gt 0 ]; do
		gh release upload "$TAG" --repo "$REPO" "${todo[@]:0:10}"
		todo=("${todo[@]:10}")
		[ "${#todo[@]}" -eq 0 ] || sleep 80
	done
	;;
fill)
	dir="${2:?usage: inputs.sh fill <dir>}"; mkdir -p "$dir"
	missing=0
	for sum in $(listed); do
		[ -f "$dir/$sum" ] && good "$sum" "$dir/$sum" && continue
		if curl -fsSL --retry 3 -o "$dir/$sum.part" "https://github.com/$REPO/releases/download/$TAG/$sum" \
			&& good "$sum" "$dir/$sum.part"; then
			mv "$dir/$sum.part" "$dir/$sum"
		else
			rm -f "$dir/$sum.part"; missing=$((missing + 1))
			echo "not in the mirror, the build fetches it upstream: $(grep "^$sum" "$LIST" | cut -f3)"
		fi
	done
	echo "filled $dir from the mirror: $(( $(listed | wc -l) - missing )) of $(listed | wc -l)"
	;;
unlisted)
	dir="${2:?usage: inputs.sh unlisted <dir>}"
	n=0
	for f in "$dir"/*; do
		[ -f "$f" ] || continue
		listed | grep -qxF "$(basename "$f")" && continue
		echo "not in $LIST: $(basename "$f")"; n=$((n + 1))
	done
	[ "$n" -eq 0 ]
	;;
*)
	sed -n '2,9p' "$0" >&2; exit 2
	;;
esac
