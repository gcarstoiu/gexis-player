# Shared by the packages built from another project's source (ADR-0173):
# GitHub's archive of a pinned commit, through the build cache (ADR-0042) and
# so the inputs mirror, checked as the clone it replaces was.
#
# fetch_source <owner/repo> <commit> <archive sha256> <commit date> <tree sha256> <dir>
#
# The tree sha256 is every file's sha256, sorted by name - the same sum the
# clone's tracked files gave, so the pins did not change.

. /src/image/stage-gexis/fetch-cached.sh

fetch_source() {
	local repo="$1" commit="$2" sum="$3" date="$4" tree="$5" dir="$6"
	local archive="/tmp/${repo##*/}-$commit.tar.gz" got
	fetch_cached "https://codeload.github.com/$repo/tar.gz/$commit" "$sum" "$archive" || return 1
	# git archive names the commit in the archive and dates every file by it.
	got=$(gzip -dc "$archive" | git get-tar-commit-id)
	[ "$got" = "$commit" ] || { echo "ERROR: $repo's archive is of $got, the pin says $commit" >&2; return 1; }
	rm -rf "$dir"; mkdir -p "$dir"
	tar -xzf "$archive" -C "$dir" --strip-components=1 --no-same-owner
	rm -f "$archive"
	got=$(cd "$dir" && TZ=UTC find . -maxdepth 1 -type f -printf '%TY%Tm%Td\n' -quit)
	[ "$got" = "$date" ] || { echo "ERROR: $commit is dated $got, the pin says $date" >&2; return 1; }
	got=$(cd "$dir" && find . \( -type f -o -type l \) -printf '%P\0' | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)
	[ "$got" = "$tree" ] || { echo "ERROR: $repo $commit source is $got, pinned $tree" >&2; return 1; }
}
