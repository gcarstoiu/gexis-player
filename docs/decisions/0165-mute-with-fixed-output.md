# ADR-0165 — Mute with fixed output

**Status:** **Accepted** — George, 2026-10-27: the second Phase 21 design
(`design/source/21`, *Fixed volume*) keeps mute on the fixed row and makes
it silence the output, on the panel too; asked how, he chose mute where the
output can be silenced and no mute where it cannot. Phase 21
(`ph-phone-controls`). **Amends** [ADR-0018](0018-volume-and-output-modes.md)
(*Mute does not exist in fixed output mode*) and
[ADR-0046](0046-fixed-output-hides-the-slider.md) (*Mute has no meaning in
fixed mode*). Builds on [ADR-0034](0034-panel-volume-travel-and-mute.md)
(mute remembers and restores) and [ADR-0164](0164-the-phone-remote.md) (the
phone remote).

## Context

With Fixed volume the device does not attenuate: the DAC's control is held
at full scale and the amplifier sets the level (ADR-0046). ADR-0018 took
mute away with the slider, because the mixer was locked. Every route to the
DAC's level goes through `VolumeBridge.write_hardware`, which refuses all
writes in Fixed; `/state` publishes no `volume` there, and
`POST /volume/mute` answers 409. The panel's fixed rows (the volume drawer,
the bar's tray) show the padlock and no mute.

The second phone remote design draws the panel's locked row with mute kept
at its left and says mute silences the output, the panel to follow.

## Decision

1. **With Fixed volume, mute silences the output where the output has a
   volume control of its own** (the HAT's DAC control, a USB DAC's): mute
   writes that control's silence, unmute writes full scale back. Both
   writes go straight to the control, as Fixed's own full-scale write does;
   the refusal in `write_hardware` stays for every other path. Unmuted, the
   chain is bit-perfect as before.
2. **Where the output has no control of its own** (a USB DAC without one,
   where Fixed takes the software stage out) nothing can silence it, and
   there is no mute: the button is left out, as a control a renderer does
   not declare is (ADR-0037), and `POST /volume/mute` answers 409 saying
   why.
3. **`fixed_mute` is published in `/state`**: `null` where there is no such
   mute (Variable, or Fixed on an output with no control), otherwise
   `false` or `true`. `volume` stays absent in Fixed (ADR-0046).
4. **The panel follows** (the panel's design is locked, so this is not
   drawn): its fixed rows - the volume drawer's, the bar's tray - get the
   mute button where the variable row has it, and the volume button on
   Now Playing and on the mini strip shows the crossed speaker in place of
   the padlock while muted (ADR-0018: the muted state is shown so it
   cannot be read as a fault).
5. **Mute ends with a change of volume type, of output, or a restart**, as
   each of them writes the level Fixed or Variable starts from: full scale
   in Fixed, the restored level in Variable. From Fixed and muted to
   Variable the DAC goes from silence to Variable's level, never through
   full scale.
6. **The meters**: while muted the published cut is silence, as with mute
   in Variable ([ADR-0146](0146-the-meters-follow-the-volume-again-with-a-gain.md));
   unmuted, Fixed cuts nothing again.
7. **The phone** (ADR-0164): the fixed row's mute uses the same route.

## Consequences

- A fixed output can be silenced for a phone call, as a variable one can,
  without touching the amplifier.
- On an output with no control of its own, Fixed still has no mute; the row
  says *Fixed output* and nothing else.
- Home Assistant's media player reads mute from `volume`; it shows mute with
  Fixed volume once the integration reads `fixed_mute` (its next release,
  with the card of ADR-0163).

## Not verified

- Whether a DAC's own control silences **native DSD** (ADR-0144: Fixed on a
  DAC that takes DSD). Many DACs pass DSD past their volume control. No test
  player has such a DAC; until one is measured, mute during native DSD is
  unproven.

## Alternatives considered

- **Pause playback where the output cannot be silenced.** Offered to
  George; not chosen. A mute that pauses is a different command under the
  same button.
- **Keep ADR-0018: no mute with Fixed.** Offered; not chosen.
