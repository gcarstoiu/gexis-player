# ADR-0046 — Fixed output hides the volume control everywhere

**Status:** Accepted — George, 2026-09-20: *"this is something that was
completely missed in the implementation until now and needs to be handled.
Should be bundled with the topic above"* — the topic being the whole volume
setup. Scheduled as Phase 9 subphase **9i, deliberately last**: it is the only
subphase with a physical consequence and nothing depends on it.
**Date:** 2026-09-20
**Raised by:** [Finding 040](../findings/040-the-design-drop-and-what-it-changes.md),
which found it never built
**Implements:** [ADR-0018](0018-volume-and-output-modes.md)'s fixed mode, open
since it was written
**Relates to:** [ADR-0034](0034-panel-volume-travel-and-mute.md) (panel volume
travel), and George's 2026-09-20 ruling on units: *"For the user the same will
be shown everywhere which is percent. How we handle it in the background is
not transparent to the user except for the sound curves where we will map dB
to percentage."* — so the presentation change is settled and costs nothing;
what is not settled is the boot level (see Open)

## Context

ADR-0018 defined two output modes. Only variable was ever built. ADR-0022's
inventory has carried `output_mode` as `[R]` recorded-and-unimplemented since,
and the design has drawn the fixed case from the beginning:

> *"Fixed comes from the output mode: the device is not attenuating at all, so
> a slider would be a lie — per ADR-0018 it disappears rather than sitting
> there disabled."*

**The code does exactly what that forbids.** With no volume published, both
triggers render as a disabled button — `disabled={!volume}` at
`NowPlaying.svelte:463` and `MiniStrip.svelte:86` — and the drawer is simply
not mounted. A user in fixed mode sees a greyed control with no explanation,
which is the one outcome the design argued against by name.

This is the oldest unbuilt decision in the project, and the only place found
in Finding 040's audit where the implementation contradicts the design
outright rather than merely lagging it.

## Decision

**In fixed output mode the volume control is absent, not disabled, and the
reason is visible where the control used to be.**

- **The slider disappears everywhere** — now playing, the mini strip and the
  volume drawer. Not greyed, not inert: gone.
- **The drawer keeps a row where the slider was**, reading *"Fixed output —
  level is set downstream. Set it on your amplifier."* The drawer still opens,
  so the answer is where the question is asked.
- **Both volume triggers carry a padlock badge**, so the state is legible
  without opening anything.
- **`/state` publishes the mode.** The panel cannot infer fixed from an absent
  volume: a renderer that simply has not reported yet looks identical, which
  is why today's `disabled={!volume}` is wrong rather than merely ugly.
- **Choosing Fixed warns before it applies**, using ADR-0044's `warn`: the
  signal leaves at 100% and the panel can no longer lower it. ADR-0018 already
  requires confirmation and application on the next track or after stop; this
  adds the sentence that makes the confirmation meaningful.

## Consequences

- **A wrong choice here is loud.** Fixed output at 100% into an amplifier set
  for a quiet source is the worst failure this device can produce, which is
  why the warning is part of the decision and not a nicety.
- **Mute has no meaning in fixed mode**, and neither does
  [ADR-0034](0034-panel-volume-travel-and-mute.md)'s travel curve or the
  restore-on-return logic. Those paths need a fixed branch rather than a
  clamped one.
- **`volume_managed` was removed** from the inventory by the design drop
  (George, 2026-09-20). What a renderer's capability means in fixed mode is
  therefore unrecorded, and this record does not settle it.
- **The Peppy screen is unaffected**: it draws levels from the meter, not from
  the mixer.

## Alternatives considered

- **Leave it disabled**, as today. Rejected: a disabled control with no
  explanation is indistinguishable from a bug, and the design named this
  outcome as the one to avoid.
- **Hide the trigger entirely, with no padlock.** Rejected: the user then has
  no way to learn why the panel will not change the volume.
- **Keep the slider and clamp it to 100%.** Rejected: it would move and change
  nothing, which is the lie the design refers to.

## Open

- ~~**Whether fixed mode is reachable at all before ADR-0044 lands.**~~
  **Closed by sequencing:** ADR-0044 is 9d and this is 9i, so `warn` exists
  before it is needed.
- **The boot level, which is the number nobody has chosen.** Measured
  2026-09-20 with the daemon's own functions: the device boots at raw 60/240
  = **−90.0 dB = 0%** (`gexis-boot-volume.service`: *"setting 'DAC' to 60/240
  (fixed safe level, not restored)"*), and the design's `boot_volume` default
  is **60% = −18.0 dB**. That is **+72 dB at every cold boot**, into an
  amplifier at whatever gain it was left at. ADR-0018 calls the present level
  "a fixed safe level". 20% is −36 dB and 40% is −27 dB; there is a great deal
  of room between the two. **George's call, inside 9i.**
- **`travel_curve` names a curve the code does not implement.** The row
  reports `dB-linear`, which the design defines as travel straight to dB —
  *"55% is already −54 dB"*, exact across the hardware's −120…0 range. The
  slider is ADR-0034's −45…0 window, where 55% is **−20.25 dB**. It is
  unwired, so nothing acts on it; wiring it as written would make every
  renderer's slider 34 dB quieter at mid-travel, since `SPOTIFY_DB_MIN` uses
  the same span. Whether ADR-0034's window *is* "Perceptual" is the real
  question.
- **`max_ceiling` is `None`** — no ceiling is enforced at all today.
- **What a renderer that manages its own volume does in fixed mode** — see
  `volume_managed` above.
- **Whether the mode is per-device or per-renderer.** ADR-0018 assumes the
  device; nothing has tested that assumption against Spotify or Bluetooth,
  both of which carry their own volume.
