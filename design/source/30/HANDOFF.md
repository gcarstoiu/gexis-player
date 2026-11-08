# Handoff: room correction for the full range — Phase 30, 2026-11-08

## Overview

Room correction already cuts the room's peaks in the bass (Phase 29, as
built). Phase 30 takes it to the full range, 15 Hz to 20 kHz. In the bass it
still makes only narrow cuts. Above 250 Hz it evens out the room's broad
bumps and dips, by **3 dB at most, up or down**, towards the speaker's own
balance. The owner chooses how far it reaches: **Bass** or **Full range**.

Brief: `design/briefs/30-room-correction-full.md` (docs branch). The design
is drawn on what is built (`design/IMPLEMENTED-DIFFERENTLY.md`, *Room
correction*):

- three positions;
- Left / Right / **Both** tabs;
- the calibration file given from the phone;
- the check waits for **Measure here** at every position;
- the level aims at about 60 dB;
- the chart's bass scale grows in 5 dB steps.

George picked, from `Room Correction 30 Options.dc.html`:

- **1a:** the Reaches chips;
- **1d:** the chart split at 250 Hz;
- **1g:** the corrections in two groups;
- **1l:** Without · Bass · Full range in the drawer.

Locked designs (`Now Playing.dc.html`, `Settings.dc.html`) are unchanged.

Target repo: `gcarstoiu/gexis-player`, a Svelte 5 UI over a Python core.

## About the design files

The `.dc.html` files are **design references built in HTML**, not production
code. Rebuild them in the repo's Svelte UI, extending what Phase 29 built:

- the room correction page, run and result;
- `RoomChart`;
- the volume drawer, `bar/BarTray.svelte`, `MiniPlayer.svelte`.

Use the repo's components and tokens. Do not copy markup.

```
cd design && python3 -m http.server 8080
# /source/30/Room%20Correction%20Board.dc.html
#   ?theme=bauhaus|sage|velvet|ink|gauge   ?group=0..6
# one state: /source/30/Room%20Correction.dc.html?surface=phone&screen=page&v=bassonly
```

The board shows one group at a time; the tabs at its top switch the group
and the theme. Every artboard is live: on the phone, a tap starts the flow,
and the automatic steps then run on a short demo clock.

## Fidelity

**High** for what is new: the Reaches choice, the split chart, the grouped
corrections, the drawer's three-way control, and the copy marked *(new)*.

Everything already built (the flow, the screens' frame, rows, switches,
sheets, the drawing, the run screens) is drawn as built. **Where the repo
and an artboard differ in something that already exists, the repo wins.**

Curves come from an invented room (`room-data-30.js`), not a measurement.

---

## 1. How far it reaches (1a)

- **Phone page:** inside the power card, under on/off.
  - A 1 px rule at 0.08.
  - A *Reaches* label: 12 px mono, 0.16em, uppercase, at 0.6.
  - Two chips, gap 8, each flex 1, at least 64 tall, padding 10 14, radius 12.
  - Each chip: a name (16/700) over a range (12 px mono): *Bass* · *Up to
    250 Hz*; *Full range* · *15 Hz to 20 kHz*.
  - Selected: accent at 0.16 with a 0.55 border; name in the accent, range
    at 0.78.
  - Not selected: 0.05 ground, 1 px border at 0.12.
- **Panel:** a card of its own at the top of the 340 px column (radius 20,
  padding 16 18) with the *Reaches* label and the two chips (name 17/700).
- **Bars:** a row of two 64 px chips (radius 14, name 18/700, range 13 px
  mono) at the top of the middle column.
- **Behaviour:**
  - A tap is heard at once, with no gap.
  - The choice is saved per output, like the rest of room correction.
  - Off or DSD: the chips sit at 0.45 and are inert.
- **A measurement from before this phase** (it covers the bass only):
  - Bass is selected.
  - Full range is drawn with a 1.5 px dashed border at 0.28, its name at 0.6,
    and *Measure again* in place of the range, in warn.
  - Tapping it opens Before on the phone; on the panel and bars it opens the
    *Measure from your phone* sheet.
  - Note under the chips on the phone *(new)*: *This measurement covers the
    bass only. Measure again to reach the full range.*
  - *Measure again* becomes *Measure again for the full range*, as a lit
    chip, on the phone, the panel and the 1850 bar.
  - Measured line: *3 November 2026 · three positions · bass only*.
  - Otherwise the line ends *· full range*.

## 2. The chart (1d)

- **Frequency:** one log axis, 15 Hz to 20 kHz, broken at 250 Hz into two
  panes. Each pane gets a share of the width equal to its share of the log
  axis: the bass about 39 %.
- **Gap between the panes:** 8 px on the phone (`--rc-pane-gap`), 12 px on
  the panel and bars.
- **Panes:** each sits on `--rc-pane`, radius 8, clipped.
- **Caption over each pane** (11 px mono caps phone, 12 panel, 0.12em):
  *Bass* and *Above the bass*, each followed by its scale in ink:
  *±20 dB* (the bass; ±15 at least, growing in 5 dB steps to fit the larger
  of the two speakers, as built, the same on every tab) and *±5 dB*.
- **Level gridlines:**
  - ±20 bass scale: lines at ±20, ±10 and 0;
  - ±15 bass scale: ±10 and 0;
  - above the bass: ±3 and 0.
  - Labels sit inside the top-left of each line, 11 px mono (13 on the panel
    and bars).
- **Frequency labels** under each pane, mono:
  - Gridlines at 20, 30, 50, 100, 200, 500, 1k, 2k, 5k and 10k, keeping only
    those at least 34 px apart (46 on the panel and bars).
  - *250* in brighter ink at the break.
  - *Hz* at the far right.
- **Lines**, as built (`--rc-stroke-*`, `--rc-dash-*`):
  - each position: a hairline;
  - the target: dotted;
  - before (average of three): solid coral;
  - after: the accent, solid when measured, dashed when expected.
- **Fills:**
  - cut, where before is above after: `--rc-cut-fill`;
  - raised, where after is above before: `--rc-raise-fill`.
  - Above the bass both appear.
- **One target throughout:** the bass rise (+3 dB below about 80 Hz) joined
  at 250 Hz to the speaker's own slope. The engine supplies it.
- **Legend**, in this order: *Before, average of three* · *Each position* ·
  *Target* · *After, measured* or *After, expected* · *Cut* · *Raised*
  (only while something is raised).
- **Bass chosen:**
  - The upper pane is hatched (`--rc-limit-hatch`, dashed edge
    `--rc-limit-edge`).
  - Its label, in a `--rc-note-ground` tag: *Left alone: Bass is chosen*
    *(new)*.
  - After is drawn to 250 Hz only.
- **Bass-only measurement:** no curves above 250 Hz; the label is *Measured
  to 250 Hz only* *(new)*.
- **Both, before the check** (the correction screen, or a Not-checked
  measurement): before, positions and target only.
  - Heading: *Both speakers, before*.
  - Line: *The two together, as you hear them. Measure again and check it to
    see them after.* *(new)*.
  - After a check, Both draws after, measured.
- **Tabs:** Left / Right / Both as built (phone 44 tall, panel 50, bar 46).
- **Header line on the panel and bars:** the result (26/700 panel, 24 bar)
  and its line, on one row with the tabs. The bar has no legend.
- **Sizes:**
  - phone: the chart card's plot 330 tall (344 at 360 px);
  - panel and bars: the plot fills.

**Result words** *(new)*:

| case | heading | line |
|---|---|---|
| Full range | *Peaks down by up to 14 dB* | *Above the bass: within 1 dB of the speaker's own balance.* |
| nothing to correct above the bass | *Peaks down by up to 14 dB* | *Above the bass: already within 1.5 dB of the speaker's own balance, so left as it is.* |
| nothing to cut in the bass | *Nothing to cut in the bass* | *Above the bass: within 1.5 dB of the speaker's own balance.* |
| nothing at all (no chart below the heading) | *Nothing to correct* | *Already near the target, in the bass and above it.* |
| Bass chosen | *Peaks down by up to 14 dB* | *Above the bass: left alone, as Bass is chosen.* |
| a bass-only measurement | *Peaks down by up to 14 dB* | *Measured for the bass only.* |
| Not checked | *…, expected* | as above |

How the figures are worked out:

- *14* is the largest drop below 250 Hz.
- *1* is the largest gap from the target, 300 Hz to 14 kHz, smoothed and
  rounded up to 0.5 dB.
- *within 1.5 dB … already* uses the room's own curve.

## 3. The corrections (1g)

On the correction screen, under the chart, and on the panel in the
*Last measurement* card:

- Title: *Left speaker · 8 corrections* (17/700 phone, 15 panel).
- Then two groups. Each has a label (12 px mono caps), a 1 px rule, and a
  13 px kind at 0.6:
  - *In the bass* · *narrow cuts*;
  - *Above the bass* · *broad, up or down*.
- Rows in two columns, gap 8 18: the frequency at 0.78 and the gain (600),
  15 px mono (14 on the panel), tabular figures.
  - Frequencies: *46 Hz*, *2.4 kHz*, *11 kHz*.
  - Gains: *−14.0 dB*, *+2.5 dB*.
  - Cuts in `--rc-before`, raises in `--rc-after`.
- An empty group says why:
  - *Nothing to cut: near the target already.*
  - *Nothing to correct: within 1.5 dB of the speaker's own balance already.*
  - *Left alone: Bass is chosen.*
  - *Not measured: this measurement covers the bass only.*
- Both tab: one line, *Each speaker's corrections are on its own tab.*
- The heading counts both kinds *(new)*:
  - *Four cuts in the bass, four broad corrections above*;
  - *…, nothing to correct above*;
  - *Nothing to cut in the bass, …*;
  - *Nothing to correct* (no list).
- Note under the list:
  - *In the bass only cuts: the dips at 68 and 118 Hz stay, as more power
    does not fill them. Above it the corrections are broad and 3 dB at most,
    so the speaker keeps its own balance.*
  - Or, with nothing above: *Above the bass the room is already within
    1.5 dB of the speaker's own balance, so it is left as it is.*
- Nothing to correct at all: *Your room is already near the target, in the
  bass and above it, so there is nothing worth correcting. Room correction
  stays off.* Foot: **Done**.

## 4. Close to the music (1l)

**Volume drawer** (820 wide): the Room correction row is one control,
**Without · Bass · Full range**.

- The segmented control: padding 4, radius 17; segments 50 tall, padding 0
  20, radius 13, 17/700.
- Without selected: warn chip (0.16 / 0.55). Bass or Full range selected:
  accent chip (0.16 / 0.55).
- A tap sets it, heard at once. Without is the same switch as *Hear it
  without* on the page.
- State line (13 px mono): *Full range · measured 7 November* · *Bass ·
  measured 7 November* · *Without · no correction at all* (warn) · *Bass ·
  measured for the bass only* · *Off · open it to turn it on* · *Stands
  aside while DSD plays*.
- Bass-only measurement: Full range at 0.4, inert.
- Off: an **Open ›** button in place of the control.
- DSD: the control at 0.4, inert.
- Never measured: no Room row.

**Bar tray and phone volume row:** one tap, On ↔ Without, as built, now
naming the reach.

- Bar tray pill: *Room · Full range* / *Room · Bass* / *Room · Without*
  (warn) / *Room · Off* (quiet ink; opens the page).
- Phone 56 px button: *Full* / *Bass* / *Without* / *Off*; the glyph alone
  under 380 px wide.
- Never measured: no Room control.

## 5. The flow: what changed from as built

- **Before:**
  - Heading *Correct what your room adds to the sound* *(new)*.
  - Lead *(new)*: *The player plays sweeps through your speakers and listens
    with a measurement microphone at your seat. It cuts the peaks your room
    adds to the bass, and above the bass evens out the room's broad bumps
    and dips by 3 dB at most, so your speakers keep their own balance.*
- **Calibration file, given from the phone (as built):**
  - The row *Its calibration file* with **miniDSP's page** and **Choose the
    file**.
  - Then *Reading the file…*, then *From the file for 707-1234 · 90°* with
    **Choose another file**.
  - Refusals, each with **Choose another file** *(new)*:
    - *This is not a calibration file* / *Choose the 90° file downloaded
      from miniDSP's page.*
    - *This is the 0° file* / *Choose the 90° one: the microphone points at
      the ceiling.*
    - *No serial in this file* / *Choose the file miniDSP gives for your
      microphone's serial.*
  - Blocked: *In a group* / *Leave the group to measure the room.* · *An
    update is installing* / *Measure once it has finished.*
- **Place** *(new words)*: *…keep the room quiet throughout: the sweeps rise
  from a low rumble to a high whistle.*
- **Measuring:**
  - Three rows: Left · Right · **Both speakers** (*Two sweeps together,
    after the right*).
  - Note: *Nothing to do while it runs, about 45 seconds a position. Each
    sweep ends in a high whistle: keep quiet until it stops.* *(new)*.
- **Check:**
  - Waits at each position: *Move it back to position 1* / *Move it to
    position n*, then **Measure here**.
  - **Skip** throughout.
  - *Checking at position n*: *Sweeps with the correction on, from each
    speaker and both together.*
- **Result: a position worse than before:** a warn banner, *Position 3 is
  1.4 dB further from the target than before.* *(new)*; Keep it stays.
- **Panel and bars while it measures:** *Please keep quiet throughout* ·
  *The sweeps rise from a low rumble to a high whistle.* *(new)*. The bars
  show the short form.
- **Panel DSD:** a one-line pill in the header, beside the power control:
  *DSD · Plays untouched. Room correction stands aside.*
- **Times stay as built** (about four minutes, 45 s a position) until
  George's measurement with the treble sweeps.

## State, added to what is built

Per output:

- `reach`: `bass` | `full`;
- the measurement's `range`: `bass` (from before this phase) | `full`;
- per speaker, `corrections`:
  - `bass`: list of `{f, gain}`, cuts only;
  - `above`: list of `{f, gain, q}`, |gain| ≤ 3 dB.

A `bass` range forces `reach: bass` and locks Full range until the room is
measured again. *Without* (the A/B) is unchanged and saved per output.

## Design tokens

`design/source/30/tokens-room-30.css` holds the default and one block per
theme (`:root[data-theme="<id>"]`), made by the Phase 28 recolour, so the
values match the themed artboards.

- **New:** `--rc-raise-fill`, `--rc-pane`, `--rc-pane-gap(-lg)`,
  `--rc-note-ground`, `--rc-reach-locked-line`,
  `--rc-stroke-position(-lg)`.
- **Changed:** `--rc-cut-fill` goes from 0.16 to 0.2.

Everything else is from `design/tokens.css` and the Phase 28 theme files.

## Open, for George

- The new words marked *(new)*.
- Times, after the treble-sweep measurement.

## Files

```
HANDOFF.md
design/source/30/README.md                         spec as drawn, picks, new words
design/source/30/Room Correction Board.dc.html     115 artboards, 7 groups, theme tabs
design/source/30/Room Correction.dc.html           the component, every surface (default)
design/source/30/RoomChart.dc.html                 the chart
design/source/30/<id>-room.dc.html, <id>-RoomChart.dc.html   bauhaus | sage | velvet | ink | gauge, generated
design/source/30/Room Correction 30 Options.dc.html  turn 1: the options George picked from
design/source/30/tokens-room-30.css                new and changed tokens, six themes
design/source/30/room-data-30.js                   invented room, cuts, broad corrections, target, path maths
design/source/30/build.js                          rebuilds the theme copies
design/source/28/themes.js, build.js               the Phase 28 values and recolour build.js uses
design/source/30/support.js                        runtime for the references
```

Text only, no PNGs. Unpack `design/` over the repo's `design/`.
