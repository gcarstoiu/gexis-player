#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Verify a built image as a file, before anyone flashes it: root partition read
# with debugfs (no root, no loop device), contents compared byte for byte
# against this checkout. Checks the artefact, not the booted system
# (docs/LESSONS.md case 5).
#
# Usage: image/verify-image.sh image/deploy/<name>.img

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
IMG="${1:?usage: $0 <image.img>}"
[ -f "$IMG" ] || { echo "no such image: $IMG" >&2; exit 2; }
OUT="$(mktemp -d)"; trap 'rm -rf "$OUT"' EXIT

fail=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; fail=1; }

start=$(sfdisk -d "$IMG" | awk '/start=/{n++; if(n==2){sub(/.*start= */,""); sub(/,.*/,""); print}}')
FS="${IMG}?offset=$((start * 512))"
dfs() { debugfs -R "$1" "$FS" 2>/dev/null; }
echo "image: $IMG"
echo "root partition starts at sector $start"
dfs stats | grep -E 'Filesystem volume name|Block count' | sed 's/^/  /'

echo "== files identical to the repo"
while read -r src dst; do
	dfs "dump $dst $OUT/one" >/dev/null
	if [ ! -s "$OUT/one" ] && [ -s "$REPO/$src" ]; then bad "$dst missing"
	elif cmp -s "$REPO/$src" "$OUT/one"; then ok "$dst"
	else bad "$dst differs from $src"; fi
	rm -f "$OUT/one"
done <<'EOF'
image/stage-gexis/03-core/files/core.toml /etc/gexis/core.toml
image/stage-gexis/03-core/files/gexis-core.service /usr/lib/systemd/system/gexis-core.service
image/stage-gexis/03-core/files/gexis-meter.service /usr/lib/systemd/system/gexis-meter.service
image/stage-gexis/03-core/files/gexis-softvol-restore.service /usr/lib/systemd/system/gexis-softvol-restore.service
image/stage-gexis/04-ui/files/gexis-kiosk.service /usr/lib/systemd/system/gexis-kiosk.service
image/stage-gexis/04-ui/files/gexis-kiosk-start /usr/bin/gexis-kiosk-start
image/stage-gexis/04-ui/files/kiosk.env /etc/gexis/kiosk.env
image/stage-gexis/04-ui/files/labwc-rc.xml /etc/xdg/labwc/rc.xml
image/stage-gexis/05-peppy/files/gexis-peppy.service /usr/lib/systemd/system/gexis-peppy.service
image/stage-gexis/05-peppy/files/gexis-peppy-start /usr/bin/gexis-peppy-start
image/stage-gexis/05-peppy/files/gexis-peppy-driver.py /opt/gexis-peppy/driver.py
image/stage-gexis/05-peppy/files/gexis_peppy_render.py /opt/gexis-peppy/gexis_peppy_render.py
image/stage-gexis/05-peppy/files/gexis_peppy_motion.py /opt/gexis-peppy/gexis_peppy_motion.py
image/stage-gexis/05-peppy/files/gexis_peppy_fanart.py /opt/gexis-peppy/gexis_peppy_fanart.py
image/stage-gexis/05-peppy/files/gexis_peppy_gauges.py /opt/gexis-peppy/gexis_peppy_gauges.py
image/stage-gexis/05-peppy/files/badge-slots.json /opt/gexis-peppy/badge-slots.json
image/stage-gexis/05-peppy/files/peppy-meter.txt /opt/gexis-peppy/peppymeter/config.txt
image/stage-gexis/05-peppy/files/peppy-spectrum.txt /opt/gexis-peppy/spectrum/config.txt
image/stage-gexis/10-lyrion/files/plugin.json /usr/share/gexis/plugins/lyrion-server/plugin.json
image/stage-gexis/10-lyrion/files/gexis-lyrion.service /usr/lib/systemd/system/gexis-lyrion.service
image/stage-gexis/10-lyrion/files/lyrion.env /usr/share/gexis/components/lyrion.env
image/stage-gexis/10-lyrion/files/lyrion-memory-limit /usr/lib/gexis/lyrion-memory-limit
image/stage-gexis/10-lyrion/files/lyrion-prepare /usr/lib/gexis/lyrion-prepare
image/stage-gexis/10-lyrion/files/90-gexis-usb-music.rules /usr/lib/udev/rules.d/90-gexis-usb-music.rules
image/stage-gexis/10-lyrion/files/gexis-music.conf /etc/samba/smb.conf.d/gexis-music.conf
image/stage-gexis/11-equaliser/files/gexis-equaliser.service /usr/lib/systemd/system/gexis-equaliser.service
image/stage-gexis/12-multiroom/files/gexis-snapserver.service /usr/lib/systemd/system/gexis-snapserver.service
image/stage-gexis/12-multiroom/files/gexis-snapclient.service /usr/lib/systemd/system/gexis-snapclient.service
image/stage-gexis/02-renderers/files/gexis-radio.service /usr/lib/systemd/system/gexis-radio.service
image/stage-gexis/00-alsa/files/gexis-loopback-load.conf /etc/modules-load.d/gexis-loopback.conf
image/stage-gexis/00-alsa/files/gexis-loopback-modprobe.conf /etc/modprobe.d/gexis-loopback.conf
EOF

# **No skins in the image** (ADR-0111 decision 9): neither the old
# gexis-skins nor a size's pack, which a device installs only once the user
# agrees. Until 2026-10-01 this section compared Gelo5's 1280x800 files and
# counted each corpus's images; those checks belong to the packs now
# (packaging/skin-packs/build.sh), and what is asserted here is their absence.
echo "== no skins in the image (ADR-0111)"
for gone in /opt/gexis-peppy/skins /opt/gexis-peppy/packs /usr/share/doc/gexis-skins; do
	dfs "stat $gone" | grep -q 'Inode:' && bad "$gone is in the image" || ok "$gone absent"
done
dfs "dump /var/lib/dpkg/status $OUT/status" >/dev/null
if [ ! -s "$OUT/status" ]; then
	bad "/var/lib/dpkg/status missing"
elif grep -qE '^Package: gexis-skins(-[0-9]+x[0-9]+)?$' "$OUT/status"; then
	bad "a skins package is installed: $(grep -oE '^Package: gexis-skins[^ ]*' "$OUT/status" | tr '\n' ' ')"
else
	ok "no gexis-skins package installed"
fi
rm -f "$OUT/status"

# ADR-0133: the player's own wallpapers are in the image, each with its credit.
echo "== the player's own wallpapers (ADR-0133)"
dfs "dump /usr/share/gexis/wallpapers/credits.json $OUT/credits.json" >/dev/null
if [ ! -s "$OUT/credits.json" ]; then
	bad "/usr/share/gexis/wallpapers/credits.json missing"
else
	want=$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$OUT/credits.json")
	got=0
	for set in $(python3 -c 'import json,sys; print(" ".join(sorted({c["set"] for c in json.load(open(sys.argv[1]))})))' "$OUT/credits.json"); do
		n=$(dfs "ls -l /usr/share/gexis/wallpapers/$set" | grep -c '\.webp')
		got=$((got + n))
	done
	[ "$got" = "$want" ] && ok "$got wallpapers, each listed in credits.json" || bad "credits.json lists $want wallpapers, the image has $got"
fi
rm -f "$OUT/credits.json"

echo "== files the services must be able to write"
# The driver rewrites the spectrum engine's config to choose a section - the
# engine has no other way to be told - and the unit runs as pi (uid 1000).
# Shipped root-owned, that write raised PermissionError after the display
# existed and left a black window on the panel (ADR-0051 §3).
own=$(dfs "stat /opt/gexis-peppy/spectrum/config.txt" | grep -o 'User: *[0-9]*' | tr -s ' ')
[ "$own" = "User: 1000" ] && ok "spectrum config owned by uid 1000" || bad "spectrum config ownership: '${own:-missing}'"

echo "== ADR-0107: nothing of ours left in the old places"
# A unit in /etc/systemd/system overrides the one in /usr/lib/systemd/system of
# the same name, so a copy a warm build left there would win silently.
for old in /etc/systemd/system/gexis-core.service /etc/systemd/system/gexis-kiosk.service \
	/etc/systemd/system/gexis-peppy.service /etc/systemd/system/go-librespot.service \
	/etc/systemd/system/squeezelite.service /etc/systemd/system/beszel-agent.service \
	/etc/systemd/system/plexamp.service /etc/systemd/system/gexis-uploaded-renderer@.service \
	/etc/systemd/system/bluealsa.service.d/override.conf \
	/usr/local/bin/go-librespot /usr/local/bin/gexis-kiosk-start /usr/local/lib/gexis; do
	dfs "stat $old" | grep -q 'Inode:' && bad "$old still there" || ok "$old gone"
done

echo "== units enabled (symlink targets)"
for u in gexis-core gexis-meter gexis-kiosk gexis-peppy gexis-softvol-restore; do
	t=$(dfs "stat /etc/systemd/system/multi-user.target.wants/$u.service" | grep -o 'Fast link dest: ".*"')
	[ "$t" = "Fast link dest: \"/usr/lib/systemd/system/$u.service\"" ] && ok "$u -> $t" || bad "$u enablement: '${t:-missing}'"
done
# Units a decision removed. A warm build keeps what an earlier build wrote,
# and gexis-bluetooth-trust shipped enabled with its module already deleted -
# which is why these are asserted absent rather than merely not installed.
# gexis-boot-volume went the same way on 2026-09-23 (ADR-0018 amended,
# Finding 047 §10: nothing carries a level across a boot).
for gone in /etc/systemd/system/gexis-bluetooth-trust.service \
	/etc/systemd/system/multi-user.target.wants/gexis-bluetooth-trust.service \
	/etc/systemd/system/gexis-boot-volume.service \
	/etc/systemd/system/multi-user.target.wants/gexis-boot-volume.service \
	/usr/local/bin/gexis-boot-volume; do
	dfs "stat $gone" | grep -q 'Inode:' && bad "$gone still in the image (ADR-0045)" || ok "$gone absent"
done
t=$(dfs "stat /etc/systemd/system/alsa-restore.service" | grep -o 'Fast link dest: ".*"')
[ "$t" = 'Fast link dest: "/dev/null"' ] && ok "alsa-restore masked" || bad "alsa-restore mask: '${t:-missing}'"
# ADR-0049 as amended 2026-10-16: nmbd answers the player's NetBIOS name.
t=$(dfs "stat /etc/systemd/system/multi-user.target.wants/nmbd.service" | grep -o 'Fast link dest: ".*"')
[ "$t" = 'Fast link dest: "/usr/lib/systemd/system/nmbd.service"' ] && ok "nmbd enabled" || bad "nmbd enablement: '${t:-missing}'"
dfs "stat /etc/systemd/system/nmbd.service" | grep -q 'Inode:' && bad "nmbd still masked" || ok "nmbd not masked"
dfs "stat /etc/systemd/system/default.target" | grep -q 'Inode:' && bad "default.target written" || ok "default.target not written"

echo "== venv code identical to core/src"
py=$(dfs "ls -p /opt/gexis-core/venv/lib" | awk -F/ '$6 ~ /^python3/{print $6}')
site="/opt/gexis-core/venv/lib/$py/site-packages/gexis_core"
dfs "rdump $site $OUT" >/dev/null
if [ -d "$OUT/gexis_core" ]; then
	d=$(diff -r -x __pycache__ "$REPO/core/src/gexis_core" "$OUT/gexis_core")
	[ -z "$d" ] && ok "$site ($(find "$OUT/gexis_core" -name '*.py' | wc -l) .py files)" || { bad "venv differs:"; echo "$d" | head -20; }
else bad "$site missing"; fi
dfs "stat /opt/gexis-core/src" | grep -q 'Inode:' && bad "/opt/gexis-core/src left behind" || ok "/opt/gexis-core/src removed"

echo "== UI identical to ui/dist"
dfs "rdump /opt/gexis-ui $OUT" >/dev/null
if [ -d "$OUT/gexis-ui" ]; then
	d=$(diff -r "$REPO/ui/dist" "$OUT/gexis-ui")
	[ -z "$d" ] && ok "/opt/gexis-ui ($(find "$OUT/gexis-ui" -type f | wc -l) files)" || { bad "UI differs:"; echo "$d" | head; }
else bad "/opt/gexis-ui missing"; fi

# George, 2026-09-28: "Keep grim in the image" - the panel's screenshots.
dfs "stat /usr/bin/grim" | grep -q 'Inode:' && ok "grim installed" || bad "grim missing"

echo "== Peppy"
for f in peppymeter/peppymeter.py spectrum/spectrum.py fonts/DSEG7Classic-Italic.ttf icons/icon-spotify.png; do
	dfs "stat /opt/gexis-peppy/$f" | grep -q 'Inode:' && ok "/opt/gexis-peppy/$f" || bad "/opt/gexis-peppy/$f missing"
done
echo "  viz_timeout default in shipped registry: $(python3 -c "import json; r=json.load(open('$OUT/gexis_core/settings_registry.json')); s=[x for sec in r for x in sec.get('rows',[]) if x.get('key')=='viz_timeout']; print(repr(s[0].get('default')) if s else 'not found')" 2>&1)"
# **This printed nothing from the refactor that introduced `minutes()` until
# 2026-09-26**, because it grepped a shape the daemon had stopped having. An
# informational line that silently says nothing is the same family as the two
# defects found today, so it now reports when it cannot find the fallback at all
# rather than printing an empty value and looking answered.
fallback=$(grep -oE 'minutes\("viz_timeout", *[0-9]+\)' "$OUT/gexis_core/__main__.py")
echo "  daemon fallback: ${fallback:-NOT FOUND - this grep no longer matches the daemon}"

echo "== Beszel: a catalogue plugin since ADR-0174, nothing of it in the image"
# Its agent and hub come from the plugin catalogue (gcarstoiu/gexis-beszel);
# a player that used them carries them over at its first start. A leftover
# here would keep the ids the player's own and refuse the catalogue's.
for gone in /usr/bin/beszel-agent /usr/bin/beszel-hub /usr/lib/gexis/beszel-agent-listen-check.sh \
	/usr/lib/systemd/system/beszel-agent.service /usr/lib/systemd/system/beszel-hub.service \
	/usr/share/gexis/plugins/beszel /usr/share/gexis/plugins/beszel-hub \
	/usr/share/doc/gexis-player/licenses/beszel /usr/share/doc/gexis-player/licenses/beszel-hub; do
	dfs "stat $gone" | grep -q 'Inode:' && bad "$gone is in the image" || ok "$gone not in the image"
done
if dfs "dump /etc/passwd $OUT/passwd" >/dev/null && grep -q '^beszel:' "$OUT/passwd"; then
	bad "a beszel account - nothing in the image runs as it"
else
	ok "no beszel account"
fi
rm -f "$OUT/passwd"

# ADR-0162 D1: CamillaDSP, the build its pin names (the binary's own checksum,
# extracted from the pinned release, v4.1.3, 2026-10-25). Raise it with every
# new pin, as Beszel's.
dfs "dump /usr/bin/camilladsp $OUT/camilladsp" >/dev/null
CAMILLADSP_BINARY_SHA256="e04c7a6603e9482bab33c1e18afc41d3c07410b54ba9c246eda69f7e9cbaedfa"
if [ ! -s "$OUT/camilladsp" ]; then
	bad "/usr/bin/camilladsp missing"
else
	got="$(sha256sum "$OUT/camilladsp" | cut -d' ' -f1)"
	[ "$got" = "$CAMILLADSP_BINARY_SHA256" ] && ok "camilladsp is the pinned build" \
		|| bad "camilladsp sha256 is $got, expected $CAMILLADSP_BINARY_SHA256"
fi
rm -f "$OUT/camilladsp"
# Started by the core only: no [Install] section, so nothing enables it.
if dfs "stat /etc/systemd/system/multi-user.target.wants/gexis-equaliser.service" | grep -q 'Inode:'; then
	bad "gexis-equaliser is enabled in the image - the core starts it (ADR-0162)"
else
	ok "gexis-equaliser not enabled (the core starts it while the equaliser is on)"
fi

# ADR-0166: Snapcast's own units masked (they would start, and the client play
# to the output); ours started by the core only.
for unit in snapserver snapclient; do
	if dfs "stat /etc/systemd/system/${unit}.service" | grep -q 'Fast link dest: "/dev/null"'; then
		ok "${unit} masked (the core runs gexis-${unit})"
	else
		bad "${unit} is not masked - Debian's postinst starts it (Finding 139)"
	fi
done
for unit in gexis-snapserver gexis-snapclient; do
	if dfs "stat /etc/systemd/system/multi-user.target.wants/${unit}.service" | grep -q 'Inode:'; then
		bad "${unit} is enabled in the image - the core starts it (ADR-0166)"
	else
		ok "${unit} not enabled (the core starts it in a group)"
	fi
done
# ADR-0180: internet radio's mpv, started by the core for a station.
if dfs "stat /etc/systemd/system/multi-user.target.wants/gexis-radio.service" | grep -q 'Inode:'; then
	bad "gexis-radio is enabled in the image - the core starts it for a station (ADR-0180)"
else
	ok "gexis-radio not enabled (the core starts it for a station)"
fi

# ADR-0179: the music services' accounts, made by their packages; none of
# them runs as pi, the screen's user.
passwd=$(dfs "cat /etc/passwd")
for account in gexis-squeezelite gexis-spotify gexis-airplay gexis-snap gexis-radio; do
	printf '%s\n' "$passwd" | grep -q "^${account}:" && ok "account ${account}" || bad "account ${account} missing"
done

# Every built-in manifest. A plugin the core cannot read is a
# source the panel cannot draw (ADR-0086).
# **Whatever is installed, not a list written here.** The first version of this
# grepped for the four names it knew, so `plexamp` could not appear in its
# output even with its manifest sitting beside the others - a check that could
# only ever confirm what it already believed.
plugins=$(dfs "ls -l /usr/share/gexis/plugins" | awk '{print $NF}' \
	| grep -vE '^(\.|\.\.)?$' | sort -u | tr '\n' ' ')
missing=""
for want in lms spotify bluetooth radio; do
	case " $plugins " in *" $want "*) ;; *) missing="$missing $want" ;; esac
done
if [ -n "$missing" ]; then
	bad "plugin manifests missing:$missing (found: $plugins)"
else
	ok "plugin manifests: $plugins"
fi

echo "== Backgrounds placed by what they show (ADR-0120)"
for f in /opt/gexis-core/models/face_detection_yunet_2023mar.onnx \
         /opt/gexis-core/models/object_detection_yolox_2022nov.onnx; do
	dfs "stat $f" | grep -q 'Inode:' && ok "$f" || bad "$f missing"
done
dfs "stat /opt/gexis-core/venv/lib/python3.13/site-packages/cv2/__init__.py" | grep -q 'Inode:' \
	&& ok "OpenCV in the core's environment" || bad "OpenCV missing from the core's environment"

echo "== AirPlay (ADR-0167), Shairport Sync and NQPTP built for AirPlay 2"
for f in /usr/bin/shairport-sync /usr/bin/nqptp \
         /usr/lib/systemd/system/gexis-shairport-sync.service \
         /usr/lib/systemd/system/gexis-nqptp.service \
         /usr/lib/systemd/system/gexis-airplay.service \
         /usr/share/gexis/airplay/shairport-sync.conf \
         /usr/lib/gexis/airplay-hook \
         /usr/share/dbus-1/system.d/gexis-airplay.conf \
         /usr/share/gexis/plugins/airplay/plugin.json \
         /usr/share/gexis/plugins/airplay/mark.png \
         /opt/gexis-airplay/src/gexis_airplay/main.py \
         /usr/share/doc/gexis-player/licenses/shairport-sync/COPYING \
         /usr/share/doc/gexis-player/licenses/nqptp/LICENSE; do
	dfs "stat $f" | grep -q 'Inode:' && ok "$f" || bad "$f missing"
done
# **On in a new image** (decision 1): the switch is the receiver's unit.
if dfs "stat /etc/systemd/system/multi-user.target.wants/gexis-shairport-sync.service" | grep -q 'Inode:'; then
	ok "gexis-shairport-sync enabled"
else
	bad "gexis-shairport-sync is not enabled - a new image has AirPlay on"
fi
# Debian's classic-only receiver must not be the one installed.
if dfs "stat /usr/lib/systemd/system/shairport-sync.service" | grep -q 'Inode:'; then
	bad "Debian's shairport-sync is installed beside ours"
else
	ok "only our Shairport Sync"
fi

echo "== Roon (ADR-0172): the plugin, never Roon Bridge"
for f in /usr/lib/systemd/system/gexis-roon.service \
         /usr/lib/systemd/system/gexis-roonbridge.service \
         /usr/lib/sysusers.d/gexis-roonbridge.conf \
         /usr/share/gexis/components/roonbridge.env \
         /usr/share/gexis/plugins/roon/plugin.json \
         /opt/gexis-roon/src/gexis_roon/main.py; do
	dfs "stat $f" | grep -q 'Inode:' && ok "$f" || bad "$f missing"
done
# Roon Labs' software is fetched on the device when Roon is switched on; a
# copy here would be a redistribution its terms forbid.
if dfs "stat /opt/RoonBridge" | grep -q 'Inode:'; then
	bad "/opt/RoonBridge is in the image - Roon Bridge must not be shipped"
else
	ok "Roon Bridge not in the image"
fi
dfs "cat /etc/modprobe.d/gexis-loopback.conf" | grep -q 'id=Loopback,Multiroom,Roon' \
	&& ok "the Roon loopback card in snd-aloop's options" || bad "no Roon card in snd-aloop's options"

echo "== Plexamp: a catalogue plugin since ADR-0174, nothing of it in the image"
# Its plugin (gcarstoiu/gexis-plexamp) comes from the plugin catalogue and
# downloads Plexamp itself; a player that used it carries it over at its first
# start. A leftover here would keep the id the player's own.
for gone in /usr/lib/systemd/system/plexamp.service /usr/lib/systemd/system/gexis-plexamp.service \
	/usr/share/gexis/plugins/plexamp /opt/gexis-plexamp /usr/lib/gexis/plexamp-run \
	/usr/lib/gexis/plexamp-start-idle /usr/share/gexis/components/plexamp.env /home/pi/plexamp; do
	dfs "stat $gone" | grep -q 'Inode:' && bad "$gone is in the image" || ok "$gone not in the image"
done
# Node is the runtime the plugin's Plexamp needs, and the sandbox cannot
# install it: the release carries it (ADR-0174). Its absence would be a
# renderer that cannot start, with the reason two layers down.
dfs "stat /usr/bin/node" | grep -q 'Inode:' && ok "node installed" || bad "node missing"

echo "== ADR-0145: Squeezelite is ours, which folds multichannel down to stereo"
# dpkg's own record of who installed the file: Debian's squeezelite has the
# same path, and would play a 5.1 file's front pair alone.
dfs "dump /var/lib/dpkg/info/gexis-squeezelite.list $OUT/one" >/dev/null
grep -qx '/usr/bin/squeezelite' "$OUT/one" 2>/dev/null \
	&& ok "/usr/bin/squeezelite comes from gexis-squeezelite" \
	|| bad "/usr/bin/squeezelite is not gexis-squeezelite's"
rm -f "$OUT/one"
dfs "dump /var/lib/dpkg/status $OUT/status" >/dev/null
if [ ! -s "$OUT/status" ]; then
	bad "/var/lib/dpkg/status missing"
elif awk -v RS= '/^Package: squeezelite\n/ && /\nStatus: [a-z]+ ok installed/' "$OUT/status" | grep -q .; then
	bad "Debian's squeezelite is installed"
else
	ok "Debian's squeezelite is not installed"
fi
rm -f "$OUT/status"

echo "== ADR-0099: licences and the source offer reach the device"
# peppy_templates' notice is not here since ADR-0111: nothing of that
# repository is in the image, and each skin pack carries it in its own
# /usr/share/doc/gexis-skins-<W>x<H>/. peppy_screensaver's comes with
# gexis-player now that gexis-skins is not installed.
for f in /usr/share/doc/gexis-player/COPYING \
         /usr/share/doc/gexis-player/SOURCE.md \
         /usr/share/doc/gexis-player/packages.txt \
         /usr/share/doc/gexis-player/licenses/peppy_screensaver/LICENSE \
         /usr/share/doc/gexis-player/licenses/go-librespot/README \
         /usr/share/doc/gexis-player/licenses/camilladsp/README \
         /usr/share/doc/gexis-player/licenses/peppyalsa/README \
         /usr/share/doc/gexis-player/licenses/squeezelite/README \
         /opt/gexis-ui/licenses/svelte/LICENSE.md \
         /opt/gexis-ui/licenses/@fontsource-variable__nunito-sans/LICENSE \
         /opt/gexis-ui/licenses/@fontsource__ibm-plex-mono/LICENSE \
         /opt/gexis-ui/licenses/uqr/LICENSE; do
	dfs "stat $f" | grep -q 'Inode:' && ok "$f" || bad "$f missing"
done

echo "== ADR-0095 as amended: LMS paused as the device goes down"
dfs "stat /usr/lib/systemd/system/gexis-park.service" | grep -q 'Inode:' && ok "gexis-park.service installed" || bad "gexis-park.service missing"
dfs "stat /etc/systemd/system/multi-user.target.wants/gexis-park.service" | grep -q 'Inode:' && ok "gexis-park.service enabled" || bad "gexis-park.service not enabled"
# ADR-0132: the reset runs early in the boot after it is asked for - only if enabled.
dfs "stat /etc/systemd/system/sysinit.target.wants/gexis-factory-reset.service" | grep -q 'Inode:' && ok "gexis-factory-reset.service enabled" || bad "gexis-factory-reset.service not enabled"

echo "== ADR-0106: uploaded plugins run under the player's own sandboxed units"
for u in gexis-uploaded-renderer@.service gexis-uploaded-service@.service; do
	dfs "dump /usr/lib/systemd/system/$u $OUT/one" >/dev/null
	if grep -q '^DynamicUser=yes' "$OUT/one" && grep -q '^ProtectSystem=strict' "$OUT/one"; then ok "$u sandboxed"
	else bad "$u missing or not sandboxed"; fi
	# ADR-0142: no mDNS responder of a plugin's own.
	if grep -q '^SocketBindDeny=ipv4:udp:5353' "$OUT/one" && grep -q '^SocketBindDeny=ipv6:udp:5353' "$OUT/one"; then ok "$u denies port 5353"
	else bad "$u lets a plugin answer mDNS itself"; fi
	# ADR-0170: the kiosk's command line, with the panel's token, out of sight.
	if grep -q '^ProtectProc=invisible' "$OUT/one"; then ok "$u hides other users' processes"
	else bad "$u lets a plugin read the kiosk's command line"; fi
	# ADR-0174: its folder is not noexec - Plexamp runs from it.
	if grep -q '^ExecPaths=/var/lib/private/gexis-uploaded/%i$' "$OUT/one"; then ok "$u lets a plugin run what it downloads"
	else bad "$u leaves the plugin's folder noexec"; fi
	rm -f "$OUT/one"
done
dfs "stat /usr/lib/gexis/gexis-run-uploaded" | grep -q 'Mode:  0755' && ok "gexis-run-uploaded executable" || bad "gexis-run-uploaded missing or not executable"
# ADR-0170: a plugin granted `usb` reaches USB and HID through plugdev.
dfs "stat /usr/lib/udev/rules.d/60-gexis-plugins.rules" | grep -q 'Inode:' && ok "60-gexis-plugins.rules installed" || bad "60-gexis-plugins.rules missing"

echo "== ADR-0085: the ALSA default is our output"
dfs "dump /etc/alsa/conf.d/zz-gexis-default.conf $OUT/one" >/dev/null
if grep -q 'pcm.!default' "$OUT/one" 2>/dev/null; then
	ok "zz-gexis-default.conf points the ALSA default at our output"
else
	bad "zz-gexis-default.conf missing or does not set pcm.!default"
fi
rm -f "$OUT/one"

echo "== ADR-0139: no passwordless sudo in the public image"
dfs "stat /etc/sudoers.d/010_pi-nopasswd" | grep -q 'Inode:' \
	&& bad "/etc/sudoers.d/010_pi-nopasswd is in the image" || ok "no sudoers rule for pi"

echo
[ $fail -eq 0 ] && echo "RESULT: all checks passed" || echo "RESULT: FAILURES above"
exit $fail
