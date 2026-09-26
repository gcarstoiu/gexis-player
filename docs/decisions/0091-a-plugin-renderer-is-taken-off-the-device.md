# ADR-0091 — A plugin renderer is taken off the device, not asked to leave

**Status:** **Accepted**, 2026-09-26 — George, after the sweep he asked for:
*"Decision 1."* **Not built yet.**
**Date:** 2026-09-26
**Raised by:** George, 2026-09-26: *"There are two issues that are making the
plexamp plugin less attractive now. The biggest is the 14 seconds takeover time
as well as the fact that I cannot just disconnect from my phone with the panel
following the disconnect. Even when taking over via lms for example in the phone
i still see the panel as connected."*
**Relates to:** [0010](0010-arbitration-slot-model.md) (the ladder this changes),
[0089](0089-arbitration-carries-a-plugin-renderer.md) (what makes a plugin
renderer possible), [0090](0090-plexamp-ships-the-way-beszel-does.md) (the two
units, and why the manifest's `unit` is the player's),
[0027](0027-lms-power-as-arbitration-mechanism.md) (acquisition is deliberate,
which is why one of the four symptoms is not a defect)
**Evidence:** [Finding 088](../findings/088-making-plexamp-behave-like-the-other-renderers.md),
and [Finding 013 §1](../findings/013-phase2c-attack-test-and-spotify-reliability-defects.md)
for the failure this deliberately does not repeat

## Context

Plexamp gives the device back in ~14 s where LMS takes 0.4 s. Finding 088
decomposed it: the stop itself is immediate (`BASS: Stopped in 0 ms`), the output
is suspended at +3 s, and **the open PCM is held in `SETUP` for a further ~11 s**
before it closes. Squeezelite behaves the same way and we configure it not to —
`squeezelite.service` carries `-C 1`, worth ~700 ms against ~8500 ms at `-C 10`.
**Plexamp is squeezelite with `-C 13` and no way to set `-C`.** Every runtime
lever was tried and none releases the device: `audioDeviceUuid` re-initialises
BASS and keeps playing, `setSinksForSource` needs a mesh this install does not
have, and `remoteControl` is not settable over HTTP at all.

The second symptom has the same single cause, and it is **ours**.
`_release_with_ladder` polls the device for the whole of `polite_grace` and
returns `POLITE` the moment it frees. The plugin declares `polite_grace: 16.0`
and the device frees at ~14 s, so **the polite rung wins the race on every
takeover, the ladder never escalates, and the player is left running, registered
and claimed.** The phone is not wrong; the player really is still there.

## Decision

### 1. The polite stop stays, its grace shrinks

`release()` is still sent first, and not as a formality: it stops the audio in
0 ms and lets Plexamp persist its position and send its final timeline to the
server. What changes is that we stop *waiting out* a renderer that has already
told us it is done — the plugin declares a short `polite_grace` so the ladder
escalates instead of sitting through the remaining eleven seconds.

**The value belongs to the plugin, not the core.** It is a fact about Plexamp's
native layer, and the manifest already has the vocabulary for it.

### 2. Escalation is SIGKILL, never SIGTERM

Measured, Finding 088 §3:

| signal | what systemd does |
|---|---|
| SIGTERM | unit goes `inactive`, `ExecMainStatus=15`, `Result=success`, `NRestarts=0` — **it does not come back** |
| SIGKILL | back by itself at t+0.6 s, `NRestarts=1`, and the plugin unit with it |

So for a unit that relies on `Restart=on-failure`, **the SIGTERM rung is not a
gentler escalation — it is the rung that prevents recovery**, because systemd
does not count a SIGTERM death as a failure. `LmsAdapter.signal_stop` already
reached this conclusion for squeezelite and says so; `PluginAdapter` now matches
it, ignoring `force` and always sending SIGKILL.

This applies to **every** plugin renderer, not only Plexamp, and that is
deliberate: SIGKILL works for a unit that would have come back from SIGTERM too,
and graceful shutdown is what step 1 is for.

### 3. It comes back by itself — there is no restart hook

`Restart=on-failure` on the player's unit is the whole path back.
**`PluginAdapter.restart_after_release` stays the inherited no-op**, and the
reason is in the repository already: two attempts to stop-and-explicitly-restart
a renderer were shipped and reverted within a day each, because the restarted
process raced a still-busy device, failed busy on systemd's own `RestartSec`
clock, and burned through `StartLimitBurst` until the unit stayed failed
(Finding 013 §1). `LmsAdapter` carries the warning: *"see ADR-0010's
implementation note and Finding 013 §1 before proposing a third."*

**This is not a third attempt.** The storm needs a renderer that opens the ALSA
device as soon as it is back, and **Plexamp measurably does not** — `pcm` stayed
`closed` across both signal tests and a full restart, because Plexamp opens the
device when it plays, not when it starts. Telling the plugin over the socket
would not work either: by then the plugin's own process is gone, `PartOf=` having
followed the player down.

### 4. The last two rungs poll, as the first one already does

`sigterm_grace` and `sigkill_grace` are `asyncio.sleep`ed blind and then checked
once. That is exactly the defect [Finding 016](../findings/016-polite-grace-blind-sleep.md)
found in the polite rung and fixed there, and the fix was never carried to the
other two. Left alone it makes this decision almost pointless: the device is free
at 169 ms and the ladder would not look for 3 s.

## Rejected alternatives

- **A manifest field naming the signal** (`release_signal: sigkill`). Rejected on
  ADR-0090's rule: the contract was amended twice in Phase 10 because things
  could not be expressed *at all*, and this needs no new vocabulary — SIGKILL is
  correct for every unit, so it is a property of the escalation rather than of a
  plugin.
- **An explicit restart, in the core or the plugin.** §3. Reverted twice already.
- **`remoteControl=false` to withdraw the player instead of killing it.** It is
  the elegant mechanism — it de-registers at plex.tv and closes the GDM socket
  without exiting — but it is not in Plexamp's `isHeadlessSetting` gate, so `PUT`
  returns 400, and setting it in the file needs a restart and would remove the
  player from the phone permanently, which is the opposite of what is wanted.
- **The `audioDeviceUuid` switch.** Measured: BASS re-initialises in 0.13 s and
  never releases the device.
- **Leaving it at 14 s.** George's *"the biggest"*.

**Not rejected, still open:** the Squeeze Plex Hub route, which reaches the same
DAC bit-identically (`S32_LE 192000Hz 2ch` both ways, no transcode) and hands
back in 1.0 s, at the cost of replacing Plexamp's playback engine with LMS's.
That is a product decision George has not taken, and this record does not
pre-empt it — the two are independent, and this one is a contained change to
work we already own.

## Consequences

- **Takeover should cost about 0.7 s** instead of ~14 s — `polite_grace` plus the
  169 ms the device took to free under a kill in
  [Finding 077](../findings/077-plexamp-on-gexis.md). **To be measured, not
  assumed**; the number above is arithmetic on two separate measurements.
- **Plexamp becomes briefly unavailable on every takeover**: `/resources`
  answering again at 3.13 s, plex.tv `presence` back at 9.1 s. This is the price
  George accepted.
- **The stale "connected" clears on its own**: plex.tv `presence` within ≤10.5 s,
  the PMS client table within roughly three minutes. What the phone's UI does with
  that is unmeasured and is George's to observe.
- **Two of the four symptoms are not addressed and cannot be.** The panel cannot
  switch when the phone *selects* Plexamp, and cannot follow a disconnect, because
  nothing reaches the player on either event — established across five places and
  corroborated by an independent implementation of the player side (Finding 088
  §4). ADR-0027 already says acquisition is deliberate; a disconnect does not even
  stop playback, so the panel showing Plexamp as active is correct.
- **Nothing to inventory.** This introduces no setting: `polite_grace` is a
  manifest declaration, not a user-facing row, so ADR-0022's inventory is
  unchanged.

## Reversal conditions

- **A plugin renderer that opens the ALSA device at startup** makes Finding
  013 §1's restart storm reachable again, and §3's argument fails with it. The
  measurement that licences this decision is *"`pcm` stayed `closed` across both
  signal tests and a full restart"*, and it is a property of Plexamp, not of the
  contract.
- **A Plexamp release that exposes its device-close timeout**, or admits
  `remoteControl` to the headless settings gate, would make step 1 sufficient on
  its own and the kill unnecessary.
