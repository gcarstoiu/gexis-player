#!/bin/bash -e

# A system account for the agent, not `pi` and not root. It reads /proc and
# /sys and writes one file; nothing it does needs an interactive user's
# identity, and `pi` owns the renderers because they need the `audio` group,
# which this does not.
#
# Idempotent: this stage can be re-run against an existing rootfs cache.
if ! getent passwd beszel > /dev/null; then
	adduser --system --group --no-create-home \
		--home /var/lib/beszel-agent --shell /usr/sbin/nologin beszel
fi

# `StateDirectory=beszel-agent` in the unit creates and re-chowns this on every
# start; this only makes sure a first boot does not have to.
install -d -m 750 -o beszel -g beszel /var/lib/beszel-agent
