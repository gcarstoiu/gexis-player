# ADR-0126 — Hardware reports from users: DACs, HATs and screens tested by the people who own them

**Status:** **Accepted** — George, 2026-10-07, all three decisions below
answered *yes*. Raised by George: *"how do we crowd source
the testing of audio hats, dacs and displays. otherwise its impossible to have
coverage"*. Takes up what [ADR-0109](0109-other-screens.md) postponed
(*"Let's leave the crowd sourcing post"*) and answers its two open questions.
**Builds on:** ADR-0117 (DACs beyond the two on the bench: *Tested*,
*Known*, *Detected*; on `phase-13d`), [ADR-0109](0109-other-screens.md)
(screens, recognised by their EDID), [ADR-0125](0125-a-problem-report-users-can-download.md)
(what is taken out before anything leaves the device).

## Context

Two boards and five screens have been on the bench. The DAC list has more
than a hundred boards (Volumio's, corrected, Finding 106), and any HDMI screen
can be plugged in. Coverage can only come from the people who own the
hardware. They need a way to tell us that takes a minute, and we need a way to
turn what they tell us into what the player shows.

## Decision

1. **[N] *Report this hardware*** - *Settings → System*, beside *Problem
   report* (ADR-0125). It runs a short, guided check and builds a report.
   Offered **once, unprompted**, after a week on a board or screen that is
   not *Tested*: a single line on Settings' System page, *"Help others with
   this DAC: report how it works"*, dismissed for good with one tap.
2. **The guided check** (phone page or panel, a minute or two):
   - **Sound:** plays a short tone at 44.1 and 96 kHz (and 192 where the
     card offers it) - *"Did you hear it, clean?"*; moves the volume -
     *"Did it change?"*; *"Any clicks between tracks?"*
   - **Screen:** shows a test pattern with the edges marked - *"Is all of it
     visible?"*; asks for four taps in the corners - touch accuracy is
     measured, not asked.
   - **Free text:** anything else worth knowing.
3. **What the report holds, read from the device:** Pi model and memory, the
   Gexis version; the sound card's name, overlay, driver, mixer controls,
   the rates and formats it accepts; the screen's maker, model, size and
   modes from its EDID, **never its serial number**, and the touch
   controller's name; the answers. Nothing else: no logs, no addresses, no
   names (ADR-0125's rules apply to the free text).
4. **How it reaches us:** a **GitHub issue form, *Hardware report***, opened
   pre-filled from the phone page (the report travels in the link; when it
   is too long for one, it is copied and pasted). It needs a GitHub account
   (George: yes). Reports are public: anyone can see which
   hardware works before buying.
5. **A fourth state, *Reported*** (amends ADR-0117, and ADR-0109 for
   screens): a board or screen with at least **one report that it works,
   on a stated Gexis version**, and none against. Shown as *"Reported to work
   by 2 owners (0.9.3)"* under *Sound card board* and on the screen row.
   A report against (no sound, wrong rates, clicks) turns it to *"Reported
   with problems"*, linking the issue. *Tested* stays ours alone: played and
   measured here, with a finding.
6. **From report to player, by a reviewed change:** a script reads the
   *Hardware report* issues labelled `accepted` and updates
   `boards_data/` and the screen list; the change is a normal commit,
   reviewed, and ships in the next release. A report never changes the
   player by itself: a wrong one cannot reach anyone's device unreviewed.
7. **A screen not yet recognised becomes recognised** through the same
   route (ADR-0109's postponed question): one accepted report that names
   its working mode adds it to the list.

## Consequences

- One ADR-0022 row, `hardware_report` [R], appended 2026-10-07; the
  one-time prompt is not a setting.
- `HARDWARE.md` gains a generated table: every board and screen, its state,
  and the number of reports.
- Someone has to read and label the issues; the issue form keeps each one
  to the same fields, so that takes minutes, not hours.
- A report can be wrong or made in bad faith. *Reported* says how many
  owners, never more than that; *Tested* is never given by a report.
- Tones at full scale can be loud: the check plays at the current volume,
  capped at the *Maximum volume*, and says to turn the amplifier down first.

## Decided (George, 2026-10-07)

1. **A GitHub account is required** to send a report; no other route.
2. **One report is enough for *Reported***, with the count shown.
3. **The one-time prompt after a week: yes.**

## Built (2026-10-07, on `phase-13d`)

1. **Facts and the form** - `hardware_report.py`, `GET /hardware-report`,
   `POST /hardware-report/issue`, the System row's sheet,
   `.github/ISSUE_TEMPLATE/hardware-report.yml`.
2. **Test tones** - 1 kHz at -20 dBFS at 44.1, 96 and 192 kHz through
   `output`, refused while anything plays; what the card ran at goes into the
   report.
3. **The screen check** - the pattern on the panel, four corner taps measured
   in screen pixels against 6 % of the diagonal; the touch answer follows.
4. **The one-time line** - a week after a piece of hardware that is not
   Tested is first seen, per piece; × or a prepared report dismisses it.
5. ***Reported*** - `tools/hardware-reports.py` writes
   `hardware_reports.json` and HARDWARE.md's table; boards, the screen list,
   both pickers' tags and the two rows' notes follow it.

**Not built:** decision 7, a screen not yet recognised added from a report -
the script names such reports, and the screen list is changed by hand.
**Owed:** nothing - the labels exist (below).

## Amended 2026-10-07 (George)

- **The name: *Hardware feedback*** - *"Report hardware trends to lean towards
  the negative."* The row, the System page's line (*"Help others with this
  DAC: share how it works"*), the GitHub form and its label (`hardware
  feedback`). The setting's key stays `hardware_report`; the state *Reported*
  is unchanged.
- **Two steps: the screen, then the sound.** The screen step (pattern, taps,
  the picture and touch questions) is **skipped when no screen is connected
  or Headless is on**; its answers are then *No screen* and *No touch*.
- The labels `hardware feedback`, `accepted` and `problem report` were
  created on the repository the same day (George: *"You can also create the
  labels"*).

## Amended 2026-10-09: a step of its own for the notes

George, on a phone: the free-text box *"should have its own step in the
modal as otherwise it's too tight on a phone"*, with the step named in the
title. The sheet is now **Screen, Sound, Anything else** (*Step 1 of 3*), or
Sound, Anything else (*Step 1 of 2*) without a screen. The last step holds the
notes and, under *What the player adds for you* (until now *What the player
read*, which did not say what it was for), the facts the player puts into the
feedback itself, so they are seen before anything is sent. *Back* goes one
step back.


## Amended 2026-10-11: answers that arrive, one way to send, feedback kept

George, after sending one from a phone: *"Values selected during test are
not passed along to the GitHub form"*, and *"Unclear for an user what to do
at the end. Show in GitHub is a link and pressing done closes the modal"*;
*"can the findings be stored to be sent again or the assessment restarted
from scratch? ... wherever the screen or audio hat changes the report
hardware should be reset."*

1. **The five answers are text fields on the form.** GitHub fills an issue
   form's text fields from a link but not its dropdowns, so every answer
   chosen on the player arrived blank. The player writes the same words
   (*Yes*, *No*, *Not tried*, *No screen*, *No touch*); the script reading
   reports takes them whatever their capitals. GitHub reads the form from
   `main`, so this holds from the release that carries it.
2. **One way to send** (George chose it of two): the last step shows a
   single main button, *Send on GitHub*, with a line saying GitHub opens
   filled in and Create sends it; *Done* becomes *Close*.
3. **The last feedback is kept on the player**, with the sound card and the
   screen it was made on. Under the *Hardware feedback* row on System (George
   chose the row over the sheet): when it was made, the two pieces, and two
   buttons - ***Send again*** (GitHub opens with it once more) and ***Start
   over*** (it is forgotten; the row opens a fresh check).
4. **Another sound card or screen forgets it**: what is kept names the
   pieces, and when either is no longer the one in use it is dropped. The
   one-time prompt was already per piece.

Not a setting: no ADR-0022 row. Kept with the prompt's record, in the
settings store's own state, so a backup carries it and a factory reset
clears it.

## Amended 2026-10-11 (again): checked through

George, the same evening: the form still came blank, *"First time the show
pattern button didn't work and then also the tones couldn't be played. Can
you thoroughly check the implementation here?"* The two failures were traced
(the phone's state connection, down for seven seconds after the browser came
back from the background; a Plexamp the player did not know was playing,
which plugin 0.4.7 fixes) and the whole feature was reviewed. Changed:

- **Touch** is a device that reports a touch and where it lands, on USB or
  I2C - not any USB input device: a keyboard with a screen without touch
  asked for four taps that could not be made.
- **The tones** wait while a source holds the card even paused (it refuses
  them as surely as one playing), play one set at a time, and never call a
  tone that played "did not play".
- **The address** keeps the details' first lines (version, card) and cuts
  the notes once the rest of the details is gone; notes in a script other
  than Latin had pushed every detail out.
- **Only the screen check a feedback ran** goes into it; a screen without
  touch answers *No touch*.
- **The Pi's own output** (HDMI, the jack) is named as that and never
  counted as a DAC.
- **What is kept** is forgotten when the connected screen changes or the
  player goes Headless, not only when Settings names another.
- **Showing the pattern** takes the visualiser down and wakes a screen in
  standby, either of which hid it.
- The phone reconnects to the player at once when the page comes back to
  the front; the pattern button also follows the player's own answer.

**The form on `main` still has dropdowns**, which GitHub never fills from a
link; the text fields reach users when the release carrying them is merged.

## Amended 2026-10-18: two states on the screen (George)

George, reviewing how screens and sound cards are marked: *"Let's also
simplify a bit the way we display tested, found etc displays"*, then, of the
proposal - two states, problems as a line, one style - *"I like the
simplification you suggest. Make it for both sound and display"*.

- **What any list shows is *Tested*, or nothing.** *Tested* beside a model
  played and measured here, **or reported working by owners** (at least one
  accepted report that it works, none against): `hardware_reports.shown_tested`.
  This reverses this record's *"Tested is never given by a report"* for what
  the lists show; the states underneath are unchanged.
- **A reported problem is a line under the model** (`hardware_reports.problem`,
  *"An owner reported a problem: <issue>"*), not a word beside it.
- **One style everywhere**: a tag beside the name - in *Attached screen*,
  *Sound card board* and *Output* alike. An output's name no longer carries its
  state after a dash ("SMSL USB DAC — Detected" is "SMSL USB DAC"); a choice
  stored the old way is rewritten once (settings migration 10) and still
  resolves before that.
- *Keep this screen?*'s untested line, setup's Screen step and the table in
  `docs/HARDWARE.md` follow the same rule. The *Hardware feedback* offer still
  follows what was tested here: more reports are still wanted.
- Underneath, the four states stay: *Tested*, *Reported*, *Reported with
  problems*, *Known* / *Untested* / *Detected* - in the hardware report, the
  logs and `hardware_reports.json`.
