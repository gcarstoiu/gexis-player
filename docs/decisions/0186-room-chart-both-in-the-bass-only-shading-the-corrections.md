# ADR-0186 — Room correction's chart: *Both* in the bass only, the shading the corrections'

**Status:** **Accepted** 2026-11-19 (George approved C1-C2); proposed the
same day: George decided D1-D2 after looking at his full-range check on
sofapi; C1-C2 are Claude's. Built on `room-chart`. **Amended** the same
day: D1 replaced by D3, *Both* in full (George); then D3 replaced by D4, no
*Both* tab (George), and C3-C4 withdrawn. **Amended** 2026-11-23: each
position's curve behind a switch, off by default (George; below).
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

- **D1 — *Both* in the bass only** *(replaced by D3, below, the same
  day)*. Above 250 Hz its pane is hatched, as
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

## Amended 2026-11-19 (George): *Both* in full

George, the same day, after D1 was built: the two speakers together are
what is heard, so *Both* shows its measurement and correction over the whole
range. D1 is replaced:

- **D3 — *Both* in full; each speaker still corrected on its own above the
  bass** *(replaced by D4, below, the same day)*. *Both*'s tab draws the whole range again: before, the shading of
  what the two speakers' corrections do together, the after. The corrections
  above the bass stay each speaker's (ADR-0175's amendment, item 3). Over:
  designing them from *Both*, the same on both speakers - above about 1 kHz
  the two together change with a centimetre of the microphone's place (in
  George's run 2.7-3.2 dB at 5-5.6 kHz between the measurement and the
  check, each speaker alone 1.2 dB at most), so a correction fitted to them
  would follow the microphone rather than the listener.

Claude's choices (withdrawn with D3, never approved):

- **C3 — *Both* with the corrections, above the bass, is an estimate.**
  Before together with the bass's cuts, and the two speakers' broad
  corrections combined as power, each weighted by that speaker's own before
  (each on its own target's level - near enough the same for two speakers
  on one amplifier). How the two add at a point depends on their phase,
  which the kept curves do not hold; over the positions' average it comes
  close to adding their power. Exact where the two corrections are the same,
  as the bass's cuts are; `corrected_bass` stays exact. On George's run the
  check lay 1.3 dB from it, root mean square, from 300 Hz to 14 kHz (3.2 dB
  at most, at 5.6 kHz), and 0.4 dB in the bass.
- **C4 — No mark of its own.** *Both*'s shading and expected after are drawn
  as the speakers' are; with the check skipped its expected after is this
  curve (C2) instead of before with the cuts alone. The manual says that
  above the bass it is an estimate, and why the check can stray from it
  there.

## Amended again 2026-11-19 (George): no *Both* tab

George, the same day, on hearing how established room correction shows its
results - each speaker's own curves; the speakers corrected jointly in the
bass only: each speaker is measured, corrected and drawn on its own, with no
joint graph.

- **D4 — *Left* and *Right* only** (replaces D3, and D1 before it). The
  chart's tabs are the two speakers'; *Both* goes from the phone's page, the
  panel's and the bar's, and the run's result. Unchanged, George confirming:
  the run still plays both speakers together at each position, measuring
  and checking; the bass's cuts are designed from that and are the same on
  both (ADR-0175's amendment), each speaker's tab showing them; above the
  bass each speaker is corrected on its own. ADR-0175's amendment, item 4
  (the *Both* tab), is withdrawn.
- C3-C4 are withdrawn: nothing needs *Both* with the corrections above the
  bass. `GET /room-correction` still gives *Both*'s curves and cuts (C1).
- **Whether the joint sweep could go**, George asked, if the industry does
  without it. Tools that correct the bass jointly measure each speaker on
  its own with a timing reference and add the speakers up in software,
  phase included; a sweep of all together is at most a check (REW with
  Multi-Sub Optimizer, as its users describe it). This player keeps
  magnitudes only, and its separate recordings start with jitter between
  playback and capture (ADR-0185 C1), so it cannot add two speakers up yet:
  the joint sweep stays.
- Not covered: each speaker's sweeps recorded with a timing reference and
  their phase kept, which would let the joint sweep go - a third of the
  run's sweep sets.

## Amended 2026-11-23 (George): each position behind a switch

After his five-position run on the research build, George found the charts
too busy with every position drawn. **Each position's curve is behind a
switch, off by default**: the legend's *Each position* key is the switch,
on the phone, the panel and the bars that have a legend; without one (a
bar's quick chart) they are not drawn. The switch is not kept: each chart
opens with it off, so it is no setting. Built on `ph-room-measurement`
(Phase 37).

