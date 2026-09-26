# ADR-0092 — A play queue this renderer has not seen is an acquisition

**Status:** **Accepted and built**, 2026-09-26 — George, given two shapes for the
fix: *"Go for the second."* Built and measured the same day: **Plexamp took the
device from a playing LMS 0.55 s after the controller's request**, where before it
never took it at all. **George then tried it from his phone, which is the path
none of the measurements could reach: *"Seems to work."*** Deployed by hand to
`gexis`; the image stage is pinned to `v0.2.1`, which **still has to be
published** - see HANDOFF.
**Date:** 2026-09-26
**Raised by:** George, 2026-09-26: *"Cannot takeover with plexamp. The plexamp
mobile app fails to playback."*
**Relates to:** [0027](0027-lms-power-as-arbitration-mechanism.md) (what an
acquisition *is*, which this extends for one renderer),
[0089](0089-arbitration-carries-a-plugin-renderer.md) (`device_freed`, the hook
this uses), [0091](0091-a-plugin-renderer-is-taken-off-the-device.md) (the
release side, and the session this surfaced in),
[0037](0037-transport-commands.md) (a control is
declared or refused — the 409 found on the way here; the core's own comment cites
ADR-0020 for this rule, which is the library browse tree, so it is wrong there)
**Evidence:** [Finding 090](../findings/090-a-refused-play-is-an-acquisition.md)

## Context

**Plexamp could not take the audio device from a renderer that was holding it.**
Not slowly — at all. Reproduced against LMS as well as Spotify, so it is nothing
to do with either of them:

```
pcm RUNNING, held by squeezelite
playMedia -> 200
pcm RUNNING, held by squeezelite      <- Plexamp never started
the core saw no plexamp acquire at all
```

The cause is a circle. **Plexamp has to open the ALSA device in order to start
playing**, and the plugin's only evidence of an acquisition is *the timeline
turning `playing`* — so while another renderer holds the device, playback cannot
start, nothing reports an acquisition, and the core is never asked to arbitrate.
Each condition waits on the other.

This predates ADR-0091 and is not caused by it — every commit there is on the
release path — and it had never been measured. [Finding
085](../findings/085-the-takeover-gaps-and-the-controls.md) recorded
*"LMS → Plexamp, 0.2 s, five times"*, but its own scope says playback was started
by API calls and it lists Spotify and Bluetooth as needing a phone. Those five
takeovers were from an LMS that had **already let go** of the device — powered on
in the core's model while squeezelite had released it via `-C 1`. **A takeover
from a renderer that actually held the device was never tested.**

## Decision

### 1. A play queue the plugin has not seen before is a deliberate act

ADR-0027 says an acquisition is a deliberate act rather than a stream starting.
For this renderer the deliberate act has been *playback beginning*, which is the
one thing a busy device makes impossible. **A controller pointing this player at
a play queue is the same deliberate act, one step earlier**, and unlike playback
it is visible whether or not the device is free.

So: **a timeline carrying a `playQueueID` the plugin has not already seen is an
acquisition**, and the plugin reports it as one.

### 2. It is visible, on the channel the plugin already watches

Finding 090 measured it. The player publishes the refused attempt on its own
timeline, and the plugin's existing `wait=1` long poll returns on the change:

```
t+0.14s  {'state': 'error', 'playQueueID': '2930', 'key': '/library/metadata/91795',
          'containerKey': '/playQueues/2930', 'machineIdentifier': '…',
          'address': '192-168-178-191.….plex.direct', 'port': '32400', …}
t+0.19s  {'state': 'stopped'}
```

**Everything needed to issue the play again is in that timeline** — key,
container key, server identity and address. It is visible for about 50 ms, which
is why this is keyed to the change-driven long poll and not to a sampling
interval: a 150 ms sampler missed it entirely while this was being investigated
(`docs/LESSONS.md` 42's trap, again).

### 3. The refused play is re-issued when the device is free, not retried blindly

The core already has the hook. `device_freed` exists to *"give the incoming
renderer a chance to retry its own acquisition now that the device is confirmed
free"* (ADR-0089, Finding 014) and this plugin has answered it with a no-op
since it was written, on the grounds that it does not retry. **It does now.**

So the order becomes: new queue → `acquire` → the core releases the holder →
`device_freed` → the plugin issues `playMedia` again with what the timeline gave
it. **No contract change**: every message used here is already in v1.

**A plain `/player/playback/play` is not enough, measured.** With the device free
again it answered 200 and nothing played, because the queue went with the error.
The re-issue has to carry the parameters.

### 4. Only when the state is not `stopped`

A queue on its own is not intent. Plexamp persists a play queue across restarts,
so a clean start can surface a `playQueueID` with nothing happening, and treating
that as an acquisition would have the panel switch renderers because a process
started. The states this acts on are the ones that mean a controller just did
something — `error`, `playing`, `buffering`, `paused` — and **not** `stopped`.

## Rejected alternatives

- **Keying on `state == "error"` instead of on the queue.** The first of the two
  shapes offered, and the one George did not pick. It catches exactly this case
  and nothing else, but it acts on a symptom: `error` will have other causes — a
  missing file, a server that has gone — and each would become a spurious
  takeover request. The queue is the thing that actually carries the intent.
- **A plain `play` on `device_freed`.** Measured insufficient, §3.
- **Having the core free the device speculatively**, on any sign of interest.
  That is a renderer taking the device without a deliberate act, which is the
  thing ADR-0027 exists to prevent.
- **Changing what an acquisition means for every renderer.** This is one
  renderer's own evidence about its own controller, which is exactly what the
  plugin contract puts on the plugin's side of the line. Nothing in the core
  changes.
- **Leaving it, with "stop the other renderer first" as the workaround.** It is
  the current behaviour and George's report is that it is not acceptable.

## Consequences

- **Plexamp can take the device from a renderer that holds it**, which it never
  could. Measured, with squeezelite playing:

  ```
  t+0.13s  pcm RUNNING, held by squeezelite
  t+0.33s  pcm closed,  held by nobody
  t+0.55s  pcm RUNNING, held by node          <- Plexamp

  17:09:16,212  plexamp was asked for play queue 2931 and could not start - asking for the device
  17:09:16,220  acquire: plexamp takes the device (was lms)
  17:09:16,447  release[lms]: polite stop freed the device (0.2s)
  17:09:16,448  the device is free; playing what was refused
  ```

  **236 ms** from the plugin noticing to the play being issued again.
- **The uncontended path is unchanged**, checked because this could have double-
  played: with the device free, one acquire, no "could not start", no re-issue,
  playing 0.54 s after the request. ADR-0091's release still escalates, 1.36 s
  from the outside.
- **The acquisition arrives earlier than playback** on the ordinary path too —
  the queue is published before the first sample — so the panel switches a
  fraction sooner. Not the point, but not nothing.
- **A failed play now costs a takeover.** If Plexamp fails for a reason that is
  not contention, the plugin will still have asked for the device and the core
  will still have released whoever had it. The device ends up held by a renderer
  that cannot play, until something else asks. **This is the cost of keying on
  intent rather than on the error**, and it is the trade George chose.
- **`activate` is declared now** (found on the way here: the plugin implemented
  it from the first version and never declared it, so the core refused with 409 —
  correctly, on what it had been told). That is a separate, smaller fix; it gives
  the panel a path but not the phone's. **Declaring it also made a latent bug
  reachable**: `activate` called Plexamp's `playPause` *toggle*, which would have
  paused a player that was already going. Fixed in the same breath with an
  explicit play.
- **This does not fix the panel switching when a phone merely *selects* the
  player.** Nothing reaches the player on selection — established in five places
  in Finding 088 — and a queue only exists once somebody presses play.

## Reversal conditions

- **A `playQueueID` that changes without a controller doing anything** — an
  auto-advance that renumbers the queue, or a Plexamp release that reuses the
  field differently — would make this fire on its own. Track changes move
  `playQueueItemID` and leave `playQueueID` alone today, which is what makes the
  trigger stable.
- **If the re-issued play turns out to be unreliable**, the honest fallback is
  the rejected first shape plus a bounded retry, not a blind loop.
