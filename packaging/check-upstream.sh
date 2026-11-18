#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ADR-0100, amended 2026-10-03 (George: "We go with A"): **we choose the
# version** of the software the player fetches from its maker. Run before
# every release, and daily on GitHub (ADR-0182, packaging/upstream-daily.sh):
# it reads each maker's own "latest" feed - for what the player fetches and
# for what we package (Beszel, go-librespot, CamillaDSP, Shairport Sync,
# NQPTP) - and says which
# pins are behind. Nothing is changed here - a newer version is tried on the
# player as a preview before its pin is moved.
#
# Exit 0: every pin is current. Exit 1: at least one is behind. Exit 2: a
# feed could not be read (that is not "current").
#
# With UPSTREAM_TSV naming a file, each pin that is behind is also added to it
# as a line - id, name, pinned, latest, the release's page - for
# packaging/upstream-daily.sh (ADR-0182).
set -uo pipefail
cd "$(dirname "$0")/.."

status=0
pin() { sed -n "s/^$2=//p" "$1" | tr -d '"'; }
behind() {  # id name pinned latest page
	[ -z "${UPSTREAM_TSV:-}" ] || printf '%s\t%s\t%s\t%s\t%s\n' "$@" >>"$UPSTREAM_TSV"
}
report() {  # id name pinned latest page
	if [ -z "$4" ]; then
		echo "?  $2: pinned $3, the maker's feed could not be read"; [ $status -eq 0 ] && status=2
	elif [ "$3" = "$4" ]; then
		echo "ok $2: $3 is the latest"
	else
		echo "!! $2: pinned $3, the maker has $4"; status=1
		behind "$@"
	fi
}
gh_page() { echo "https://github.com/$1/releases/tag/$2"; }

# Plexamp: Plex publishes the headless build's latest version as JSON. The
# pin is the catalogue plugin's since ADR-0174 (gcarstoiu/gexis-plexamp).
plex_have=$(curl -fsS --max-time 20 https://raw.githubusercontent.com/gcarstoiu/gexis-plexamp/main/plexamp.pin 2>/dev/null \
	| sed -n 's/^URL=.*-v\([0-9.]*\)\.tar\.bz2$/\1/p')
plex_latest=$(curl -fsS --max-time 20 https://plexamp.plex.tv/headless/version.json 2>/dev/null \
	| python3 -c 'import json, sys; print(json.load(sys.stdin)["latestVersion"])' 2>/dev/null)
report plexamp Plexamp "$plex_have" "$plex_latest" https://plexamp.plex.tv/headless/version.json

# Lyrion: the community's repository lists each build; ours is `tararm`.
lyrion_pin=image/stage-gexis/10-lyrion/files/lyrion.env
lyrion_have=$(pin "$lyrion_pin" URL | sed -E 's/.*lyrionmusicserver-([0-9.]+)-arm-linux\.tgz$/\1/')
lyrion_latest=$(curl -fsS --max-time 20 https://lyrion.org/lms-server-repository/latest.xml 2>/dev/null \
	| grep -o '<tararm [^>]*' | sed -n 's/.* version="\([^"]*\)".*/\1/p')
report lyrion Lyrion "$lyrion_have" "$lyrion_latest" https://lyrion.org/lms-server-repository/latest.xml

# **The components we package from GitHub releases** (George, 2026-10-08: "I see
# the client is already older than the latest release of the beszel client" -
# this check named only the two fetched on the device, so Beszel and
# go-librespot fell behind unseen). Each one's latest release, by tag.
# With GH_TOKEN set (the daily workflow), GitHub's API is asked with it: a
# runner's address shares the 60 calls an hour GitHub allows without one.
auth=()
[ -z "${GH_TOKEN:-}" ] || auth=(-H "Authorization: Bearer $GH_TOKEN")
gh_latest() {
	curl -fsS --max-time 20 "${auth[@]}" "https://api.github.com/repos/$1/releases/latest" 2>/dev/null \
		| python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])' 2>/dev/null
}
# Beszel's agent and hub are catalogue plugins since ADR-0174: their pin is in
# their own repository.
beszel_have=$(curl -fsS --max-time 20 https://raw.githubusercontent.com/gcarstoiu/gexis-beszel/main/pins.sh 2>/dev/null \
	| sed -n 's/^BESZEL_VERSION="\(.*\)"/\1/p')
beszel_latest=$(gh_latest henrygd/beszel)
report beszel "Beszel (gexis-beszel)" "$beszel_have" "$beszel_latest" "$(gh_page henrygd/beszel "$beszel_latest")"
# **A pin on upstream's own build** (ADR-0181) waits for the first release
# that contains its commit: GitHub's compare says whether the release tag is
# that commit or after it.
report_build() {  # id name pinned repo commit latest-tag
	local how
	how=$(curl -fsS --max-time 20 "${auth[@]}" "https://api.github.com/repos/$4/compare/$5...$6" 2>/dev/null \
		| python3 -c 'import json, sys; print(json.load(sys.stdin)["status"])' 2>/dev/null)
	if [ -z "$6" ] || [ -z "$how" ]; then
		echo "?  $2: pinned $3, the maker's feed could not be read"; [ $status -eq 0 ] && status=2
	elif [ "$how" = ahead ] || [ "$how" = identical ]; then
		echo "!! $2: pinned $3, upstream's build; $6 contains it"; status=1
		behind "$1" "$2" "$3" "$6" "$(gh_page "$4" "$6")"
	else
		echo "ok $2: $3, upstream's build; no release contains it yet ($6 is the latest)"
	fi
}
librespot_pin=$(pin packaging/go-librespot/pins.sh GO_LIBRESPOT_VERSION)
librespot_latest=$(gh_latest devgianlu/go-librespot)
case "$librespot_pin" in
*+git*) report_build go-librespot go-librespot "$librespot_pin" devgianlu/go-librespot \
	"$(pin packaging/go-librespot/pins.sh GO_LIBRESPOT_COMMIT)" "$librespot_latest" ;;
*) report go-librespot go-librespot "$librespot_pin" "$librespot_latest" \
	"$(gh_page devgianlu/go-librespot "$librespot_latest")" ;;
esac
camilla_latest=$(gh_latest HEnquist/camilladsp)
report camilladsp CamillaDSP "$(pin packaging/camilladsp/pins.sh CAMILLADSP_VERSION)" "$camilla_latest" \
	"$(gh_page HEnquist/camilladsp "$camilla_latest")"
# AirPlay's two (ADR-0167), built here from a tag's commit, pinned in their
# build scripts (George, 2026-11-18: Shairport Sync 5.6.3 was out a week
# before anyone saw it). Their tags have no `v`.
for part in shairport-sync:"Shairport Sync" nqptp:NQPTP; do
	id=${part%%:*}
	latest=$(gh_latest "mikebrady/$id")
	report "$id" "${part#*:}" "$(pin "packaging/$id/build.sh" TAG)" "$latest" "$(gh_page "mikebrady/$id" "$latest")"
done

exit $status
