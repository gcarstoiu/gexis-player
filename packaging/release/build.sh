#!/bin/bash
# ADR-0108: build one release locally - two signed flat apt repositories, ours
# plus Raspberry Pi's part of the tested set, and Debian's part - from
# packaging/out and the image the release was tested as. Nothing is uploaded:
# packaging/release/publish.sh does that, on George's say-so.
#
# Usage: packaging/release/build.sh <image.img>
set -euo pipefail
cd "$(dirname "$0")/../.."

IMG="${1:?usage: packaging/release/build.sh <image.img>}"
OUT_DEBS=packaging/out
CACHE="${GEXIS_DEB_CACHE:-$HOME/.cache/gexis-player/os-debs}"
export GNUPGHOME="${GEXIS_RELEASE_GNUPGHOME:-$HOME/.gnupg-gexis-release}"
SIGNER='B6643AE345702FBA!'   # the release subkey (ADR-0105)
KEY=packaging/keys/gexis-release.asc

players=( "$OUT_DEBS"/gexis-player_*.deb )
[ "${#players[@]}" -eq 1 ] && [ -f "${players[0]}" ] || { echo "ERROR: need exactly one gexis-player in $OUT_DEBS" >&2; exit 1; }
VERSION=$(basename "${players[0]}" | sed -E 's/^gexis-player_(.*)_all\.deb$/\1/')
TAG="r${VERSION//+/-}"
DEST=packaging/release/out/$TAG
rm -rf "$DEST"; mkdir -p "$DEST/main" "$DEST/debian" "$CACHE"
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

# The tested set, each file checked against its archive's signed index.
docker run --rm --platform linux/arm64 \
	-v "$WORK":/in:ro -v "$CACHE":/cache -v "$PWD/$DEST":/out \
	-v "$PWD/packaging/release/fetch-tested-set.py":/fetch.py:ro \
	gexis-deb-builder python3 /fetch.py

# Ours, beside Raspberry Pi's half: exactly the versions the image has.
while read -r name version arch; do
	f="$OUT_DEBS/${name}_${version}_${arch}.deb"
	[ -f "$f" ] || { echo "ERROR: the image has $name $version, not in $OUT_DEBS" >&2; exit 1; }
	cp "$f" "$DEST/main/"
done < "$WORK/ours.txt"

# The indexes, then the signatures (on this machine: the key never enters a container).
for half in main debian; do
	docker run --rm --platform linux/arm64 -v "$PWD/$DEST/$half":/r gexis-deb-builder sh -c "
		cd /r && apt-ftparchive packages . > Packages && gzip -9kn Packages &&
		apt-ftparchive -o APT::FTPArchive::Release::Origin='Gexis Player' \
			-o APT::FTPArchive::Release::Label='Gexis Player' \
			-o APT::FTPArchive::Release::Suite='$TAG' -o APT::FTPArchive::Release::Codename='$TAG' \
			release . > Release"
	docker run --rm -v "$PWD/$DEST":/o alpine chown -R "$(id -u):$(id -g)" /o
	gpg --batch --yes -u "$SIGNER" --clearsign -o "$DEST/$half/InRelease" "$DEST/$half/Release"
	gpg --batch --yes -u "$SIGNER" -abs -o "$DEST/$half/Release.gpg" "$DEST/$half/Release"
done

# Checks: counts under GitHub's limit, the set complete, the signatures good.
for half in main debian; do
	n=$(find "$DEST/$half" -type f | wc -l)
	[ "$n" -lt 1000 ] || { echo "ERROR: $half has $n files; a GitHub release holds 1,000" >&2; exit 1; }
	gpg --batch --verify "$DEST/$half/InRelease" 2>/dev/null || { echo "ERROR: $half's InRelease does not verify" >&2; exit 1; }
done
# Counted from the image's status on its own terms - every record dpkg calls
# installed, whatever the selection - so a filter above cannot hide a package.
image_count=$(grep -cE '^Status: [a-z]+ ok installed$' "$WORK/status")
release_count=$(( $(ls "$DEST"/main/*.deb | wc -l) + $(ls "$DEST"/debian/*.deb | wc -l) ))
[ "$release_count" -eq "$image_count" ] || { echo "ERROR: $release_count packages in the release, the image has $image_count installed" >&2; exit 1; }
for pinned in libasound2t64; do
	ls "$DEST"/main/"${pinned}"_*.deb >/dev/null 2>&1 || { echo "ERROR: the pinned $pinned is not in the release" >&2; exit 1; }
done
du -sh "$DEST/main" "$DEST/debian" | sed 's/^/  /'
# Which image this release is (ADR-0105 as amended 2026-09-30): promoting it to
# stable attaches that image, so a new device starts from what an updated one has.
printf '%s\n' "$(realpath "$IMG")" > "$DEST/image.txt"
echo "built $DEST ($TAG, gexis-player $VERSION); nothing uploaded"
