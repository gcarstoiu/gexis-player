# ADR-0109 — Other screens: two families, a known list, and the skins per size

**Status:** **Accepted** — George, 2026-09-30: *"1. All as you said.
2. agreed 3. Those are the default ones. More available from gelo5"* (each
marked **Decided** below).
**Phase:** 13b ([DEVELOPMENT.md](../DEVELOPMENT.md)); before the first public
release (George, 2026-09-29: *"13a, b and c all needed before release"*).
**Builds on:** Claude Design's 2026-09-30 handoff
(`design/source/13b/Screen Families Chosen.dc.html`, `design/BUNDLE-README.md`
*Phase 13b*, settled with George that day: Settings stays a tile on bars; the
copy is accepted as drawn), [Finding 100](../findings/100-screens-what-the-pi-can-learn-and-what-exists.md),
[ADR-0022](0022-settings.md) (*Attached screen*, *Screen rotation*, confirmed
2026-09-30), [ADR-0107](0107-our-parts-as-debian-packages.md) and
[ADR-0108](0108-how-a-release-is-published-and-found.md) (packages, parts).

## Context

Everything so far is drawn for one screen: `App.svelte`, `NowPlaying.svelte`
and `IdleScreen.svelte` fix the panel at 1280 × 800, and the visualiser's skins
are bitmaps for 1280 × 800. George has, besides the 10.1″ 1280 × 800 on
`sofa-pi`: **a 13.3″ 1920 × 1080, a 1280 × 400 bar and a 1480 × 320 bar**
(2026-09-30). An 800 × 480 is in the design but not on the bench.

## Decided by the design (recorded here, not reopened)

- **Two families by aspect, not resolution**: Standard (1.5-1.8) and Bar
  (3-5). One token set for both.
- **Standard** lays out at a logical width of 1280; the height left over
  (711-853 logical) goes to one element per screen (Now Playing: the
  artwork, H - 300; library cards × (H - 424) / 376; lists: more rows). Type
  scales with the screen; nothing is capped; the touch floor is 7 mm.
- **Bar** lays out at a logical height of 400, width = aspect × 400 (1280 or
  1850); a strip per screen, a pull-down tray on Now Playing, the library's
  rail and six cards, full-screen moments as strips; what is dropped is listed
  in the handoff.
- **The Screen step** in setup (recognised / uncertain / nothing shown yet /
  Headless) and **Attached screen** and **Screen rotation** in Display.
- **The visualiser**: a screen uses skins drawn for its exact size; with none,
  the largest set that fits, centred at 1 : 1 on black.

## Proposed (technical)

### How a family is applied: Chromium's zoom, not our CSS

The kiosk starts Chromium with `--force-device-scale-factor` = screen width ÷
1280 (Standard) or screen height ÷ 400 (Bar). The page then always sees a
logical width of 1280 (or a logical height of 400) and Chromium renders it at
the screen's real resolution - crisp text, no bitmap scaling. The UI reads its
logical height from the viewport and applies the family's rule; the fixed
1280 × 800 goes. The panel keeps 1280 × 800 exactly (factor 1).

### How a screen is applied: at boot, from one file

The chosen screen is written to `/etc/gexis/screen.env` (model, family, mode,
rotation). At boot:
- the **mode** by the kernel's `video=` on the command line - this image runs
  full KMS, where the firmware's `hdmi_timings` / `hdmi_mode` from the presets
  do not apply (Finding 100); a preset's timings become a `video=` mode;
- the **rotation** by the compositor (`wlr-randr --transform` before Chromium
  starts), and the **touchscreen tied to that output** in labwc's config, so
  touch turns with the picture;
- the **Chromium factor** and the family from the same file.

Changing screen or rotation restarts the device (the rows are marked R).

### How a screen is recognised

EDID's maker, name and modes (`/sys/class/drm/card*-HDMI-A-*/edid`) and the
touch controller's USB ID suggest a model from our list; the user confirms in
setup's Screen step or in Settings. EDID sizes are not trusted (Finding 100:
the panel on `gexis` claims a 55″ television). Physical size, which the 7 mm
touch floor needs, comes from the list.

## Decided (George, 2026-09-30)

1. **Which screens the list offers.** foonerd's presets (MIT) name 197 models.
   **Decided: all of them, credited, with the four George owns marked
   tested; recognition only suggests a tested model, and an untested one says
   so when chosen.** The alternative is the tested four only - honest, and
   small.
2. **Where the other sizes' skins come from.** Each size's skin set is
   hundreds of megabytes (1280 × 800 alone is 168 MB), so one image with every
   size's set grows by gigabytes. **Decided: one package per skin set
   (`gexis-skins-1920x1080`, …), part of every release (ADR-0108), and
   installed when a screen of that size is chosen - from the same signed
   repository an update uses. The image carries the 1280 × 800 set only.** The
   alternative is every set in the image.
3. **Which skins each size gets. Decided:** the catalog's packs for that size
   are its default set, **and Gelo5's set for that size** is added - Gelo5
   publishes one for every size George has (PeppyMeter.doc release
   2024.03.02: 1920 × 1080 120 skins, 1280 × 400 120, 1480 × 320 116, 800 × 480
   60; Finding 100 as corrected), from the same source as the 1280 × 800 set
   shipped today. Each catalog pack's licence is checked before it ships.

## Decided on the handoff review (George, 2026-09-30)

The review of Claude Design's handoff ([`design/briefs/13b-handoff-review.md`](../../design/briefs/13b-handoff-review.md))
found seven things that were George's to settle. His answers:

4. **Touch floor: 44 logical px, and nothing grows.** The design's "7 mm on
   every screen" would need 59 px on a 7″ 800 × 480, where today's panel has
   about twenty targets of 36-58 px. On the screens George owns, 44 px is
   6.6 mm (1280 × 400) to 10 mm (13.3″). The 7″ is below 7 mm and is not on
   the bench. *"Agree"*.
5. **A screen is confirmed before setup trusts it.**
   - Until a screen is confirmed, the setup network uses the fixed password.
     Today, anything connected to HDMI switches to a made-up password shown
     only on the panel, which a dark screen hides.
   - After a screen is chosen, the panel asks **Keep this screen?** If it is
     not touched within about 30 s, the player goes back to the previous
     screen. A touch proves both the picture and the touch input.

   *"agree"*.
6. **Rotation: 0° and 180° only.** 0° is the model's landscape (the bars are
   portrait panels by nature; their list entry carries the turn). Portrait is
   not designed, and 90° on a bar gives an aspect in no family. *"fine"*.
7. **What a bar drops is dropped by design.** Artist and release info, the
   biography, top tracks, similar artists and per-row actions are on a
   Standard screen only. The brief's *nothing only the panel can do* does not
   hold on a bar. George: *"the losing is by design and was considered due
   to bar limitations"*.
8. **Skins become plugins.** This replaces decision 2's *installed when a
   screen of that size is chosen*. George: *"Maybe all of them become
   plugins, with a selector for choosing the resolution set by default to the
   Displays resolution or nearest neighbour that would work."*
   - Each skin set, for one size and one source (a catalog pack or Gelo5's),
     is a plugin in our repository. It is installed and removed on the
     Plugins screen and updated with the release (ADR-0106).
   - A selector in Visualiser picks the size in use. Its default follows the
     screen: the exact size, or the largest installed set that fits,
     letterboxed.
   - The selector is ADR-0022's *Skin size*; see *Settled the same day*.
9. **Ethernet as a choice (`connection`, `eth_ip`) is struck** from the
   design docs. George: *"strike it. We will need to consider the ethernet
   later."*
10. **The Network step keeps saving without testing** (IMPLEMENTED-DIFFERENTLY,
    phone steps). *"yes"*.

### Settled the same day

- **1280 × 800 is a plugin too, preinstalled**, so a panel shows meters with
  no network; it is removed like any other. George: *"Agree"*.
- **Skin size** is in ADR-0022's inventory: *Match the screen* (default) or
  any installed set's size; the picker offers only that size's skins.
  George: *"Agree"*.

### Amended 2026-10-01: the bar library keeps the row reveal

George, after the bar library was built: *"We keep the behaviour from
standard, showing the reveal"*. A library row on a bar reveals Play now, Add
to queue and Add to playlist, as on Standard. The other drops in decision 7
stand: artist and release info, biography, top tracks, similar artists.

## Not in this record

- The 800 × 480 on real hardware: designed and built, not tested until one is
  on the bench.
- Portrait use of any screen (see decision 6).
- Ethernet as a user's choice (decision 9).

## Unverified (to be shown on George's three screens)

- `--force-device-scale-factor` on this Chromium under labwc: crisp at 1.5,
  touch coordinates right.
- `wlr-randr --transform` with labwc, and touch following it; the boot
  animation and the splash on a rotated panel (Plymouth draws before the
  compositor exists).
- Each bar's mode reaching KMS through `video=` from a preset's timings.
- What each screen's EDID and touch controller actually say.
