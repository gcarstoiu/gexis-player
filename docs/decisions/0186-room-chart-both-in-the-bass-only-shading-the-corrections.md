# ADR-0186 — Room correction's chart: *Both* in the bass only, the shading the corrections'

**Status:** **Accepted** 2026-11-19 (George approved C1-C2); proposed the
same day: George decided D1-D2 after looking at his full-range check on
sofapi; C1-C2 are Claude's. Built on `room-chart`.
**Amends:** [ADR-0177](0177-room-correction-for-the-full-range.md) (the
chart, the design's §2) and
[ADR-0175](0175-room-correction-for-the-bass.md)'s amendment of 2026-11-17,
item 4 (the *Both* tab).

## Context

On sofapi's *Both* tab, above the bass, the after the check measured lay
2.7-3.2 dB under before at 5-5.6 kHz, where before was near the target, and
the chart shaded the gap *Cut*. Read from the measurement kept on sofapi
(its curves and filters only; George's run of 2026-11-19, made before
ADR-0185, with the speakers' cables swapped - which changes neither speaker's
own figures nor *Both*):

- **The corrections at 5 kHz:** +0.2 dB on the left, −0.4 dB on the right.
- **Each speaker alone, the check against before with its corrections**
  (exact: the same filters on every position): 0.6-0.7 dB apart, root mean
  square, from 300 Hz to 14 kHz at 1/3 octave, 1.8 dB at most; 0.3 and
  0.6 dB at 5 kHz; 0.5-0.8 dB in the bass, where the 46 Hz peak went from
  16.7 dB over the target to 2.5. The corrections do what they were
  designed to.
- **Both:** at 5-5.6 kHz it fell 2.7-3.2 dB while neither speaker alone
  moved more than 1.2 dB, and the two speakers' corrections turn one
  against the other by 8° there (4 µs). What changed is how the two met at
  the microphone, which above the bass depends on its place to a centimetre
  or two (at 5 kHz half a wavelength is 3.4 cm): likely the microphone put
  back slightly differently for the check - likely, not shown, as the check
  keeps only the three positions' average.
- Nothing is designed from *Both* above the bass (ADR-0175's amendment,
  item 3), so its after there judges nothing.
- **The shading** was drawn between before and the after - measured, so it
  mixed what the corrections do with how the check's sweeps came out: on
  the left at 700 Hz it shaded *Raised* where the correction cuts 1.1 dB.

## Decisions (George, 2026-11-19)

- **D1 — *Both* in the bass only.** Above 250 Hz its pane is hatched, as
  with *Bass* chosen, with a line saying each speaker is corrected on its
  own there, on their tabs. Over: *Both*'s before alone above the bass; as
  it was, with a note.
- **D2 — The shading is the corrections'**: between before and before with
  the corrections; the after - measured or expected - is a line of its own,
  so *Cut* and *Raised* always mean what the player changes. Over: as it
  was.

## Claude's choices (approved 2026-11-19)

- **C1 — The corrected curve from the core.** The chart in
  `GET /room-correction` gives each speaker `corrected`, before with every
  correction kept (the bass's cuts and the broad corrections; for *Both*,
  the cuts), and `corrected_bass`, with the cuts alone (for *Bass*), from
  the equaliser's own filter response (`equaliser.band_db`) at 48 kHz, as
  designed. Exact, the filters being the same on every position; worked out
  from any kept measurement's filters, so nothing new is stored.
- **C2 — With the check skipped** the expected after is the corrected
  curve: its dashed line is the shading's edge, as it was.

## Consequences

- *Both* is still measured in the check: the bass's cuts are judged on it
  (a position named worse, ADR-0175's amendment, item 4).
- The manual's paragraph on the chart; the technical guide's UI and API
  pages.
- Not covered: keeping each check position's own curve, which would show
  where the microphone stood differently.
