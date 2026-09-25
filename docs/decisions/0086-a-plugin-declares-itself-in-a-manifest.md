# ADR-0086 — A plugin declares itself in a manifest

**Status:** Accepted
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
