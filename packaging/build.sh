#!/bin/sh
# ADR-0107: build our Debian packages into packaging/out/, in the arm64
# builder container. Usage: packaging/build.sh [package ...] (default: all).
set -eu
cd "$(dirname "$0")/.."

# **A package's version is the last commit that changed what it is built
# from**, not the repository's: the skins are 176 MB and change rarely, and a
# version per commit would have every device download them again for every
# release. 0.2.1-819-g0bf1f48 -> 0.2.1+git819.0bf1f48, where 819 is that
# commit's own count, so later changes still sort later. The release
# (gexis-player) is the repository as a whole.
inputs() {
	case "$1" in
		core) echo core packaging/core packaging/keys image/stage-gexis/03-core/files ;;
		ui) echo ui packaging/ui ;;
		system) echo image/stage-gexis packaging/system ;;
		skins) echo skins packaging/skins image/stage-gexis/fetch-cached.sh \
			image/stage-gexis/05-peppy/files/letterbox.py \
			image/stage-gexis/05-peppy/files/meter-background-check.awk ;;
		*) echo . ;;   # the release, and components that carry their own
	esac
}
version_for() {
	# shellcheck disable=SC2046
	local paths; paths=$(inputs "$1")
	local commit; commit=$(git log -1 --format=%H -- $paths)
	local v; v=$(git describe --tags --always "$commit" | sed -E 's/^v//; s/-([0-9]+)-g([0-9a-f]+)$/+git\1.\2/')
	# shellcheck disable=SC2046
	if [ -n "$(git status --porcelain -- $paths)" ]; then v="$v.dirty"; fi
	printf '%s' "$v"
}

# Rebuilt when the Dockerfile changes: its hash is the image's label.
want=$(sha256sum packaging/builder.Dockerfile | cut -c1-12)
have=$(docker image inspect -f '{{index .Config.Labels "gexis.dockerfile"}}' gexis-deb-builder 2>/dev/null || true)
[ "$want" = "$have" ] \
	|| docker build --label "gexis.dockerfile=$want" -q --platform linux/arm64 -t gexis-deb-builder -f packaging/builder.Dockerfile packaging

mkdir -p packaging/out
for pkg in ${*:-core ui system skins peppyalsa peppy-engines go-librespot beszel-agent plexamp player}; do
	docker run --rm --platform linux/arm64 \
		-v "$PWD":/src:ro -v "$PWD/packaging/out":/out \
		-v "${GEXIS_BUILD_CACHE:-$HOME/.cache/gexis-player/downloads}":/cache \
		-e GEXIS_BUILD_CACHE=/cache \
		gexis-deb-builder bash "/src/packaging/$pkg/build.sh" "$(version_for "$pkg")"
done
# The container writes as root; hand the results back.
docker run --rm -v "$PWD/packaging/out":/out alpine chown -R "$(id -u):$(id -g)" /out
