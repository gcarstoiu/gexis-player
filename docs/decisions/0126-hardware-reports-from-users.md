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
