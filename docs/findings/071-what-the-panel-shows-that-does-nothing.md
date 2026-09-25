# Finding 071 — What the panel shows that does nothing

**Date:** 2026-09-25
**Question:** Phase 9 criterion 2 — *no unwired UI remains, or each survivor
is explicitly justified.* What is left?
**Scope:** `ui/src` at `phase-8-plan`, every `.svelte` file, plus the running
daemon's `/settings` and its route table. **Four generated lists, not an
audit**, which is what the criterion asks for: it is the backstop for a
control nobody revisited, and it "should ideally find nothing". It found one
thing, and that thing was the check itself.

## 1. The marker was lying about two rows

Settings marks a row `data-unwired` when the daemon reports `wired: false`.
Two rows reported that and work: **`wifi` joins a network and `bt_trusted`
forgets a device**, both through `POST /settings/{key}/items` (ADR-0044 §1)
rather than through `set`. The registry's flag only ever knew about `set`.

Those two were already noted as exceptions in
[Finding 068](068-what-is-left-unwired-in-settings.md) — *"not on the list
after all"* — and carried as a footnote a reader had to remember. **A generated
list with two standing false positives is not a check**: the next person either
chases two non-problems or learns to skip the list.

`Settings` now takes a `lists={...}` declaration, and a row in it reports
itself wired. **Declared, not inferred from `type == "list"`** — a future list
row with no handler behind it must still report itself unwired. Writing is
unaffected: `set` refuses a list row with `NotSettable`, which it did before
and does regardless of the declaration.

**After: of 74 rows, no visible row is marked unwired.**

## 2. Seventeen controls that can be disabled, none of them unwired

Every `<button>`, `<input>` and `<select>` in the UI that is not plainly
wired-and-enabled. All seventeen carry a real handler and a *conditional*
`disabled` — "cannot work right now", which ADR-0037 §3 requires rather than
forbids, and which the design dims.

| where | disabled when | why that is not unwired |
|---|---|---|
| Now Playing: previous, next, shuffle, repeat | the renderer does not declare that control | ADR-0037: a renderer declares what it can do, and Bluetooth declares less than LMS |
| Now Playing: volume | fixed output | ADR-0046: the padlock says so, and the drawer still opens to explain |
| Now Playing: artist | the track has no artist | nothing to open |
| Mini strip: volume | fixed output | as above |
| Library: jump rail letter | that letter has no artists | the key is drawn for the alphabet's shape |
| Pairing: accept, reject | an answer is in flight | stops a double answer |
| Settings: a readonly row | always | it takes no tap and draws no chevron by design |
| Settings: the current skin's Use | it is already current | |
| Settings: sheet buttons, option rows | a save is in flight | |

## 3. Nothing offers a callback nobody supplies

The shape [ADR-0079](../decisions/0079-with-lms-off-the-panel-is-two-screens.md)
fixed by hand — Now Playing called `onartist?.(...)` and, with LMS off, nothing
passed one, so a link led nowhere. Asked for every component at once:
**0 optional callbacks are called that no parent ever supplies.** Also 0 empty
handlers, and 0 clickable `div`/`span` elements without a button role.

## 4. Nothing points at a route that is gone

Every path the UI fetches, against every route the daemon registers:
**20 distinct paths, 33 routes, all matched.** No control is still wired to a
feature that was removed underneath it.

## What this did not check

- **A control that works and arrives somewhere empty.** A tab that renders
  nothing, a sheet with no content. Static analysis cannot see it and the
  screen-by-screen review is criterion 3's job.
- **Gestures.** Swipe-to-remove on the queue rail, the drawer's drag, the
  jump rail's scrub are not elements and are not in these lists.
- **The visualiser.** PeppyMeter is another process with its own surface.
- **The phone.** It renders Settings only, from the same registry, so §1
  covers it; nothing else on it was looked at.
- **Whether every *enabled* control does what its label says.** These lists
  answer "is something attached", not "is it the right thing".
