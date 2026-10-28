#!/bin/bash -e

# What the packages' scripts must have done, checked where it happened.
[ "$(plymouth-set-default-theme)" = gexis ] || { echo "ERROR: plymouth theme is not gexis" >&2; exit 1; }
for image in /boot/firmware/initramfs*; do
	lsinitramfs "${image}" 2>/dev/null | grep -q plymouth \
		|| { echo "ERROR: plymouth is not in ${image}; the splash would start late" >&2; exit 1; }
done
for unit in gexis-core gexis-meter gexis-park gexis-kiosk gexis-panel-warmup gexis-peppy \
	squeezelite go-librespot gexis-bluetooth-setup gexis-splash-backstop.timer nmbd; do
	[ "$(systemctl is-enabled "${unit}")" = enabled ] || { echo "ERROR: ${unit} is not enabled" >&2; exit 1; }
done
for unit in beszel-agent beszel-hub gexis-lyrion plexamp gexis-plexamp; do
	[ "$(systemctl is-enabled "${unit}")" = disabled ] || { echo "ERROR: ${unit} should ship disabled" >&2; exit 1; }
done
# ADR-0162, ADR-0166: started and stopped by the core only - no [Install] section at all.
for unit in gexis-equaliser gexis-snapserver gexis-snapclient; do
	[ "$(systemctl is-enabled "${unit}")" = static ] || { echo "ERROR: ${unit} should be static" >&2; exit 1; }
done
for unit in alsa-restore samba-ad-dc plymouth-quit plymouth-quit-wait snapserver snapclient; do
	[ "$(systemctl is-enabled "${unit}" 2>/dev/null)" = masked ] || { echo "ERROR: ${unit} is not masked" >&2; exit 1; }
done
[ ! -e /home/pi/.config/labwc/rc.xml ] || { echo "ERROR: a home-folder labwc config would override /etc/xdg/labwc" >&2; exit 1; }
echo "packages' install scripts: checked"
