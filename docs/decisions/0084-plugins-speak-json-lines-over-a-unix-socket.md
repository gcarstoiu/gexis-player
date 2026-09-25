# ADR-0084 — Plugins speak JSON lines over a Unix socket

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0016](0016-plugins-as-separate-processes.md) (separate
processes with an IPC contract — this is that contract's carrier),
[ADR-0013](0013-defaults-implement-public-contract.md) as amended (the
defaults are the contract's source, not its consumers),
[ADR-0028](0028-ui-serving-and-command-channel.md) (the LAN is unauthenticated
by decision, and this is deliberately not on it), Phase 10 criterion 1

## Context

ADR-0016 chose separate processes and an IPC contract, and named the reasons:
fault isolation, language independence, and a plugin that can live in another
repository. It did not choose what the processes say to each other.

The surface is not in question — it is **derived** from the three defaults,
which ADR-0013 makes their job:

- **core → plugin:** `run`, `release`, `signal_stop(force)`; optionally
  `device_freed`, `restart_after_release`, `activate`, `set_volume` /
  `get_volume`, and whichever transport commands the plugin declares.
- **plugin → core:** `on_acquire`, `on_release`, `on_metadata_change`,
  `on_queue_change`, `on_availability_change`, `on_volume_change`.
- **declared once:** `renderer_id`, `release_action`, `unit_name`,
  `release_ladder`, and `Capabilities`' nine fields.

## Decision

**A Unix domain socket at `/run/gexis/plugins.sock`, carrying
line-delimited JSON. The core listens; plugins connect.**

- One JSON object per line, `\n`-terminated. No length prefix, no envelope
  beyond the object itself.
- A plugin's **first line declares it**: the contract version it speaks, its
  renderer id, and everything in the "declared once" list above.
- The core answers with the version it will hold the plugin to, or closes the
  connection with a reason.
- **The contract is versioned** from the first line onwards, because ADR-0016
  says it must be: plugins in other repositories will lag the core.

## Rationale

### Why a Unix socket and not a port

ADR-0028 leaves the command API unauthenticated on the LAN, and ADR-0049
reasoned from it that a guest share is the same class of exposure. **This is
not the same class.** The plugin channel declares renderers, raises
acquisition events and takes release commands — a thing that can claim the
audio device and lie about what is playing. Putting that on a port means
either an authentication story this project does not have, or a genuinely new
exposure to justify.

A filesystem socket makes the answer boring: **the permission on the socket is
the authorisation**. Nothing on the network can reach it, and nothing has to
be invented.

It also costs nothing that matters. ADR-0016 said separate *processes*, not
separate machines, and no plugin this project has planned — Plexamp, Qobuz, a
Beszel agent — runs anywhere but here.

### Why JSON lines

**Language independence is the whole reason for the contract** (ADR-0016), and
JSON is the format every language already reads. No schema compiler, no
generated stubs, no build step a plugin author has to adopt before writing a
line of code.

And it is legible. A contract that can be watched with `socat - UNIX-CONNECT:`
and read on screen is one that can be debugged from a report; `docs/LESSONS.md`
is largely a record of instruments that were harder to trust than the thing
they measured.

### Rejected: D-Bus

The strongest alternative, and already a dependency — `dbus-next` is how
Bluetooth works here. Rejected on the same ground it was chosen for elsewhere:
BlueZ's object model is worth binding to because BlueZ *is* an object model.
Ours is a stream of events and a handful of commands, which D-Bus expresses
through interfaces, properties and signals that a plugin author has to learn
and a plugin in a private repository has to find a binding for. It makes the
contract harder to write against in exchange for structure this contract does
not need.

### Rejected: HTTP or a WebSocket on loopback

Considered because the core already serves aiohttp, so it is nearly free.
Rejected because a port invites the LAN question that the socket answers by
construction, and because "loopback only" is a configuration promise rather
than a property — one `--host 0.0.0.0` away from being wrong, and nothing
would notice.

### Rejected: a binary framing (protobuf, msgpack, CBOR)

Faster and smaller, and neither matters: this channel carries a track change,
not audio. Each costs a compiler or a library in every language a plugin might
be written in, which is exactly the tax ADR-0016 chose separate processes to
avoid.

### Why the core listens

Plugins come and go; the core is the fixed point, and a single well-known path
means a plugin needs to know one thing to connect. It also keeps **discovery**
— which plugins exist, and how they get started — a separate problem from
**transport**, which is what this record is. They are settled separately and
on purpose.

## Consequences

- **A plugin runs on this device.** Remote plugins are not possible and are
  not wanted; if that ever changes, this record is what changes with it.
- **The socket's permissions are the security model.** They have to be right,
  and they are one thing rather than a protocol.
- A plugin can be written in a shell script with `socat`, which is a fair test
  of whether the contract is as simple as it claims.

## What this does not settle

- **The schema.** What the lines actually say, field by field, is the contract
  document Phase 10 criterion 1 asks for. This record says only how it travels.
- **Discovery and lifecycle.** How the core learns a plugin exists, who starts
  it, what happens when it stops answering. ADR-0016 listed lifecycle as its
  own open consequence and it still is.
- **Whether the defaults ever move onto it.** ADR-0013 as amended says they do
  not, and that the guard against drift is a test rather than a shared path.
