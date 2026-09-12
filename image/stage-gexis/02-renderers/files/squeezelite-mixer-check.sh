#!/bin/sh
# ADR-0018: squeezelite -V does not fail on a missing or misnamed mixer
# control - it logs an error and reverts to software volume, which
# falsifies the bit-perfect claim with no symptom (confirmed by reading
# squeezelite's output_alsa.c, not assumed). This is a startup assertion,
# not a preference: refuse to start rather than play.
#
# Checks squeezelite's actual -O/-V target (B2, George's decision
# 2026-09-08): the private hw:gexislmsvol dummy control, not the real
# DAC directly - see squeezelite.service's own comment for why. The
# real DAC is asserted separately, at boot, by the snd-dummy module load
# itself failing if absent - this script's job is only "does squeezelite's
# own mixer target exist".
if amixer -D hw:gexislmsvol sget Master >/dev/null 2>&1; then
    echo "mixer check: control 'Master' present on 'hw:gexislmsvol' - hardware volume asserted"
    exit 0
fi
echo "mixer check: control 'Master' NOT found on 'hw:gexislmsvol' - refusing to start" >&2
amixer -D hw:gexislmsvol scontrols >&2 || true
exit 1
