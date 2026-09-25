#!/bin/bash -e

# **The first plugin this repository ships that is not part of the core**
# (ADR-0087). A monitoring agent: no metadata, no transport, no claim on the
# audio device - which is exactly what Phase 10 criterion 3 asks for. If the
# contract cannot express that, it is a renderer API wearing a plugin's name.
#
# Its own stage rather than another directory under 03-core's manifest loop: the
# three there are the core's own renderers, and everything about this one - a
# binary, a unit, a user, a manifest - belongs in one place, which is also what
# an outside plugin author would have to assemble.
#
# George chose the image over an on-demand install, 2026-09-25: *"In the
# image."* An installer would have meant a writable plugin directory, a
# checksummed download at runtime and a rule about who may ask for one, which is
# a phase of its own.

# Pinned and verified the way go-librespot is (ADR-0042), and the checksum was
# agreed three ways before being written here rather than copied from the API
# once: the computed sum, GitHub's asset digest, and upstream's own
# `beszel_0.20.0_checksums.txt`.
#
# The release also carries an arm64 .deb and it is deliberately not used: it
# brings its own unit, its own user and its own update path, and this unit has to
# carry `--listen -1` and ADR-0088's environment file.
BESZEL_VERSION="v0.20.0"
BESZEL_ASSET="beszel-agent_linux_arm64.tar.gz"
BESZEL_URL="https://github.com/henrygd/beszel/releases/download/${BESZEL_VERSION}/${BESZEL_ASSET}"
BESZEL_SHA256="dbb292d7309ca00cfd7f3d8f86480991f7c959e65af6506754a55d3e345452ab"

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

# Content-addressed cache first, network on a miss (ADR-0042).
# shellcheck source=../fetch-cached.sh
. /pi-gen/stage-gexis/fetch-cached.sh

fetch_cached "${BESZEL_URL}" "${BESZEL_SHA256}" "${WORK}/${BESZEL_ASSET}"

tar -xzf "${WORK}/${BESZEL_ASSET}" -C "${WORK}" beszel-agent

install -D -m 755 "${WORK}/beszel-agent" "${ROOTFS_DIR}/usr/local/bin/beszel-agent"

install -D -m 755 files/beszel-agent-listen-check.sh \
	"${ROOTFS_DIR}/usr/local/lib/gexis/beszel-agent-listen-check.sh"

install -D -m 644 files/beszel-agent.service \
	"${ROOTFS_DIR}/etc/systemd/system/beszel-agent.service"

# ADR-0086: the same path and the same shape as the three built-in manifests.
# Nothing in the core knows this plugin's name.
install -D -m 644 files/plugin.json \
	"${ROOTFS_DIR}/usr/share/gexis/plugins/beszel/plugin.json"

# **Not enabled.** ADR-0087: an unenrolled device runs nothing, and the switch on
# the settings screen reads the unit's real state (ADR-0086 as amended), so
# leaving it disabled here is what makes that row say "off" on a fresh image
# rather than claiming something that is not running.
