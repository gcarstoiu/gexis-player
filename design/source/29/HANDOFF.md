# Handoff: room correction for the bass — Phase 29, 2026-11-05

## Overview

The player measures the room through a miniDSP UMIK-1 at the listening seat
and cuts the peaks the room adds below 250 Hz, towards a +3 dB rise below
about 80 Hz. Brief: `design/briefs/29-room-correction.md` (docs branch), its
mock-up, and ADR-0175. This bundle draws:

- the run, started and followed on the **phone**;
- the **Room correction page** on the phone, the panel (1280 × 800) and the
  bars (1850 × 400 at 0.8; 1280 × 400);
- the **panel and bars while it measures** (display only);
- the **Room** control beside the equaliser's in the panel's volume drawer,
  the bar's tray and the phone's pull-up tray;

in the default theme and in Bauhaus, Sage, Velvet, Ink and Gauge.

Target repo: `gcarstoiu/gexis-player` (Svelte 5 UI over a Python core).
Locked `Now Playing.dc.html` and `Settings.dc.html` are unchanged; the one
new Settings row (Audio → Room correction) is drawn here, not in Settings.

## About the design files

The `.dc.html` files are **design references built in HTML**, not production
code. Recreate them in the repo's Svelte UI with its existing components
(Settings rows, the equaliser's power control and switch, the volume drawer,
`bar/BarTray.svelte`, `MiniPlayer.svelte`) and tokens. Do not copy markup.

```
cd design && python3 -m http.server 8080
# http://localhost:8080/source/29/Room%20Correction%20Board.dc.html
# ?theme=bauhaus | sage | velvet | ink | gauge   (none = default)
# one artboard: /source/29/Room%20Correction.dc.html?surface=phone&screen=before&v=nofile
```

Every artboard is live. On the phone, a tap starts the flow; the automatic
steps (level, sweeps, countdown, checking) then run on a short demo clock.

## Fidelity

**High.** Colours, type, sizes, spacing and copy are final, within the
existing design system. Curves are invented (`room-data.js`), not measured:
draw production charts from the real measurement.

If production and an artboard differ in anything that already exists
(Settings rows, drawer, trays, header, switch), **production wins**.

## Copy

Copy on the flow is agreed with George (brief + mock-up). Use it verbatim.
The words below that are new here are marked *(new)*; George to confirm.

---

## 1. Phone flow (412 wide; also checked at 360)

Common frame:

- Ground: the blurred weave + veil, as the equaliser's phone page.
- Header 78 min, padding 14 18, 1 px rule at 0.09: Back 56 circle
  (`rgba(233,238,242,0.07)`, only outside the run); title 23/700 −0.01em;
  crumb 13 px mono 0.06em at 0.6.
  - Titles: *Audio* · *Room correction* · during the run *Measure the room*.
  - Crumbs: *Settings* · *Settings · Audio · DAC* · *Step 1 of 4* (place),
    *Step 2 of 4* (level), *Step 3 of 4* (measure, move), *Step 4 of 4*
    (correction, result), *Checking*.
- Scroll area padding 16 16 28, gap 12.
- Heading 25/800, −0.015em, line-height 1.15, balance. Lead 16/1.45 at 0.78.
- Cards: radius 15 (chart, drawing 18), `rgba(255,255,255,0.05)`, 1 px
  `rgba(233,238,242,0.1)`; rows split by 1 px at 0.08.
- Foot (when present): padding 12 16 22, 1 px rule at 0.09, ground
  `rgba(13,21,28,0.55)`, gap 10. Buttons 52 tall, radius 15, 16 px:
  quiet (*Cancel*, *Discard*) 600 at 0.82 on 0.05 / 0.1; secondary (*Skip*)
  flex 1, 700 on 0.08 / 0.16; primary flex 1, 800, `#7ed6bc` with `#0d151c`
  ink. A primary that cannot be used yet sits at 0.4 and is inert.
- **Cancel on every step of the run** → *Measuring cancelled*. **Discard**
  → back to Audio, the output as it was.

### Screens (board ids)

| id | screen | content |
|---|---|---|
| R01–R04 | **Settings → Audio** | Groups *Output* (Output · *HiFiBerry DAC2 HD*, Volume · *Hardware*) and *Sound* (Equaliser · *Rock*, **Room correction**). Rows 72 min, title 18/600, sub 14 at 0.6, value 14 mono, chevron. Room correction's sub is its state: *Not measured yet* · *On · measured 3 November* · *Without · comparing, the cuts at 0 dB* (in `--rc-without`) · *Off*. Note under: *Room correction sits beside the equaliser and is kept for each output, as the equaliser is.* Tap: never measured → Before; else → the page. |
| R05–R12 | **Before** | *Correct the bass your room adds* + lead (two sentences, brief). Checks card, three rows (26 px mark, title 17/600, sub 14 at 0.6): Microphone · *miniDSP UMIK-1 · 707-1234*; Calibration · *Downloaded from miniDSP · 90°*; A quiet room · *About five minutes, music stops*. A disabled power card (*Room correction* · *Measure first*, at 0.5). Foot: **Measure**. |
| R13 | **Place** | *Put the microphone where your head is*; the drawing (position 1 lit); *On a stand at ear height, pointing at the ceiling. Then keep the room quiet: the measurement plays loud sweeps for a few seconds at a time.*; note *Music stops now, on every source. The player's screen shows that it is measuring.* (second sentence absent without a screen, R33). Foot: Cancel · **Start**. |
| R14–R15 | **Finding the level** | Card: the level 56 px mono 600 in the accent + *dB at the seat* 17/600; a 12 px track (`--rc-run-track`) with fill, a 2 px ink tick at 75 dB; scale 50 · *75 dB · the aim* · 85 (12 px mono). Note *Never above the maximum level set for this output.* Foot: Cancel only. |
| R16–R18 | **Measuring a position** | Tracker (five 4 px segments, gap 4: done accent, current accent 0.5, to come 0.12; caption *Position n of 5* 12 px mono uppercase). *Position n of 5*; drawing (n lit, earlier ones ticked, the speaker playing outlined in the accent); speakers card: Left / Right speaker with *Two sweeps, they agree* (tick), *Playing · sweep 1 of 2* (accent disc with three bars), *Two sweeps, after the left* (dashed ring). Note *Nothing to do while it runs, about 25 seconds a position.* Foot: Cancel. |
| R19–R20 | **Move the microphone** | Tracker; *Move it to position n*; drawing with a 2 px dashed accent arrow from the head to n; *About 40 cm to the left of where your head was, at the same height, still pointing at the ceiling. Step back, then tap Measure here.* Foot: Cancel · **Measure here**. **It waits for the tap; it never carries on by itself.** After the tap: the instruction gives way to a countdown card (accent 0.08 ground, 0.35 border, a 72 px ring with 38 px mono numeral, *Sweeps in 3. Stay where you are and keep quiet.* *(new)*), 3 → 2 → 1 at 1 s, then the sweeps. Primary hidden. |
| R21–R23 | **The correction** | *Four cuts for each speaker*; Left / Right; chart (expected); cuts card (*Left speaker · 4 cuts*, two columns, 15 px mono, value in `--rc-before`); note *Only cuts: the dips at 65 and 110 Hz stay, as more power does not fill them. The bass rise below 80 Hz is the target.* (dips per speaker). Foot: Discard · **Check it**. |
| R23 | **Nothing to cut** *(new)* | *Nothing to cut*; chart with before and target only; *Your room's bass is already near the target, so there is nothing worth cutting. Room correction stays off.* Foot: **Done**. |
| R24 | **Checking** | Tracker *Checking · position n of 5*; *Checking, with the correction on*; drawing; *The same five positions again, about a minute more.*; 10 px progress; *Skip keeps the correction as it is worked out, marked Not checked.* *(new)*. Foot: Cancel · **Skip**. |
| R25 | **The result** | *Peaks down by up to 8 dB*; Left / Right; chart (measured); *No position is worse than before.* Foot: Discard · **Keep it** → the page, on. |
| R26 | **Not checked** | *Peaks down by up to 8 dB, expected*; *Not checked* flag; chart (expected); *The check was skipped: this is what the correction should do. Measure again to check it.* Foot: Discard · **Keep it** → the page, on, Not checked. |
| R27 | **Cancelled** *(new)* | *Measuring cancelled* / *Nothing changed: the output is as it was. Music can play again.* Foot: **Done**. |

### States on Before (R06–R12)

| v | Microphone row | Calibration row | Quiet-room sub | Measure |
|---|---|---|---|---|
| playing | ✓ | ✓ | *About five minutes. Spotify is playing: it stops when you start.* | on |
| dsd | ✓ | ✓ | *About five minutes. DSD is playing: it stops when you start.* | on |
| nomic | ! *Plug in the UMIK-1* / *Into one of the player's USB ports. It is found by itself.* | dashed ring, *Downloaded from miniDSP once the microphone is found* | default | off |
| othermic | ! *This microphone is not supported yet* / *Room correction measures with the miniDSP UMIK-1 for now.* | as nomic | default | off |
| downloading | ✓ | spinner (accent top arc on 0.2 ring), *Downloading from miniDSP for 707-1234* | default | off |
| nofile | ✓ | ! *miniDSP has no file for 707-1234* / *Check the serial on the microphone's label and type it here.* + field under the row: label *Serial on the label* (12 px mono), a 48 px field (1.5 px accent border, 17 px mono) and **Download** (lit chip) | default | off |
| typed | ✓ *707-1235* | ✓ *Downloaded from miniDSP for 707-1235, typed · 90°* | default | on |

Problem titles and the *!* mark are in `--rc-without` (the warn family).

### Run states

- **Too quiet (R15):** heading *Only 63 dB at the seat* in warn; lead *At the
  player's maximum level. Turn the amplifier up a little and try again.*; the
  level in warn. Foot: Cancel · **Try again**.
- **Noise spoiled a sweep (R17):** that speaker's row gets the *!* mark and
  *A noise spoiled this sweep. Measuring it again.* in warn; it repeats.
- **Page closed and opened again mid-run (R18):** the run screen as it
  stands, under a banner (accent 0.1 / 0.35, radius 12, 8 px accent dot):
  *Picked up where it is. The measuring went on while this page was closed.*
  *(new)*. The phone page must ask the player where the run is on open.

### The drawing (top-down, 340 × 196, scales to the card)

Speakers L and R at the top corners (28 × 36, radius 5, 1.5 px border at
0.3, accent while that speaker plays); the seat a 48 % × 44 % rounded
rectangle low centre, *Your seat* 11 px; a dashed circle (r ≈ 50 cm) round
the head. Positions as discs: **1** the head (170, 98); **2** 40 cm left
(122, 98); **3** 40 cm right (218, 98); **4** 30 cm towards the speakers
(170, 64); **5** 30 cm behind (170, 132). Current: 30 px, accent fill, ink
`#0d151c`, 6 px accent glow at 0.2; done: 24 px, ✓, accent 0.2 / 0.6; to
come: 24 px, number, 0.3 ring. Moves for 3–5: *About 40 cm to the right of
where your head was*; *About 30 cm in front of where your head was, towards
the speakers*; *About 30 cm behind where your head was* *(new; 2 is the
brief's)*.

---

## 2. Room correction page

### Phone (R28–R32, R35)

Stack, gap 12: [DSD banner] · power card (*Room correction*; note *For the
DAC, HiFiBerry DAC2 HD. Each output keeps its own.* / off: *Off: the
correction is taken out. With the equaliser also off, the sound is
untouched, bit-perfect.*; the 60 × 34 switch) · **A/B card** · *Measured*
card (*3 November 2026 · five positions*, *Not checked* flag when so) ·
Left / Right · chart card with *Peaks down by up to 8 dB* 18/700 and
*No position is worse than before.* (or *Expected, not checked. Measure
again to check it.*) above the chart · **Measure again** (52, secondary) →
Before. A never-measured page is Before.

### Panel 1280 × 800 (N01–N07)

- Header as the equaliser's: 92 min, padding 0 36; Back 56; *Room
  correction* 25/700; crumb *Audio · for the DAC, HiFiBerry DAC2 HD · each
  output keeps its own*; power control 58 tall (state 13 px mono 0.14em:
  *On* in accent, *Off · bit-perfect* at 0.72; never measured: *Measure
  first*, at 0.5, inert).
- Body padding 22 36 26, gap 24. Left column 340, gap 12:
  - [DSD banner];
  - **A/B card**, radius 20, padding 20 20 18: *A/B* tag (30 tall, 13 px mono
    700, 1.5 px border), *Hear it without* 20/700, switch; sub 15/1.4;
  - **Last measurement** card, radius 20: label 12 px mono 0.2em + rule;
    *3 November 2026* 20/700, *Five positions*; *Not checked* flag; then
    *Left speaker · 4 cuts* and the cuts, 16 px mono, values in `--rc-before`;
  - spacer; **Measure again** 58, radius 15, 17/700, phone glyph.
- Chart card flex 1, radius 22, padding 20 24 16 14: *Peaks down by up to
  8 dB* 26/700 + line 16 at 0.72; Left / Right (50 tall, 17/700) on the
  right; the chart (fills); Hz row 28 (14 px mono at 0.72: 20 30 50 100 200,
  *Hz*); legend 15 px.
- **Never measured (N06):** A/B at 0.4; *Not measured yet*; the chart card
  holds *Correct the bass your room adds* 32/800, the brief's two sentences
  18/1.5, and *You measure from the phone, which you hold at the seat while
  you move the microphone. This screen shows that it is running.* *(new)*.
  The button reads **Measure from your phone** (lit chip).
- **Measure from your phone sheet (N07)** *(proposed)*: 720 wide, `#16232c`,
  radius 22, padding 30 32 28, over `rgba(8,12,16,0.62)`. A 200 px QR
  (placeholder) that opens the phone page at Room correction; *Measure from
  your phone* 24/700; *You hold the phone at the seat while you move the
  microphone. Scan this, or open the player's page and go to Settings ·
  Audio · Room correction.*; the address 16 px mono in accent; **Close**.

### Bars (B01–B04, B07)

Left column 220 as the equaliser's bar (Back + Home 60, *Room correction*
26/700, *Audio · DAC* 15 px mono, power 60 at the foot). Middle column 400
(1280: 330), padding 24 20 24 24: A/B card 96 min (title 20/700, sub one
line 16 px), measured card 72 min, spacer, **Measure again** 60. Right:
headline 26/700 + line 17 on one row, Left / Right 52 tall; chart card
radius 20 with the legend as a 150 px column on the right (*Before*,
*Positions*, *Target*, *After* / *Expected*) and Hz labels 20 50 100 250.
Sheet: 820 × 320, QR left, text and Close right.

### Off, Without, DSD, Not checked

- **Off:** chart at 0.5; A/B at 0.4 and inert, sub *Only while room
  correction is on.*
- **Without:** A/B card ground `--rc-without-fill`, border
  `--rc-without-line`; tag, sub and switch in `--rc-without`; sub *Now
  without: the cuts at 0 dB. Switch back to hear them.* (bars: *Now without:
  the cuts at 0 dB*). Default sub: *Compare: the cuts at 0 dB, heard at
  once. Stays where you put it.* (bars: *Compare, heard at once*).
- **DSD:** banner (*DSD* tag + *DSD plays untouched. Room correction stands
  aside for this track and is back for the next PCM one.*), chart at 0.5,
  A/B inert.
- **Not checked:** the flag on the measurement; the chart draws *after,
  expected*.

**Which switch compares (proposed):** power is the header / top control as
on the equaliser and takes the stage out. *Hear it without* is the A/B:
tagged, set apart, amber when set, and *Without* is amber wherever the state
is shown. It is heard at once with no gap, stays where it is put and is
saved per output.

---

## 3. While it measures, panel and bars (N08–N12, B05, B06, B08)

Display only; nothing to press.

- **Panel:** ground blurred weave under a centred veil; centred stack, gap
  22: *Room correction* 15 px mono 0.22em accent; *Measuring the room*
  (checking: *Checking the room*) 64/800; *Please keep quiet* 26/600 at
  0.82; a 640 block: the line 22 px mono (*Position 2 of 5 · Right speaker*
  · *Finding the level · soft noise, getting louder* · *Position 2 of 5 ·
  Moving the microphone* · *Position 2 of 5 · Sweeps in 3* · *Position 3 of
  5 · Left speaker*), a 12 px progress bar, five numbered 4 px segments;
  then a phone glyph and *Follow it on the phone. Sources can play again
  when it ends.* 20 px at 0.72.
- **Bars:** one row, padding 0 64, gap 56: mark, head 48/800 and *Please
  keep quiet* 22/600 on the left; line, progress and the follow line on the
  right.
- Progress: level 5 %; positions 8 → 78 % (each position ½ per speaker, ¼
  per sweep); checking 80 → 100 %.

---

## 4. Close to the music (Q01–Q11)

| host | control |
|---|---|
| Volume drawer (820 wide) | Under the equaliser block, a rule (24 / 20), then *Room correction* 19/600 with a state line 13 px mono, and a segmented **On / Without** (4 px padding, radius 17; segments 50 tall, radius 13, 17/700). On selected: accent chip (0.16 / 0.55); Without selected: warn chip. A tap anywhere on it switches. |
| Bar tray | After the EQ button: a **Room** pill, 60 tall, radius 30, house-and-wave glyph 24, *Room · On* / *Room · Without* 19/700. On: accent 0.12 / 0.45; Without: warn 0.12 / 0.5. |
| Phone tray | After the EQ chip: a **Room** chip, 44 tall, radius 12, glyph 18, 13/700: *Room* / *Without*, same colours. |

State lines (drawer): *On · measured 3 November* · *Without · the cuts at
0 dB* (warn) · *Off · open it to turn it on* · *Stands aside while DSD
plays*.

**Proposed:** On ↔ Without is the only tap. **Off:** reads *Room · Off* /
*Room off* in quiet ink; in the drawer an **Open ›** button; a tap opens the
page. **Never measured:** no Room control at all. **DSD:** at 0.4, inert.

---

## 5. The chart

- x: log, 15–300 Hz (x = ln(f/15) / ln 20). Gridlines at 20, 50, 100, 200
  (panel adds 30). 250 Hz at 93.9 %: dashed 1 px edge (`--rc-limit-edge`)
  and a 135° hatch to the right (`--rc-limit-hatch`); panel labels it *250 Hz
  limit* 12 px mono; phone legend *Above 250 Hz, left alone* *(new)*.
- y: +15 to −15 dB, labels +10 / 0 / −10 (11 px mono phone, 13–14 panel and
  bars); gridlines at ±10 (`--rc-grid`), 0 line `--rc-zero`.
- Lines, drawn in this order:
  1. cut area: fill between before and after where before is higher,
     `--rc-cut-fill`;
  2. each position: one 1 px (panel 1.25) path per position, `--rc-position`;
  3. target: dotted, `--rc-target`, 2 px (2.5), dash 0.5 / 5 (0.5 / 6),
     round caps;
  4. before (power average of the five): solid `--rc-before`, 2.25 px (2.75);
  5. after: `--rc-after`, 3.25 px (4); **measured solid, expected dashed
     7 / 5 (8 / 6)**.
- Lines differ by weight and dash as well as colour, so the chart reads
  without colour. Legend: line samples + *Before, average of five* · *Each
  position* · *Target* · *After, measured* or *After, expected*.
- Left and right one at a time (Left / Right chips: selected accent 0.16 /
  0.55; phone 42 tall, 15/700).
- Phone plot 200 tall in a card with 30 px dB gutter; panel and bars fill.
- Target: 3 / (1 + (f / 70)⁴) dB. Brief: fixed, the owner does not choose it.

## Interactions & behaviour

- Switches 60 × 34, knob 26, 140 ms ease (left and background). Presses
  scale to 0.95 (wide buttons 0.97), as elsewhere. No other motion.
- The run never advances to a new position without the tap; the countdown
  is 3 s; level, sweeps and checking advance by themselves.
- Measuring stops every source; nothing plays until it ends or is cancelled.
- Discard and Cancel leave the output as it was. Keep it switches it on.

## State

Per output (DAC, HDMI, optical): `measured` (date, positions, curves per
speaker: five positions, before, after, measured or expected), `cuts` per
speaker (f, gain), `on`, `without` (A/B, saved), `checked`.
While playing: `dsd`. During a run (on the player, so a reopened phone page
can show it): step (`level` / `measure` / `move` / `countdown` / `checking`
/ `result`), position 1–5, speaker, sweep 1–2, noise retry, level dB,
progress. Microphone: `absent` / `other` / `found(serial)`; calibration:
`downloading` / `ok` / `nofile` / `typed(serial)`.

## Design tokens

New names are in `design/source/29/tokens-room.css`: the default block, and
one block per theme (`:root[data-theme="<id>"]`) made by the Phase 28
recolour over the default, so they match the themed artboards exactly.
Everything else is from `design/tokens.css` and the Phase 28 theme files:
ground `#101a21`, panel `#16232c`, ink `#e9eef2` (0.82 / 0.78 / 0.72 / 0.6
levels), accent `#7ed6bc`, on-accent `#0d151c`, warn `#e0a758`, artist
`#f2a48f`; Nunito Sans; IBM Plex Mono (each theme's mono in its copy).

## Open, for George

- Does the check wait for **Measure here** at each position? Drawn as
  running on its own, as the brief's "about a minute" suggests.
- No Stop on the panel while it measures (the brief: display only). If the
  phone is lost mid-run, the run needs a timeout.
- The proposals above: the QR sheet, Off / never measured close to the
  music, the A/B treatment, the *(new)* copy.

## Files

```
HANDOFF.md                                   this file
design/source/29/README.md                   short spec, decisions
design/source/29/Room Correction Board.dc.html   66 artboards, theme tabs
design/source/29/Room Correction.dc.html     the component, every surface (default theme)
design/source/29/<id>-room.dc.html           bauhaus | sage | velvet | ink | gauge, generated
design/source/29/tokens-room.css             new tokens, default + five themes
design/source/29/room-data.js                invented room, cuts, target, path maths
design/source/29/build.js                    rebuilds the theme copies
design/source/28/themes.js, build.js         the Phase 28 values and recolour build.js uses
design/source/29/support.js                  runtime for the references
```

No PNGs in this bundle. Fonts load from Google Fonts in the references; the
player ships its own (Phase 28 handoff). Unpack `design/` over the repo's
`design/`.
