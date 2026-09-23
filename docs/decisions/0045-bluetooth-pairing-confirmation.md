# ADR-0045 — Bluetooth pairing is confirmed on the panel

**Status:** Accepted — George, 2026-09-20: *"yes, but it is secure. If the
user is serious about connecting by phone then he needs to accept the
connection on the [panel]"*. Scheduled as Phase 9 subphase 9f.
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

## The gate, 2026-09-21

**Passed with a real phone**, George: *"connection worked fine. pin was
shown and accepting it had no issues."* Which leaves the two Open questions
below answered by use rather than by argument.

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

## And `bt_discoverable` is not implemented either

**Found 2026-09-20 while scoping this.** The row offers Always / 3 min after
boot / Off and reports "3 min after boot". **Nothing chose three minutes.**
`bluetooth-setup.sh` runs `bluetoothctl discoverable on` and never touches
`DiscoverableTimeout`, so BlueZ's 180 s default silently reverts it — the
device reads `Discoverable: no`, `DiscoverableTimeout: 0x000000b4 (180)`.

`docs/LESSONS.md` already records this exact trap, which cost 1h36m and a
blocker, and the script still hits it. **None of the three options works**,
and "Always" needs `DiscoverableTimeout=0` before `discoverable on`, not
just the latter. George, 2026-09-20: *"It was a pain with the discoverable
for 3 minutes."* It belongs in this subphase because a device nobody can
discover cannot be paired with, confirmed or otherwise.

## Open

- ~~**What the agent actually is.**~~ **Established 2026-09-20 on the
  device: it has to be ours.** `gexis-bt-agent.service` runs
  `/usr/bin/bt-agent --capability=NoInputNoOutput` — the `bluez-tools`
  binary, which answers on its own console and has no route to the panel —
  and **`gexis_core` contains no agent code at all** (no match for
  `RequestConfirmation`, `DisplayYesNo` or `Capability` anywhere in the
  installed package). So this is not a capability flag: it is a BlueZ
  `Agent1` registered on D-Bus from the daemon, implementing
  `RequestConfirmation`, `AuthorizeService` and `Cancel`.
- **Whether `bt_autotrust` survives**, and if so what it means once a human is
  being asked.
- ~~**What happens to a request that arrives while the Peppy screen or the
  idle screen is up.**~~ **Closed 2026-09-21: it takes the screen, and the
  two cases are not the same problem.**

  The idle screen is a `div`, so the frame covers it by z-index alone — and
  that is what shipped, which was not enough. At 95% opacity the clock read
  through it, and the panel went back to idle the moment the frame closed
  (George, on the panel). **A request is attention**: it dismisses idle and
  counts as a touch, so after pairing the thing you just connected is the
  thing on screen.

  **The visualiser is not a layer at all.** PeppyMeter is a separate X
  client, and no z-index in the panel can draw over another process's
  window — a request arriving while the meter was up would have been
  invisible for its whole thirty seconds and then lapsed, with nothing on
  screen to explain it. So the daemon lowers the meter when the agent asks,
  which is the half the panel cannot do for itself. Only while the question
  is open: the outcome states publish like any other and leave the screen
  alone, because by then there is an answer and whatever was up should come
  back on its own.
