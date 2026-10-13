#!/bin/sh
# ADR-0145: Squeezelite's decoders end to end, upstream against patched, on
# the build machine. Builds both in an amd64 Debian trixie container (the
# device's release and libraries, its architecture aside) from the pinned
# commit, with Debian's options, and runs decoder_test.py against them.
#   packaging/squeezelite/tests/run-decoder-tests.sh
# Needs docker and network access (the upstream clone).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
docker build -q -t gexis-squeezelite-test -f "$here/test.Dockerfile" "$here" >/dev/null
COMMIT=$(sed -n 's/^COMMIT=//p' "$here/../build.sh")
docker run --rm -v "$repo":/src:ro gexis-squeezelite-test bash -c "
set -eu
git clone -q https://github.com/ralph-irving/squeezelite.git /tmp/up
git -C /tmp/up checkout -q $COMMIT
cp -r /tmp/up /tmp/pa
git -C /tmp/pa apply /src/packaging/squeezelite/squeezelite-downmix.patch
export DEB_BUILD_MAINT_OPTIONS=hardening=+all DEB_CFLAGS_MAINT_PREPEND=-Wall
eval \"\$(dpkg-buildflags --export=sh)\"
for d in /tmp/up /tmp/pa; do
	make -C \$d -s -j\$(nproc) EXECUTABLE=squeezelite \
		OPTS='-DDSD -DFFMPEG -DRESAMPLE -DVISEXPORT -DLINKALL -DIR -DUSE_SSL -DOPUS -I/usr/include/opus' >/dev/null 2>&1
done
cc -O2 -o /tmp/dsfgen /src/tools/dsd-test-file/dsfgen.c -lm
python3 /src/packaging/squeezelite/tests/decoder_test.py \
	--upstream /tmp/up/squeezelite --patched /tmp/pa/squeezelite --dsfgen /tmp/dsfgen $*
"
