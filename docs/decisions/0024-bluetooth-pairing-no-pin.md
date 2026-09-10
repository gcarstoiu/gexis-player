# ADR-0024 — Bluetooth pairing: no PIN, for this installation

**Status:** Accepted
**Date:** 2026-09-06

## Context

Attempted Bluetooth pairing during Phase 2b hardware testing failed with
a PIN error — nothing on `gexis` supplies or confirms one, so the phone's
pairing request has no way to complete. A BlueZ pairing agent has to be
registered to answer these requests at all; its *capability* determines
whether that means "prompt for a PIN," "ask for confirmation," or
"accept without asking" (`NoInputNoOutput`, the "Just Works" model).

## Decision

**Pair without a PIN, at this installation, indefinitely — not just
until a display exists.** George's location does not require pairing
confirmation, and the reasoning does not change once Phase 4 adds a
screen: a display changes what *could* be shown during pairing, not
whether confirmation is *needed* here.

Implemented with `bt-agent --capability=NoInputNoOutput`
(`bluez-tools`), registered as the default agent, alongside making the
adapter persistently pairable and discoverable — see
`image/stage-gexis/02-renderers/files/gexis-bt-agent.service` and
`gexis-bluetooth-setup.service`.

## Consequence, stated plainly

**Anyone within Bluetooth range can pair with `gexis` and play audio
through it, with no confirmation step on the device.** This is the
direct effect of `NoInputNoOutput`, not a side effect — accepted for
this installation, not overlooked.

## Not a shipping default

This is a per-installation choice, not a product default. A flat in a
building with neighbours within range is a different threat model than
the location this was decided for, and defaults to "no PIN, always
discoverable" would be wrong there. **To be recorded** (ADR-0022,
settings): pairing mode (PIN-free / confirm / PIN) as a per-installation
setting, once that settings infrastructure exists. Until then, this
record is the only place the choice is written down, and it applies to
this installation specifically — a future default-setting decision for
new installs should not assume this one.
