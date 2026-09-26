# ADR-0086 — A plugin declares itself in a manifest

**Status:** Accepted, **amended the same day** — every plugin gets an
`Enabled` switch, which is the gap a Beszel agent found. See *Amendment*.
**Date:** 2026-09-25
**Relates to:** [ADR-0016](0016-plugins-as-separate-processes.md) (separate
processes; lifecycle left open), [ADR-0084](0084-plugins-speak-json-lines-over-a-unix-socket.md)
(the runtime channel, which deliberately does not settle discovery),
[ADR-0013](0013-defaults-implement-public-contract.md) as amended,
`docs/PLUGIN-CONTRACT.md`, Phase 10 criterion 2

## Context

Phase 10 criterion 2 is *"a fourth renderer built against it, in a separate
repository, **with no changes to the core**"*. ADR-0084 carries what a plugin
says once it is running. It says nothing about how the core learns a plugin
exists at all — which is most of what "no changes to the core" means.

**What a fourth renderer forces today**, counted rather than estimated:

| where | what |
|---|---|
| `__main__.py` | the `adapters` dict and `RENDERER_ROWS` |
| `metadata_file.py` | `{"lms": "Squeezelite Active", …}` — the moOde-compatible status line |
| `settings_registry.json` | its own rows, starting with `Enabled` |
| `SourceMark.svelte` | the glyph: a branch per renderer, two of them PNG imports |
| `WaitingServices.svelte` | `SERVICES` — name, status line, mark size, ring delays |
| `HandoffScreen.svelte` | `LABELS`, and the same two PNG imports |
| `WaitingHome.svelte` | `['lms', 'spotify', 'bluetooth']`, for "every source is off" |
| `NowPlaying.svelte` | `data-source`, which selects the accent colour |

**Eight places, and three of them are name maps.** The rest of the codebase's
mentions of a renderer id are not this problem and must not be dragged into
it: `providers.py` and `wsserver.py` name `lms` because LMS's *artist
information plugin* is an enrichment source; `config.py` names a pair because
[Finding 020](../findings/020-criterion8-takeover-gap-adr0027.md) measured it;
`PairingFrame` names Bluetooth because pairing is Bluetooth's. A fourth
renderer needs none of them.

## Decision

**A plugin ships a manifest, and the core scans a directory for them.**

```
/usr/share/gexis/plugins/<id>/plugin.json
/usr/share/gexis/plugins/<id>/mark.png
```

`/usr/share`, because a plugin is software installed by a package, not
configuration somebody edits.

**The manifest is the static half; `hello` is the runtime half.** The split is
not arbitrary — it is what the built-ins already have. Their capabilities are
declared at runtime because they depend on what the adapter finds; their
name, unit, glyph and settings rows are fixed at build time. A plugin gets the
same shape:

| in the manifest, read whether or not the plugin is running | in `hello`, read when it connects |
|---|---|
| `id`, `name`, `kind`, `unit` | `capabilities`, `release_action`, `release_ladder` |
| `label` — the moOde status line | |
| `accent` — a colour token for the UI | |
| `mark` — a file beside the manifest | |
| `status` — the waiting screen's line (*"Listening"*, *"Pairable"*) | |
| `settings` — rows merged into the registry | |

**The core must be able to draw a plugin it has never seen running.** Settings
has to offer its `Enabled` row before it is enabled; the waiting screen has to
name it while it waits. That is the whole reason a manifest exists rather than
just a `hello`.

**The published state carries the presentation.** `SourceMark`,
`WaitingServices`, `HandoffScreen` and `NowPlaying` stop holding a branch per
renderer and read name, accent, status and mark URL from the payload — served
at `/plugins/<id>/mark.png`. **The three built-ins are described the same
way**, by manifests this repository ships, so there is one path and not a
special case beside a general one.

## Rationale

### Why not put everything in `hello`

Because a renderer that is switched off never connects, and its row still has
to exist to be switched on. Settings is built from the registry at startup;
the waiting screen lists what is *not* playing. Both need to know about a
plugin that is not there.

### Why the built-ins get manifests too

ADR-0013 as amended says the defaults are the contract's **source** and not
its consumers, and that the guard against drift is a test rather than a shared
path. **Presentation is the exception, and deliberately so**: there is no
reason for `SourceMark` to have a branch for LMS and a generic path for
everything else, and every reason for the generic path to be the one that is
exercised on every boot. A plugin's glyph being drawn by untested code is
exactly how the first external plugin finds a hole.

### Rejected: a directory of Python modules the core imports

The obvious shape, and it is ADR-0016's rejected one: in-process modules
cannot give fault isolation or language independence, and a crashing plugin
would take playback with it.

### Rejected: registering through the socket alone, with no file

Considered because it is less machinery. Rejected on the switched-off case
above, and because it would make a plugin's settings rows appear and disappear
as it connects — a Settings screen that changes shape depending on whether a
background process is up.

### Rejected: `/etc/gexis/plugins.d/`

`/etc` is for what an administrator edits. A manifest is part of the plugin,
shipped and upgraded with it. Putting it in `/etc` would invite hand-editing
and make a package upgrade a conffile fight — the same reasoning ADR-0049
applied to samba's include.

## Amendment, 2026-09-25 — every plugin can be switched off

**Found by the thing it was meant to find.** `docs/DEVELOPMENT.md` says a
non-renderer *"only wants to be installed, started, kept running and switched
off again. If the contract cannot express that, it is a renderer API wearing a
plugin's name."* Building a Beszel agent against this record showed it could
not: a plugin could declare rows, and **nothing could stop its unit**. The
three renderers get that from a hardcoded `RENDERER_ROWS` and a renderer-only
`_apply_renderer`.

So: **every plugin gets an `Enabled` toggle it did not ask for**, wired to
ADR-0077's `set_unit_enabled` against the unit in its manifest — enabled and
started, or stopped and kept stopped, for the same reason that record gives.

- **Not something a plugin declares.** One that forgot would be one nobody
  could turn off, and the point of this is that there is no such plugin.
- **`enabled` is the core's key.** A plugin shipping its own is ignored with
  the reason logged, and keeps its other rows — dropping the whole plugin over
  one row would cost it every setting it has, and letting the plugin's win
  would leave a switch that switches nothing.
- **A manifest may name a row that already exists**, `enabled_row`. The three
  built-ins do: theirs predate this and do more than manage a unit — ADR-0077's
  `lms_enabled` also stops the adapter watching and makes arbitration refuse
  it — so they keep the keys they have always had rather than growing a second
  switch each.

## Consequences

- **The three built-ins gain manifests**, and the UI's per-renderer branches
  go. That is a change to the core made once, so that the next one is none.
- **A plugin can present itself wrongly**: a missing mark, an unreadable
  accent. The core validates what it can — the id, the unit, the settings rows
  against the registry's own vocabulary — and draws a generic glyph for the
  rest rather than refusing to start.
- **`metadata_file.py`'s label map becomes the manifest's `label`.** A fourth
  renderer gets a moOde-compatible status line for free instead of silence.

## What this does not settle

- **Who starts a plugin.** The manifest names a unit; whether the core enables
  it, whether the package does, and what happens when it stops answering is
  ADR-0016's open lifecycle question and is still open.
- **Whether a plugin may add anything but rows and a mark** — a screen, a tab,
  a visualiser. Nothing has asked.
- **Versioning of the manifest itself**, as distinct from the contract version
  in `hello`. One number until something needs two.

## Amendment, 2026-09-25 — the mark reached the payload and not the screen

**The manifest's glyph was published and almost never drawn.** `sources` carried
`"mark": "/plugins/<id>/mark"`, the daemon served it, and **only the waiting
screen passed it down** to `SourceMark`. Now Playing and the mini strip pass the
renderer's id and nothing else, and that component's branch chain has no final
`else` — so a plugin renderer drew an **empty span**.

Found with Plexamp: the payload was right, the route answered 200 with the file,
and the panel showed a blank where the mark goes.

`SourceMark` now looks the glyph up from the `sources` store when a caller does
not pass one. A caller's own value still wins — the waiting screen passes one,
and a screen that knows better than the store should not be argued with.

**Why this counts as an amendment to this record** rather than a UI bug fix:
ADR-0086's claim is *"a screen that reads this draws a renderer it has never
heard of without being edited"*. That was not true. It required every screen
drawing a mark to have been edited to pass one, and two of the three had not
been. The claim is true now because the lookup lives in the one component that
draws marks.
