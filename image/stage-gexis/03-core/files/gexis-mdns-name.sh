#!/bin/sh
# **The player's own name back after a clash** (George, 2026-10-14: the bar
# answered as shelvespi-2.local for a whole day). At a start, Avahi found
# shelvespi.local still answered on the network - most likely a cache of the
# previous start - took "shelvespi-2" and kept it until the next start, while
# the player's pages kept saying shelvespi.local. Run by a timer: when Avahi
# is announcing this host's name with a number added, it is asked for the
# real name again, by then free. At most TRIES times a start, so a genuine
# second device with the same name does not set the two flipping for ever.
set -u
TRIES=5
COUNT=${GEXIS_MDNS_TRIES:-/run/gexis/mdns-name-tries}

want=$(hostname)
now=$(busctl --system call org.freedesktop.Avahi / org.freedesktop.Avahi.Server GetHostName 2>/dev/null \
	| sed -n 's/^s "\(.*\)"$/\1/p')
[ -n "$now" ] || exit 0
[ "$now" = "$want" ] && exit 0
case "$now" in
"$want"-[0-9]*) ;;
*) exit 0 ;;
esac

mkdir -p "$(dirname "$COUNT")"
tried=$(cat "$COUNT" 2>/dev/null || echo 0)
if [ "$tried" -ge "$TRIES" ]; then
	exit 0
fi
echo $((tried + 1)) > "$COUNT"
echo "mdns: announced as $now.local after a name clash; claiming $want.local back (try $((tried + 1)) of $TRIES)"
busctl --system call org.freedesktop.Avahi / org.freedesktop.Avahi.Server SetHostName s "$want" \
	|| echo "mdns: could not claim $want.local back"
