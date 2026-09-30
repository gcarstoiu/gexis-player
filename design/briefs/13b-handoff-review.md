# Review of Claude Design's 2026-09-30 handoff (Phase 13b)

Written 2026-09-30 by Claude Code, before building anything from it. This file
covers the handoff committed in 84a725a, checked against the brief
(`13b-screen-families.md`), ADR-0109 and the code on `phase-13b`.

**What was checked:**
- `design/verify.html` was run over HTTP in headless Chromium, and all 37
  checks passed.
- Sizes were computed from the numbers the design states, and text widths
  were measured with the bundled fonts through fontTools.
- **Nothing was rendered at 720, 1850 or 1200 logical px.** Every overflow
  below is arithmetic until a render or a device confirms it.

Section 1 lists the decisions that belong to George. Section 2 is feedback
for Claude Design. Section 3 is ours to fix.

## 1. Decisions for George

**Answered 2026-09-30**; recorded in ADR-0109 as decisions 4-10.

1. **Touch floor.** The design says "7 mm on every screen". On the 7″
   800 × 480 that means at least 59 logical px. The design's own study and
   today's panel use 36–58 px targets in about 20 places, for example:
   - row actions at 40 px, Browse rows at 46, Clear at 44;
   - the alphabet keys, which are about 21 px tall.

   `tokens.css` still says 44 px is the "hard floor".
2. **Setup when the screen is dark.** When anything is plugged into HDMI,
   the setup Wi-Fi password is made up on the device and shown only on the
   panel (`setup_network.py:82,197`). So a screen that is connected but shows
   nothing (both bars until their mode is set, Finding 100) hides the password
   the phone needs to reach the Screen step. After a wrong pick, only a line of
   copy tells the user how to recover. Nothing reverts after a timeout, and
   nothing asks "Keep this screen?".
3. **Rotation.** The design offers 0/90/180/270. 90 and 270 turn a Standard
   screen into portrait, which ADR-0109 leaves out. On a bar they give an
   aspect of 0.3, which belongs to no family. Both bars are portrait panels by
   nature, so "0°" also has to be defined.
4. **"Nothing only the panel can do" (the brief).** The bars drop things the
   phone does not have either:
   - artist info and release info;
   - biography, top tracks (which play when tapped) and similar artists;
   - per-row Play now, Add to queue and Add to playlist.

   The Chosen page says so openly: "on the standard panel only".
5. **Skins for a new size.** These arrive as a package (ADR-0109, decision
   2). No state is drawn for downloading, offline, failed or no space. During
   setup the device is on its own setup Wi-Fi with no internet at all.
6. **Ethernet as a user choice** (`connection`, `eth_ip`). This is new in
   this handoff: README:325, settings.md, screens.md, each dated 2026-09-22.
   It is not in any ADR or the registry, and it sits badly with ADR-0104
   (Ethernet runs the same setup). As a setting it needs George's yes before
   it goes into ADR-0022, or it is struck.
7. **The Network step.** In screens.md it scans and shows connecting and
   error states. IMPLEMENTED-DIFFERENTLY says the step saves the choice and
   does not test it.

## 2. Back to Claude Design

### Errors
- **The Standard family's height numbers.**
  - 711 is aspect 1.8, not 16:9.
  - 16:9 is **720**, which is George's 13.3″.
  - The 7″ is 768.
  - No artboard matches a screen he has.
- **"One element takes H − 800" is not true for the artist page and album.**
  The photo and cover grow by H/800 and absorb 29 of the 89 px. Their
  columns stay 262/264 while the picture grows to 279/281 at 853, which
  overflows into the gap.
- **The home cards at 720.** The card's fixed content is about 163 px (26 +
  26 padding, 44 icon row, title, sub-line). The card is 200 × k = 157, so
  the bottom padding is lost. The constant 424 in k is not explained; it is
  104 + 60 + 137 + 123 in the study code only.
- **The Chosen page's claims contradict its own study.**
  - "Smallest target 60 px": the study uses 36–58.
  - "Smallest mono label 13 px": the study uses 11 and 12 px about forty
    times.
- **"Rule B" / "rule 1b" is cited** but the file that defines it is not in
  the bundle.
- **The bar forecast.**
  - README says one day below 1500 and four at 1850. The Chosen page says one
    at 1280. The script switches at W > 1500.
  - Four days need about 1712 px, so anything from 1501 to 1711 clips. An
    aspect-4 bar is 1600.
  - The breakpoint is written `< 1500` in one file and `> 1500` in another.
- **Idle on a 1280 bar fits by 6 px**, with nowhere left for "drifts
  sideways".
  - A longer condition ("Thunderstorm, hail") clips.
  - At aspect 3 (1200) the sample itself overflows by 74 px.
- **Rows marked "R".** Attached screen and Screen rotation are called
  "marked R (restart)". In ADR-0022, R means *recorded*. New rows are [N].
- **Stale references.**
  - design/README.md says the rows are "not yet in Settings.dc.html", but
    they are there.
  - It cites `Setup Screen Step.dc.html`, which does not exist.
  - The comment in `Settings Screen Row.dc.html` is out of date.
  - The file map uses the bundle's paths, not the repo's.
  - `now-playing.css:334` has the transport gap at 20 px; the prototype has
    14.
- **The Setup Screen step.**
  - The Headless warning (the fallback setup network is gone) is computed but
    never shown.
  - *Choose another* on a recognised screen opens a view saying "not which
    model", with a hardcoded maker.
  - The list silently filters by the resolution the screen reported.
- **The bar queue.** It is drawn without the rail's Clear and "Play from"
  buttons. With them, about 3 rows fit in 400 px; the drawing shows 5.

### Not drawn
- **Standard:**
  - panel setup at 720. *Rendered afterwards:* the join step fits; the
    tallest step, *Could not join*, ran into the header by about 60 px. It
    is fixed on our side: the QR code gives up the height (260 at 720, 340
    from 800 up);
  - the LMS-off waiting home;
  - the add-to-playlist sheet;
  - which part of the artist page takes the "more rows".
- **Bar setup:** 4 of the panel's 10 states are drawn. Missing:
  - joined, page, phone, done (with the Lyrion outcome), failed-start,
    starting;
  - `lan`, where over Ethernet the only QR code is the page's, so "one QR, to
    join" does not apply.
- **Bar tray:**
  - fixed output (padlock), mute, no meters (no visualiser button), LMS off;
  - whether it opens over the library when the volume changes elsewhere;
  - its slider fill is ink, where the panel uses the accent.
- **Bar strip:**
  - artwork pending;
  - no position (Bluetooth, radio);
  - lyrics loading, instrumental or plain, and the lyrics credit;
  - a long artist name runs under the mark.
- **Bar library:**
  - the rail with nothing playing;
  - Artists as one sideways row, with no letter index, for thousands of
    artists;
  - playlist detail, radio folders, toasts;
  - Settings sheets at 400 tall, which leave about 2 option rows, including
    the 197-model list.
- **Bar pairing:** the outcome screens and the no-code case.
- **Bar LMS-off:** 4 or more renderers need about 1456 px.
- **Bar transition:** long manifest names ("Music Assistant" at 64/800 is
  476 px).
- **Idle on a bar:** clock off, weather off, and External URL.
- **Aspect 3 and 5** (1200 and 2000 logical): the family's own limits, never
  shown.
- **The visualiser's "largest set that fits":** by area or by width?
- **Settings:** the Updates group (update status, Check now, Update now,
  Updates, Update channel) and plugin upload. Both were added after the
  designer's sync commit.
- **Attached screen in Settings:** no designed form for 197 models. The
  setup list is grouped and searchable, but the row is drawn as a flat sheet.
  Nothing marks untested models or shows their message (ADR-0109,
  decision 1).
- **Target sizes on the bars:** the tray's volume glyph is 30 px and its
  knob 40 px, and the handle's drag zone is not defined.

## 3. Ours to fix

- **The fixed 1280 × 800** in `App.svelte`, `NowPlaying.svelte` and
  `IdleScreen.svelte`, and `PANEL_RATIO` in the idle screen.
- **Artwork requests assume 1 CSS px = 1 device px.**
  - Now Playing asks for 500 and draws 630 device px on the 13.3″.
  - Covers and photos ask for 300 and draw about 355.
  - The artist grid asks for 200 and draws about 225.
  - On the 7″ they are oversized.
- **The kiosk** does not pass `--force-device-scale-factor` yet.
- **Already fine:** pointer and geometry maths use CSS px throughout, so the
  scale factor does not disturb them. There is no `devicePixelRatio`,
  `innerHeight` or panel `@media`.
