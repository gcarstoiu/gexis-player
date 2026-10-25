# Phase 20: the equaliser

Settings → Audio → Equaliser on the panel, the bars and the phone, and the
quick change in the panel's volume drawer, the bar's tray and the phone's
pull-up tray. ADR-0162 sets the bands, presets and headroom rule.

Open `Equaliser Board.dc.html` over HTTP from `design/`
(`cd design && python3 -m http.server 8080`, then
`/source/20/Equaliser Board.dc.html`). Every artboard is live: drag a band,
pick a setting, save, rename, delete. `#shot=E03,Q01` mounts only those
artboards.

**George's pick, 2026-10-25: look 3a, "Ridge".** It is now the default look
on every surface. The board's Turn 2 (2a–2c) and Turn 3 (3b–3e) are the
options that were not chosen; ignore them. Turn 1 (E, B, P, Q artboards) is
the design to build.

**High fidelity.** Values below are extracted from `Equaliser.dc.html`. New
tokens are at the end of `../../tokens.css` under *Phase 20*.

| File | What it is |
|---|---|
| `Equaliser.dc.html` | The editor. Props `surface` (`panel` / `bar` / `phone`), `on`, `sel`, `from`, `drag`, `sheet`, `full`, `fixed`, `dsd`, `output`, `screen`, `shift`, `look` (default `d` = 3a; `current` is the pre-pick look, for reference only). |
| `EQ Quick.dc.html` | The quick change. Props `host` (`drawer` / `bartray` / `phonetray`), `w` (1850 / 1280), `on`, `sel`, `open`, `dsd`, `fixed`, `screen`. |
| `Equaliser Board.dc.html` | Every state, plus the look options. |
| `eq-data.js` | Bands, the ten presets, sample owner settings, the filter maths and the headroom rule. Port its numbers as-is. |
| `eq/` | Pictures of the locked screens, used only as backdrops under the quick change. |

---

## Bands and presets (`eq-data.js`)

Ten bands, an octave apart: 31, 63, 125, 250, 500, 1k, 2k, 4k, 8k, 16k
(centres 31.25 × 2ⁿ Hz). Each −12 to +12 dB in 1 dB steps. Presets, low band
to high:

| Preset | Gains |
|---|---|
| Flat | 0 0 0 0 0 0 0 0 0 0 |
| Rock | 4 3 2 0 −1 −1 0 2 3 4 |
| Pop | −1 0 2 3 2 0 −1 −1 0 1 |
| Jazz | 3 2 1 2 −1 −1 0 1 2 3 |
| Classical | 3 2 1 0 0 0 0 −1 −1 −2 |
| Electronic | 4 4 1 0 −2 1 0 1 3 4 |
| Hip-hop | 5 4 1 2 −1 −1 1 −1 2 3 |
| Acoustic | 3 3 2 1 1 1 2 3 2 1 |
| Vocal | −2 −1 −1 0 2 3 3 2 0 −1 |
| Late night | 5 4 2 0 0 0 0 1 2 3 |

The owner's own: up to ten, one list shared by every output. *Evening*,
*Kitchen radio*, *Old records* are samples.

**Headroom (ADR-0162 D3):** the sum of the ten peaking biquads (RBJ, Q = √2,
48 kHz, as CamillaDSP's GraphicEqualizer runs them), sampled at 241 points
from half an octave below 31 Hz to 20 kHz; its highest point rounded up to
0.5 dB. Zero when the peak ≤ 0.05.

---

## The look (3a, Ridge)

All three surfaces draw the same thing in a box where +12 is the top edge,
0 the middle and −12 the bottom edge.

- **The line** passes through every knob. Between two knobs it is a
  monotone cubic (Fritsch–Carlson: a knob that is a local peak or trough, or
  either end, has zero slope; otherwise the slope is the harmonic mean of the
  two neighbouring secants). It never dips or overshoots between two bands:
  two neighbours at the same level are joined by a flat line. It runs flat
  from the left edge to the first knob and from the last knob to the right
  edge. Knobs sit at the centre of each tenth of the width. Stroke
  `#f4f1ea`, 2.5 px (phone 2 px), round joins.
- **The fill** is the area between the line and 0, painted with one vertical
  gradient over the whole ±12 box (`--eq-ridge-fill`): from the top
  `#f2b35e` at 0.95, `#ef8f7a` at 0.75 (30 %), `#ef8f7a` at 0.26 (50 %), then a
  hard step to `#7fb0dc` at 0.26 (50 %), `#7f9fe6` at 0.75 (70 %), `#a48ce8`
  at 0.95 (bottom). So a boost warms from coral to amber as it rises and a cut
  deepens from blue to violet.
- **Lines:** 0 dB is 1 px `rgba(233,238,242,0.3)`, drawn over the fill; +12
  and −12 are 1 px at 0.05. No other gridlines.
- **Each band** (panel and bar): a 1 px dashed centre line
  `rgba(233,238,242,0.1)` the height of the travel; a ring knob 34 px, 4 px
  border `#f4f1ea`, centre `#0d151c`, shadow `0 3px 10px rgba(0,0,0,0.5)`.
- **Value colour** for a band at gain g, t = |g| / 12: boost mixes
  `rgb(239,143,122)` → `rgb(242,179,94)` by t; cut mixes
  `rgb(127,176,220)` → `rgb(164,140,232)` by t; 0 is `rgba(233,238,242,0.6)`.
  Channels mix linearly and round.
- **Dragging a band:** the column gets `rgba(233,238,242,0.05)` (radius 16,
  inset 8 px each side; bar 14 and 6); the knob's centre fills `#f4f1ea` and
  gains `0 0 0 8px rgba(244,241,234,0.18)` before its shadow; the band's
  value above it becomes a chip, its value colour as ground (`#e9eef2` at 0)
  with `#0d151c` ink.

## The editor

### Panel, 1280 × 800

- Ground: the blurred weave (`repeating-linear-gradient(38deg,#3f5a6d 0 48px,#2e4453 48px 96px)`,
  blur 70, scale 1.14, inset −90) under
  `radial-gradient(130% 105% at 20% 42%, rgba(20,33,42,0.72), rgba(13,21,28,0.96))`.
- **Header** 92 min, padding 0 36, gap 18, 1 px bottom rule at 0.09: Back
  56 circle (`rgba(233,238,242,0.07)`); *Equaliser* 25/700, −0.01em; crumb
  13 px mono 0.06em at 0.6, *Audio · for the DAC, HiFiBerry DAC+ HD · each
  output keeps its own*; the power control 58 tall, radius 15 (state 13 px
  mono 0.14em uppercase, *On* in `#7ed6bc` or *Off · bit-perfect* at 0.72; a
  60 × 34 switch, 26 px knob, 140 ms).
- **Body** padding 22 36 26, gap 24.
  - **List** 300 wide, scrolls, gap 6. Group heads *Presets* and *Yours · n
    of 10*: a 9 px `#7ed6bc` dot, 13 px mono 0.2em uppercase `#7ed6bc`, a rule.
    Rows 56 min, radius 14, padding 0 16, gap 14: a 22 px radio ring (2 px,
    0.3; selected `#7ed6bc` with an 11 px dot), name 17/600. Row ground
    `rgba(255,255,255,0.04)` with a `rgba(233,238,242,0.1)` border; selected
    `rgba(126,214,188,0.14)` / `rgba(126,214,188,0.4)`. **Custom** sits at the
    top when present, with *Not saved* 12 px mono 0.14em uppercase `#e0a758`.
  - **Bands card** radius 22, `rgba(255,255,255,0.05)`, 1 px at 0.1, padding
    20 24 14. Title row: the setting's name 26/700; meta 13 px mono 0.06em
    (*Preset*, *Yours*, or *From Rock · not saved* in `#e0a758`). Then the
    graph: a 36 px value row (17 px mono 600, chip padding 6 9, radius 9); the
    ±12 box with 26 px above and below; a 24 px Hz row (15 px mono at 0.72).
    The left axis is 44 wide: *dB*, *+12*, *+6*, *0* (at 0.82), *−6*, *−12*,
    12 px mono at 0.6; *Hz* under it. Each band's touch column runs the box's
    full height plus 26 px above and below; the knob's travel is inset 26 px
    at each end.
  - **Footer** 58 min, gap 12: the note badge (64 min wide, 36 tall, radius
    10, 15 px mono 600) and the note at 15 px / 1.4 at 0.78; then the actions,
    58 tall, radius 15, padding 0 24, 17 px.

### Bars (logical height 400; 1850 at 0.8 on the 11.9″, 1280 on the 7.9″)

- Ground `#37505f` under `radial-gradient(130% 105% at 20% 42%, rgba(20,33,42,0.62), rgba(13,21,28,0.93))`.
- Left column 220, padding 28 24 24, gap 12, rule on its right: Back and Home
  60 circles; *Equaliser* 26/700; crumb *Audio · DAC* 15 px mono; at its foot
  the power control 60 tall (*On* / *Off* 15 px mono).
- List `clamp(250px, 18%, 340px)`, padding 12 20 24 24, fading out over its
  last 18 %; rows 56 min, names 18/600; Custom's mark is a 9 px `#e0a758` dot.
- Content, padding 22 32 22 24, gap 12: name 26/700 and meta 15 px mono on
  one line, the note 16 px under it (amber with Fixed volume and a boost);
  actions 60 tall, 18 px. The bands card radius 20, padding 8 18: value row
  30 (chip padding 5 8, radius 8), the box with 24 px above and below, Hz row
  22 (16 px mono); axis 40 wide with *+12*, *0*, *−12* only (13 px mono).
  Knob travel inset 24.
- The 34 px knob is smaller than the old 44, but the touch target is the
  whole band column (≥ 44 wide at both widths), so the 44 px floor holds.

### Phone, 412 wide

- Header 78 min: Back 56, *Equaliser* 23/700, *Settings · Audio*.
- Scrolls, padding 14 16 240 (room for the tray), gap 6: the power card
  (*Equaliser*, *For the DAC, HiFiBerry DAC+ HD. Each output keeps its own.*,
  the switch); the **Setting** row 78 min (name 15 px mono on the right and a
  chevron; opens the picker sheet on the setting in use); the actions 44
  tall, 15 px; then the curve card.
- **Curve card**, radius 18, padding 14 14 10: the picture 104 tall, the
  same fill and line (2 px), the 0 line at 0.3, ±12 at 0.05; each band a 12 px
  ring dot (2 px `#f4f1ea`, centre `#0d151c`, `#f4f1ea` while dragged); band
  labels 11 px mono; the note under a rule, badge 30 tall.
- *Bands · −12 to +12 dB* head, then ten **rows** 52 tall, radius 12,
  padding 0 12, gap 12: label 15 px mono at 0.82 (38 wide); the slider (6 px
  track at 0.14, a 2 × 16 centre tick at 0.4, the fill from the centre in the
  band's value colour, a 26 px ring knob with a 3 px `#f4f1ea` border and the
  panel's knob centre and shadows); the value 15 px mono 600 in the value
  colour, `#f4f1ea` while dragged. The dragged row's ground is
  `rgba(126,214,188,0.1)`. A press decides within 8 px: mostly vertical
  scrolls, mostly horizontal slides; a tap sets the value where it lands.

### Off, DSD, Fixed volume, another output

- **Off:** list and actions at 0.4 and inert; the bands card at 0.4, bands
  keep their place; note *Off. The sound is untouched, bit-perfect.* A
  setting cannot be chosen while off.
- **DSD playing:** the card at 0.5; *DSD plays untouched. The equaliser
  stands aside for this track and is back for the next PCM one.*
- **Headroom:** *Lowered by &lt;n&gt; dB so the boost cannot clip.*; no boost: badge
  *0 dB*, *No boost, so nothing is lowered.* With **Fixed volume** the badge
  is amber (`rgba(224,167,88,0.14)` ground, 0.4 border, `#e0a758`) and the
  note adds *With Fixed volume the music plays &lt;n&gt; dB quieter: turn the
  amplifier up to match.*
- **Output:** each output (DAC, HDMI, optical) keeps its own setting; the
  crumbs name the one being set.

### Custom, saving, sheets

- Moving any band of a preset or saved setting makes it **Custom** (*From
  &lt;name&gt; · not saved*), and **Save as…** becomes the lit button
  (`rgba(126,214,188,0.16)` / 0.4 / `#7ed6bc`, 700).
- An owner's setting adds **Rename** and **Delete** (amber).
- Sheets: centred, `calc(100% − 44px)` up to 560, `#16232c`, radius 22,
  padding 26, over `rgba(8,12,16,0.62)`. *Save as…* (*Saved settings are
  shared by every output. n of 10 used.*, a 62 px field offering *My setting
  n*, and on panel and bar *Type with a keyboard on the player, or from the
  phone's touchpad.*); *Rename "&lt;name&gt;"*; *Delete "&lt;name&gt;"?* (*Its
  bands go. An output that uses it goes back to Flat.*); at ten, *Ten saved
  already* with OK only. The phone's **Setting** picker is the same list in
  a sheet with *Close*.
- No on-screen keyboard on the panel (CLAUDE.md).

## Changing setting: the glide

Choosing a setting (and Delete sending it back to Flat) moves the bands to
the new levels instead of jumping:

- each band eases from where it is drawn to its new gain over **380 ms**,
  ease-out cubic (`1 − (1 − x)³`, about `cubic-bezier(0.33, 1, 0.68, 1)`);
- band *i* starts **32 ms × i** after the lowest, so the move rolls from
  left to right and ends 668 ms after the tap;
- the line, fill, knobs, dots, row fills and values are all drawn from the
  moving levels; values show the rounded level, so they count;
- a new choice mid-glide starts from where the bands are drawn;
- touching a band stops the glide; the bands snap to the chosen setting
  and the drag takes over;
- the state commits at once (the setting is chosen on the tap); only the
  drawing moves. The first frame must draw the old levels, not the new ones.

Animate position only (transform or the SVG path); no filters.

## The quick change (`EQ Quick.dc.html`)

Shows the setting in use, changes it, turns the equaliser on and off, and
leads to the editor (*Edit*). Settings are chips in one sideways row,
presets then the owner's after a 1 px rule, opening scrolled to the one in
use; Custom comes first with a 7 px amber dot. Selected chip
`rgba(126,214,188,0.16)` / 0.55 / `#7ed6bc`. Off or DSD dims the row. The
row fades out over its last 64 px (bar 88).

- **Volume drawer** (panel, Q01–Q05): 820 wide, `#16232c`, 1 px
  `rgba(126,214,188,0.22)`, radius 28, padding 34 40 36; *Controls*, the
  volume (or the fixed-output row), a rule, then *Equaliser* 19/600 with
  its state line, *Edit* 58 tall, the switch, the chips (56 tall, radius 14,
  17/600) and the note.
- **Bar tray** (Q06–Q09): the 13b tray gains an **EQ button** after Home and
  the visualiser: 60 tall pill, a three-slider glyph, the setting's name
  19/700, a chevron. Open, the tray grows from 136 to 254 and a second band
  (120 tall) holds the switch, the chips (60 tall, radius 15, 18/600), the
  note and *Edit*.
- **Phone tray** (Q10–Q13): an **EQ chip** beside the volume (44 tall,
  radius 12, 13/700). Open: *Equaliser* head with *Edit* and an On/Off pill,
  chips 44 tall, the note. A player without a screen has no Panel row.

## Open, for George

- **The line and the note can disagree.** The line joins the knobs; the
  headroom note is worked out from the ten filters, where neighbouring
  boosts add up. Rock's line tops out at +4 while its note can say a larger
  figure. Keep the note as ADR-0162 D3 has it unless George says otherwise.
- **Delete sends outputs back to Flat.** Not in ADR-0162; to confirm.

## State

Per output: `on`, `sel` (preset key, owner key, or `custom`), `from` (what
Custom came from), `gains[10]`. Shared: the owner's list (≤ 10, name +
gains). While playing: `dsd`, `fixed` (output volume fixed). The glide's
drawn levels are view state only.
