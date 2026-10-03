# Brief for Claude Design: what the bars still need (Phase 13b, round 2)

Written 2026-10-01 by Claude Code for George to hand to Claude Design.
- **Answers:** your 2026-09-30 handoff (`design/source/13b/`, `design/BUNDLE-README.md`
  *Phase 13b*).
- **Covers:** the **Bar family only** (1280 × 400 and 1480 × 320, aspect 3–5).
- **Elsewhere:** the Standard family, the Setup Screen step and Settings are
  in [`13b-corrections.md`](13b-corrections.md). The full review behind both
  is [`13b-handoff-review.md`](13b-handoff-review.md).

The bars as drawn are good and stay as they are. This round asks for the
states that were not drawn, and for a few numbers that do not add up.
Everything here is needed before the bar screens can be built.

## Decided by George since your handoff (context, not questions)

- **Touch floor: 44 logical px, and nothing grows.** The handoff's 7 mm
  stands only where 44 px reaches it. On the bars, 44 px is 6.6 mm
  (1280 × 400) and 7.0 mm (1480 × 320).
- **What a bar drops is dropped by design.** Artist and release info, the
  biography, top tracks, similar artists and per-row actions stay on Standard
  screens only. George: *"the losing is by design and was considered due to
  bar limitations"*. No need to find them a home.
- **Screen rotation is 0° / 180° only.** 0° is the screen's landscape. The
  bars are portrait panels used sideways, and the model list carries that
  turn.
- **Skins are plugins.** Each size's set is installed and removed on the
  Plugins screen. A new Visualiser row, **Skin size**, defaults to *Match the
  screen*: the exact size, or else the largest installed set that fits,
  letterboxed on black. The picker shows only that size's skins.

## 1. Numbers that do not add up

- **The forecast on a bar.** Three places disagree:
  - README: one day below 1500, four at 1850.
  - The Chosen page: one at 1280.
  - The `Bar Panels` script: `W > 1500`.

  Four days need about 1712 px, so every width from 1501 to 1711 clips; an
  aspect-4 bar is 1600. The cut-off is also written `< 1500` in `Bar Frame`
  and `> 1500` in `Bar Panels`. **Please state one rule** for how many days
  show at a given width, valid from 1200 to 2000.
- **Idle at 1280 fits by 6 px.** Clock 523, gaps 97, weather 384, gap 48 and
  one day 94 take 1146 of 1152. That leaves no room for "drifts sideways", and
  a longer condition clips: "Thunderstorm, hail" is 259 px where the sample is
  181. At 1200 (aspect 3) the sample itself overflows by 74 px.
- **The queue.** It is drawn without the panel rail's **Clear** and its 66 px
  *Play from* source button. With both, about 3 rows of 60 fit in 400; the
  drawing shows 5. Which is meant?
- **Targets under 44 px on the bars:**
  - the tray's volume glyph, 30 px (on the panel it is the 58 px mute
    button);
  - the slider knob, 40 px;
  - the 88 × 6 handle, whose drag zone is not defined.

## 2. Screens and states not drawn

### Setup (4 of the panel's 10 states are drawn)
Missing:
- joined, page, phone;
- **done**, with the Lyrion outcome card;
- failed-start and starting;
- **`lan`**: setup over Ethernet. There the only QR code is the page's, so
  "one QR, to join" does not hold.

*Could not join* also drops the network name and password, which the panel
still shows.

### The Now Playing strip
- Artwork pending (the placeholder).
- **No position.** Bluetooth and radio have no progress or times; the panel
  hides them.
- Lyrics loading, instrumental, plain text (unsynced) and none, and the lyrics
  credit line.
- Marks for the other sources (Spotify, Bluetooth, plugin renderers).
- A long artist name: the line is `nowrap` and runs under the mark and the
  lyrics switch.

### The pull-down tray
- Fixed output: the padlock and its sentence instead of the slider.
- Muted.
- No meters, where the visualiser button disappears.
- LMS off, where Home becomes Settings.
- **Does it open over the library** when the volume changes elsewhere? On the
  panel the drawer opens over any screen, and the bar's library rail has no
  volume control.
- Its slider fill is ink; the panel's is the source accent. Intended?

### The library
- The rail with nothing playing.
- **Artists:** one sideways row of 220 px circles, for libraries of
  thousands, with no letter index. The panel has a jump rail; what does the
  bar use?
- Playlist detail, radio folders, and toasts ("Added to queue").
- **Settings at 400 tall:** a choice sheet is capped at 82%, which leaves
  about 2 option rows. That includes **Attached screen**, which lists 197
  models.

### Moments
- **Pairing:** the outcome screens (Paired, Not paired, Expired), and the
  request that arrives with no code.
- **LMS off:** 4 or more renderers (plugins add them, e.g. Plexamp) need
  about 1456 px, more than 1280.
- **Transition:** a long plugin name at 64/800 ("Music Assistant" is 476 px)
  squeezes the line to about 116 px at 1200.
- **Idle:** clock off, weather off, and *External URL*.

## 3. The family's own limits

Every board is drawn at 1280 and 1850 logical. The family runs from aspect 3
to 5, that is **1200 to 2000** logical. Please check, or draw, the strip,
idle, the library home and pairing at both ends.

## What we need back

- The states above, at 1280 × 400 and 1480 × 320, as before.
- One stated rule for each number in section 1.
- The answers to the three questions: queue rows, the tray over the library,
  and the slider fill.
