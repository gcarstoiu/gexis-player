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
install -D -m 644 files/gexis-boot-volume.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-boot-volume.service"
# `gexis-bluetooth-trust.service` is gone (ADR-0045). It polled every two
# seconds and trusted *every* paired-but-untrusted device, which would grant
# exactly what a human had just been asked about and might have refused -
# the confirmation would have decided nothing. The agent trusts what it was
# told to, and `bt_autotrust` became a real switch rather than a description
# of something that happened regardless.
install -D -m 644 files/gexis-meter.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-meter.service"

# ADR-0018: "alsactl state is not used to restore volume across boots."
# The stock image ships alsa-restore.service (ExecStart=alsactl restore,
# ExecStop=alsactl store) enabled by default, which does exactly the
# restoring that record forbids - found on hardware, 2026-09-06: the
# mixer was stuck at 0% because some earlier session's level got stored
# on a clean shutdown and restored on every boot since, with
# gexis-boot-volume.service's own explicit set racing it with no
# guaranteed order (both only declare `After=sound.target`). Masking is
# more correct than winning the race: it makes "never restored" actually
# true rather than "restored, then immediately overwritten," and stops
# alsactl from persisting a level on shutdown at all.
mkdir -p "${ROOTFS_DIR}/etc/systemd/system"
ln -sf /dev/null "${ROOTFS_DIR}/etc/systemd/system/alsa-restore.service"

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
