#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ADR-0100, amended 2026-10-03 (George: "We go with A"): **we choose the
# version** of the software the player fetches from its maker. Run before
# every release: it reads each maker's own "latest" feed - for what the player
# fetches and for what we package (Beszel, go-librespot) - and says which pins
# are behind. Nothing is changed here - a newer version is tried on the
# player as a preview before its pin is moved.
#
# Exit 0: every pin is current. Exit 1: at least one is behind. Exit 2: a
# feed could not be read (that is not "current").
set -uo pipefail
cd "$(dirname "$0")/.."

status=0
pin() { sed -n "s/^$2=//p" "$1" | tr -d '"'; }
report() {  # name pinned latest
	if [ -z "$3" ]; then
		echo "?  $1: pinned $2, the maker's feed could not be read"; [ $status -eq 0 ] && status=2
	elif [ "$2" = "$3" ]; then
		echo "ok $1: $2 is the latest"
	else
		echo "!! $1: pinned $2, the maker has $3"; status=1
	fi
}

# Plexamp: Plex publishes the headless build's latest version as JSON.
plex_pin=image/stage-gexis/03-core/files/components/plexamp.env
plex_have=$(pin "$plex_pin" URL | sed -E 's/.*-v([0-9.]+)\.tar\.bz2$/\1/')
plex_latest=$(curl -fsS --max-time 20 https://plexamp.plex.tv/headless/version.json 2>/dev/null \
	| python3 -c 'import json, sys; print(json.load(sys.stdin)["latestVersion"])' 2>/dev/null)
report Plexamp "$plex_have" "$plex_latest"

# Lyrion: the community's repository lists each build; ours is `tararm`.
lyrion_pin=image/stage-gexis/10-lyrion/files/lyrion.env
lyrion_have=$(pin "$lyrion_pin" URL | sed -E 's/.*lyrionmusicserver-([0-9.]+)-arm-linux\.tgz$/\1/')
lyrion_latest=$(curl -fsS --max-time 20 https://lyrion.org/lms-server-repository/latest.xml 2>/dev/null \
	| grep -o '<tararm [^>]*' | sed -n 's/.* version="\([^"]*\)".*/\1/p')
report Lyrion "$lyrion_have" "$lyrion_latest"

# **The components we package from GitHub releases** (George, 2026-10-08: "I see
# the client is already older than the latest release of the beszel client" -
# this check named only the two fetched on the device, so Beszel and
# go-librespot fell behind unseen). Each one's latest release, by tag.
gh_latest() {
	curl -fsS --max-time 20 "https://api.github.com/repos/$1/releases/latest" 2>/dev/null \
		| python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])' 2>/dev/null
}
report "Beszel agent" "$(pin packaging/beszel-agent/pins.sh BESZEL_VERSION)" "$(gh_latest henrygd/beszel)"
report "Beszel hub" "$(pin packaging/beszel-hub/pins.sh BESZEL_HUB_VERSION)" "$(gh_latest henrygd/beszel)"
report go-librespot "$(pin packaging/go-librespot/pins.sh GO_LIBRESPOT_VERSION)" "$(gh_latest devgianlu/go-librespot)"

exit $status
