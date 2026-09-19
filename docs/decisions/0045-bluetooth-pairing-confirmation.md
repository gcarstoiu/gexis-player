# ADR-0045 — Bluetooth pairing is confirmed on the panel

**Status:** Proposed — awaiting George
**Date:** 2026-09-20
**Raised by:** the 2026-09-19 design drop, reviewed in
[Finding 040](../findings/040-the-design-drop-and-what-it-changes.md)
**Reverses:** [ADR-0024](0024-bluetooth-pairing-no-pin.md) — pairing without a
PIN, for this installation
**Depends on:** [ADR-0044](0044-settings-row-vocabulary.md) for the
`bt_trusted` list

## Context

ADR-0024 chose PIN-free pairing — BlueZ's "Just Works", agent capability
`NoInputNoOutput` — because the panel had nothing to confirm with and the
device sits in one home. `bt_pairing` has carried a `?` in ADR-0022's
inventory ever since, with the note that it *"needs this screen before it can
be anything but hardcoded"*.

**That screen now exists**, and the drop makes "Confirmation required" the
default.

**What PIN-free actually means today:** any phone in range that finds the
device can pair with it and take the audio, with no moment at which anyone
present agrees. ADR-0024 accepted that knowingly for a single household. It
is the same shape as [ADR-0028](0028-ui-serving-and-command-channel.md)'s
unauthenticated LAN API — defensible in one room, indefensible as a property
of a product.

## Decision

**Pairing asks, on the panel, and the panel's answer is the decision.**

- **`bt_pairing` defaults to "Confirmation required"**, with PIN-free
  remaining a choice for anyone who wants the old behaviour.
- **Only on a device's first pair.** Once trusted, later connections run the
  plain handoff. The question is "should this device be allowed", not "is this
  you again".
- **The agent's capability changes** from `NoInputNoOutput` to one that can
  display and confirm, so BlueZ produces a six-digit code and waits.
- **The panel shows the requesting device's name, the code, Reject and
  Accept**, in the handoff frame rather than a new overlay — the same visual
  language as a takeover, because that is what accepting is.
- **Accepting is the takeover.** The frame becomes a tick, then hands
  straight into the handoff, whether or not audio has started.

### The countdown is real, and it is the agent's

The panel counts 30 seconds down and, at zero, shows **"Request expired"**,
holds 1.8s and dismisses — no handoff, the device not trusted, the same
outcome as Reject.

**This is the load-bearing part.** The timeout belongs to the BlueZ agent, not
to the panel's animation: the panel must not outlive the request it is
displaying. A frame still offering Accept after the phone has given up is a
lie, and tapping it would either do nothing or trust a device whose request no
longer exists.

## Consequences

- **Pairing can now fail by being ignored**, which it could not before. That
  is the point, but it means a pair attempted while nobody is at the panel
  does not succeed — a real behaviour change for a device in another room.
- **`gexis-bt-agent.service` changes capability**, and the agent needs a
  channel to the daemon for the request, the code, and the two answers. None
  of that exists today.
- **`bt_pairing` stops carrying a `?`**, and ADR-0024's accepted risk is
  narrowed to whoever chooses PIN-free deliberately.
- **`bt_autotrust` needs re-examining.** `gexis-bluetooth-trust.service`
  currently trusts every paired-but-untrusted device on a 2s poll, which would
  undercut a confirmation the user was asked for. It is a separate unit, not
  part of `gexis-core`.

## Alternatives considered

- **Keep PIN-free and skip the screen.** Rejected by George in accepting the
  design; the screen was the thing ADR-0024's open question was waiting for.
- **Confirm on the phone only.** That is what Just Works already does, and it
  asks the person holding the phone rather than the person at the device.
- **Confirm every connection, not just the first.** Rejected: the second
  connection is a takeover, and ADR-0027 already decides how those resolve.
- **A panel-side timeout independent of the agent's.** Rejected — see the
  countdown above. Two timers disagreeing is how a frame comes to be offering
  something it cannot deliver.

## Open

- **What the agent actually is.** `bt-agent --capability=DisplayYesNo` is the
  obvious move, but whether it can be driven from `gexis-core` or needs
  replacing with our own agent on D-Bus is not established.
- **Whether `bt_autotrust` survives**, and if so what it means once a human is
  being asked.
- **What happens to a request that arrives while the Peppy screen or the idle
  screen is up.** The frame has to take the screen from something.
