#!/bin/bash
# ADR-0108: build one release - its parts, flat apt repositories of ours, the
# skin packs, and Raspberry Pi's and Debian's parts of the tested set - from
# packaging/out and the image the release was tested as. Nothing is uploaded:
# packaging/release/publish.sh does that, on George's say-so.
#
# Usage: packaging/release/build.sh <image.img> [--unsigned]
#
# **--unsigned on GitHub** (ADR-0173): the key is on R2D2 alone, which signs
# with packaging/release/sign.sh. Earlier releases are read from GitHub, their
# indexes proven by the release key (published.py), so nothing here needs a
# release built on this machine.
set -euo pipefail
cd "$(dirname "$0")/../.."

IMG="${1:?usage: packaging/release/build.sh <image.img> [--unsigned]}"
SIGN=1; [ "${2:-}" = --unsigned ] && SIGN=0
OUT_DEBS=packaging/out
CACHE="${GEXIS_DEB_CACHE:-$HOME/.cache/gexis-player/os-debs}"

players=( "$OUT_DEBS"/gexis-player_*.deb )
[ "${#players[@]}" -eq 1 ] && [ -f "${players[0]}" ] || { echo "ERROR: need exactly one gexis-player in $OUT_DEBS" >&2; exit 1; }
VERSION=$(basename "${players[0]}" | sed -E 's/^gexis-player_(.*)_all\.deb$/\1/')
TAG="r${VERSION//+/-}"
DEST=packaging/release/out/$TAG
KINDS="ours skins rpi debian"   # ADR-0108 as amended: a release is parts
rm -rf "$DEST"; mkdir -p "$CACHE"; for k in $KINDS; do mkdir -p "$DEST/$k"; done
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
# Readable by apt's own unprivileged user, which checks the signatures: it
# holds only public keyrings and a package list.
chmod 755 "$WORK"

# The image: its OS packages, and the keyrings it trusts its archives with.
start=$(sfdisk -d "$IMG" | awk '/start=/{n++; if(n==2){sub(/.*start= */,""); sub(/,.*/,""); print}}')
FS="${IMG}?offset=$((start * 512))"
debugfs -R "dump /var/lib/dpkg/status $WORK/status" "$FS" 2>/dev/null
image_player=$(awk -v RS= '/^Package: gexis-player\n/' "$WORK/status" | sed -n 's/^Version: //p')
[ "$image_player" = "$VERSION" ] || { echo "ERROR: the image has gexis-player $image_player, packaging/out has $VERSION: build the release from the image it was tested as" >&2; exit 1; }
# One record per installed package: name, version, architecture.
# Installed whether held or not: alsa-lib is held (`apt-mark hold`), and dpkg
# writes that as `hold ok installed` - the first version of this script took
# only `install ok installed` and left out the one package the pin protects.
awk -v RS= '/\nStatus: [a-z]+ ok installed/ {
	p = v = a = ""; n = split($0, L, "\n")
	for (i = 1; i <= n; i++) {
		if (L[i] ~ /^Package: /) p = substr(L[i], 10)
		else if (L[i] ~ /^Version: /) v = substr(L[i], 10)
		else if (L[i] ~ /^Architecture: /) a = substr(L[i], 15)
	}
	print p, v, a
}' "$WORK/status" | sort -u > "$WORK/all.txt"
grep -v '^gexis-' "$WORK/all.txt" > "$WORK/installed.txt"
grep '^gexis-' "$WORK/all.txt" > "$WORK/ours.txt"
mkdir -p "$WORK/keyrings"
for k in debian-archive-keyring.pgp raspberrypi-archive-keyring.pgp; do
	debugfs -R "dump /usr/share/keyrings/$k $WORK/keyrings/$k" "$FS" 2>/dev/null
	[ -s "$WORK/keyrings/$k" ] || { echo "ERROR: $k not in the image" >&2; exit 1; }
done
echo "release $TAG: tested set of $(wc -l < "$WORK/installed.txt") OS packages, from $(basename "$IMG")"

# What every published part holds, each index proven by the release key; kept
# between runs in GEXIS_PUBLISHED if it is set.
INDEXES=$(realpath -m "${GEXIS_PUBLISHED:-$WORK/published}")
packaging/release/published.py indexes "$INDEXES"

# The tested set, each file checked against its archive's signed index.
docker run --rm --platform linux/arm64 \
	-v "$WORK":/in:ro -v "$CACHE":/cache -v "$PWD/$DEST":/out -v "$INDEXES":/prev:ro \
	-v "$PWD/packaging/release/fetch-tested-set.py":/fetch.py:ro \
	gexis-deb-builder python3 /fetch.py

# Ours: exactly the versions the image has, the skins apart - 176 MB that
# rarely change, their own part so they are not uploaded again with ours.
while read -r name version arch; do
	f="$OUT_DEBS/${name}_${version}_${arch}.deb"
	[ -f "$f" ] || { echo "ERROR: the image has $name $version, not in $OUT_DEBS" >&2; exit 1; }
	case "$name" in gexis-skins) cp "$f" "$DEST/skins/";; *) cp "$f" "$DEST/ours/";; esac
done < "$WORK/ours.txt"
# **Every size's skin pack, though the image has none** (ADR-0111 decisions 5
# and 9): a device installs its own from the release, with consent. One
# version of each: two would leave the device to choose between builds.
packs=0
for size in 1920x1080 1280x400 1480x320 800x480 1280x800; do
	found=( "$OUT_DEBS"/gexis-skins-"$size"_*_all.deb )
	[ "${#found[@]}" -eq 1 ] && [ -f "${found[0]}" ] \
		|| { echo "ERROR: need exactly one gexis-skins-$size in $OUT_DEBS, found ${#found[@]}" >&2; exit 1; }
	cp "${found[0]}" "$DEST/skins/"
	packs=$((packs + 1))
done
# A pack rebuilt at a published version differs in bytes (BUILD-TRAPS, 1.4.0):
# the published file is the release's. None is in the image.
packaging/release/published.py prefer "$INDEXES" "$DEST/skins"

# Each part: its index and its name from that index; sign.sh signs it.
# **Named by content**
# (ADR-0108 as amended): the same packages give the same Packages file and so
# the same name, and a part already on GitHub is not uploaded again. The name
# is the part's suite, so apt can prefer it when going back.
mkdir -p "$DEST/repos"
: > "$DEST/parts.txt"
# **Each file is uploaded once, ever** (ADR-0108 as amended 2026-10-01): what
# a published part already holds is fetched from there (reuse.py).
for kind in $KINDS; do
	# **Named as GitHub will name them** (found 2026-10-01): GitHub renames an
	# uploaded file, `~` becoming `.`, and 73 of the tested set's packages
	# have a `~` in their version - `chromium_154.0.8037.57-1~deb13u1+rpt1`.
	# apt asks for the name its index gives, so the index has to give the name
	# the file will have: renamed here, before indexing. Anything outside
	# letters, digits and `._+-` is renamed the same way.
	for f in "$DEST/$kind"/*.deb; do
		b=$(basename "$f"); safe=$(printf '%s' "$b" | sed 's/[^A-Za-z0-9._+-]/./g')
		[ "$b" = "$safe" ] && continue
		[ -e "$DEST/$kind/$safe" ] && { echo "ERROR: $b and $safe would be one file on GitHub" >&2; exit 1; }
		mv "$f" "$DEST/$kind/$safe"
	done
	docker run --rm --platform linux/arm64 -v "$PWD/$DEST/$kind":/r gexis-deb-builder sh -c "
		cd /r && apt-ftparchive packages . > Packages && gzip -9kn Packages"
	docker run --rm -v "$PWD/$DEST":/o alpine chown -R "$(id -u):$(id -g)" /o
	# A file a published part already holds, byte for byte, is fetched from
	# there (`Filename: ../<part>/<file>`) and this part does not carry it.
	packaging/release/reuse.py part "$DEST/$kind" "$INDEXES" > "$WORK/reused-$kind"
	gzip -9kn -f "$DEST/$kind/Packages"
	name="$kind-$(sha256sum "$DEST/$kind/Packages" | cut -c1-12)"
	docker run --rm --platform linux/arm64 -v "$PWD/$DEST/$kind":/r gexis-deb-builder sh -c "
		cd /r && apt-ftparchive -o APT::FTPArchive::Release::Origin='Gexis Player' \
			-o APT::FTPArchive::Release::Label='Gexis Player' \
			-o APT::FTPArchive::Release::Suite='$name' -o APT::FTPArchive::Release::Codename='$name' \
			release . > Release"
	docker run --rm -v "$PWD/$DEST":/o alpine chown -R "$(id -u):$(id -g)" /o
	while read -r f; do rm "$DEST/$kind/$f"; done < "$WORK/reused-$kind"
	echo "  $kind: $(grep -c '^Package:' "$DEST/$kind/Packages") packages, $(wc -l < "$WORK/reused-$kind") already on GitHub, $(ls "$DEST/$kind"/*.deb 2>/dev/null | wc -l) to upload"
	mv "$DEST/$kind" "$DEST/repos/$name"
	printf '%s %s\n' "$kind" "$name" >> "$DEST/parts.txt"
done

# Checks: counts under GitHub's limit (two signatures to come), the set complete.
for part in "$DEST"/repos/*/; do
	n=$(find "$part" -type f | wc -l)
	[ "$n" -lt 998 ] || { echo "ERROR: $(basename "$part") has $n files; a GitHub release holds 1,000" >&2; exit 1; }
done
# Counted from the image's status on its own terms - every record dpkg calls
# installed, whatever the selection - so a filter above cannot hide a package.
# The skin packs are counted apart: they are in the release and not in the
# image (ADR-0111), so the image's count plus the packs is the release's.
image_count=$(grep -cE '^Status: [a-z]+ ok installed$' "$WORK/status")
release_count=$(cat "$DEST"/repos/*/Packages | grep -c '^Package:')
pack_count=$(cat "$DEST"/repos/skins-*/Packages | grep -cE '^Package: gexis-skins-[0-9]+x[0-9]+$')
[ "$pack_count" -eq "$packs" ] || { echo "ERROR: $pack_count skin packs in the skins part, $packs copied" >&2; exit 1; }
if grep -qE '^Package: gexis-skins-[0-9]+x[0-9]+$' "$WORK/status"; then
	echo "ERROR: the image has a skin pack installed (ADR-0111 decision 9)" >&2; exit 1
fi
[ "$release_count" -eq "$((image_count + pack_count))" ] || { echo "ERROR: $release_count packages in the release, the image has $image_count installed and $pack_count skin packs go beside them" >&2; exit 1; }
for pinned in libasound2t64; do
	grep -qx "Package: $pinned" "$DEST"/repos/rpi-*/Packages || { echo "ERROR: the pinned $pinned is not in the release" >&2; exit 1; }
done

# The release's own list of its parts, signed by sign.sh: what the updater
# reads to go back to this release once a later one is installed.
{
	printf 'Release: %s\n' "$VERSION"
	printf 'Parts: %s\n' "$(awk '{print $2}' "$DEST/parts.txt" | tr '\n' ' ' | sed 's/ $//')"
} > "$DEST/parts.plain"
du -sh "$DEST"/repos/* | sed 's|packaging/release/out/[^/]*/repos/||; s/^/  /'
# Which image this release is (ADR-0105 as amended 2026-09-30): promoting it to
# stable attaches that image, so a new device starts from what an updated one has.
printf '%s\n' "$(realpath "$IMG")" > "$DEST/image.txt"
if [ "$SIGN" = 1 ]; then packaging/release/sign.sh "$DEST"; fi
echo "built $DEST ($TAG, gexis-player $VERSION)$([ "$SIGN" = 1 ] || echo ', unsigned'); nothing uploaded"
