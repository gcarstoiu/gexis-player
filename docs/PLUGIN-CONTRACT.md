# The Gexis plugin contract

**Version:** `1` — **draft, not frozen.**
**Status:** derived from the three default renderers, per
[ADR-0013](decisions/0013-defaults-implement-public-contract.md) as amended.
**Carried by:** a Unix socket at `/run/gexis/plugins.sock`, one JSON object per
line ([ADR-0084](decisions/0084-plugins-speak-json-lines-over-a-unix-socket.md)).

> **Why it is still a draft.** Phase 10 required a non-renderer built against
> this before freezing — *"if the contract cannot express that, it is a renderer
> API wearing a plugin's name."* **The Beszel agent was that test and it passed,
> having first forced two amendments**: every plugin gets a switch (ADR-0086),
> and a plugin's settings reach its unit as environment (ADR-0088).
>
> **The freeze moved to Phase 11 with criterion 2**, because the *renderer* half
> of this document has never been spoken by a renderer. Freezing it here would
> freeze a protocol nothing has used, which is the same mistake in the other
> direction. Everything about a `service` is settled; everything about a
> `renderer` is provisional until Plexamp has used it.

## What this is, and what it is not

**It is derived, not designed.** Every field comes from something LMS, Spotify
or Bluetooth already does; nothing is here because it seemed useful.
`core/tests/test_contract_surface.py` pins that surface so this document and
`adapters/base.py` cannot drift apart in silence — which matters, because the
defaults **do not speak this protocol**. They are its source, not its
consumers (ADR-0013 as amended).

**It is not a renderer API.** A plugin may be a renderer, or it may be
something with no metadata, no transport and no claim on the audio device.
Both use the same handshake; a renderer simply declares more.

## Transport

- **Socket:** `/run/gexis/plugins.sock`, Unix domain, stream.
- **Framing:** one JSON object per line, `\n`-terminated, UTF-8. No length
  prefix, no envelope.
- **Direction:** the core listens, the plugin connects. A plugin may reconnect
  freely; the core treats a closed connection as the plugin being gone.
- **Ordering:** messages are processed in the order they arrive on a
  connection. Nothing is assumed about ordering *between* connections.

Every message has a `t` (type). Everything else depends on `t`.

## The handshake

**The plugin speaks first.** Its first line declares what it is:

```json
{"t": "hello", "contract": 1, "id": "plexamp", "kind": "renderer",
 "name": "Plexamp",
 "unit": "plexamp.service",
 "release_action": "disconnect",
 "capabilities": {
   "audio_connection": "output",
   "acquisition_events": ["playback-started"],
   "supports_artwork": true,
   "supports_sample_rate": true,
   "volume_managed": true,
   "volume_mechanism": "software_api",
   "dummy_mixer_card": null,
   "volume_over_bluealsa": false,
   "controls": ["play", "pause", "next", "previous", "repeat", "shuffle"]
 },
 "release_ladder": {"polite_grace": 1.0, "sigterm_grace": 2.0, "sigkill_grace": 2.0}}
```

The core answers, handing over the current value of every setting the plugin
declared:

```json
{"t": "welcome", "contract": 1, "settings": {"hub": "http://beszel.local:8090"}}
```

**Keys are the plugin's own**, without the `<id>.` prefix the registry stores
them under — a plugin declares `hub` and is told `hub`. It is handed them at
`welcome` because **its rows outlive its process**: somebody can change one
while it is stopped, and it has to come up on the answer rather than on its
own default.

or refuses and closes, saying why:

```json
{"t": "refused", "reason": "contract 2 is not served here"}
```

### Versioning

`contract` is an integer and the plugin states the version **it** speaks. The
core accepts a version it can serve and refuses otherwise, with a reason. It
never guesses and never silently downgrades — ADR-0016's own consequence is
that *"plugins in other repositories will lag the core"*, and a plugin that
gets a quiet partial service is worse than one that gets a clear refusal.

**Within a version, fields are added and never removed or repurposed.** A
plugin ignores fields it does not know.

### `kind`

| `kind` | means | must declare |
|---|---|---|
| `renderer` | plays audio and takes part in arbitration (ADR-0010) | `unit`, `release_action`, `capabilities` |
| `service` | anything else — a monitoring agent, a scheduled job | `unit` only |

**A `service` declares no capabilities and receives no arbitration.** This
split is the point of the whole exercise: if a Beszel agent cannot be
expressed as a `hello` with `kind: "service"` and nothing else, the contract
is wrong.

## Declaration fields

Taken from `Adapter` and `Capabilities` as they are. The prose for each is in
`core/src/gexis_core/adapters/base.py`, which is the authority.

| field | type | notes |
|---|---|---|
| `id` | string | The renderer id. Unique; the core refuses a duplicate |
| `unit` | string | The systemd unit whose process opens the device. The release ladder attributes a still-busy device to it (`alsa.device_held_by`) |
| `release_action` | `pause` \| `disconnect` | ADR-0010/0027 |
| `release_ladder` | object, optional | Per-renderer override. **Plexamp needs one** — its device is not free for 14 s after a polite stop ([Finding 077](findings/077-plexamp-on-gexis.md)) |
| `capabilities.audio_connection` | string | `output` for everything today (ADR-0009) |
| `capabilities.acquisition_events` | array of strings | The *names* of what this renderer treats as taking the device, so an accountability UI has something to point at |
| `capabilities.supports_artwork` | bool | Whether it can ever supply one, not whether this track has one |
| `capabilities.supports_sample_rate` | bool | As above |
| `capabilities.volume_managed` | bool | Whether a remembered level is restored on acquisition |
| `capabilities.volume_mechanism` | `dummy_mixer` \| `software_api` | ADR-0053 |
| `capabilities.dummy_mixer_card` | string or null | Only for `dummy_mixer` |
| `capabilities.volume_over_bluealsa` | bool | ADR-0054 §1 |
| `capabilities.controls` | array | Subset of `play`, `pause`, `next`, `previous`, `repeat`, `shuffle`, plus `activate` |

## Plugin → core

```json
{"t": "acquire"}
{"t": "release"}
{"t": "available", "available": true}
{"t": "metadata", "metadata": { … }}
{"t": "queue", "queue": [ … ]}
{"t": "volume", "value": 62, "steps": 100}
```

- **`acquire`** — a deliberate acquisition (ADR-0010's table as amended by
  ADR-0027), not a stream starting. The core may refuse it silently: a
  renderer whose row is off does not take the device (ADR-0077).
- **`release`** — this renderer gave the device up with nobody taking over.
  **Safe to send at any time**: the core ignores it unless this renderer is
  currently active, which is what makes the echo of a commanded release
  harmless.
- **`metadata`** — fields from `TrackMetadata`; every one optional, absent is
  absent and draws nothing. `track_id`, `title`, `artist`, `album`, `year`,
  `artwork`, `artwork_small`, `sample_rate`, `codec`, `position`, `duration`,
  `transport`, `source_type`, `shuffle`, `repeat`, `unavailable`.
- **`queue`** — only a renderer that has one (ADR-0038 §5). Others send a
  stream and no queue.

## Core → plugin

```json
{"t": "release", "id": 7}
{"t": "signal_stop", "id": 8, "force": false}
{"t": "device_freed", "id": 9}
{"t": "restart_after_release", "id": 10}
{"t": "activate", "id": 11}
{"t": "transport", "id": 12, "command": "pause", "argument": null}
{"t": "set_volume", "id": 13, "value": 62, "steps": 100}
{"t": "setting", "id": 14, "key": "hub", "value": "http://beszel.local:8090"}
```

Each carries an `id`; the plugin answers exactly once:

```json
{"t": "ok", "id": 7, "result": true}
{"t": "error", "id": 7, "message": "…"}
```

- **`release`** is the *polite* stop through the renderer's own control
  channel. `result: true` means its API confirmed the action — **not** that
  the device is free. The core checks that separately, and for Plexamp the
  two are fourteen seconds apart.
- **`signal_stop`** is process-level escalation, `force` being SIGKILL rather
  than SIGTERM. A plugin that has nothing to do here may answer `true`; the
  core also has the unit name and can act itself.
- **`device_freed`** and **`restart_after_release`** are the two hooks that
  exist because of measured races, not design (Findings 013 §1 and 014).
  Default: do nothing, answer `true`.
- **`setting`** is one of the plugin's own rows being changed, under the key
  the plugin declared. **The core stores the value whether or not the plugin
  is connected**, so one that is down misses nothing: it is handed every
  current value at `welcome`.

### A plugin's own settings

A manifest may carry `settings`, and those rows are merged into the registry
(ADR-0086). **Their keys are prefixed with the plugin's id** — a plugin
declaring `enabled` is stored as `plexamp.enabled` — because two plugins
shipping the same obvious key would otherwise collide and the second would be
refused. On the wire the prefix is not used: a plugin says and hears its own
key.

**Every plugin also gets an `Enabled` toggle it did not declare**, wired to
its `unit` — because a plugin nobody can switch off is what
`docs/DEVELOPMENT.md` calls a renderer API wearing a plugin's name. `enabled`
is therefore the core's key: a plugin shipping its own is ignored and keeps
its other rows. A manifest may name an existing row instead with
`enabled_row`, which is how the three built-ins keep the keys they have always
had.

A renderer's rows land in **Sources**, under a sub-heading carrying its name,
which is the shape the three built-ins already have. A service's land in
**System**, same shape. Rows that fail the registry's own validation are dropped
with the reason logged rather than taking the device down: one badly packaged
plugin must not cost the others.

**A row may hide behind another with `onlyWhen`** (ADR-0044's vocabulary), and
**it names your rows, not the core's**: the key is prefixed exactly as `key` is,
so `["enabled", true]` becomes `["<id>.enabled", true]` and means *"only when
this plugin is switched on"*. A manifest cannot make a row depend on a core
setting — that would couple it to a registry it does not ship with — and one
that tries has all its rows dropped, because the row it named does not exist.

### A row may name an environment variable

**ADR-0088.** For the case that matters most in practice: the program being
configured is not yours, will never connect to this socket, and reads its
configuration from the environment like most daemons do.

```json
{ "key": "token", "type": "text", "secret": true, "env": "TOKEN",
  "onlyWhen": ["enabled", true] }
```

- Every row with an `env` is exported to **`/run/gexis/plugins/<id>.env`**, mode
  `0600`, in systemd's `EnvironmentFile` syntax. Your unit reads it with
  `EnvironmentFile=-/run/gexis/plugins/<id>.env` — the `-` so a plugin with
  nothing set still starts.
- **The file is written before your unit is started**, and again whenever one of
  those values changes; the unit is then restarted **if it is enabled** — whatever
  state its process is in. Enabled means somebody asked for it to run, and a
  plugin switched on before it was configured is sitting in `failed` *because*
  the value just typed was missing. A value changed while the plugin is switched
  **off** writes the file and starts nothing.
- **A value nobody has given writes no line at all**, so the variable is unset
  rather than empty. `false` *is* written, because a toggle that is off is a
  decision.
- Values are quoted, so spaces, `"` and `\` are safe — the case that forced it
  is an SSH public key. A value containing a newline is refused and logged, since
  no `EnvironmentFile` line can carry one.
- The variable name must match `[A-Za-z_][A-Za-z0-9_]*`. A manifest naming
  anything else is refused outright, because a credential that silently never
  reaches your process is the hardest kind of broken to find.

**This is not encryption.** The values are in the settings store and `GET
/settings` serves them to the same LAN, which
[ADR-0083](decisions/0083-a-backup-leaves-the-device.md) states outright.
`secret: true` masks a row on the panel and nothing more.

## Deliberately not here yet

- ~~**Who starts a plugin.**~~ **Answered for a plugin that is a unit**, which
  every plugin is today: it declares one in its manifest, the core gives it a
  switch, and the switch is `systemctl enable/disable --now`
  ([ADR-0086](decisions/0086-a-plugin-declares-itself-in-a-manifest.md) as
  amended). Its settings reach it before it starts
  ([ADR-0088](decisions/0088-a-plugins-settings-reach-its-unit-as-environment.md)).
  **Discovery is settled too**: a plugin ships `plugin.json` under
  `/usr/share/gexis/plugins/<id>/`, and its id must match one before it may
  connect. Connecting says a plugin is *running*, not that it exists.

  **What is still open is who puts it there.** Every plugin so far arrives in
  the image ([ADR-0087](decisions/0087-the-beszel-agent-is-the-first-service-plugin.md),
  George's call), and nothing installs one on a running device: that needs a
  writable plugin directory, a checksummed download and a rule about who may
  ask. ADR-0016's lifecycle consequence survives as *installation*, not as
  *starting*.
- ~~**Arbitration for a plugin renderer.**~~ **Built**
  ([ADR-0089](decisions/0089-arbitration-carries-a-plugin-renderer.md)): a
  `renderer` that connects gets an adapter built around its session and
  registered with the supervisor, and its `acquire` and `release` reach
  arbitration the way the three built-ins' events do. **Not yet exercised by a
  real renderer** — that is Phase 11's Plexamp, and until it has happened this
  document stays a draft.

  Three things worth knowing before writing one:

  - **Your `hello` is validated and a bad one costs you the connection**, with
    the reason on the wire. A renderer registered with wrong capabilities would
    be offered on the panel, chosen, and then fail to do what it said.
  - **The manifest owns your unit name.** You may repeat it in `hello`; you may
    not disagree with it.
  - **`signal_stop` is a command and a core-side action**, not either/or. You
    are told first, and the core then acts on your unit regardless — so
    disconnecting cannot strand the audio device, and answering `true` without
    doing anything does not fool the ladder.
- **Authentication.** The socket's permissions are the model (ADR-0084).
- **Anything about themes.** ADR-0016 lists them as plugins and a theme has no
  process; Phase 14 settles that before anything is built.
