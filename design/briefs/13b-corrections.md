# Brief for Claude Design: corrections and one new screen (Phase 13b, round 2)

Written 2026-10-01 by Claude Code for George to hand to Claude Design.
- **Answers:** your 2026-09-30 handoff.
- **Covers:** the Standard family, the Setup Screen step, Settings and the
  design docs.
- **Elsewhere:** the bars are in [`13b-bar-gaps.md`](13b-bar-gaps.md). The
  full review behind both is [`13b-handoff-review.md`](13b-handoff-review.md).

## Decided by George since your handoff (context)

- **Touch floor: 44 logical px, nothing grows.** On a 7″ 800 × 480 that is
  5.2 mm, below the handoff's 7 mm; the 7″ is not on the bench. On the
  screens George owns it is 6.6 to 10 mm.
- **A chosen screen is confirmed before setup trusts it.** Until then, the
  setup network uses the fixed password: a dark screen would hide a made-up
  one. After a screen is chosen, the panel asks **Keep this screen?**, and
  goes back to the previous one if nobody touches it within about 30 s.
  **This screen is new; please draw it (section 3).**
- **Rotation is 0° / 180° only;** portrait is not designed.
- **Skins are plugins**, with a Visualiser row **Skin size** (*Match the
  screen*, or any installed size). The 1280 × 800 set comes preinstalled.
- **Ethernet as a choice (`connection`, `eth_ip`) is struck** from the design
  docs; it will be considered later.
- **The Network step keeps saving without testing**, as
  `IMPLEMENTED-DIFFERENTLY.md` records.

## 1. Standard family

**Already fixed on our side** (take them back into the design; nothing to
answer):
- The home cards take their share of the height but are never shorter than
  their content. At 720 the rule gives 157 against about 163 of content.
- The artist and album columns grow with their pictures. Before, the
  picture grew alone, into the gap.
- Panel setup at 720: the QR code gives up the height (260 at 720, 340 from
  800 up). Otherwise *Could not join* ran into the header.

**Still to correct:**
- **The heights.** 711 is aspect 1.8, not 16:9. 16:9 is **720**, which is
  George's 13.3″, and the 7″ is **768**. Please show 720 and 768 among the
  artboards.
- **The Chosen page's claims.** "Smallest target 60 px": the study uses
  36–58. "Smallest mono label 13 px": it uses 11 and 12 px about forty times.
  Please restate both against the 44 px floor.
- **"Rule B" / "rule 1b"** is cited, but the file that defines it is not in
  the bundle.
- **The artist page's "more rows":** which of the biography, top tracks and
  the album peek takes them?
- **Not drawn at other heights:** the LMS-off waiting home and the
  add-to-playlist sheet.

## 2. The Setup Screen step

- The Headless warning (without a panel, the fallback setup network is gone)
  is computed in the prototype but never shown.
- *Choose another* on a recognised screen opens a view saying the screen did
  not say which model, with a hardcoded maker.
- The list is silently filtered by the resolution the screen reported.
- **Recognition only suggests a model, and only a tested one** (ADR-0109).
  "The player recognised…" claims more than it knows.
- **An untested model says so when chosen** (George's decision 1). The
  wording and its place are not drawn.

## 3. New: Keep this screen?

Shown on the panel after a screen or rotation is chosen and the player has
restarted on it.
- One question, a way to say yes, and a visible countdown of about 30 s.
- With no touch it goes back to the previous screen.
- It also confirms the touch works: the yes is a touch on the panel itself.

Please draw it for the Standard family and for a bar.

## 4. Settings

- **Updates group** (System, top), added after your sync commit. Rows:
  - *Release*: read-only, the installed release and its state;
  - *Check now*: an action;
  - *Update now*: an action with a confirmation;
  - *Updates*: Manual or Automatic;
  - *Update channel*: Stable or Testing, with a warning on Testing.
- **Plugin upload**, added after your sync commit.
- **Attached screen:** 197 models. The setup list is grouped and searchable,
  but the row is drawn as a flat sheet. Please give the row the setup list's
  form, mark untested models, and limit the rotation row to 0° / 180°.
- **Skin size** (Visualiser), new.

## 5. Stale references in the bundle

- The rows are called "marked R (restart)". In ADR-0022, R means *recorded*;
  new rows are [N].
- `design/README.md`:
  - says the rows are "not yet in Settings.dc.html", but they are there;
  - cites `Setup Screen Step.dc.html`, which does not exist.
- The comment in `Settings Screen Row.dc.html` is out of date.
- The BUNDLE-README's file map uses the bundle's paths, not the repo's
  (`design/source/13b/…`).
- `now-playing.css:334` has the transport gap at 20 px; the prototype has
  14.
