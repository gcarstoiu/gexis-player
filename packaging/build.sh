#!/bin/sh
# ADR-0107: build our Debian packages into packaging/out/, in the arm64
# builder container. Usage: packaging/build.sh [package ...] (default: all).
set -eu
cd "$(dirname "$0")/.."

# 0.2.1-819-g0bf1f48 -> 0.2.1+git819.0bf1f48: later commits sort later.
describe=$(git describe --tags --always)
VERSION=$(printf '%s' "$describe" | sed -E 's/^v//; s/-([0-9]+)-g([0-9a-f]+)$/+git\1.\2/')
if [ -n "$(git status --porcelain -- core ui packaging)" ]; then
	VERSION="$VERSION.dirty"
fi

docker image inspect gexis-deb-builder >/dev/null 2>&1 \
	|| docker build -q --platform linux/arm64 -t gexis-deb-builder -f packaging/builder.Dockerfile packaging

mkdir -p packaging/out
for pkg in ${*:-core ui}; do
	docker run --rm --platform linux/arm64 \
		-v "$PWD":/src:ro -v "$PWD/packaging/out":/out \
		gexis-deb-builder sh "/src/packaging/$pkg/build.sh" "$VERSION"
done
# The container writes as root; hand the results back.
docker run --rm -v "$PWD/packaging/out":/out alpine chown -R "$(id -u):$(id -g)" /out
