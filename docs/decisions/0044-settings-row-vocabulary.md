# ADR-0044 — The settings row vocabulary grows five mechanics

**Status:** Proposed — awaiting George
**Date:** 2026-09-20
**Raised by:** the 2026-09-19 design drop, reviewed in
[Finding 040](../findings/040-the-design-drop-and-what-it-changes.md)
**Amends:** [ADR-0035](0035-settings-api.md) (one registry, a generic API, one
setting wired at a time) and [ADR-0022](0022-settings.md)'s inventory
**Settles:** [ADR-0029](0029-text-entry-on-every-surface.md)'s open question
about on-screen keyboards

## Context

ADR-0035 gave settings seven row types — `toggle`, `choice`, `number`,
`text`, `readonly`, `action`, `group` — and a registry that is the executable
form of ADR-0022's inventory. Every row since has fitted that vocabulary.

The new design does not. It needs a row that lists discovered things, a choice
that warns about one of its options, rows that appear only when another row
holds a particular value, options that come from a corpus rather than a
literal list, and a picker too large for a sheet. **Nearly every new row in
the drop depends on at least one of these**, so they cannot be taken one at a
time behind the features that want them.

## Decision

**Five additions to the row vocabulary. Nothing else about ADR-0035 changes:
one registry, one generic API, and a row is still wired only when something
reads it.**

### 1. `list` — an eighth type, seventh settable

A row whose sheet lists items, each with an optional per-item action. Two
shapes today, distinguished by `kind`:

- **`kind: "server"`** — LMS servers found by discovery. Tapping one sets the
  value. Carries `discover: true` (a searching state while it looks) and
  `manual` (a labelled escape into a text sheet for an address discovery
  cannot reach).
- **no `kind`** — Wi-Fi networks and Bluetooth devices: name, meta, and a
  `Forget` action per item. Wi-Fi items add signal bars and a locked state
  that opens a password sheet.

**A `list` is navigation, not a value**, which is what `action` rows with
`navigation: true` were standing in for. Those rows can never be "wired" under
ADR-0035's definition — `settings_registry.py` raises `NotWired` for them
unconditionally — and this replaces that dead end with a type that means what
it does.

### 2. `warn` on a choice option

A per-option warning shown when that option is selected and before it is
confirmed. One use today: choosing Fixed output warns that the signal leaves
at 100% before the user commits.

**A choice can now hold back a consequence until it is chosen.** That is worth
having exactly where a wrong tap is loud and irreversible, and nowhere else.

### 3. `onlyWhen` — conditional visibility

`onlyWhen: [key, value]` hides a row unless that key holds that value, with an
`ANY` sentinel for "holds anything non-empty". **Rows are removed from the
list, not disabled** — a disabled row invites a tap that cannot work.

The test is transitive: a row whose dependency is itself hidden is hidden too.
At the drop's defaults, 7 of the 21 Display rows are hidden.

### 4. `optionsFrom` — options derived from real data

A choice whose options come from a named source rather than a literal list.
One use: the skin picker's options are the corpus, 71 or 84 entries depending
on `skin_corpus`.

**The stored value is the real name** (`06G5_McIntosh`); only the display
splits off the ordinal. When the corpus narrows and the stored value is no
longer in it, the row shows the first available skin — **and this record
requires the store to be rewritten too**, rather than left holding an orphan
that reappears if the corpus widens again. The design is ambiguous here; this
is the choice.

### 5. `picker` — a full-screen chooser

For a choice too large for a 560px sheet. One use: 84 skins in a four-across
grid of tiles. Thumbnails are placeholders until skin previews exist.

### And text rows take real input

**There is no difference between the panel and the phone.** A text row renders
an `<input>` on both, with `secret` masking a stored value as bullets and a
`placeholder` where one helps.

**No on-screen keyboard, ever.** George, repeatedly and again on 2026-09-20:
*"No difference between panel and phone. If the user wants to change anything
on the panel he needs a keyboard."* ADR-0029 left this open by saying the
panel "may need" one; it does not. A panel with no keyboard attached can read
every setting and change every one that is not text.

## Consequences

- **`settings_registry.py` grows a type and three row-level modifiers**, and
  its validator has to reject a `list` given a scalar, an `onlyWhen` naming a
  key that does not exist, and an `optionsFrom` naming an unknown source.
- **`navigation: true` disappears** along with the `NotWired` branch that
  served it. `plugins` is removed by the drop; `bt_trusted` and `wifi` become
  lists.
- **Conditional rows change what "wired" means for a phone**: a hidden row is
  not a missing row, and the API still publishes it. The panel filters.
- **Wi-Fi joining becomes a settings flow**, which is the first time Settings
  performs an action with a failure state rather than storing a value.

## Alternatives considered

- **Take them one at a time, behind the features that want them.** This is the
  project's normal rule and it does not work here: six new rows need `list`,
  eleven need `onlyWhen`, and building those features first would mean
  building them twice.
- **Keep `action` + `navigation` for lists.** Rejected: that pairing is
  already a dead end in the code, and a sub-screen that can never be wired is
  a row that can never be finished.
- **Disable conditional rows rather than hiding them.** Rejected on the same
  grounds ADR-0037 gives for transport controls: a control that cannot work
  now is only worth showing when the user can tell why.

## Open

- **Where a `list`'s items come from.** Wi-Fi needs a scan route, Bluetooth a
  device list and a forget command, LMS a discovery mechanism. None exists.
- **Whether `warn` should also gate the confirm button** rather than only
  colouring the sheet.
- **What `optionsFrom` sources exist** beyond `skin_corpus`.
