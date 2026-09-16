# ADR-0035 — Settings: one registry in the daemon, a generic API, wired one setting at a time

**Status:** Accepted (George, 2026-09-15, with the answers below)
**Date:** 2026-09-15
**Raised by:** Phase 4 criterion 5 ([ADR-0032](0032-one-page-two-surfaces.md)), and George's
concern that settings discovered later would keep reopening the topic
**Builds on:** [ADR-0022](0022-settings.md) (inventory, application rules),
[ADR-0028](0028-ui-serving-and-command-channel.md) (REST commands, publish-only socket),
[ADR-0032](0032-one-page-two-surfaces.md) (one responsive settings component)

## Problem

ADR-0022 decided *what* settings exist and how they apply; ADR-0032 decided
the screen is one responsive component, and that the HTTP API is built to the
design's row vocabulary. Nothing decides the API. Meanwhile settings keep
appearing with each feature (idle timeout, drawer auto-hide, slider span) and
land hardcoded.

The goal: **a new setting costs one registry row plus the code that reads it,
in the same change as its feature** — never a return to "the settings work".

## Proposal

### 1. One registry, in the daemon

A single list of rows in `gexis-core`, keyed by the design's own keys
(`design/settings.md`: `idle_timeout`, `boot_volume`, …), carrying for each:
group, label, note, row type and its parameters (`options`, `min`/`max`/`unit`/`step`),
marks (`R`/`H`/`N`/`?`), default, and **whether it is wired**.

The daemon owns it because the daemon owns the values and validation. The UI
renders whatever the registry returns and hardcodes no row. ADR-0022 stays the
human record; the registry is its executable form, and a row added to one is
added to the other in the same commit.

### 2. A generic API over the seven row types

| Route | Does |
|---|---|
| `GET /settings` | groups and rows, each with its current value |
| `PUT /settings/{key}` `{value}` | validates against the row type; stores; applies |
| `POST /settings/{key}` | runs an `action` row |

Validation is per row type, not per setting. Errors come back as an HTTP
status with a message, as ADR-0028 chose for commands. A row type the design
later changes is one validator and one component, not every setting.

### 3. Unwired rows render, and refuse writes

Every inventory row appears now, as ADR-0032 requires. A row nothing reads yet
shows its current or default value and answers a write with **409, not
wired**. The UI marks it with the existing `data-unwired` convention, driven by
the registry's flag — so the list of unwired settings is generated, like the
rest of the shell.

**Wiring a setting** = the feature's code reads it from the store, and its
row's flag flips. Done in the same change as the feature, then panel-tested
like any other step.

### 4. Values: the store overrides `core.toml`

Precedence, highest first: a stored value, the flash-time seed (§4b),
`core.toml`, the registry default.

`core.toml` (deployment, provisioning) supplies a setting's default; the
SQLite store (`settings.py`, built in Phase 3) holds what a user changed, and
wins. Clearing a stored value falls back to `core.toml`. This keeps the
provisioning route (`idle_url`, time zone on the card) working after settings
exist.

### 4b. Settings can be seeded at flash time

**Added 2026-09-16, George's request:** `make provision` writes
`SETTINGS` — JSON keyed by the settings screen's own keys — into the card's
`firstrun.sh`, which drops it at `/etc/gexis/settings-seed.json` on first
boot. The daemon treats the seed as a **default**, above `core.toml` and the
registry default and below anything the user later changes, so a reflash
restores the chosen starting point without freezing it.

The seed is hand-written, so every entry is validated against the registry at
startup and a bad one is dropped with a log line — an unknown key or an
out-of-range value must not stop the daemon. `make provision` also refuses
invalid JSON, because the alternative is discovering it on a booted device.

### 5. Other surfaces learn of a change through `/state`

`/state` gains a `settings_revision` counter, bumped on every write. A client
refetches `GET /settings` when it moves. The socket stays publish-only
(ADR-0028), and a change on the phone appears on the panel without the whole
settings payload riding every playback broadcast.

### 6. Which surface is asking: the daemon says

`GET /surface` returns whether the request came from loopback (the panel) or
the LAN (a remote browser). Settles ADR-0032's open question on the more
reliable of its two candidates — source address, verified in the access log
2026-09-14 — without templating the served page.

### 7. Application, unchanged from ADR-0022

Toggles, choices and numbers apply immediately; text rows commit explicitly;
anything changing audible behaviour mid-playback confirms and defers. Carried
per row as a flag.

## Row types (Claude Design, relayed by George, 2026-09-15)

Build against the six settable types plus `group`. Two refinements:

- **`number` requires `min` and `max`.** The design renders a stepper for an
  unbounded number, but no row is unbounded, so the API rejects a `number` row
  without bounds rather than carrying an unexercised path.
- **`bt_trusted` and `plugins` are navigation, not commands.** Typed `action`
  in the design, each is really a list with per-item removal. They stay
  unwired and are revisited when one is designed — as its own screen (no new
  type) or as a seventh, list type. Not guessed now.

`text` rows have no input on the panel (ADR-0029: no on-screen keyboard); on
a remote browser they are a native input.

## Increments (criterion 5), each panel- or phone-tested before the next

1. **Registry and screen.** Every inventory row, all unwired; the three routes,
   `settings_revision`, `/surface`; `Settings.dc.html` ported as the
   responsive component; a remote browser gets only settings.
2. **First wired settings:** idle timeout, show the drawer on external change,
   drawer auto-hide delay, and the idle URL, editable from the phone (George).
   Everything else wires with its own feature.

## Decided on the open points (George, 2026-09-15)

- **No panel entry to settings before Home exists.** The design reaches
  settings from the library root (Phase 7); until then the panel has no route
  in, and the phone is where settings are used.
- **Row types:** as above.
- **Idle URL:** editable from the phone, in increment 2.
