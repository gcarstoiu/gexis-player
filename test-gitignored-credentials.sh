#!/bin/bash
# Asserts that files holding real credentials are actually gitignored -
# not that the rule looks right in a diff, but that `git check-ignore`
# agrees, on whatever branch this runs on.
#
# This exists because it silently regressed once already: the rule was
# added and merged into main, but a parallel branch (phase-2a-renderers)
# was cut before that merge and never got it back, so `git check-ignore`
# returned nothing there and a real Wi-Fi password sat untracked and
# unprotected. A rule that "looks right" on one branch proves nothing
# about any other branch working off the same tree - only actually
# running `git check-ignore` does.
#
# Run this directly, and on every branch, not just after editing
# .gitignore - that's exactly when it's least likely to be checked and
# most likely to have silently drifted.
set -euo pipefail

cd "$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"

# Add future credential-file paths here as they appear.
PATHS_THAT_MUST_BE_IGNORED=(
	"image/provision.local.env"
)

FAILED=0
for path in "${PATHS_THAT_MUST_BE_IGNORED[@]}"; do
	PRE_EXISTING=0
	[ -e "${path}" ] && PRE_EXISTING=1

	if [ "${PRE_EXISTING}" -eq 0 ]; then
		mkdir -p "$(dirname "${path}")"
		echo "test placeholder - $(basename "$0")" > "${path}"
	fi

	if git check-ignore -q "${path}"; then
		echo "OK: ${path} is gitignored"
	else
		echo "FAIL: ${path} is NOT gitignored - git check-ignore found no rule" >&2
		FAILED=1
	fi

	if [ "${PRE_EXISTING}" -eq 0 ]; then
		rm -f "${path}"
	fi
done

if [ "${FAILED}" -ne 0 ]; then
	echo "" >&2
	echo "One or more credential paths are not gitignored on this branch." >&2
	echo "A 'git add -A' here would stage real secrets. Fix .gitignore" >&2
	echo "before doing anything else." >&2
	exit 1
fi

echo "All credential paths confirmed gitignored."
