#!/bin/sh
# ADR-0018: squeezelite -V DAC does not fail on a missing or misnamed mixer
# control - it logs an error and reverts to software volume, which
# falsifies the bit-perfect claim with no symptom (confirmed by reading
# squeezelite's output_alsa.c, not assumed). This is a startup assertion,
# not a preference: refuse to start rather than play.
#
# Checked through the same "output" ctl indirection squeezelite itself
# resolves -V against (see output.conf's ctl.output block), not a
# separate hw:sndrpihifiberry reference - ADR-0009 stays true even in
# a guard script.
exec amixer -D output sget DAC >/dev/null
