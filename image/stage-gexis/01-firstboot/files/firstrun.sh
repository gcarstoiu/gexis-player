#!/bin/sh
set +e

# Gexis Player first-boot provisioning.
#
# Edit the values below before booting the card, then save. This runs once,
# very early in boot (systemd.run=, before regular multi-user targets), and
# deletes itself and its cmdline.txt entry when done — see the end of this
# file. There is no other first-boot mechanism on this image: no cloud-init,
# no interactive setup wizard. Without an SSH_PUBKEY here, the device has no
# way to reach it remotely.
#
# This calls the same platform helpers Raspberry Pi Imager's own generated
# firstrun.sh calls (/usr/lib/raspberrypi-sys-mods/imager_custom,
# /usr/lib/userconf-pi/userconf) — not a custom mechanism.

SSH_PUBKEY=""                  # required: e.g. "ssh-ed25519 AAAA... you@host"
WIFI_SSID=""                   # leave blank for Ethernet-only
WIFI_PASS=""
WIFI_COUNTRY="GB"               # ISO 3166-1 alpha-2; required by set_wlan when WIFI_SSID is set
HOSTNAME=""                     # leave blank to keep the built-in default
TIMEZONE=""                     # e.g. "Europe/Berlin"; blank keeps the image default
IDLE_URL=""                     # idle screen page (ADR-0019); blank shows the built-in clock

IMAGER_CUSTOM=/usr/lib/raspberrypi-sys-mods/imager_custom
USERCONF=/usr/lib/userconf-pi/userconf

if [ -n "$HOSTNAME" ] && [ -x "$IMAGER_CUSTOM" ]; then
	"$IMAGER_CUSTOM" set_hostname "$HOSTNAME"
fi

if [ -n "$SSH_PUBKEY" ] && [ -x "$IMAGER_CUSTOM" ]; then
	"$IMAGER_CUSTOM" enable_ssh -k "$SSH_PUBKEY"
fi

# Finalises the default "pi" account and cancels the interactive first-boot
# setup wizard (which would otherwise wait for a screen and keyboard that
# don't exist here). Empty password is deliberate: it leaves the account's
# existing locked/no-password state untouched — this image is SSH-key-only.
if [ -x "$USERCONF" ]; then
	"$USERCONF" pi ""
fi

if [ -n "$WIFI_SSID" ] && [ -x "$IMAGER_CUSTOM" ]; then
	"$IMAGER_CUSTOM" set_wlan "$WIFI_SSID" "$WIFI_PASS" "$WIFI_COUNTRY"
fi

if [ -n "$TIMEZONE" ] && [ -x "$IMAGER_CUSTOM" ]; then
	"$IMAGER_CUSTOM" set_timezone "$TIMEZONE"
fi

# Set on the card, not in the image: a real idle URL can carry a per-display
# identifier. Escaped for a TOML basic string.
if [ -n "$IDLE_URL" ]; then
	printf '\nidle_url = "%s"\n' "$(printf '%s' "$IDLE_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')" >> /etc/gexis/core.toml
fi

rm -f /boot/firstrun.sh
sed -i 's| systemd.run.*||g' /boot/cmdline.txt
exit 0
