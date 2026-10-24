#!/bin/bash
# Finding 131: every skin of every pack the image carries, through the driver
# that ships and the engine it runs (frames.py), before the image is built:
#
#     packaging/skin-packs/check.sh [<deb dir> ...]
#
# Takes gexis-peppy-engines and each gexis-skins-<W>x<H> from packaging/out,
# else the newest in the build cache ($GEXIS_DEB_CACHE), else the newest a
# release published (~/projects/gexis-release-out). Fails if any
# skin of any pack fails.
set -euo pipefail
cd "$(dirname "$0")/../.."
dirs=("$@")
[ ${#dirs[@]} -gt 0 ] || dirs=(packaging/out "${GEXIS_DEB_CACHE:-$HOME/.cache/gexis-player/debs}" "${HOME}/projects/gexis-release-out")
# The newest file of that name in the first directory that has one (the
# release output keeps one copy per release, so it is searched deep).
newest() {
	local d found
	for d in "${dirs[@]}"; do
		[ -d "$d" ] || continue
		found=$(find "$d" -name "$1" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true)
		[ -z "$found" ] || { echo "$found"; return; }
	done
}
engines=$(newest 'gexis-peppy-engines_*.deb')
[ -n "$engines" ] || { echo "ERROR: no gexis-peppy-engines .deb in ${dirs[*]}" >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
unpack() { mkdir -p "$2" && (cd "$2" && ar x "$1" && tar xf data.tar.* && rm -f data.tar.* control.tar.* debian-binary); }
unpack "$(realpath "$engines")" "$work/engines"
docker build -q -t gexis-skins-check -f packaging/skin-packs/check.Dockerfile packaging/skin-packs >/dev/null
status=0
for size in 1280x800 800x480 1280x400 1480x320 1920x1080; do
	deb=$(newest "gexis-skins-${size}_*.deb")
	if [ -z "$deb" ]; then echo "$size: no pack to check"; continue; fi
	unpack "$(realpath "$deb")" "$work/$size"
	echo "== $(basename "$deb")"
	docker run --rm -v "$PWD:/src:ro" -v "$work/$size/opt/gexis-peppy/packs/$size:/pack:ro" \
		-v "$work/engines/opt/gexis-peppy:/engines:ro" gexis-skins-check \
		python /src/packaging/skin-packs/frames.py /pack "$size" /engines 2>&1 \
		| grep -v -E '^peppy: skin ->|libpng warning' || status=1
	[ "${PIPESTATUS[0]}" -eq 0 ] || status=1
done
exit $status
