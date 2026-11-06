# Phase 29: room correction for the bass

Brief: `design/briefs/29-room-correction.md` (docs branch), with its mock-up
and ADR-0175. Open `Room Correction Board.dc.html` over HTTP from `design/`
(`/source/29/Room Correction Board.dc.html`); tabs switch theme
(`?theme=bauhaus|sage|velvet|ink|gauge`, none = default Deep Teal). Every
artboard is live: tap through the phone flow (the automatic steps run on a
clock once you tap), switch Left / Right, try Hear it without.

| File | What it is |
|---|---|
| `Room Correction.dc.html` | One component, every surface. URL or props: `surface` (`phone` / `panel` / `bar` / `drawer` / `bartray` / `phonetray`), `screen`, `v` (variant), `ch` (`L` / `R`), `n` (position), `spk`, `sweep`, `count`, `sheet`, `resumed`, `screenless`, `w` (bar 1850 / 1280). |
| `<id>-room.dc.html` | The same file recoloured for a theme by `build.js` (Phase 28's recolour, unchanged). Never edit these; rebuild. |
| `room-data.js` | The invented room: 121 log points 15–300 Hz, five positions per speaker, the cuts, the target, path helpers. Made up, not measured. |
| `Room Correction Board.dc.html` | 66 artboards (R phone, N panel, B bars, Q close to the music). |
| `build.js` | `eval(await readFile('design/source/29/build.js')); await build29();` |

## Screens and states

- **Phone flow** (R01–R27): Settings → Audio row (never / on / without /
  off); before, with the microphone and calibration states and a source or
  DSD playing; place; level (rising, too quiet); measuring (sweep, noise,
  reopened mid-run); move (waits for the tap, then 3 · 2 · 1); the correction
  (left, right, nothing to cut); checking with Skip; the result (measured,
  not checked); cancelled.
- **Page** (R28–R35, N01–N07, B01–B04, B07): on, without, off, not checked,
  DSD, never measured; at 412 and 360 px.
- **While it measures** (N08–N12, B05, B06, B08): level, sweep, waiting for
  the tap, countdown, checking. Display only.
- **Close to the music** (Q01–Q11): volume drawer, bar tray, phone tray.

## Decisions taken here (George to confirm)

- **Panel to phone:** *Measure again* (or *Measure from your phone* when never
  measured) opens a sheet with a QR code and the player's address. Nothing on
  the panel or bars starts a run.
- **Quick control:** On ↔ Without is one tap. Off reads *Room · Off* and
  opens the page. Never measured: no control. DSD: dimmed, inert.
- **Which switch compares:** power is the header control, as on the
  equaliser. *Hear it without* has an A/B tag, sits apart and goes amber
  (`--warn` family) when set; *Without* is amber wherever the state shows.
  Disabled while off.
- **The chart:** told apart by weight and dash, not only colour. Before:
  solid 2.25 px (panel 2.75) in the artist accent. Each position: 1 px hairline
  at 0.2. Target: dotted (0.5 / 5, round caps) ink at 0.82. After measured:
  solid 3.25 px (panel 4) in the accent; after expected: the same, dashed 7 / 5
  (panel 8 / 6). The cut area between before and after: artist at 0.16. Above
  250 Hz: hatched at 135°, dashed edge. Axis ±15 dB, gridlines at ±10 and the
  0 line at 0.26; x at 20, 30 (panel), 50, 100, 200.
- **Positions:** 1 at the head; 2 and 3, 40 cm left and right; 4, 30 cm
  towards the speakers; 5, 30 cm behind.

## Open

- Does the check wait for a tap at each position? Drawn as running on its own.
- No Stop on the panel while it measures (brief: display only).
- `themes.js` gives Velvet Red Hat Mono, Ink JetBrains Mono, Sage Martian
  Mono, Bauhaus Space Mono; the copies follow it.

## Proposed tokens (not yet in `tokens.css`)

```css
--rc-before: var(--accent-artist);      /* #f2a48f */
--rc-after: var(--accent);              /* #7ed6bc */
--rc-target: rgba(233,238,242,0.82);
--rc-position: rgba(233,238,242,0.2);
--rc-cut-fill: rgba(242,164,143,0.16);
--rc-limit-hatch: rgba(233,238,242,0.12);
--rc-without: var(--warn);              /* #e0a758 */
```

## Still to do for the export

PNG per state, the tokens into `tokens.css` and each `tokens-<id>.css`, and
`verify.html`, once George has picked.
