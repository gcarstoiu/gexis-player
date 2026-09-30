#!/bin/sh
# ADR-0107: gexis-core as a Debian package. Runs inside gexis-deb-builder
# (arm64 trixie), with the repository at /src and the output in /out.
#
# The environment is built at its real path, /opt/gexis-core/venv, because a
# venv is not relocatable: its scripts name that path in their first line.
# Every file pip installs is checked against packaging/core/*.lock, the core
# itself included only as a wheel built here from /src/core.
set -eu

VERSION="$1"
VENV=/opt/gexis-core/venv
STAGE=/tmp/stage/gexis-core

rm -rf "$VENV" /tmp/stage /tmp/wheels /tmp/buildenv
python3 -m venv /tmp/buildenv
/tmp/buildenv/bin/pip install -q --no-cache-dir --require-hashes \
	-r /src/packaging/core/build-requirements.lock
# The core's own wheel, with the locked build backend and nothing fetched.
cp -r /src/core /tmp/core-src
rm -rf /tmp/core-src/.pytest_cache /tmp/core-src/build
find /tmp/core-src -name __pycache__ -type d -prune -exec rm -rf {} +
/tmp/buildenv/bin/pip wheel -q --no-cache-dir --no-deps --no-build-isolation \
	-w /tmp/wheels /tmp/core-src

python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --no-cache-dir --require-hashes --no-deps \
	-r /src/packaging/core/requirements.lock
"$VENV/bin/pip" install -q --no-cache-dir --no-deps /tmp/wheels/gexis_core-*.whl
# pip is the one thing in the venv nobody runs on the device; it stays so a
# developer can inspect the environment, and costs ~10 MB.

mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/gexis-core"
cp -a "$VENV" "$STAGE/opt/gexis-core/"
PYV=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
NEXT=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1] + 1}")')
cat > "$STAGE/DEBIAN/control" <<EOF
Package: gexis-core
Version: $VERSION
Architecture: arm64
Maintainer: Gexis Player <noreply@github.com>
Depends: python3 (>= $PYV), python3 (<< $NEXT)
Section: sound
Priority: optional
Description: Gexis Player's core, in its own Python environment
 Arbitration, the state and settings API, and the panel's server, with every
 Python dependency pinned by hash (ADR-0107).
EOF
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-core_${VERSION}_arm64.deb" >/dev/null
echo "/out/gexis-core_${VERSION}_arm64.deb"
