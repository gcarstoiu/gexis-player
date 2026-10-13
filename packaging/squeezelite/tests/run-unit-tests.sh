#!/bin/sh
# ADR-0145: the fold-down helper's unit tests, on the build machine (any
# architecture, any C99 compiler). downmix.c and downmix.h are taken out of
# squeezelite-downmix.patch, so what is tested is what the package builds.
#   packaging/squeezelite/tests/run-unit-tests.sh
set -eu
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
git init -q .
git apply --include='downmix.c' --include='downmix.h' "$here/../squeezelite-downmix.patch"
[ -f downmix.c ] && [ -f downmix.h ] || { echo "ERROR: the patch carries no downmix.c/.h" >&2; exit 1; }
${CC:-cc} -std=gnu99 -O2 -Wall -Wextra -Werror -I. -o downmix_test "$here/downmix_test.c" downmix.c -lm
./downmix_test
