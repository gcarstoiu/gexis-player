#!/bin/sh
# **Asserts that `--listen -1` still means "listen on nothing"** (ADR-0087,
# Finding 078).
#
# The agent opens an inbound SSH port on 45876 by default, including when it is
# configured to connect *out* to a hub. `--listen -1` removes it - measured - but
# that is a value the flag parser happens to accept rather than documented
# behaviour. An upgrade could make it fatal, or a literal port, or simply ignore
# it. Ignored is the one that matters: the port would come back and nothing would
# say so.
#
# So this runs *after* the agent has started, looks at what it actually bound,
# and fails the unit if the answer is anything. A plugin whose whole security
# story is "there is nothing inbound to secure" should not start when that stops
# being true.
set -e

if ! command -v ss > /dev/null 2>&1; then
	# Warn and allow: a missing tool is not a reason to leave the device
	# without its monitoring, and this says plainly that the check did not run.
	echo "beszel-agent: ss is not installed, cannot verify that nothing is listening" >&2
	exit 0
fi

# The agent binds within its first moments; two seconds is well past that and
# well inside the unit's default start timeout.
sleep 2

if ss -ltn 2>/dev/null | grep -q ':45876[[:space:]]'; then
	echo "beszel-agent: something is listening on 45876 - '--listen -1' no longer" \
		"suppresses the agent's SSH server, so this build would put an inbound" \
		"port on the device. Refusing to run it. See ADR-0087 and Finding 078." >&2
	exit 1
fi
exit 0
