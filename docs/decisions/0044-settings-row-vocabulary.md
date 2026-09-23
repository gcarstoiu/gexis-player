# ADR-0044 — The settings row vocabulary grows seven mechanics, then an eighth

**Status:** Accepted — George, 2026-09-20, reviewing the second design drop
against the device: *"You should consider the list coming from the updated
design as the point of truth as of now. What is not there is a future
possibility not a must at this point."*
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

**Seven additions to the row vocabulary. Nothing else about ADR-0035 changes:
one registry, one generic API, and a row is still wired only when something
reads it.**

### 1. `list` — an eighth type, seventh settable

A row whose sheet lists items, each with an optional per-item action. Three
shapes, distinguished by `kind`:

- **`kind: "server"`** — LMS servers found by discovery. Tapping one sets the
  value. Carries `discover: true` (a searching state while it looks) and
  `manual` (a labelled escape into a text sheet for an address discovery
  cannot reach).

  **A server list therefore stores, and the other shapes do not** - decided
  while building 9d, because the two sentences above are in tension with
  "a `list` is navigation, not a value" three paragraphs down. `validate`
  draws the line inside the type: a `list` with `kind: "server"` takes a
  non-empty address like a `text` row, and any other `list` raises
  `NotSettable`. The alternative - a separate route for choosing a server -
  would have made the one row whose whole purpose is to hold an address the
  only list that cannot.
- **`kind: "network"`** — Wi-Fi: name, meta, a `Forget` per item, signal
  bars, and a locked state that opens a password sheet.
- **`kind: "device"`** — Bluetooth: name, meta, and a `Forget` per item.

  **Named 2026-09-21, in 9f.** Both were "no `kind`" until then, which
  worked for `validate` — it asks only whether a row is a server — and not
  for anything that has to say something about the shape in front of it.
  The searching state fell through to Wi-Fi's words, so the Bluetooth sheet
  said *"Looking for networks / The adapter sweeps every channel"*. A
  branch with no case for what it is given is a branch that answers wrongly
  rather than not at all.

**Amended 2026-09-21, in 9f: `discover` decides whether the sheet waits.**
The three shapes above say what a list *is*; this says when its items
arrive, which is the part that is visible on the panel.

- **`discover: true`** — the items are looked for when the sheet opens, and
  the sheet says so while it looks. LMS discovery listens for 2.5 s and a
  Wi-Fi scan takes seconds; a sheet that sat blank that long would read as
  broken. **`wifi` carries the flag now**: it always searched, and only the
  server row said so.
- **no `discover`** — the items are one cheap local read, so they arrive
  **with the row** in `/settings` and the sheet opens already drawn.
  `bt_trusted`'s are a single BlueZ `GetManagedObjects`: 22–29 ms measured
  on the device over five runs, which was never a wait and was still three
  frames of spinner, because the sheet began in its searching state whatever
  the answer cost. The sheet refreshes behind the drawn list, so a device
  forgotten from the phone does not linger.

  **The row needs the items anyway.** A device list's value is a count of
  them, and a row that counted only what the *sheet* fetches reads "None"
  until someone opens it — which is what it did on the device with a phone
  paired (George, 2026-09-21).

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

**Amended 2026-09-22: `warn` is also a plain string, and then it is about
the row.** The drop gives `device_name` one. The difference is when it is
shown: an object waits for its option, a string is up the whole time the
sheet is open, because what it describes happens whatever is typed. A string
is only allowed on a row that takes a value, since a row with no sheet has
nowhere to show it.

**The `device_name` warning is worded for this device, not as the drop
writes it.** The drop says *"Saving restarts the services that carry the
name. Anything playing stops."* On this device it does not:
[ADR-0048](0048-how-the-device-name-reaches-four-services.md) writes all four
and applies none until the next restart, deliberately, so a device that is
playing keeps playing. The mechanic is the design's; the sentence has to
match what happens, or the warning is the thing that is wrong.

### 3. `onlyWhen` — conditional visibility

`onlyWhen: [key, value]` hides a row unless that key holds that value, with an
`ANY` sentinel for "holds anything non-empty". **Rows are removed from the
list, not disabled** — a disabled row invites a tap that cannot work.

The test is transitive: a row whose dependency is itself hidden is hidden too.
At the drop's defaults, 7 of the 21 Display rows are hidden.

**Amended 2026-09-21, in 9g: `onlyWhen: [key, {"not": value}]`.** George,
asking for background brightness: *"a setting for background brightness that
can apply to all background types except black"*. Three of the four
backgrounds is not a value a row can be equal to.

**A negation rather than a list of the three that do apply.** The list is
right today and silently wrong the day a fifth background is added - the new
background would have no brightness control and nothing would say why. The
negation says the thing that is actually true: everything except black,
because black is not a picture.

An object rather than another string sentinel, because a setting's value is
always a scalar and so cannot be mistaken for one. The load rejects an
object with any other key: a typo in `not` would read as "not equal to
nothing", which is every value, which is a row that never hides.

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

### 5a. `grouped` — a choice taken in two steps

**Added 2026-09-20, after George found the time zone row unusable on the
panel.** It was missed when this record was written: the drop's `tz: true`
was read as a fixture of its demo rather than as a mechanic, and six were
counted where there are seven.

A choice whose options are `Region/Place` is offered a region at a time. The
sheet's title becomes the region, Cancel becomes Back, and the second tap
sets the value — the drop's own two short lists instead of one long one.

**And the list is the system's, not a curated one.** The drop names about
thirty-five zones; `zoneinfo.available_timezones()` gives 486 on this image,
and a user outside a curated list cannot set their clock at all. `grouped` is
what makes the full set navigable, which is the whole reason to prefer it.

`timezone` is wired here too: `timedatectl set-timezone`, which moves
`/etc/localtime`. The row had three options and no effect before.

### 6. `surfaced` — inventoried but not shown

**Added 2026-09-20, from George's ruling on the 20 rows the drop drops.**
Asked whether their absence was a decision or an omission, George: *"decisions.
They should still be kept on a list, but not used at this point in the
settings screen."*

So ADR-0022's inventory does not shrink from 54 rows to 49. It keeps all of
them and the *screen* shows the design's 49. A row carries `surfaced: false`
when it is catalogued but not offered.

**The registry cannot express this today.** Its rows carry `accent, confirm,
danger, default, key, label, marks, max, min, navigation, note, options, step,
type, unit` - nothing about visibility - and `Settings.svelte` renders
`current?.rows` without filtering. This is the same mechanism `onlyWhen` needs,
and the same rule applies: **the API still publishes the row, the panel
filters.** The difference is only that `surfaced` is permanent and `onlyWhen`
is conditional.

**Where the rule runs, settled in 9d.** Both tests are transitive and one of
them is cycle-sensitive, so writing the recursion twice - once in Python for
the phone's sake and once in JavaScript - would mean two chances to get it
wrong and one place to test it. `Settings.to_json` computes it and publishes
`visible` on every row; the panel filters on that and does nothing else. The
row still travels in full, which is what ADR-0022's catalogue needs, and a
client that wants the whole inventory still has it.

**A category with no visible row is not drawn either.** All six System rows
are `surfaced: false`, so the registry's seven groups become the design's six
without the group list being touched.

Rejected: **omitting them from the registry entirely.** The registry is the
executable form of ADR-0022's inventory, and an inventory that silently drops
what it decided not to build stops being a record of the decisions.

### 7. `multi` — a choice that takes more than one

**Added 2026-09-21, in 9g**, for `wallpaper_topics`: which Pixabay categories
the idle screen draws its wallpapers from. George: *"the photos should come
randomly from all the categories, not be stuck in only one of the many"* —
which needs a row that holds a **set**, and nothing in this vocabulary held
one. `choice` holds exactly one; a row per category would be twenty toggles
in a screen that is already long.

**It is `choice` with the radio replaced.** Same sheet, same option rows,
same selection background, one behavioural difference: tapping toggles rather
than replaces, and the sheet stays open because there is no single answer
that ends it. The row reads out the names it holds — `Nature, Animals +2` —
because a count alone ("4 topics") hides the thing the row exists to show.

**The rules, all of which the validator enforces:**

- the value is a **list of strings**, every one of them in `options`;
- **stored in the registry's option order, not tap order**, so the readout is
  stable and two devices with the same selection say the same thing;
- **no duplicates**;
- **never empty.** An empty set is not a weaker selection, it is a broken
  screen: no category means no picture. The last selected item cannot be
  turned off, which the sheet shows by refusing the tap rather than by
  accepting it and failing on the write.

**Rejected: a `list` row with selectable items.** A `list` is navigation with
a per-item *action* (ADR-0044 §1) and its items come from the world — a scan,
a discovery, a bus. A `multi`'s options are a fixed literal in the registry,
known before anything is asked. Reusing `list` would have meant one type
whose items sometimes mean "go here" and sometimes mean "this is the value",
which is the confusion §1 already had to settle once for `kind: "server"`.

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

- **`settings_registry.py` grows two types and three row-level modifiers**,
  and its validator has to reject a `list` given a scalar, a `multi` given
  anything but a non-empty list of known options, an `onlyWhen` naming a key
  that does not exist, and an `optionsFrom` naming an unknown source.
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

- ~~**Where a `list`'s items come from.**~~ **Closed for two of the three,
  2026-09-20**, after George found the lists empty on the panel and no
  subphase owning them: *"or we append 9d and do both now."*
  - **Wi-Fi** is NetworkManager through `nmcli` (`wifi.py`). The daemon is
    root on this image, so there is no polkit agent to answer. A scan names
    each network connected / saved / secured / open, and joining, failing and
    forgetting are real. **`-t` output is escaped, not split-able** — a
    network called `2:1` would be cut in half by `split(":")` — and **a saved
    connection is not named after its network**: this image's is called
    `preconfigured`, so SSIDs are matched through
    `802-11-wireless.ssid`, not through the connection's name.
  - **Lyrion servers** answer a UDP broadcast on 3483 (`discovery.py`). The
    protocol was verified against the real server rather than read: the reply
    carries `NAME`, `JSON`, `VERS`, `UUID` as tag + length + value, and
    **`IPAD` comes back absent, so the address is the datagram's source** —
    which is the interface that can reach us, and the one worth connecting
    to. Choosing one stores it; **the switch happens at the next start**,
    because moving a running daemon means dropping a CometD subscription,
    re-resolving the player and re-arbitrating. The panel says so.
  - **Bluetooth's trusted devices are still 9f's.** That row opens on its own
    empty state, which is true, rather than on an error.
  - **`Forget` is drawn for a saved network and never for the one in use.**
    Forgetting the network the device is reachable over drops the daemon with
    it, quite possibly from the phone on that same network. The design draws
    it on both.
- **`optionsFrom` and `picker` have no row until 9h.** Both are implemented
  on the panel and validated in the registry, and the only row that uses them
  is `skin`, which needs the corpus path and the thumbnails that are 9h's
  work. Until then they are exercised by tests and by nothing on screen.
- ~~**Whether `warn` should also gate the confirm button** rather than only
  colouring the sheet.~~ **Closed 2026-09-20, in 9d: it gates.** §2 above
  already says the warning is shown *"before it is confirmed"*, and the
  design's own comment says the same - but the drop's code writes the value
  on the tap and closes, so the warning can only ever appear on a later
  visit, after the amplifier is already at 100%. A warning that arrives after
  the consequence is decoration. **Tapping a warned option now selects it
  without writing**, the warning appears, and a Confirm commits it; tapping
  the stored option again lets go of the selection. Every unwarned option
  still writes on the tap, as before. Recorded here rather than assumed:
  George has not ruled on it, and reverting it is one branch in `choose()`.
- **What `optionsFrom` sources exist** beyond `skin_corpus` and `timezones`.
  Both resolve in `Settings.to_json`, so the panel never learns where a
  corpus lives; `skin_corpus` resolves to an empty list until 9h gives it
  one, which draws the row and offers nothing rather than pretending.
- ~~**Whether the panel needs an on-screen keyboard.**~~ **Closed
  2026-09-20**, and it was closed before — George: *"mentioned several times
  that there is no difference for input between the panel and the phone ... We
  assume the user can connect a keyboard to the panel if the desire is to
  change things there, otherwise the phone is the way."* It is not to be
  raised again as a usability concern; the design's own preference for
  avoiding input fields is a separate and welcome argument.
