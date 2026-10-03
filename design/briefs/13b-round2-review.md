# Review of Claude Design's round 2 (Phase 13b), 2026-10-01

Written by Claude Code before implementing round 2 (commit db31a5b). It was
checked against `13b-bar-gaps.md`, `13b-corrections.md`, ADR-0109 and the code.

**How it was checked:**
- `verify.html` passes all 37 checks.
- Text widths were measured with the bundled fonts (fontTools; kerning
  ignored, ±3 px).
- Nothing was rendered at bar sizes yet.

**Verdict.** Round 2 answers almost every point of both briefs. It brings our
three Standard fixes back into the design and draws *Keep this screen?*. The
forecast rule is exact: the row is 1112 + 136n px wide. Every interactive
target drawn on a bar is now 44 px or more.

## 1. Decisions for George

**Answered 2026-10-01** (George): 1 *"Rewrite copy and I will check"*;
2 panel only; 3 and 4 agreed; **5: no** - *"it should have progress when
information is provided via bluetooth. Just like it is now"*, so the bar
shows progress exactly as the panel does; 6 the bar matches the panel; 7 keep
teal; 8 to 12 agreed; 13 keep ours; 14 keep ours (ADR-0074), after an explanation; 15 keep
ours; 16 keep *Device*; 17 keep the layout.

| # | Question | Recommendation |
|---|---|---|
| 1 | **Headless warning.** The design's copy says there is "no fallback setup network" without a screen. That is untrue: the setup network falls back to the fixed password, and under decision 5 an unconfirmed device uses it too. | Say what is true: without a screen, the setup network always uses the fixed password from the guide. Draft the copy and confirm it. |
| 2 | **Who may press Keep:** the panel only, or the phone too? | The panel only. Pressing it proves both the picture and touch. |
| 3 | **What "going back" means at first setup**, when there was no earlier screen. | Back to *no screen chosen*: the screen's own preferred mode, the fixed password, and setup still open on the phone. |
| 4 | **Keep this screen? after only a rotation change.** | Title *Keep this rotation?*; countdown *Going back to 0° in n s*. |
| 5 | **Bluetooth has no position.** The bar design hides progress and times. The panel draws an empty bar and 0:00. | Hide it on both. It is honest, and the panel follows. |
| 6 | **Lyrics on a bar.** The design treats *instrumental* as *none*, hides the switch when there are no lyrics, and draws no error state. The panel has *Instrumental* and *Retry*, and its tab is always there. | The bar follows the panel: the switch is always there, with *Instrumental*, *No lyrics* and *Retry* states. |
| 7 | **Tray slider fill.** The design uses the source accent, believing that is what the panel does. The panel actually fills LMS teal for every source. | Keep the panel's teal everywhere. |
| 8 | **A plugin with no mark:** its initial in a ring. Today the panel draws nothing. | Adopt it on both. |
| 9 | **Attached screen on a bar:** makers and models side by side, with no search. | Yes: two short columns need none. Record the reason as *short lists*, not *no keyboard* (input parity). |
| 10 | **External URL on a bar:** W × 400; a touch returns to Now Playing. | Yes. |
| 11 | **Bar idle drops** feels-like, wind and sunrise/sunset. | Yes: the same as decision 7 (by design). |
| 12 | **Playlist tracks scroll sideways** on a bar. | Yes. |
| 13 | **Standard QR code.** The design steps at 260 / 340. Ours is `min(340, H − 460)`: 308 at 768, and it also fits at 711, where 260 overruns by about 9 px. | Keep ours. |
| 14 | **The artist page on a taller screen.** Round 2 gives the extra height to the albums and caps the biography. ADR-0074 gives it to the biography and lets the albums peek. | Keep ADR-0074. |
| 15 | **Updates copy.** Theirs promises that *Manual tells you on the panel and the phone*, which nothing does today. | Keep ours, which is accurate to ADR-0105. |
| 16 | **System's "Device" heading becomes "Maintenance"** in the design, which also leaves out four of its rows. | Keep *Device*. |
| 17 | **Upload a plugin.** The design puts it last, as a sheet. Ours is first, with a file icon and a centred dialog (George, 2026-09-30). | Keep ours, and record it in IMPLEMENTED-DIFFERENTLY. |

### The bar library (George, 2026-10-01, after it was built)

1. **A row reveals its actions, as on Standard** (*"We keep the behaviour
   from standard, showing the reveal"*): Play now, Add to queue, Add to
   playlist, one row at a time. This takes back, for the library's rows,
   ADR-0109 decision 7's *per-row actions dropped on a bar*.
2. **Radio scrolls sideways** (*"Yes"*).
3. **Browse's album rows reveal the same actions** (*"Same as standard. We
   show reveal."*), so a whole album plays from Browse too.

### The bar's moments (George, 2026-10-01, after seeing them)

1. **Idle on a cold day:** at −14° with a −12/−18 day, a 1280 bar drops its
   forecast day rather than let it collide; 1850 keeps all three. Accepted
   as built (*"I'll go with your recommendations for both"*).
2. **Setup's join line on a bar** keeps the design's wording, *Scan to join,
   then open 10.42.0.1:8090*: a bar has one QR code, so the address is
   written out.

## 2. Back to Claude Design (round 3)

### Errors
- **Idle on a bar:**
  - *today* is not always 360. With two-digit negative temperatures it is
    about 401, so the side margin falls from 72 to about 51 at the zero-slack
    widths.
  - Forecast days are 100 wide, but "-12° -18°" measures 138, so two such
    days collide. Their own sample, "21° 11°", is 111.
- **"At 2000 the extra goes to the gaps":** the gaps are fixed at 40, so it
  goes to the side margins.
- **LMS off:** "five fit at 1280" is false. Five need 1412 px; in the code the
  columns shrink to about 174.
- **Premises about the panel that are wrong:**
  - The panel has an *Instrumental* state and a lyrics error state, and its
    Lyrics tab is always present.
  - The panel's volume fill is LMS teal for every source.
  - The panel never hides progress.
- **Bar Frame and Bar States disagree:**
  - Bar Frame's artist line still has no ellipsis.
  - The title in Bar States' lyrics header has no ellipsis either.
  - Bar Frame fills the slider teal; Bar States uses the source accent.
- **The bar sheet** is 400 − 24 = 376 tall, not "full height less 12".
- **Overlapping touch zones, with no rule for which gesture wins:**
  - the 44 px pull-down band overlaps the top 12 px of the lyrics switch;
  - on the open tray, the slider's full-height touch area overlaps the
    bottom 44 px close band.
- **Bar Library's artist page** still draws *Top tracks* and tags, which
  ADR-0109 decision 7 drops.
- **Lyrics switch:** Bar States hides it for Spotify and Bluetooth with no
  rule given. Enrichment is not limited by source.
- **Standard, Panel Setup:** a 260 px QR code at 711 overruns by about 9 px.
- **The artist page's extra height** contradicts ADR-0074 (decision 14
  above).
- **"Any pick says the player restarts…"** shows only in the
  *nothing shown* state. The uncertain state shows it only for an untested
  model, and the recognised state never shows it.
- **Keep this screen?** has no wording for a rotation-only change.
- **The Headless warning's facts** (decision 1).

### Missing
- **Strip:** radio or a stream with no duration; the lyrics error/retry state.
- **Jump strip:** no "#" step. The panel's rail has one, and 14 steps still
  fit at 51 px.
- **Done card:** drawn only as *found*. Also needed: *given*, *several*,
  *off* and *none*.
- **Mobile-data warning:** missing on the bar's *page* and *could not join*
  boards.
- **Not checked at 1200:**
  - Ethernet setup, where "Set up gexis" wraps beside a 520 px address;
  - a single-word plugin name wider than 340 in the transition
    ("Squeezelite-ESP32" is 454 px).
- **Radio folder grid:** scroll direction.
- **Data contract:** not updated for round 2. Round 2 needs the screen
  table's *tested* flag and the *Keep this screen?* state.
- **Your own "Not done" list:** the 82% sheet cap in Settings.dc.html;
  skin-set rows on the Plugins screen.

### Naming: keep ours, please adopt in the design
- The Updates keys are `update_status`, `update_check` and `update_install`,
  not `release`, `check_now` and `update_now`.
- The grouped picker's flag is `grouped`, not `groups`.
- The Release row's note carries the release notes, *What's new in …*,
  while an update waits and after it is installed (added 2026-10-01).
- **Hygiene:**
  - `Screen Families Chosen.dc.html` line 21 links to a file that does not
    exist.
  - `design/README.md` still says verify.html has not been run.
