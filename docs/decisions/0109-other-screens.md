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

**Superseded in part by [ADR-0111](0111-skin-sets-follow-the-screen.md)** (2026-10-01): one pack per device, chosen by the screen, with consent in setup; no *Skin size* selector; the image ships no skins.

### Settled the same day

- **1280 × 800 is a plugin too, preinstalled**, so a panel shows meters with
  no network; it is removed like any other. George: *"Agree"*.
- **Skin size** is in ADR-0022's inventory: *Match the screen* (default) or
  any installed set's size; the picker offers only that size's skins.
  George: *"Agree"*.

### Settled 2026-10-01: which screens, and which are tested

- **George's four are Waveshare HDMI screens:** *"All of them are waveshare
  with hdmi inputs"*. Tested, as decision 1 has it: the 10.1" HDMI LCD (B),
  the 13.3" HDMI LCD (H), the 7.9" HDMI and the 11.9" HDMI. Step 6 tries the
  three not yet on a device before a release offers them.
- **Square and round screens are left out:** *"Leave them out"*. That is 11
  models, 480×480 to 1080×1080, which no family lays out.
- **The list is 181 models.** foonerd's 197 entries, less *Auto Detect* and
  *Custom timings* (not screens), less 3 without a size, less those 11.
- **HDMI only, for now: 110 models.** George, 2026-10-01: *"B it is and I
  will try to get my hands on one"*. A DSI or DPI screen needs its own
  `dtoverlay` in `config.txt`, which applying does not write and nothing
  here can test. They come back when one can be tested.

### Settled 2026-10-01: setup's Screen step

- **The full list folds by maker on the phone** ("Waveshare · 91 models").
  181 open rows would be about 13,000 px; the search and the
  resolution-matching models stay open.
  **Amended 2026-10-10: the makers are chips.** Folded, the 18 makers were
  still 18 full-width headings, most of a phone's height before one model
  (George: *"It is important but it takes a few screens to scroll"*). They
  now wrap as chips with their model counts (about 350 px at 390 px wide,
  where the headings took about 860); one maker opens at a time, under the
  chips, headed with its name. A search still lists every match, open.
- **If the list cannot be loaded, the step says so and offers Retry.** The
  list comes from the player over the setup Wi-Fi, so a failure means the
  phone dropped off it for a moment. Offering only Headless would turn the
  screen off with one tap (*"I agree"*).
- **Nothing is preselected when no screen is detected.** Today the step
  starts on Headless in that case, but a DSI screen (67 of the 181) never
  shows on the HDMI check, and nor does one plugged in late. Continue waits
  for a choice (*"yes, it makes sense"*).

### Amended 2026-10-01: the bar library keeps the row reveal

George, after the bar library was built: *"We keep the behaviour from
standard, showing the reveal"*. A library row on a bar reveals Play now, Add
to queue and Add to playlist, as on Standard. The other drops in decision 7
stand: artist and release info, biography, top tracks, similar artists.

### Amended 2026-10-02: Keep is asked only when the picture changes

George, after the first setup of 0.5.0 asked *Keep this screen?* at boot
while he was still at the phone: *"A and C. Also fix the defect"*. Decision 5
becomes:

- **The question is asked only when choosing the screen changes the
  picture**: a forced mode (`video=`), a scale or a rotation that differs
  from what the screen shows now. A screen driven at its own mode, at scale 1
  and unrotated - of the four tested, the 10.1" HDMI LCD (B) - is kept
  without asking. The 13.3" (drawn at 1.5) and both bars (a forced mode and
  a turn) are still asked.
  The question guards against a screen left dark or unreadable, and a change
  that alters nothing cannot do that.
- **After setup, the phone says the question is coming, and it waits 2
  minutes** rather than 30 s: setup ends on the phone, not beside the panel.
- **A screen that goes back also goes back in Settings** (the defect): until
  then, *Attached screen* went on naming the screen that had been undone.

The fixed setup password still waits for a kept screen; one kept without
asking counts as kept.

### Amended 2026-10-03: a case is not a screen

George, 2026-10-03: *"there is a wave share 1280 X 800 and the same box. Now I
have the box one, but selected is the non box one ... In general the box and
non box i would say are the same."* Upstream's list names five Waveshare
panels "with Case"; the case changes nothing the player sets. So a preset
"with Case" is listed as its panel - **dropped where the bare panel is listed
(10.1" (B), 7" (H), 10.1" (H), 11.6" (H)), renamed where it is not (10.1" (D)
and (G))** - and is tested when its panel is. A choice saved under the old
name or id still finds the panel. HDMI models listed: **106** (was 110).

### Settled 2026-10-03: Browse on a bar, and the 800 x 480 size

George, 2026-10-03, on the two points DEVELOPMENT.md still listed as owed:

- **A bar keeps Browse; Settings is on the phone only** (*"already answered
  and we have designs for it. We keep browse and put settings only on the
  phone"*). The bar designs (round 2) draw it.
- **800 x 480 stays in the list, untested,** until such a screen is at hand
  (*"we leave it untested for now. No point in holding off an entire phase for
  it. Once I have one, we can test"*). It does not hold 13b's close.

### Amended 2026-10-03: a new screen is noticed at start

George, 2026-10-03, after attaching the 13.3": *"Upon boot couldn't we detect
that a new display was connected and give the user the choice to keep the new
resolution?"* Until now a screen was recognised only in setup's Screen step,
or when the Attached screen row was opened. **Decided (George, "All three
decisions in agree with your recommendation"):**

- **What the player remembers:** when a screen is kept, what it reported -
  EDID maker, name and preferred mode, and the touch controller.
- **At every start it compares** what is attached with that. If they differ,
  it asks, on the panel and on the phone page: a recognised tested model by
  name (*"A Waveshare 13.3" HDMI LCD (H) is attached. Use it?"*), anything
  else by its size, opening the screen list on that size. A yes goes through
  the existing restart and Keep, which goes back by itself - the new screen's
  touch may not work yet, as the 13.3"'s did not (a charge-only cable).
- **1. Any screen that reports something different** from the one kept is
  asked about, not only tested ones (A, of A/B).
- **2. "Not now" is remembered for that screen**, which is not asked about
  again; a different one is (A, of A/B).
- **3. A headless player never asks.**

Also confirmed on the hardware that day: the 1920 x 1080 size, on the
13.3" (George: *"You can also consider that the 1920 resolution was
checked"*).

### Amended 2026-10-04: a recognised screen is switched to

George, 2026-10-04, after the swap test: *"if we know that another display
was connected why not show directly in the correct resolution and ask the
user to keep it? Why this additional screen that we have now?"* The question
before the switch was a step of mine, not his: he had asked for "the choice
to keep the new resolution". **Decided (A):**

- **A recognised screen** - one whose fingerprint was measured here, so
  today the 10.1" (B) and the 13.3" (H) - **is switched to at start**,
  without asking: the panel comes up on it with *Keep this screen?*, and
  goes back by itself if nobody keeps it.
- **Only the kiosk restarts** when the kernel's mode does not change (no
  `video=`; true of both tested screens); otherwise the device does, as a
  choice in Settings does.
- **A switch that went back is asked about at the next start**, by name as
  before, rather than tried again - a screen with no working touch would
  otherwise restart into a Keep nobody can press at every start. Keeping
  any screen clears this.
- **Any other screen** - the 106 listed models included, whose fingerprints
  are unknown - is still asked about, opening the list on its size.

### Amended again 2026-10-04: every new screen, before the panel starts

George, 2026-10-04, testing the bars: the first start on the 11.9" showed
*Keep this screen?* with no Keep button on the bar (the phone answered it),
and switching 10.1" <-> 13.3" had drawn in the old screen's layout first. *"The
expectation is though that we know the screen resolution so we should render
in that resolution already, asking the user whether to keep it or not. If the
display gets garbled up, after the 2 minutes we restart with the previous
setting in place. Also for resolutions like the bar's we should put it into
landscape automatically. Of course all of these apply on the go changes and
not when the setup takes care of things."* Reproduced 2026-10-04: drawn on
a portrait page, the Keep screen's standard layout runs off its right edge,
and at the bar's own width Keep is off the screen entirely.

- **Decided before the panel starts.** `gexis-screen-check.service`, a
  oneshot before the core and the panel, compares what is attached with
  what was kept and switches a different screen at once: the panel's first
  frame is the new screen's own, with *Keep this screen?*. A change of the
  kernel's mode (a bar's `video=`) restarts the device first, before
  anything is drawn. The core no longer switches screens itself.
- **To what:** the recognised model; else, for a bar, the one listed bar of
  exactly its mode; else **the screen laid out from its own mode**
  (`screens.other`, *Other screen W x H*). **Always landscape**: a panel
  that reports a portrait mode is turned. Only a bar is named by its size -
  a standard size is any monitor's. Found in the tests: by size alone a
  1920 x 1200 monitor matched a listed 1200 x 1920 portrait panel and would
  have been turned on its side, so a listed model must match the mode as the
  panel reports it.
- **Keep waits 2 minutes for every change** (George: *"A change to a
  different screen should also wait 2 minutes"*; a rotation's was raised
  the same day). Not kept: back to the previous setting, restart; the next
  start asks about that screen instead of switching again.
- **Not during setup** (its Screen step decides) **nor headless.**

### Amended 2026-10-04: a bar boots in its own mode, turned

George, on the 11.9" bar: the boot logo was *"zoomed in a lot"*; he chose
**A** - tell the kernel how the panel is turned. Found on the way, and
settled on the bar the same evening:

- **A bar's `video=` is its resolution alone**, not the preset's `M@60`. With
  `M` the kernel calculates CVT timings for 60 Hz, which the bar does not
  display: it was dark for ~27 s of every boot, until the compositor set the
  mode its EDID gives (57.7 Hz, 59.4 MHz). Without `M` or a rate the kernel
  takes the EDID's mode of that size. **Shown:** the logo from the start.
- **The panel's orientation goes on `video=`** (`panel_orientation=`), so
  plymouth and the console draw turned; the compositor still turns the panel
  itself (`wlr-randr --transform`) and does not turn it twice (plane rotation
  0, measured). A total turn of 90 is `left_side_up`, 270 `right_side_up`:
  **shown at 270** (the 11.9" at 180°, *"It displayed correctly"*); 90 is its
  mirror, not yet seen.
- **The boot stages fit a bar's logo to its height** - plymouth's script,
  `gexis-splash-fb`, and swaybg behind the compositor - instead of filling,
  which cut the logo. `gexis-splash-fb` draws on the landscape canvas and
  turns it into the native portrait framebuffer by the screen's transform.
- **A bar kept before** has its `video=` brought up to date at the core's
  next start, for the restart after.

Not yet seen: the 7.9" bar (1280 x 400), and any bar at 0°.

Considered and **postponed** (George: *"Let's leave the crowd sourcing
post"*): users sending a screen's fingerprint through a pre-filled GitHub
issue from the phone page, without the EDID serial, so more models become
recognised. Its open questions - an account-free route, and whether one
report makes a screen recognised - stay open until it is taken up.

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

## Amended 2026-10-07: the screen applied during setup too

George, after flashing 0.9.2 onto a 13.3" (1920 x 1080): *"The QR codes on the
screen were skewed to the left of the image as though the pi was displaying
the 1280 resolution on the 1920 screen. This should be address as on a bar it
could be problematic."* At start, a new screen was switched to only once setup
was done (amended 2026-10-04: *"not when the setup takes care of things"*), so
setup's own screen ran unscaled - 1280 logical px in the left of 1920 - and on
a bar it would have stood on its side. George then agreed: apply it during
setup too.

1. **During setup, `gexis-screen-check` applies the attached screen before the
   panel starts**, as it does after setup: the recognised model, else the one
   listed bar of its mode, else the screen laid out from its own mode (scale
   only - no rotation, no kernel mode). A bar whose kernel mode changes
   restarts the device first, before anything is drawn.
2. **Provisional, not kept, and no Keep asked:** setup's Screen step is the
   question. The setup network keeps the **fixed** password (ADR-0104): a
   provisional screen is not one anybody has confirmed is readable, and the
   fixed password works whatever the screen shows.
3. **Setup's Screen step confirms it or replaces it**; a different choice asks
   Keep after setup, as before.
4. Applied once per setup: a screen applied provisionally is not applied
   again at the next start while setup is still under way.

## Amended 2026-10-11: the Keep warning only where it is true

George, on the bar after a reset: setup warned that the player would restart
and ask *Keep this screen?* for the recognised, tested 11.9" - already
applied for setup, so choosing it changes nothing and nothing is asked. The
Screen step's data now names the screens whose picture is the one on the
screen now (`unchanged`, from `screen_apply.picture_of`); the warning's Keep
sentence shows only for a choice outside it. An untested model still says so.

## Amended 2026-10-12: a TV as the screen is out of scope - a possibility for later

George: *"Let's keep 4k TVs out of scope for now. Record them as a could in the
future."* ADR-0111 had already answered for the skins (*"We will not support
4k"*). A code trace the same day found what would happen with one (the
to-do list's item, and below), so a later phase starts from it rather than
from nothing:

- setup does not lock: a 3840 x 2160 TV is an unknown Standard screen, drawn
  at x3 (the 13.3"'s 1280 x 720 layout); the phone's touchpad answers what a
  touch would;
- but a TV off or on another input at boot leaves the page unscaled in a
  1280-wide strip with no re-check; the Pi 4 is not set for 4K at 60 Hz (the
  list's *Generic 60Hz* preset writes nothing to make it so) and the mode a
  TV comes up in may not be the one assumed; *Keep this screen?* can only be
  answered from the phone's touchpad, with nothing saying so; the visualiser
  fills a quarter of the screen (the 1920 x 1080 pack, centred); a TV's own
  auto-off after no signal defeats standby's wake, and there is no CEC;
- only a real TV can show the mode chosen, frame drops at x3, overscan and
  what its auto-off does.

A *could* for later, not on the plan: it would be its own phase, ADR first.

## Amended 2026-10-12: the screen on the port it is plugged into

George: *"The two bugs we need to fix now"* - two faults found tracing a TV
as the screen the same day:

- **Rotation on an unlisted screen did nothing.** *Screen rotation* re-applied
  the screen by its label, and `Other screen/W × H` is in no list, so the core
  logged "not a screen gexis knows" and turned nothing. The screen in use is
  now found by its stored id when the label is its own (`screen_apply.named`),
  so a portrait panel used sideways keeps its turn, and *Attached screen*
  offers the unlisted screen in use, tagged Untested.
- **The screen was taken to be on HDMI-A-1.** Detection found the right port,
  but the mode (`video=`), touch, the turn and standby all went to HDMI-A-1.
  Now:
  - the screen is applied on the port it is seen on, and `screen.json` keeps
    that port; a state written before it was kept reads as HDMI-A-1, which
    every such player ran on - no migration;
  - with no screen connected (switched off at the boot) the port applied last
    stays;
  - **the same screen moved to the other port** is applied again there at the
    next start. For a bar its `video=` moves with it: a change of picture,
    which restarts and asks *Keep* like any other, and goes back if not kept.
    A screen without a forced mode moves without asking;
  - `gexis-kiosk-start compositor` writes a copy of labwc's configuration
    with touch mapped to that port, and off HDMI-A-1 a window rule moving the
    kiosk and the visualiser there, then starts labwc on it (`labwc -C`); if
    the copy cannot be written labwc starts on the installed file, as before.

**Still open** (ADR-0141): with **both** ports connected, the first connected
one is the screen. A receiver on HDMI 1 and the panel on HDMI 2 is the case
that record decides.

**Unverified** on the hardware when written: `labwc -C` and the window rule on
labwc 0.20.2, the boot picture's hand-over on HDMI-A-2, and a bar moved
between ports.

## Amended 2026-10-14: the countdown starts with the question on the screen

George, moving the 11.9" bar to HDMI 2 and back: *"The keep timer was in its
roughly last 40% when it showed up."* The countdown ran from the panel's
first painted frame (ADR-0043's report), and the question was seen about 70 s
after it on that start - why is not in the logs. **The countdown now starts
when the panel has drawn the question** (George: *"The countdown should start
with the keep screen displayed"*): the panel reports `/screen/shown` (loopback
only) two frames after it appears, and the core sets the deadline then. A
question never drawn still goes back after `NEVER_DRAWN_S` from the start.

## Amended 2026-10-14 (Finding 125): who answers Keep this screen?

Finding 125 (#9, #11) found that only the three panels whose fingerprint
names a USB touch device counted as having touch: every other listed panel,
the tested 7.9" bar among them, had *Keep this screen?* sent to the phone and
its own Keep and Go back hidden. A listed panel's touch may also not work at
all - many need an SPI ads7846 overlay or a goodtft driver the player never
installs. Who answers is now:

- **A panel recognised by its USB touch fingerprint** is answered on the
  panel only (decision 2 as before).
- **Any other listed touch panel** shows its own *Keep* and *Go back*, and
  the phone may answer too, so a panel whose touch does not work is not left
  to its countdown.
- **A TV, a screen in no list, a generic monitor mode, or a listed model
  whose notes say it has no touch** shows no buttons and is answered on the
  phone.

The question carries both: `panel_buttons` (`screen_detect.has_touch`, by the
model's id, so a panel kept under its old `-case` id keeps its touch, #8) and
`phone` (not `screen_detect.touch_recognised`, the fingerprint test that
`has_touch` was until now). Scheduled display standby no longer blanks the
screen while the question is up, and drawing it wakes a dark screen (#17).

Decision 5's *a touch proves both the picture and the touch input* now holds
for the fingerprinted panels only; on any other screen an answer from the
phone proves the picture alone.

## Amended 2026-10-18: two states on the screen

What the lists show of the Tested / Untested marks of decision 1 is now *Tested* (here, or reported working by
owners) or nothing, with a reported problem as a line under the model
(George: *"Make it for both sound and display"*). The states underneath are
unchanged. See ADR-0126's amendment of the same day.

## Amended 2026-10-18: the setup network's password is always gexis-setup

George, after a full setup on a fresh card: *"Why don't we generate passwords
anymore for the WiFi hotspot but use the generic one meant for devices
without displays?"* - then *"Let's just use gexis-setup for all cases"*.
Decision 5's first point no longer applies: the setup network's password is
`gexis-setup` on every player. A freshly flashed card never has a confirmed
screen, so in practice setup always used it already.

## Amended 2026-10-18: every window fills its screen

A visualiser opened from the phone on a freshly installed panel was drawn
partly off the screen. On the device (sofapi, 1280×800 panel on HDMI-A-1): the meter
window is restarted hidden when its skin changes, and when it was then
raised, labwc had placed it offset from the corner, where it stayed. A
`MoveTo 0,0` rule fixed it, but uses layout coordinates, which are wrong for a
panel on HDMI-A-2. A `Maximize` rule fixed it on either port.

`labwc-rc.xml` now carries one window rule for every window, `Maximize`.
`gexis-kiosk-start` adds `MoveToOutput` with the panel's port to that same
rule, ahead of `Maximize`, instead of writing a rule of its own. The meter
shows black for about three seconds while it loads after a skin change; that
was judged acceptable and is not gated.

## Amended 2026-10-23 (ADR-0158): DSI screens too

*HDMI only, for now* ends: every DSI model in the list but five is offered
([ADR-0158](0158-dsi-screens.md) D1, George: *"For all that we have in the
dsi list that we deferred until now"*). A DSI model that needs its overlay
has it written in a block of our own at the end of `config.txt`, with the
restart and *Keep this screen?* of decision 5 and the same way back; a model
picked from the list is shown by its own name, and a recognised panel not
yet chosen as *Raspberry Pi Touch Display or compatible* (D2).
