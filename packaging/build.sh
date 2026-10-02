#!/bin/sh
# ADR-0107: build our Debian packages into packaging/out/, in the arm64
# builder container. Usage: packaging/build.sh [package ...] (default: all).
# A skin pack is named by its size: `skins-800x480` builds gexis-skins-800x480
# (ADR-0111) with packaging/skin-packs/build.sh.
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
		# One version for all five: they are built from the same files, and
		# a pack changes only when one of them does - not with each release.
		skins-*) echo skins packaging/skin-packs image/stage-gexis/fetch-cached.sh \
			image/stage-gexis/05-peppy/files/letterbox.py image/stage-gexis/05-peppy/files/badge-slots.json \
			core/src/gexis_core/skin_counts.json ;;
		*) echo . ;;   # the release, and components that carry their own
	esac
}
version_for() {
	# shellcheck disable=SC2046
	local paths; paths=$(inputs "$1")
	local commit; commit=$(git log -1 --format=%H -- $paths)
	# **"." is the whole tree, so its commit is HEAD** (found 2026-10-02):
	# `git log -- .` simplifies away a merge whose tree equals one parent's,
	# and v0.6.0, tagged on such a merge, built gexis-player 0.5.0+git21.
	if [ "$paths" = "." ]; then commit=$(git rev-parse HEAD); fi
	local v; v=$(git describe --tags --match 'v[0-9]*' --always "$commit" | sed -E 's/^v//; s/-([0-9]+)-g([0-9a-f]+)$/+git\1.\2/')
	# shellcheck disable=SC2046
	if [ -n "$(git status --porcelain -- $paths)" ]; then v="$v.dirty"; fi
	printf '%s' "$v"
}

# **Reproducible** (found 2026-10-01): dpkg-deb stamps the build time into
# the package, so a package rebuilt unchanged got new bytes, a new hash, and
# its part was uploaded again - 168 MB of skins every release. With
# SOURCE_DATE_EPOCH, the time of the commit the version names, the same
# version is the same file (measured: two builds of gexis-system identical
# with it, different without).
epoch_for() {
	# A component that carries its own version (peppyalsa, go-librespot,
	# Plexamp's pin...) has "." as its inputs, so the newest commit's time
	# gave it new bytes at every commit (found 2026-10-01: five of them
	# uploaded again with 0.3.2 at unchanged versions). Its own folder says
	# when it last changed. The player's "." is right: it is the release.
	local paths; paths=$(inputs "$1")
	if [ "$paths" = "." ] && [ "$1" != player ]; then paths="packaging/$1"; fi
	# shellcheck disable=SC2086
	git log -1 --format=%ct -- $paths
}

# Rebuilt when the Dockerfile changes: its hash is the image's label.
want=$(sha256sum packaging/builder.Dockerfile | cut -c1-12)
have=$(docker image inspect -f '{{index .Config.Labels "gexis.dockerfile"}}' gexis-deb-builder 2>/dev/null || true)
[ "$want" = "$have" ] \
	|| docker build --label "gexis.dockerfile=$want" -q --platform linux/arm64 -t gexis-deb-builder -f packaging/builder.Dockerfile packaging

mkdir -p packaging/out
# **A skin pack is rebuilt only when what it is built from changed** (George,
# 2026-10-02: "let's do this"). Its version names the commit of its inputs
# (`version_for`), and the same inputs build byte-identical packages
# (SOURCE_DATE_EPOCH above; checked for two sizes, 2026-10-01 and -02). So a
# pack whose exact file is in this cache is copied, not built - about eight
# of the ten minutes `make packages` took. Never a `.dirty` one.
DEB_CACHE="${GEXIS_DEB_CACHE:-$HOME/.cache/gexis-player/debs}"
mkdir -p "$DEB_CACHE"
reused=""
# The skin packs (ADR-0111) are built with the rest, and the release carries
# them all; the image installs none (decision 9: 01-packages leaves them out).
SKIN_PACKS="skins-1920x1080 skins-1280x400 skins-1480x320 skins-800x480 skins-1280x800"
for pkg in ${*:-core ui system skins $SKIN_PACKS peppyalsa peppy-engines go-librespot beszel-agent beszel-hub lyrion-server plexamp player}; do
	case "$pkg" in
		skins|skins-*)
			ver=$(version_for "$pkg")
			cached="$DEB_CACHE/gexis-${pkg}_${ver}_all.deb"
			case "$ver" in *.dirty) ;; *)
				if [ -f "$cached" ]; then
					cp "$cached" packaging/out/
					echo "reused $(basename "$cached"): its inputs have not changed"
					reused="$reused $(basename "$cached")"
					continue
				fi ;;
			esac ;;
	esac
	case "$pkg" in
		skins-*) script=/src/packaging/skin-packs/build.sh; extra=${pkg#skins-} ;;
		*) script="/src/packaging/$pkg/build.sh"; extra="" ;;
	esac
	# shellcheck disable=SC2086
	docker run --rm --platform linux/arm64 \
		-v "$PWD":/src:ro -v "$PWD/packaging/out":/out \
		-v "${GEXIS_BUILD_CACHE:-$HOME/.cache/gexis-player/downloads}":/cache \
		-e GEXIS_BUILD_CACHE=/cache -e SOURCE_DATE_EPOCH="$(epoch_for "$pkg")" \
		gexis-deb-builder bash "$script" "$(version_for "$pkg")" $extra
done
# The container writes as root; hand the results back.
docker run --rm -v "$PWD/packaging/out":/out alpine chown -R "$(id -u):$(id -g)" /out
# Keep what was just built for next time, and only the current set: an older
# version of a pack is never wanted again.
for deb in packaging/out/gexis-skins_*_all.deb packaging/out/gexis-skins-*_all.deb; do
	[ -f "$deb" ] || continue
	case "$deb" in *.dirty_all.deb) continue ;; esac
	[ -f "$DEB_CACHE/$(basename "$deb")" ] || cp "$deb" "$DEB_CACHE/"
done
for old in "$DEB_CACHE"/gexis-skins*_all.deb; do
	[ -f "$old" ] || continue
	[ -f "packaging/out/$(basename "$old")" ] || rm -f "$old"
done
[ -z "$reused" ] || echo "skin packs reused, not rebuilt:$reused"
