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

Split on 2026-10-01 into two briefs, each written as a request:
- [`13b-bar-gaps.md`](13b-bar-gaps.md): the bars' numbers that do not add up,
  and the states not drawn.
- [`13b-corrections.md`](13b-corrections.md): the Standard family, the Setup
  Screen step, the new *Keep this screen?* prompt, Settings, and stale
  references.

The findings themselves are unchanged; they are listed there.

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
