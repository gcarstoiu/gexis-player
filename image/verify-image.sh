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
image/stage-gexis/03-core/files/gexis-core.service /etc/systemd/system/gexis-core.service
image/stage-gexis/03-core/files/gexis-boot-volume.service /etc/systemd/system/gexis-boot-volume.service
image/stage-gexis/03-core/files/gexis-bluetooth-trust.service /etc/systemd/system/gexis-bluetooth-trust.service
image/stage-gexis/03-core/files/gexis-meter.service /etc/systemd/system/gexis-meter.service
image/stage-gexis/04-ui/files/gexis-kiosk.service /etc/systemd/system/gexis-kiosk.service
image/stage-gexis/04-ui/files/gexis-kiosk-start /usr/local/bin/gexis-kiosk-start
image/stage-gexis/04-ui/files/kiosk.env /etc/gexis/kiosk.env
image/stage-gexis/04-ui/files/labwc-rc.xml /home/pi/.config/labwc/rc.xml
image/stage-gexis/05-peppy/files/gexis-peppy.service /etc/systemd/system/gexis-peppy.service
image/stage-gexis/05-peppy/files/gexis-peppy-start /usr/local/bin/gexis-peppy-start
image/stage-gexis/05-peppy/files/gexis-peppy-driver.py /opt/gexis-peppy/driver.py
image/stage-gexis/05-peppy/files/gexis_peppy_render.py /opt/gexis-peppy/gexis_peppy_render.py
image/stage-gexis/05-peppy/files/peppy-meter.txt /opt/gexis-peppy/peppymeter/config.txt
image/stage-gexis/05-peppy/files/peppy-spectrum.txt /opt/gexis-peppy/spectrum/config.txt
skins/templates/meters.txt /opt/gexis-peppy/skins/gelo5/templates/1280x800/meters.txt
skins/templates_spectrum/meters.txt /opt/gexis-peppy/skins/gelo5/templates_spectrum/1280x800/meters.txt
skins/templates_spectrum/spectrum.txt /opt/gexis-peppy/skins/gelo5/templates_spectrum/1280x800/spectrum.txt
EOF

echo "== files the services must be able to write"
# The driver rewrites the spectrum engine's config to choose a section - the
# engine has no other way to be told - and the unit runs as pi (uid 1000).
# Shipped root-owned, that write raised PermissionError after the display
# existed and left a black window on the panel (ADR-0051 §3).
own=$(dfs "stat /opt/gexis-peppy/spectrum/config.txt" | grep -o 'User: *[0-9]*' | tr -s ' ')
[ "$own" = "User: 1000" ] && ok "spectrum config owned by uid 1000" || bad "spectrum config ownership: '${own:-missing}'"

echo "== units enabled (symlink targets)"
for u in gexis-core gexis-boot-volume gexis-bluetooth-trust gexis-meter gexis-kiosk gexis-peppy; do
	t=$(dfs "stat /etc/systemd/system/multi-user.target.wants/$u.service" | grep -o 'Fast link dest: ".*"')
	[ "$t" = "Fast link dest: \"/etc/systemd/system/$u.service\"" ] && ok "$u -> $t" || bad "$u enablement: '${t:-missing}'"
done
t=$(dfs "stat /etc/systemd/system/alsa-restore.service" | grep -o 'Fast link dest: ".*"')
[ "$t" = 'Fast link dest: "/dev/null"' ] && ok "alsa-restore masked" || bad "alsa-restore mask: '${t:-missing}'"
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

echo "== Peppy"
for f in peppymeter/peppymeter.py spectrum/spectrum.py fonts/DSEG7Classic-Italic.ttf icons/icon-spotify.png; do
	dfs "stat /opt/gexis-peppy/$f" | grep -q 'Inode:' && ok "/opt/gexis-peppy/$f" || bad "/opt/gexis-peppy/$f missing"
done
for c in gelo5 stock; do
	n=$(dfs "ls /opt/gexis-peppy/skins/$c/templates/1280x800" | grep -oE '[^ ]+\.(png|jpg)' | wc -l)
	[ "$n" -ge 10 ] && ok "$c templates: $n images" || bad "$c templates: $n images"
done
echo "  viz_timeout default in shipped registry: $(python3 -c "import json; r=json.load(open('$OUT/gexis_core/settings_registry.json')); s=[x for sec in r for x in sec.get('rows',[]) if x.get('key')=='viz_timeout']; print(repr(s[0].get('default')) if s else 'not found')" 2>&1)"
echo "  daemon fallback: $(grep -o 'settings.value("viz_timeout") or [0-9]*' "$OUT/gexis_core/__main__.py")"

echo
[ $fail -eq 0 ] && echo "RESULT: all checks passed" || echo "RESULT: FAILURES above"
exit $fail
