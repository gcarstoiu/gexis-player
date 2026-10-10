#!/bin/bash
# ADR-0107: gexis-system - our units, scripts, ALSA and Samba files, the kiosk,
# the Peppy driver and the splash, and the edits to other packages' files that
# the image stages make today. Runs inside gexis-deb-builder with the
# repository at /src. Reads every file from image/stage-gexis/*/files, one
# source of truth until the stages go.
#
# Not here, on purpose: the first-boot script and its cmdline entry (they
# belong to one card), the pi user's sudoers drop-in (kept in development
# images, decided before release - ADR-0107 decision 3), the image stamp.
set -euo pipefail

VERSION="$1"
S=/src/image/stage-gexis
STAGE=/tmp/stage/gexis-system
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"
put() { install -D -m "$1" "$2" "$STAGE$3"; }   # mode source destination
U=/usr/lib/systemd/system
DEF=/usr/share/gexis/defaults

# --- ALSA (00-alsa) ----------------------------------------------------------
put 644 "$S/00-alsa/files/zz-gexis-default.conf" /etc/alsa/conf.d/zz-gexis-default.conf
# Boot status off through systemd's own configuration, not cmdline.txt,
# which Raspberry Pi's first boot strips of systemd.* options (2026-10-01).
put 644 "$S/06-splash/files/gexis-show-status.conf" /etc/systemd/system.conf.d/gexis-show-status.conf
put 644 "$S/00-alsa/files/gexis-dummy-mixers-load.conf" /etc/modules-load.d/gexis-dummy-mixers.conf
put 644 "$S/00-alsa/files/gexis-dummy-mixers-modprobe.conf" /etc/modprobe.d/gexis-dummy-mixers.conf
# Rewritten when the output is chosen (outputs.py): a default, placed once.
put 644 "$S/00-alsa/files/output.conf" "$DEF/output.conf"

# --- Renderers (02-renderers) -------------------------------------------------
put 644 "$S/02-renderers/files/squeezelite.service" "$U/squeezelite.service"
put 755 "$S/02-renderers/files/squeezelite-mixer-check.sh" /usr/lib/gexis/squeezelite-mixer-check.sh
put 644 "$S/02-renderers/files/bluealsa-aplay-override.conf" "$U/bluealsa-aplay.service.d/override.conf"
put 644 "$S/02-renderers/files/bluealsa-override.conf" "$U/bluealsa.service.d/override.conf"
put 755 "$S/02-renderers/files/gexis-bluetooth-setup.sh" /usr/lib/gexis/bluetooth-setup.sh
put 644 "$S/02-renderers/files/gexis-bluetooth-setup.service" "$U/gexis-bluetooth-setup.service"
# The name, before setup gives one; rewritten by a rename (device_name.py).
mkdir -p "$STAGE$DEF"
printf 'GEXIS_DEVICE_NAME=gexis\n' > "$STAGE$DEF/device-name.env"
printf 'PRETTY_HOSTNAME=gexis\n' > "$STAGE$DEF/machine-info"
chmod 644 "$STAGE$DEF/device-name.env" "$STAGE$DEF/machine-info"

# --- The shares (03-core) -----------------------------------------------------
put 644 "$S/03-core/files/gexis-pictures.conf" /etc/samba/smb.conf.d/gexis-pictures.conf
put 644 "$S/03-core/files/gexis-smb.service" /etc/avahi/services/gexis-smb.service

# --- The panel (04-ui) --------------------------------------------------------
put 644 "$S/04-ui/files/kiosk.env" /etc/gexis/kiosk.env
put 755 "$S/04-ui/files/gexis-kiosk-start" /usr/bin/gexis-kiosk-start
put 755 "$S/04-ui/files/gexis-panel-warmup" /usr/bin/gexis-panel-warmup
put 644 "$S/04-ui/files/gexis-panel-warmup.service" "$U/gexis-panel-warmup.service"
put 644 "$S/04-ui/files/gexis-kiosk.service" "$U/gexis-kiosk.service"
# The system-wide place labwc reads when the user has none of their own:
# a package does not install into /home (ADR-0107).
put 644 "$S/04-ui/files/labwc-rc.xml" /etc/xdg/labwc/rc.xml
# No system cursor on the panel (2026-10-05, ADR-0121): labwc draws one where
# it starts and hides it only at a real touch, which a panel driven from the
# phone never gets. A theme whose every cursor is one transparent pixel - a
# 68-byte Xcursor file - and gexis-kiosk.service names it. Every common name
# points at it, so a name the theme lacked could not bring the arrow back.
B=/usr/share/icons/gexis-blank/cursors
put 644 "$S/04-ui/files/blank-cursor" "$B/default"
for name in left_ptr arrow pointer hand1 hand2 text xterm grab grabbing wait \
		watch progress not-allowed crosshair move all-scroll; do
	ln -s default "$STAGE$B/$name"
done

# --- The visualiser's driver (05-peppy); the engines and skins are their own ---
P=/opt/gexis-peppy
put 644 "$S/05-peppy/files/peppy-meter.txt" "$P/peppymeter/config.txt"
# Rewritten by the driver (ADR-0051 §3), owned by the service user: placed once.
put 644 "$S/05-peppy/files/peppy-spectrum.txt" "$DEF/peppy-spectrum.txt"
put 755 "$S/05-peppy/files/gexis-peppy-driver.py" "$P/driver.py"
for m in gexis_peppy_render gexis_peppy_motion gexis_peppy_gauges gexis_peppy_fanart; do
	put 644 "$S/05-peppy/files/$m.py" "$P/$m.py"
done
put 644 "$S/05-peppy/files/badge-slots.json" "$P/badge-slots.json"
for icon in "$S"/05-peppy/files/icons/*; do
	put 644 "$icon" "$P/icons/$(basename "$icon")"
done
put 644 "$S/05-peppy/files/gexis-peppy.service" "$U/gexis-peppy.service"
put 755 "$S/05-peppy/files/gexis-peppy-start" /usr/bin/gexis-peppy-start

# --- The splash (06-splash) ---------------------------------------------------
T=/usr/share/plymouth/themes/gexis
for f in gexis.plymouth gexis.script still.png ground.png; do
	put 644 "$S/06-splash/files/theme/$f" "$T/$f"
done
put 644 "$S/06-splash/files/theme/still.png" /usr/share/gexis/panel-background.png
put 644 "$S/06-splash/files/gexis-splash-backstop.service" "$U/gexis-splash-backstop.service"
put 644 "$S/06-splash/files/gexis-splash-backstop.timer" "$U/gexis-splash-backstop.timer"
put 755 "$S/06-splash/files/gexis-splash-fb" /usr/bin/gexis-splash-fb

# --- The install script ---------------------------------------------------------
cat > "$STAGE/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
# ADR-0107: gexis-system. Every step checks before it changes anything, so a
# second run - an update - changes nothing that is already right, and never
# overwrites what the device itself wrote.
set -e
[ "$1" = configure ] || exit 0
DEF=/usr/share/gexis/defaults

# Placed once: the player rewrites each of these.
place() {  # default destination mode owner
	[ -e "$2" ] && return 0
	install -D -m "$3" -o "${4%:*}" -g "${4#*:}" "$1" "$2"
}
place "$DEF/output.conf" /etc/alsa/conf.d/output.conf 644 0:0
place "$DEF/device-name.env" /etc/gexis/device-name.env 644 0:0
place "$DEF/machine-info" /etc/machine-info 644 0:0
place "$DEF/peppy-spectrum.txt" /opt/gexis-peppy/spectrum/config.txt 644 1000:1000
install -d -m 755 -o 1000 -g 1000 /var/lib/gexis-kiosk

# Samba reads our share through an include in its own file (ADR-0049).
SMB=/etc/samba/smb.conf
if [ -f "$SMB" ] && ! grep -q "smb.conf.d/gexis-pictures.conf" "$SMB"; then
	printf '\n# ADR-0049: the idle screen pictures share.\ninclude = /etc/samba/smb.conf.d/gexis-pictures.conf\n' >> "$SMB"
fi

# The boot configuration. A change here takes effect at the next boot, so it
# is recorded for the updater, which restarts the device (ADR-0107).
REBOOT=/var/lib/gexis/reboot-required
CMDLINE=/boot/firmware/cmdline.txt
CONFIG=/boot/firmware/config.txt
changed=
if [ -f "$CMDLINE" ]; then
	before=$(cat "$CMDLINE")
	grep -qw 'cgroup_enable=memory' "$CMDLINE" || sed -i 's/\brootwait\b/rootwait cgroup_enable=memory/' "$CMDLINE"
	sed -i 's/\bconsole=tty1\b/console=tty3/' "$CMDLINE"
	for option in quiet loglevel=0 logo.nologo vt.global_cursor_default=0 \
		plymouth.ignore-serial-consoles splash; do
		grep -qw -- "$option" "$CMDLINE" || sed -i "$ s#\$# ${option}#" "$CMDLINE"
	done
	[ "$before" = "$(cat "$CMDLINE")" ] || changed=1
	grep -qw 'cgroup_enable=memory' "$CMDLINE" || { echo "gexis-system: cgroup_enable=memory not in $CMDLINE" >&2; exit 1; }
fi
if [ -f "$CONFIG" ] && ! grep -q '^disable_splash=1' "$CONFIG"; then
	printf '\n# ADR-0043: no rainbow square before the boot animation.\ndisable_splash=1\n' >> "$CONFIG"
	changed=1
fi
if [ -n "$changed" ] && [ -n "$2" ]; then
	install -d /var/lib/gexis && touch "$REBOOT"
fi

if command -v systemctl >/dev/null; then
	# Units of other packages that must not run on this device.
	systemctl mask alsa-restore.service nmbd.service samba-ad-dc.service \
		plymouth-quit.service plymouth-quit-wait.service >/dev/null
	if [ -z "$2" ]; then
		# First install only; after that the core switches the renderers.
		systemctl enable squeezelite.service gexis-bluetooth-setup.service \
			gexis-kiosk.service gexis-panel-warmup.service gexis-peppy.service \
			gexis-splash-backstop.timer
	fi
	if [ -d /run/systemd/system ]; then systemctl daemon-reload; fi
else
	echo "gexis-system: no systemctl here; units not masked or enabled" >&2
fi

# The boot animation: our theme, and an initramfs that carries it. Rebuilt
# only when the theme's files changed - it takes a while on a Pi.
if command -v plymouth-set-default-theme >/dev/null; then
	[ "$(plymouth-set-default-theme)" = gexis ] || plymouth-set-default-theme gexis
	STAMP=/var/lib/gexis/splash-theme.sha256
	now=$(cat /usr/share/plymouth/themes/gexis/* | sha256sum | cut -c1-64)
	if [ "$(cat "$STAMP" 2>/dev/null)" != "$now" ] && command -v update-initramfs >/dev/null; then
		CONF=/etc/initramfs-tools/update-initramfs.conf
		ORIGINAL=$(grep '^update_initramfs=' "$CONF" 2>/dev/null || echo 'update_initramfs=no')
		[ -f "$CONF" ] && sed -i 's/^update_initramfs=.*/update_initramfs=all/' "$CONF"
		update-initramfs -u -k all
		[ -f "$CONF" ] && sed -i "s/^update_initramfs=.*/${ORIGINAL}/" "$CONF"
		install -d /var/lib/gexis && echo "$now" > "$STAMP"
		[ -z "$2" ] || { install -d /var/lib/gexis && touch "$REBOOT"; }
	fi
fi
POSTINST
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/control" <<CTL
Package: gexis-system
Version: $VERSION
Architecture: all
Maintainer: Gexis Player <noreply@github.com>
Depends: gexis-core, gexis-peppy-engines, gexis-peppyalsa
Section: sound
Priority: optional
Description: Gexis Player's system files
 The panel, the visualiser's driver, the boot animation, the ALSA output and
 the renderers' units, and the edits to other packages' files they need
 (ADR-0107).
CTL
mkdir -p /out
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "/out/gexis-system_${VERSION}_all.deb" >/dev/null
echo "/out/gexis-system_${VERSION}_all.deb"
