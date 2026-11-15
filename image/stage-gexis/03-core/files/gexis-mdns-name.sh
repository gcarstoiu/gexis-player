#!/bin/sh
# **The player's own name back after a clash** (George, 2026-10-14: the bar
# answered as shelvespi-2.local for a whole day). Avahi takes "<name>-2" when
# something else answers for <name>.local - a cache of the previous start, or
# a plugin's own mDNS responder (Finding 148) - and keeps it, while the
# player's pages go on saying <name>.local. Run by a timer: when Avahi is
# announcing this host's name with a number added, it is asked for the real
# name again. TRIES times in a row, then once every SLOW_S (Finding 148: the
# five tries were spent while the plugin still answered, and the player kept
# "-2" for days after it had stopped), so a genuine second device with the
# same name is asked at most twice an hour.
set -u
TRIES=5
SLOW_S=${GEXIS_MDNS_SLOW_S:-1800}
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
	# The count file's time is the last try's.
	last=$(stat -c %Y "$COUNT" 2>/dev/null || echo 0)
	[ $(($(date +%s) - last)) -ge "$SLOW_S" ] || exit 0
	how="every $((SLOW_S / 60)) min now"
else
	how="of $TRIES"
fi
echo $((tried + 1)) > "$COUNT"
echo "mdns: announced as $now.local after a name clash; claiming $want.local back (try $((tried + 1)) $how)"
busctl --system call org.freedesktop.Avahi / org.freedesktop.Avahi.Server SetHostName s "$want" \
	|| echo "mdns: could not claim $want.local back"
