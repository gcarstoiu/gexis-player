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

> **"Persistently discoverable" has never actually been true — found
> 2026-09-12 (Finding 018, blocker 3).** `gexis-bluetooth-setup.sh` runs
> `bluetoothctl discoverable on`, but BlueZ's `DiscoverableTimeout`
> defaults to **180 seconds** and `/etc/bluetooth/main.conf` (which this
> image already edits, to set `Name`) never overrides it. So the adapter
> has been discoverable for three minutes after each boot and not
> afterwards. `Pairable` is unaffected — its own default is never-expire —
> which is why pairing still completes once a phone reaches the adapter.
>
> Measured consequence: after a reflash, `/var/lib/bluetooth` is wiped, so
> a phone holding a stale bond has to pair afresh — and fresh pairing needs
> discoverability, which by then was long gone. That is the "Bluetooth
> doesn't connect on the first try after a new build" report, and the logs
> show 60 seconds from first contact to audio with a 36-second dead spot.
>
> **DECIDED, 2026-09-12: no change. George's call.** The fix is one line
> (`DiscoverableTimeout = 0` in `main.conf`, or `bluetoothctl
> discoverable-timeout 0` before `discoverable on`; mechanism confirmed
> live) and it is deliberately **not** being applied, because it widens
> this record's accepted exposure from *three minutes after each boot* to
> *continuously*. The shipped behaviour stays the 3-minute window.
>
> **What that means in practice, so nobody is surprised by it later:**
> re-pairing a phone — after a reflash, or after the bond is cleared on
> either side — must happen within three minutes of boot, or the adapter
> has to be made discoverable by hand first. Reconnecting an
> already-bonded phone is unaffected and needs no discoverability at all.
> The wording above this note is therefore now accurate about *intent*
> only; the implementation deliberately does less.

## Consequence, stated plainly

**Anyone within Bluetooth range can pair with `gexis` and play audio
through it, with no confirmation step on the device.** This is the
direct effect of `NoInputNoOutput`, not a side effect — accepted for
this installation, not overlooked.

**Narrower in practice than this says, accidentally** (2026-09-12, see the
note above): the adapter is only *discoverable* for three minutes after
boot, so in practice a stranger's window to initiate a fresh pairing has
been small. That is an accident of an unset BlueZ default, not a designed
mitigation, and it is exactly what the pending decision above would
remove. Anyone weighing that decision should read this consequence as
what it becomes, not what it has been.

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
