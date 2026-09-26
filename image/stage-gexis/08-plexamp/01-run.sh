#!/bin/bash -e

# **Plexamp, and the plugin that makes it a Gexis renderer** (ADR-0090).
#
# `07-beszel`'s shape, because George asked for it: *"Present in the image just
# like beszel. I thought in general we did beszel to learn how to do it. Let's
# rely on the learnings and do it similarly."*
#
# **Two downloads, because this is two things.** Plexamp headless is
# third-party and plays the music; `gexis-plexamp` is ours, lives in its own
# repository, and is what speaks the contract - which is Phase 10's criterion 2
# and the reason any of this exists.

# Plexamp headless. Pinned to the version every measurement in Findings 077 and
# 082 was taken against, not to "latest": `plexamp.plex.tv/headless/version.json`
# names the current one and it happens to be this today, which is exactly why
# the version is written down here rather than followed.
PLEXAMP_VERSION="4.13.2"
PLEXAMP_ASSET="Plexamp-Linux-headless-v${PLEXAMP_VERSION}.tar.bz2"
PLEXAMP_URL="https://plexamp.plex.tv/headless/${PLEXAMP_ASSET}"
PLEXAMP_SHA256="86e5ede3d852a87099a106f2cc6b83e4ec1350000176d83fbcedb83950c48041"

# Our plugin, from its own release rather than from a tag's auto-generated
# archive: GitHub does not promise those are byte-stable, and a checksum that
# changes under you is worse than none because it fails a build nobody touched.
PLUGIN_VERSION="0.2.1"
PLUGIN_ASSET="gexis-plexamp-${PLUGIN_VERSION}.tar.gz"
PLUGIN_URL="https://github.com/gcarstoiu/gexis-plexamp/releases/download/v${PLUGIN_VERSION}/${PLUGIN_ASSET}"
PLUGIN_SHA256="a816fc5e7670766a38288207a5add56ecf4d6df061e907011b9d5e799128553c"

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

# shellcheck source=../fetch-cached.sh
. /pi-gen/stage-gexis/fetch-cached.sh

fetch_cached "${PLEXAMP_URL}" "${PLEXAMP_SHA256}" "${WORK}/${PLEXAMP_ASSET}"
fetch_cached "${PLUGIN_URL}" "${PLUGIN_SHA256}" "${WORK}/${PLUGIN_ASSET}"

# **Plexamp lives in `pi`'s home, not in /opt**, and that is not a preference:
# it keeps its settings - including the Plex token the plugin reads - under
# `~/.local/share/Plexamp`, and its own service file assumes the layout. Fighting
# that would mean patching an upstream tree on every upgrade.
tar -xjf "${WORK}/${PLEXAMP_ASSET}" -C "${WORK}"
rm -rf "${ROOTFS_DIR}/home/pi/plexamp"
mkdir -p "${ROOTFS_DIR}/home/pi"
cp -a "${WORK}/plexamp" "${ROOTFS_DIR}/home/pi/plexamp"
chown -R 1000:1000 "${ROOTFS_DIR}/home/pi/plexamp"

# Its unit is ours, not the tarball's: the one it ships hardcodes a user and a
# path, and this one has to match what the manifest names as the unit the
# release ladder escalates against.
install -D -m 644 files/plexamp.service \
	"${ROOTFS_DIR}/etc/systemd/system/plexamp.service"

# The plugin: source, manifest, mark and unit, from the release tarball rather
# than copied out of this repository - what ships is what that repository
# published, which is the whole point of criterion 2.
tar -xzf "${WORK}/${PLUGIN_ASSET}" -C "${WORK}"
PLUGIN_SRC="${WORK}/gexis-plexamp"
# **`rm -rf` first, or a warm rebuild nests instead of replacing.** `cp -a SRC
# DEST` copies *into* DEST when DEST already exists as a directory, and every
# build here runs `CONTINUE=1` against a preserved rootfs - so the second build
# left the previous release exactly where it was and hid the new one at
# `src/gexis_plexamp/gexis_plexamp/`, which `PYTHONPATH=/opt/gexis-plexamp/src`
# does not import.
#
# Found 2026-09-26 by reading the rootfs instead of the exit status. The stage
# reported success in one second, `verify-image.sh` passed because the file it
# looks for existed, and the image would have shipped v0.2.0 under a manifest
# that said v0.2.1. The Plexamp copy twenty lines up already did this; the
# plugin copy never did. Same shape as the `Wants=` defect found the same day:
# something was checked for existing and never for being right.
rm -rf "${ROOTFS_DIR}/opt/gexis-plexamp/src/gexis_plexamp"
mkdir -p "${ROOTFS_DIR}/opt/gexis-plexamp/src"
cp -a "${PLUGIN_SRC}/src/gexis_plexamp" "${ROOTFS_DIR}/opt/gexis-plexamp/src/gexis_plexamp"
install -D -m 644 "${PLUGIN_SRC}/gexis-plexamp.service" \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-plexamp.service"

# ADR-0086: the manifest and its glyph, at the same path as every other
# plugin's. **The plugin's repository owns these**, unlike Beszel's, whose
# manifest this repository writes because Beszel has never heard of us.
install -D -m 644 "${PLUGIN_SRC}/plugin.json" \
	"${ROOTFS_DIR}/usr/share/gexis/plugins/plexamp/plugin.json"
install -D -m 644 "${PLUGIN_SRC}/mark.png" \
	"${ROOTFS_DIR}/usr/share/gexis/plugins/plexamp/mark.png"

# **Neither unit is enabled.** An unclaimed Plexamp is a renderer that cannot
# play anything, and the switch in the Plugins category reads the unit's real
# state (ADR-0086 as amended), so leaving them off is what makes that row say
# "off" on a fresh image instead of claiming something that is not running.
