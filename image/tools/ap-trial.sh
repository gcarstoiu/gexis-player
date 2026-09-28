#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# **A timed trial of the setup access point** (ADR-0031, amended 2026-09-28).
# gexis has no Ethernet, so raising the AP takes down the Wi-Fi Claude reaches
# it through. This runs detached on the device, logs to the card, and gives the
# Wi-Fi back when it ends - and a separate systemd timer gives it back anyway a
# minute after it should have, whatever happened to this script.
#
# On the device, as root:
#   systemd-run --unit=gexis-ap-trial /usr/local/lib/gexis/ap-trial.sh [SECONDS] [PASSWORD]
# Log: /var/lib/gexis-trials/ap-<time>.log
set -u
DURATION="${1:-180}"
PASSWORD="${2:-gexis-setup}"
SSID="gexis-setup"
AP="gexis-setup-trial"
LOGDIR=/var/lib/gexis-trials
mkdir -p "$LOGDIR"
LOG="$LOGDIR/ap-$(date +%Y%m%d-%H%M%S).log"
exec >>"$LOG" 2>&1
t0=$(date +%s.%N)
# Only what the image has: no bc, no iw (checked on gexis, 2026-09-28).
since() { awk -v a="$1" -v b="$(date +%s.%N)" 'BEGIN { printf "%.2f", b - a }'; }
say() { printf '%7ss %s\n' "$(since "$t0")" "$*"; }

# The Wi-Fi to give back: whatever wlan0 is on now.
HOME_WIFI="$(nmcli -t -f NAME,DEVICE connection show --active | awk -F: '$2=="wlan0"{print $1; exit}')"
say "trial: ${DURATION}s, ssid ${SSID}; home Wi-Fi is '${HOME_WIFI}'"
[ -n "$HOME_WIFI" ] || { say "no Wi-Fi active on wlan0; nothing to give back, stopping"; exit 1; }

# **The guard that does not depend on this script.** A transient timer, a
# minute after the trial should end: bring the home Wi-Fi up if it is not.
systemd-run --unit=gexis-ap-trial-guard --on-active=$((DURATION + 60)) /bin/sh -c \
	"nmcli -t -f NAME connection show --active | grep -qx '$HOME_WIFI' || { nmcli connection down '$AP'; nmcli connection up '$HOME_WIFI'; }; nmcli connection delete '$AP' 2>/dev/null; true" \
	&& say "guard armed: home Wi-Fi back at +$((DURATION + 60))s regardless"

say "regulatory: $(cat /sys/module/cfg80211/parameters/ieee80211_regdom 2>/dev/null); wlan0 rfkill: $(cat /sys/class/net/wlan0/phy80211/rfkill*/soft 2>/dev/null)"
say "scan before the AP (kept for the setup page):"
nmcli -t -f SSID,SIGNAL,SECURITY device wifi list --rescan yes 2>&1 | sed 's/^/    /' | head -20

say "raising the AP"
nmcli connection delete "$AP" >/dev/null 2>&1
if nmcli device wifi hotspot ifname wlan0 con-name "$AP" ssid "$SSID" password "$PASSWORD"; then
	say "AP up: $(nmcli -g IP4.ADDRESS device show wlan0)"
else
	say "AP FAILED to come up"
fi

end=$(( $(date +%s) + DURATION ))
scanned=0
while [ "$(date +%s)" -lt "$end" ]; do
	stations=$(ip neigh show dev wlan0 2>/dev/null | grep -c -E 'REACHABLE|STALE|DELAY')
	leases=$(cat /var/lib/NetworkManager/dnsmasq-wlan0.leases 2>/dev/null | awk '{print $3" "$4}' | tr '\n' ';')
	say "clients: ${stations}; leases: ${leases:-none}"
	# Once, mid-way: can a scan run while the radio is hosting?
	if [ "$scanned" = 0 ] && [ "$(date +%s)" -gt $(( end - DURATION / 2 )) ]; then
		scanned=1
		say "scan while hosting:"
		timeout 20 nmcli -t -f SSID,SIGNAL device wifi list --rescan yes 2>&1 | sed 's/^/    /' | head -10
		say "scan while hosting done; clients now: $(ip neigh show dev wlan0 2>/dev/null | grep -c -E 'REACHABLE|STALE|DELAY')"
	fi
	sleep 5
done

say "taking the AP down and rejoining '${HOME_WIFI}'"
nmcli connection down "$AP"
back0=$(date +%s.%N)
nmcli connection up "$HOME_WIFI"
say "home Wi-Fi up after $(since "$back0")s: $(nmcli -g IP4.ADDRESS device show wlan0)"
nmcli connection delete "$AP" >/dev/null 2>&1
systemctl stop gexis-ap-trial-guard.timer 2>/dev/null
say "trial done"
