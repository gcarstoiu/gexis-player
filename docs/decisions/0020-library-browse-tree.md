# ADR-0020 — Library browse as a normalised tree

**Status:** Accepted
**Date:** 2026-09-04
**Establishes:** a cross-cutting rule on unusable controls — see below

## Context

"Library navigation" means the whole LMS browse tree, not a music-library
browser: My Music with all its branches, Radio, My Apps (Could tier), and
whatever plugins have added.

The architecture states the browse tree is data rather than screens — one
generic browser driven by what the server returns — and that the core normalises
LMS menu items into a source-agnostic node shape so the UI never learns LMS's
vocabulary. Artwork URLs point directly at LMS.

That rested on an assumption I flagged and had not checked: that LMS menu
responses carry enough structure to drive navigation generically.

## The assumption, verified

**It holds, and the mechanism is a documented protocol.**

SlimBrowse is the specification in which LMS menus are defined. The original
Squeezebox clients were entirely service-agnostic: they asked the server for the
main menu and drilled down from there, with no knowledge of whether a given item
was a setting or a result from a streaming service.

That is precisely the generic-browser model, and it has been in production since
the Squeezebox hardware.

### The shape

Menu items carry, among other fields:

```
icon              full or partial base URL for images
window            elements for a window opened from this item
actions           the command(s) for this item
nextWindow        where selection navigates to
setSelectedIndex
onClick
```

Actions are JSON-RPC commands:

```
player            replaced by the client
cmd               array of command terms, e.g. ['playlist', 'jump']
params            hash, passed as "key:value"
itemsParams       names the field in an item's actions that completes a
                  base-level command for that item
nextWindow        takes precedence over an item-level nextWindow
```

Two placeholder values matter: `__INPUT__` is replaced by user-entered data, and
`__TAGGEDINPUT__` by user-entered data in key:value form. **This is how search
and any other text-entry menu works.** See Q3.

### Two menu systems, not one

Worth knowing before building: LMS distinguishes **home menu items**, registered
individually by plugins via `Slim::Control::Jive::registerPluginMenu`, from
**SlimBrowse items**, delivered as full menus in response to a CLI command.
Home menu items can be promoted to the top level; SlimBrowse submenu items
cannot.

A client has to handle both.

### Warnings from people who have built this

- **It is a lot of work.** Stated plainly by developers on the LMS forums who
  have implemented it, including one who rewrote an existing browse
  implementation onto SlimBrowse and considered it worth it.
- **Affordance mapping is not fully specified.** A developer implementing it
  asked how to know when to show a play, add, or favourite control, noting these
  must presumably be derived from `base.actions` — and the protocol does not
  spell this out. See Q4.
- **Not everything is in the menu.** The same discussion raises getting extra
  track information such as duration, which the menu response does not
  obviously carry.
- **A full-featured client outgrows it.** Material Skin has added a number of
  non-standard commands of its own — for example setting a player's active
  library — which suggests SlimBrowse alone does not cover everything a rich
  client wants.
- **Input fields are a real capability clients can lack.** A current LMS plugin
  documents that one popular Android client cannot render Jive input fields, so
  its typed features appear in the menu but do not respond.

Standard JSON-RPC commands can also be issued with `menu:1` and `html:1` to
retrieve SlimBrowse-like responses, which is a middle path some clients use.

---

## Resolved

### SlimBrowse is the internal browse protocol

**Adopted as-is.** The core passes SlimBrowse through rather than translating it
into a shape of our own.

*Rationale:* it is already service-agnostic by design and has been in production
since the Squeezebox hardware. Defining a parallel model would be reinventing a
working wheel, and any mapping would be lossy — plugin menus using constructs our
shape had not anticipated would degrade or break.

**Accepted cost:** we take on another project's vocabulary and its quirks,
including the two menu systems and the unspecified affordance mapping.

**Consequence for Qobuz navigation:** the Should-tier Qobuz browser cannot simply
be expressed in this model without thought. Either Qobuz menus are shaped into
SlimBrowse form by an adapter, or a second browse path exists. **That is deferred
and will need its own record.** The architecture's claim that a normalised model
makes Qobuz navigation cheap is weaker under this decision than it was written.

### Full SlimBrowse, not a curated subset

**Every menu the server returns is rendered.**

*Rationale, having examined where the work actually is:* curated does not save
what it appears to save. To hide an unsupported item rather than show it broken,
the client must first **recognise** it — so recognition is implemented either
way. The only saving is in rendering item types already identified, which is the
smaller half. Curated additionally costs a permanent judgement about what is in
and out, plus a hiding mechanism that full mode does not need.

#### Where the work is

Not in parsing — the JSON is straightforward, and localised text comes from the
server, so there is no internationalisation work either. The work is:

- **Item and window types.** Plain items, choice items, radio and checkbox items
  that refresh in place on selection, items carrying input fields, items with
  context menus behind them. Each needs a control and a behaviour.
- **The `base.actions` / `itemsParams` indirection.** Commands are defined once
  at the base level of a menu, and `itemsParams` names the field in each item's
  actions that completes that command for that item. Dispatch is a two-level
  lookup, not a direct read.
- **`nextWindow` precedence.** A command-level `nextWindow` overrides an
  item-level one; `setSelectedIndex` without a `nextWindow` implies a refresh.
- **Window layouts**, specified by the `window` field.
- **Pagination.** An artists list is thousands of items.

*Scope of that assessment:* read from protocol summaries, not a full
specification read. There may be more.

### No search on the touchscreen; browse only

Text-bearing menu items are not operable on the panel. Search is available from
remote browsers, which have real keyboards.

This upholds ADR-0022 rather than amending it. No on-screen keyboard is built.

### Actions map to controls through a lookup table

**Known command names map to known controls. Unknown actions are surfaced in a
context menu rather than as primary controls.**

*Rationale:* the protocol supplies commands but does not specify which control to
draw — a developer implementing it asked precisely this, and concluded the
mapping must be derived from `base.actions`. A purely generic derivation would
work for unknown plugins but could produce controls whose meaning is unclear to
the user. A table gives a predictable interface for the common cases and a
sensible fallback for the rest.

---

## The cross-cutting rule this record establishes

Three records now address controls the user cannot operate, and they appear to
disagree. They do not, once the distinction is stated:

> **If the capability does not exist, hide it. If it exists but cannot be
> operated here, show it and say where it can be.**

| Case | Record | Behaviour | Why |
|---|---|---|---|
| Volume slider in fixed output mode | ADR-0018 | **hidden** | there is no volume control on this device in that mode — the capability is absent |
| Settings text field on the panel | ADR-0022 | **shown, not editable**, with where to change it | the value exists and matters; only editing is elsewhere |
| Search item on the panel | this record | **shown, not editable** | same |

A search item hidden on the panel would leave the user unable to see that their
library is searchable at all. A greyed volume slider would imply a volume control
that does not exist.

ADR-0014's wording — "hidden or greyed" — should be read through this rule.

## Settled by the architecture

- **The core proxies the browse tree; artwork URLs point directly at LMS.**
  Artwork is the heavy part and LMS already has a caching image resizer. It
  degrades gracefully if unreachable.
- **List data is cached aggressively in RAM**, consistent with spending the
  hardware on responsiveness.
- **CometD for push, JSON-RPC for calls.** Polling would visibly lag on track
  changes.

## Unverified

- Whether track duration and similar detail are available through menu responses
  or require separate queries — this determines how many round trips a track
  list costs.
- What `menu:1, html:1` on standard commands returns compared with a true
  SlimBrowse request, and whether the middle path is worth taking.
- Whether the browse tree can be cached across sessions or must be re-fetched,
  since it is server-generated and player-specific in places.
- How Radio and My Apps differ structurally from My Music, if at all.
