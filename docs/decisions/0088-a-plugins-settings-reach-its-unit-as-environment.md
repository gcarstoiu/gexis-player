# ADR-0088 — A plugin's settings reach its unit as environment

**Status:** **Accepted and built**, 2026-09-25, and **amended the same day on the
device** — the restart gate was `is-active` and had to become `is-enabled`; see
the decision below. The mechanism
[ADR-0087](0087-the-beszel-agent-is-the-first-service-plugin.md) needs, drawn
generically because a Beszel-shaped answer would fail Phase 10 criterion 2's
*"no changes to the core"* the first time a second service plugin arrived.
**Date:** 2026-09-25
**Raised by:** George, 2026-09-25: *"When enabled fields appear that allow keys
to be provided."* The fields are ADR-0044's; how what is typed into them reaches
the process is not settled anywhere.
**Relates to:** [0086](0086-a-plugin-declares-itself-in-a-manifest.md) (the
manifest this adds one field to), [0084](0084-plugins-speak-json-lines-over-a-unix-socket.md)
(the channel this deliberately does not use),
[0048](0048-how-the-device-name-reaches-four-services.md) (the same trick, for
one value, already in the image), [0044](0044-settings-row-vocabulary.md)
(`onlyWhen`, `secret`), [0083](0083-a-backup-leaves-the-device.md) (what the
backup has to carry once a plugin has an identity)

## Context

ADR-0084 gives a plugin a Unix socket and a line protocol, and that is the right
channel for a plugin written against this contract. **The Beszel agent will never
speak it.** It is a third-party binary; so is Plexamp; so is anything else worth
plugging in that already exists. A contract that can only configure programs
written for it is, again, *"a renderer API wearing a plugin's name"*.

So the question is narrow: a value is typed into a settings row, and a process
this device starts needs it. Three ways were available.

- **Through the socket.** Requires the plugin to be ours. Rejected: it is the
  case ADR-0084 already covers, and the one that does not need solving.
- **A config file per plugin, rendered by the core.** How `go-librespot`'s
  `config.yml` and `squeezelite`'s flags already work — but each of those is
  hand-written core code that knows one program's format. Generalising it means
  the core learning YAML, INI, TOML and whatever the next plugin wants. Rejected.
- **An environment file the unit reads.** Every service manager already has
  this, systemd's `EnvironmentFile=` is one line in a unit, and **the image
  already does exactly this for one value**: ADR-0048 writes
  `GEXIS_DEVICE_NAME=` to `/etc/gexis/device-name.env` and
  `squeezelite.service` reads it. It is format-free — a name and a string — so
  the core never learns anything about the program it is configuring.

## Decision

**A manifest row may name an environment variable, and the core exports every
such row to one file per plugin.**

```json
{ "key": "token", "type": "text", "secret": true, "env": "TOKEN",
  "onlyWhen": ["enabled", true] }
```

- **`/run/gexis/plugins/<id>.env`**, mode `0600`, written by the daemon. In
  `/run` and not `/etc`: it is derived state, it holds secrets, and a reflash or
  a reboot should rebuild it from the store rather than leave a stale copy of a
  credential on disk.
- **Written before the unit is started, and again whenever one of those rows
  changes** — then the unit is restarted **if it is enabled**, because environment
  is read once at exec. A row change with the plugin switched off writes the file
  and starts nothing.

  **Amended the same day, on the device.** This first read *"if it is active"*,
  implemented as `systemctl try-restart`, and it was wrong in the case this plugin
  exists for: the agent is switched on before anything has been typed into it —
  the fields only appear once it is on — so it refuses to start and sits in
  `failed`. `try-restart` does nothing to a failed unit, so the token arrived and
  nothing read it until the next reboot. `is-enabled` is the honest gate: enabled
  means somebody asked for this to run. `reset-failed` runs first, because a unit
  that spent its `StartLimitBurst` while unconfigured is the expected path here
  ([Finding 079](../findings/079-what-the-plugin-contract-carries-to-a-unit.md)).
- **A row with no value is omitted entirely**, not written empty: an unset
  variable and one set to the empty string are different to most programs, and
  the honest statement is *not configured*.
- **Values are quoted for systemd's `EnvironmentFile` syntax**, because they are
  not safe: the hub's public key is `ssh-ed25519 AAAA… comment`, with spaces.
  Double quotes, with `\\` and `"` escaped; a value containing a newline is
  refused and logged, because no `EnvironmentFile` line can carry one and
  silently truncating a credential is worse than not writing it.
- **`onlyWhen` inside a manifest names the plugin's own rows**, and the merge
  prefixes it exactly as it prefixes `key`. A manifest writes
  `onlyWhen: ["enabled", true]`; the registry holds
  `["beszel.enabled", true]`. Unconditional, rather than "prefix it unless it
  looks like a core key": a plugin that could depend on a core row would be
  coupled to a registry it does not ship with, and the failure would arrive the
  day a core key was renamed.

## Consequences

- **The contract gains one manifest field and the core gains no per-plugin
  code.** `plugin.json` is still the whole of what a service plugin is.
- **`docs/PLUGIN-CONTRACT.md` moves to describing this**, and v1 still cannot be
  frozen until it does — which is the second time criterion 3's plugin has
  changed the contract before criterion 1 could close it, and the argument for
  building it in that order.
- **A unit written against this is portable.** `EnvironmentFile=-/run/gexis/
  plugins/<id>.env`, with the `-` so a plugin whose rows are all empty still
  starts.
- **Secrets are in one more place**, and not a worse one: `/run` is tmpfs, mode
  `0600`, and ADR-0083 already records that `GET /settings` serves the same
  values in plaintext to anyone on the LAN. The file is not the exposure.
- **The values are not validated.** A wrong token is a plugin that fails to
  connect and says so in its own journal, not something the core can catch. The
  screen will show the plugin enabled and the hub will not show the system,
  which is a diagnosis a person can make and the daemon cannot.
