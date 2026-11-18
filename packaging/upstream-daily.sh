#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ADR-0182: run daily by .github/workflows/upstream.yml, on a checkout of
# main. For each pin packaging/check-upstream.sh finds behind:
# - a part packaged here (packaging/upstream-bump.py knows it) gets a branch
#   bump-<part>-<version> from main with the pin moved, its two files in the
#   `inputs` mirror, a pull request into main, and its tests and a preview
#   build started (a push by the workflow's own token starts no workflow);
# - anything else - fetched on the device (ADR-0100), pinned in another
#   repository, or a release the pin does not fit - gets an issue.
# Once per part and version: an existing pull request or issue, open or
# closed, stops it. A branch pushed without its pull request gets the pull
# request on the next run.
#
#   packaging/upstream-daily.sh [--dry-run]     --dry-run reads, and writes nothing
#
# Exit 0, or 1 once the rest is done when a maker's feed could not be read.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO=${GITHUB_REPOSITORY:-gcarstoiu/gexis-player}
DRY=
[ "${1:-}" = --dry-run ] && DRY=1
run() { if [ -n "$DRY" ]; then echo "  would run: $*"; else "$@"; fi; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

status=0
UPSTREAM_TSV="$work/behind.tsv" packaging/check-upstream.sh || status=$?
[ "$status" -le 2 ] || exit "$status"
touch "$work/behind.tsv"

# Where a pin that is not moved here lives, for the issue.
why() {
	case "$1" in
	plexamp) echo "Fetched on the device from its maker (ADR-0100); the pin is in gcarstoiu/gexis-plexamp (\`plexamp.pin\`)." ;;
	lyrion) echo "Fetched on the device from the Lyrion community (ADR-0115 decision 11); the pin is \`image/stage-gexis/10-lyrion/files/lyrion.env\`." ;;
	beszel) echo "A catalogue plugin (ADR-0174); the pin is in gcarstoiu/gexis-beszel (\`pins.sh\`), which this workflow cannot write." ;;
	shairport-sync|nqptp) echo "Built here from the tag's commit (ADR-0167), moved by hand: \`TAG\`, \`COMMIT\`, \`COMMIT_DATE\` and the archive's and source tree's sha256 in \`packaging/$1/build.sh\` (as \`fetch-source.sh\` checks them), the archive's line in \`packaging/inputs.tsv\` and the \`inputs\` mirror, the revision back to 1 in it and \`packaging/revisions.json\`; a preview with AirPlay on." ;;
	*) echo "Not a pin this workflow moves." ;;
	esac
}

issue() {  # id name pinned latest page [reason]
	local title="Upstream: $2 $4"
	# Matched whole, not searched: the search reads brackets and colons itself.
	if gh issue list -R "$REPO" --state all --limit 1000 --json title --jq '.[].title' | grep -qxF "$title"; then
		echo "$title: its issue exists"; return
	fi
	echo "$title: an issue"
	run gh issue create -R "$REPO" --title "$title" --body "$(printf '%s\n' \
		"**$2 $4** is out; the player pins $3." "" "Release: $5" "" "${6:-$(why "$1")}" "" \
		"Opened by \`.github/workflows/upstream.yml\` (ADR-0182).")"
}

pull_request() {  # id name pinned latest page
	local id=$1 name=$2 pinned=$3 tag=$4 page=$5
	local branch="bump-$id-${tag#v}" title="$name ${tag#v}"
	if [ -n "$(gh pr list -R "$REPO" --state all --head "$branch" --json number --jq '.[].number')" ]; then
		echo "$title: its pull request exists"; return
	fi
	echo "$title: a pull request from $branch"
	if [ -n "$DRY" ]; then
		echo "  would move the pin on $branch from main, fill the mirror and push it"
	elif ! git ls-remote --exit-code --heads origin "$branch" >/dev/null; then
		local why_not=
		git switch -q -c "$branch" origin/main
		python3 packaging/upstream-bump.py "$id" "$tag" --keep "$work/mirror" 2>"$work/why" || {
			[ $? -eq 3 ] || { cat "$work/why" >&2; exit 1; }
			why_not=$(cat "$work/why")
		}
		if [ -n "$why_not" ]; then
			git switch -q - && git branch -q -D "$branch"
			issue "$id" "$name" "$pinned" "$tag" "$page" "The pin was not moved: ${why_not#not moved: }"
			return
		fi
		git diff --stat
		git -c user.name='github-actions[bot]' -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
			commit -q -am "$title (upstream's release; ADR-0182)"
		# The mirror first, so the branch never names a file it lacks (ADR-0173).
		have=$(gh release view inputs -R "$REPO" --json assets --jq '.assets[].name')
		for f in "$work"/mirror/*; do
			grep -qxF "$(basename "$f")" <<<"$have" || gh release upload inputs -R "$REPO" "$f"
		done
		rm -rf "$work/mirror"
		git push -q origin "$branch"
		git switch -q -
	fi
	run gh pr create -R "$REPO" --base main --head "$branch" --title "$title" --body "$(printf '%s\n' \
		"**$name ${tag#v}**, upstream's release: $page" \
		"" \
		"Pinned until now: $pinned. Moved by \`.github/workflows/upstream.yml\` (ADR-0182): the pin (version, address, sha256) and the binary's and its source's lines in \`packaging/inputs.tsv\`; both files are in the \`inputs\` mirror." \
		"" \
		"Started on this branch: the tests and a preview build (*Release build*, kind preview)." \
		"" \
		"Before it is merged (ADR-0182, a patch release for one part): the preview on a test player, the part's checklist in \`docs/tech/updates-and-releases.md\`, one line of notes approved by George, and the release tagged on this branch.")"
	run gh workflow run tests.yml -R "$REPO" --ref "$branch"
	run gh workflow run release.yml -R "$REPO" --ref "$branch" -f ref="$branch" -f kind=preview
}

moved_here=$(python3 packaging/upstream-bump.py --parts)
# Read on its own descriptor: nothing in the loop takes the list as its input.
while IFS=$'\t' read -r -u 3 id name pinned latest page; do
	if grep -qxF "$id" <<<"$moved_here"; then
		pull_request "$id" "$name" "$pinned" "$latest" "$page"
	else
		issue "$id" "$name" "$pinned" "$latest" "$page"
	fi
done 3<"$work/behind.tsv"

if [ "$status" -eq 2 ]; then
	echo "::warning::a maker's feed could not be read (above)"
	exit 1
fi
exit 0
