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
image/stage-gexis/07-beszel/files/beszel-agent.service /etc/systemd/system/beszel-agent.service
image/stage-gexis/07-beszel/files/beszel-agent-listen-check.sh /usr/local/lib/gexis/beszel-agent-listen-check.sh
image/stage-gexis/07-beszel/files/plugin.json /usr/share/gexis/plugins/beszel/plugin.json
skins/templates/meters.txt /opt/gexis-peppy/skins/gelo5/templates/1280x800/meters.txt
skins/templates_spectrum/spectrum.txt /opt/gexis-peppy/skins/gelo5/templates_spectrum/1280x800/spectrum.txt
EOF

# The spectrum pack's meters.txt is the one file the build does not install
# verbatim: two sections named the *spectrum's* blank panel as their meter
# background, and 05-peppy/01-run.sh corrects them (Finding 050). So it is
# compared against the upstream copy *with that correction applied* - the
# same sed, run here, rather than the check being dropped.
sm_src="$OUT/meters-expected.txt"
sed -e '/\[111G5_Teletronix S+M\]/,/\[112G5/ s/Teletronix_bgr\.png/Teletronix.jpg/' \
	-e '/\[107G5_Marantz S+M\]/,/\[108G5/ s/Marantz_bgr\.png/Marantz.jpg/' \
	"$REPO/skins/templates_spectrum/meters.txt" > "$sm_src"
if ! cmp -s "$REPO/skins/templates_spectrum/meters.txt" "$sm_src"; then
	dfs "dump /opt/gexis-peppy/skins/gelo5/templates_spectrum/1280x800/meters.txt $OUT/one" >/dev/null
	if cmp -s "$sm_src" "$OUT/one"; then
		ok "spectrum meters.txt = upstream + the two corrected backgrounds"
	else
		bad "spectrum meters.txt is neither upstream nor upstream+correction"
	fi
	rm -f "$OUT/one"
else
	bad "the meter background correction matched nothing in skins/ (Finding 050)"
fi

echo "== files the services must be able to write"
# The driver rewrites the spectrum engine's config to choose a section - the
# engine has no other way to be told - and the unit runs as pi (uid 1000).
# Shipped root-owned, that write raised PermissionError after the display
# existed and left a black window on the panel (ADR-0051 §3).
own=$(dfs "stat /opt/gexis-peppy/spectrum/config.txt" | grep -o 'User: *[0-9]*' | tr -s ' ')
[ "$own" = "User: 1000" ] && ok "spectrum config owned by uid 1000" || bad "spectrum config ownership: '${own:-missing}'"

echo "== units enabled (symlink targets)"
for u in gexis-core gexis-meter gexis-kiosk gexis-peppy; do
	t=$(dfs "stat /etc/systemd/system/multi-user.target.wants/$u.service" | grep -o 'Fast link dest: ".*"')
	[ "$t" = "Fast link dest: \"/etc/systemd/system/$u.service\"" ] && ok "$u -> $t" || bad "$u enablement: '${t:-missing}'"
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

echo "== Beszel (ADR-0087), the first plugin that is not part of the core"
# The binary is pinned in the stage and verified there against a checksum agreed
# three ways; this asserts the *image* got that exact build, which the stage's
# own check cannot say anything about once it has exited.
want_sha="$(grep -oE 'BESZEL_SHA256="[0-9a-f]+"' "$REPO/image/stage-gexis/07-beszel/00-run.sh" | cut -d'"' -f2)"
dfs "dump /usr/local/bin/beszel-agent $OUT/agent" >/dev/null
if [ ! -s "$OUT/agent" ]; then
	bad "/usr/local/bin/beszel-agent missing"
else
	size=$(stat -c%s "$OUT/agent")
	[ "$size" -gt 1000000 ] && ok "beszel-agent installed ($size bytes)" \
		|| bad "beszel-agent is $size bytes"
	# The tarball's checksum is what the stage pins; the extracted binary has its
	# own, and this is it - taken from the first image built with this stage
	# (2026-09-25) and confirmed identical to the binary that was run, enrolled
	# and measured on `gexis` before the stage existed (Findings 078 and 080).
	# So this asserts the image ships the build that was actually tested.
	BESZEL_BINARY_SHA256="4c95b91e7c07912c8f8b6ea4286a6be926cc0616ba49b079082120bea3b203ed"
	got="$(sha256sum "$OUT/agent" | cut -d' ' -f1)"
	[ "$got" = "$BESZEL_BINARY_SHA256" ] && ok "beszel-agent is the build that was tested" \
		|| bad "beszel-agent sha256 is $got, expected $BESZEL_BINARY_SHA256"
	[ -n "$want_sha" ] || bad "no BESZEL_SHA256 pin found in the stage"
fi
rm -f "$OUT/agent"

# **Not enabled.** An unenrolled device runs nothing, and the switch on the
# settings screen reads the unit's real state (ADR-0086 as amended) - so a unit
# enabled here would put a row on screen claiming something nobody asked for.
if dfs "stat /etc/systemd/system/multi-user.target.wants/beszel-agent.service" | grep -q 'Inode:'; then
	bad "beszel-agent is enabled in the image - ADR-0087 ships it off"
else
	ok "beszel-agent not enabled (ADR-0087: an unenrolled device runs nothing)"
fi

# The unit runs as its own account and the stage creates it in the chroot.
if dfs "dump /etc/passwd $OUT/passwd" >/dev/null && grep -q '^beszel:' "$OUT/passwd"; then
	ok "the beszel system account exists"
else
	bad "no beszel account - the unit names User=beszel and would fail to start"
fi
rm -f "$OUT/passwd"

# Every built-in manifest plus this one. A plugin the core cannot read is a
# source the panel cannot draw (ADR-0086).
plugins=$(dfs "ls /usr/share/gexis/plugins" | grep -oE '(beszel|lms|spotify|bluetooth)' | sort -u | tr '\n' ' ')
case "$plugins" in
	*beszel*lms*spotify*) ok "plugin manifests: $plugins" ;;
	*) bad "plugin manifests incomplete: $plugins" ;;
esac

echo "== ADR-0085: the ALSA default is our output"
dfs "dump /etc/alsa/conf.d/zz-gexis-default.conf $OUT/one" >/dev/null
if grep -q 'pcm.!default' "$OUT/one" 2>/dev/null; then
	ok "zz-gexis-default.conf points the ALSA default at our output"
else
	bad "zz-gexis-default.conf missing or does not set pcm.!default"
fi
rm -f "$OUT/one"

echo
[ $fail -eq 0 ] && echo "RESULT: all checks passed" || echo "RESULT: FAILURES above"
exit $fail
