# ADR-0089 — Arbitration carries a plugin renderer

**Status:** Proposed — the first work of Phase 11, and the thing
`docs/PLUGIN-CONTRACT.md` names first in its own open list. Nothing is built
yet.
**Date:** 2026-09-25
**Raised by:** George, 2026-09-25: *"start 11, with the aim as having plexamp as
the new renderer as a plugin."* Phase 10 closed with the renderer half of the
contract **never having been spoken by a renderer**, and this is what makes it
speakable.
**Relates to:** [0010](0010-arbitration-slot-model.md) (the slot model and the
release ladder this has to obey), [0084](0084-plugins-speak-json-lines-over-a-unix-socket.md)
(the socket the commands ride on), [0086](0086-a-plugin-declares-itself-in-a-manifest.md)
(the manifest, which already names the unit),
[0013](0013-defaults-implement-public-contract.md) as amended (the three
defaults are the contract's source, not its consumers),
[0077](0077-a-source-that-is-off-is-not-running.md) (a source that is off does
not take the device), [0027](0027-lms-power-as-arbitration-mechanism.md)
(acquisition is deliberate, not a stream starting)

## Context

A `renderer` that connects today is welcomed, logged, and **left idle**:

```python
logger.info("plugins: %s is a renderer and arbitration does not carry plugins "
            "yet - it is connected and idle", session.id)
```

Everything either side of the gap exists. `docs/PLUGIN-CONTRACT.md` specifies
both directions in full — `acquire`, `release`, `available`, `metadata`,
`queue`, `volume` inbound; `release`, `signal_stop`, `device_freed`,
`restart_after_release`, `activate`, `transport`, `set_volume` outbound — and
`Adapter` is an abstract class with exactly those methods. **What is missing is
one object**: an `Adapter` whose implementation is "send that message on this
session", registered with the supervisor.

Three things about the existing machinery shape it, and none of them are
negotiable:

- **`Supervisor` takes its adapters at construction** and raises `ValueError`
  for an id it does not know. A plugin arrives minutes later and can leave at
  any moment.
- **`Adapter.run(on_acquire, on_release)` is a long-running watch.** A plugin
  adapter watches nothing: its events arrive on a socket someone else is
  already reading.
- **The release ladder is the core's clock, not the renderer's.** `release()`
  returning True means *the renderer's API confirmed the action*, never that
  the device is free — the core checks that with `alsa.device_busy`, and for
  Plexamp the two are **fourteen seconds** apart
  ([Finding 077](../findings/077-plexamp-on-gexis.md)).

## Decision

**A `PluginAdapter`, constructed from a session, registered with the supervisor
while that session lives.**

### 1. The supervisor gains `register` and `unregister`

Its adapter map stops being fixed at construction. Everything else about it is
unchanged: the lock, the ladder, the ADR-0077 gate, `device_busy`.

**A duplicate id is refused, not replaced.** A second connection claiming a
renderer that is already registered loses; ADR-0084's handshake already refuses
a second session for one plugin id, so this is the same rule stated where the
consequence would be worst.

### 2. `run()` parks; the socket is the watch

`run(on_acquire, on_release)` stores the two callbacks and waits until
cancelled. The plugin's `acquire` and `release` lines, arriving through
`PluginServer.on_event`, call them. This is the same shape the three built-ins
have — an event source calling `on_acquire` — with the event source being a
socket rather than D-Bus, a WebSocket or a poll.

**`on_acquire` is not "the plugin started playing".** ADR-0027's rule is
unchanged and belongs to the plugin: a deliberate acquisition. The contract
already says so.

### 3. The manifest owns the unit, not the handshake

`hello` may carry `unit`, and **the manifest's value wins**; a `hello` that
disagrees is refused with that reason. The release ladder attributes a
still-busy device to a unit (`alsa.device_held_by`), and a renderer that could
name its own unit at runtime could point the escalation at any process on the
device.

**Two statements of one fact is the failure this session already had twice** —
a synthesised switch defaulting to `True` beside a unit the image installs
disabled ([Finding 079](../findings/079-what-the-plugin-contract-carries-to-a-unit.md)).
The manifest is on disk, installed with the plugin, and readable whether or not
it is running. That is the copy to keep.

### 4. A disconnected plugin is still escalatable, and that is the point

`release()` on a dead session raises `PluginGone`. The ladder reads that as a
polite stop that did not work — which it is — and proceeds to `signal_stop`,
**which the core performs itself against the unit the manifest names**. A
plugin cannot strand the device by dying, because the step that actually frees
it never needed the plugin's cooperation.

This is why `signal_stop` is a command *and* a core-side action. A plugin that
has something useful to do there may do it; the core does not depend on it.

### 5. What a disconnect means, and what it does not

On disconnect the adapter is unregistered, the renderer is marked
**unavailable**, and if it was active the supervisor is told it relinquished.

**A plugin disconnecting is not the same as its renderer stopping**, and this
is the honest limit of the design: if the plugin process dies while its
renderer keeps playing, the core believes nobody holds the device while
something does. It self-corrects at the next acquisition — `device_held_by`
still attributes the device to the unit, so the ladder escalates against it —
but between those two moments the published state is wrong. **Written down
rather than engineered around**: the alternative is the core polling the device
to second-guess its own model, which is a bigger mechanism than the failure.

### 6. Declared timing, declared capabilities

`release_ladder` and `capabilities` come from `hello` and are validated the way
a manifest's settings rows are — refused with a reason, not silently defaulted.
**Plexamp needs the ladder override**: 14 s of hold after a stop its own API
confirms instantly, against a default sized for go-librespot's sub-100 ms.

A `hello` the core cannot parse refuses the session. A renderer whose
capabilities are wrong is worse than one that never connected: it would be
offered on the panel, chosen, and then fail to do what it said.

## Consequences

- **The contract's renderer half becomes exercisable**, which is the
  precondition for Phase 10's criterion 2 and therefore for freezing v1.
- **`Supervisor`'s adapter map becomes mutable**, which is new surface on the
  one object where a mistake costs the audio device. Its own tests grow: a
  registration during a takeover, a disconnect during a release, and a
  duplicate id.
- **ADR-0013's amendment holds.** The three defaults keep their own adapters
  and are not ported; this adds a fourth kind of adapter beside them rather
  than replacing anything.
- **`_run_renderer`'s ADR-0077 gate needs no plugin case.** Switching a plugin
  off stops its unit, the session drops, and the adapter unregisters — the gate
  arrives by the same door the plugin left through. The supervisor's `enabled`
  predicate must answer for plugin ids, which is a one-line change and easy to
  forget: **a plugin renderer whose row is off must be refused even if it is
  somehow still connected.**
- **Nothing here makes Plexamp work.** It makes a plugin renderer possible; what
  Plexamp does with it is the rest of Phase 11, in its own repository.
