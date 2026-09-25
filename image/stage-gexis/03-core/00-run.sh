#!/bin/bash -e

# Source for the venv install below (00-run-chroot.sh) has to be inside
# ${ROOTFS_DIR} before that chroot step runs - it can't reach outside the
# chroot to find it. Copied from the Makefile's second bind-mount
# (/pi-gen/gexis-core-src -> repo root's core/), not vendored into
# stage-gexis itself, so `core/`'s own tests (tier 1, every commit) run
# against one source tree, not a copy that can drift from it.
CORE_SRC="/pi-gen/gexis-core-src"
if [ ! -f "${CORE_SRC}/pyproject.toml" ]; then
	echo "ERROR: ${CORE_SRC}/pyproject.toml not found - is the core/ bind-mount wired up in the Makefile?" >&2
	exit 1
fi

install -d -m 755 "${ROOTFS_DIR}/opt/gexis-core"
rm -rf "${ROOTFS_DIR}/opt/gexis-core/src"
cp -r "${CORE_SRC}" "${ROOTFS_DIR}/opt/gexis-core/src"
# .git-ish or test-cache cruft from a dev checkout shouldn't ship, even
# though it wouldn't be installed - keep the copy itself clean.
rm -rf "${ROOTFS_DIR}/opt/gexis-core/src/.pytest_cache"
find "${ROOTFS_DIR}/opt/gexis-core/src" -name "__pycache__" -exec rm -rf {} +

install -D -m 644 files/core.toml "${ROOTFS_DIR}/etc/gexis/core.toml"
install -D -m 644 files/gexis-core.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-core.service"
# `gexis-bluetooth-trust.service` is gone (ADR-0045). It polled every two
# seconds and trusted *every* paired-but-untrusted device, which would grant
# exactly what a human had just been asked about and might have refused -
# the confirmation would have decided nothing. The agent trusts what it was
# told to, and `bt_autotrust` became a real switch rather than a description
# of something that happened regardless.
#
# **Deleted here, not merely un-installed.** Builds are warm - the stage
# rootfs is preserved between them (`CONTINUE=1`), so a file an earlier
# build wrote stays until something removes it. Not removing it shipped an
# enabled unit whose module no longer exists: it would have failed at every
# boot and retried every two seconds for ever. Found by
# `image/verify-image.sh` against the built artefact, 2026-09-22.
rm -f "${ROOTFS_DIR}/etc/systemd/system/gexis-bluetooth-trust.service" \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-bluetooth-trust.service"
# `gexis-boot-volume.service` is gone too (2026-09-23, ADR-0018 amended).
# Measured: the converter comes up at -20 dB of its own accord, nothing
# restores a level across a boot (alsa-restore masked below, no
# asound.state, and the udev rule's own attempt fails with code 99), and
# nothing plays before a renderer acquires - at which point ADR-0054 §5
# sets the level from the renderer itself. **Same warm-build reasoning as
# above**: not installing it is not enough, it has to be removed.
rm -f "${ROOTFS_DIR}/etc/systemd/system/gexis-boot-volume.service" \
	"${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/gexis-boot-volume.service"
install -D -m 644 files/gexis-meter.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-meter.service"

# ADR-0018: "alsactl state is not used to restore volume across boots."
# The stock image ships alsa-restore.service (ExecStart=alsactl restore,
# ExecStop=alsactl store) enabled by default, which does exactly the
# restoring that record forbids - found on hardware, 2026-09-06: the
# mixer was stuck at 0% because some earlier session's level got stored
# on a clean shutdown and restored on every boot since.
#
# **This mask outlived `gexis-boot-volume` and is the load-bearing half.**
# With the boot unit gone (2026-09-23), it is the only thing standing
# between a level stored on shutdown and a device that boots into it, and
# Finding 047 §10 rests on it: "nothing carries a level across a boot" is
# true *because* of this line.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system"
ln -sf /dev/null "${ROOTFS_DIR}/etc/systemd/system/alsa-restore.service"

# ADR-0086: the three built-ins describe themselves the way a plugin does.
# Not for tidiness - so the generic path is the one exercised on every boot. A
# plugin's glyph drawn by code nothing else runs is how the first external
# plugin finds a hole.
#
# `/usr/share`, not `/etc`: a manifest is part of the software, shipped and
# upgraded with it, not something an administrator edits.
for plugin in files/plugins/*/; do
	id="$(basename "${plugin}")"
	install -D -m 644 "${plugin}plugin.json" \
		"${ROOTFS_DIR}/usr/share/gexis/plugins/${id}/plugin.json"
done

# ADR-0049: the idle screen's own pictures arrive over SMB, because nothing
# else on this appliance can put a file on it. **One directory**: not the
# home directory, not /var/lib/gexis-core - which holds the settings
# database, the enrichment cache and the downloaded wallpaper cache - and
# not a parent of either.
#
# The directory has to exist before the share does, owned by the user the
# share forces writes to. An absent path makes samba answer "connection
# refused" for a reason nobody can see from a phone.
install -d -o 1000 -g 1000 -m 2775 "${ROOTFS_DIR}/var/lib/gexis-core/pictures"
# ADR-0083: the second share, for the same reason and with the same shape - a
# backup that stays on the device does not survive the event it exists for,
# and this is how one leaves without a shell. Same file, same include.
install -d -o 1000 -g 1000 -m 2775 "${ROOTFS_DIR}/var/lib/gexis-core/backups"
install -D -m 644 files/gexis-pictures.conf \
	"${ROOTFS_DIR}/etc/samba/smb.conf.d/gexis-pictures.conf"
# Debian ships one monolithic smb.conf. Appending an include leaves their
# file to be theirs, so a package upgrade that rewrites it takes our share
# with it rather than fighting a conffile prompt - and the chroot step
# below asserts samba still reads the share afterwards.
if ! grep -q "smb.conf.d/gexis-pictures.conf" "${ROOTFS_DIR}/etc/samba/smb.conf"; then
	printf '\n# ADR-0049: the idle screen pictures share.\ninclude = /etc/samba/smb.conf.d/gexis-pictures.conf\n' \
		>> "${ROOTFS_DIR}/etc/samba/smb.conf"
fi

# ADR-0049 §4: avahi already runs here - it is how gexis.local resolves - so
# this is what puts the share in Finder's sidebar without nmbd.
install -D -m 644 files/gexis-smb.service \
	"${ROOTFS_DIR}/etc/avahi/services/gexis-smb.service"

# **Two of samba's three services are not wanted.** `nmbd` is NetBIOS name
# service, a second discovery protocol broadcasting on a LAN that already
# has one; `samba-ad-dc` is a domain controller, which the package enables
# by default and which this is not. Masked rather than disabled, so an
# upgrade cannot quietly re-enable them.
ln -sf /dev/null "${ROOTFS_DIR}/etc/systemd/system/nmbd.service"
ln -sf /dev/null "${ROOTFS_DIR}/etc/systemd/system/samba-ad-dc.service"

# **What build this is** (ADR-0022's `version` row). Nothing on a running
# device reported it: the `.info` file the Makefile writes sits beside the
# image in `deploy/`, where a device cannot read it. `IMG_SUFFIX` is the
# git-describe version with a leading dash, which is how the Makefile
# already names the image (see its `IMAGE_VERSION`).
install -d -m 755 "${ROOTFS_DIR}/etc/gexis"
printf 'version=%s\nbuilt=%s\n' \
	"${IMG_SUFFIX#-}" \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
	> "${ROOTFS_DIR}/etc/gexis/image.info"
chmod 644 "${ROOTFS_DIR}/etc/gexis/image.info"
