# Finding 089 — The takeover after ADR-0091

**Date:** 2026-09-26
**Question:** ADR-0091 was accepted with its own number unmeasured — *"Takeover
should cost about 0.7 s… **to be measured, not assumed**; the number above is
arithmetic on two separate measurements."* This is the measurement, plus the one
risk the decision argues away rather than tests: the restart storm.
**Scope:** `gexis`. The four changed files **deployed by hand**, not built into
an image: `arbitration.py` and `adapters/plugin.py` copied into
`/opt/gexis-core/venv/.../gexis_core`, the plugin's `main.py` into
`/opt/gexis-plexamp/src`, and the stage's `plexamp.service` installed over the
hand-written one the device had been running. Plexamp headless 4.13.2. Every
takeover driven by the core's own `POST /renderer/lms/activate` — **no phone in
the loop**, so nothing here says what a phone displays. **George's regression
pass has not been run.** Seven takeovers in one direction only, plexamp → lms.

## The number: 0.9 s, from 14 s

The ladder's own log, which since this change names the rung rather than a signal
it no longer chooses:

```
16:08:36.909  acquire: lms takes the device (was plexamp)
16:08:37.675  release[plexamp]: still holds the device after polite stop, signalling it
16:08:37.818  release[plexamp]: freed after the first signal (0.9s)
16:08:38.353  plugins: plexamp connected (renderer)
```

| | |
|---|---|
| `release()` round trip + the declared 0.5 s polite grace | **766 ms** |
| the signal, to the device reading `closed` | **143 ms** (Finding 077 measured 169 ms) |
| **the ladder's total** | **0.9 s** |
| the same thing from outside, timed from the `activate` POST | **1.34–1.48 s** across seven takeovers |

The two differ by the `activate` round trip and LMS powering its player on, which
are not this renderer's cost. **0.9 s is the number comparable to the 12.6–14.2 s
of [Finding 085](085-the-takeover-gaps-and-the-controls.md).**

## It comes back on its own, and the pair comes with it

`plexamp.service` went `NRestarts 1 → 2` on the first takeover and one per
takeover after that, each time with a new `MainPID` and `Result=signal`. On the
unit the image now ships (`RestartSec=1`) the player answered `/resources` again
**4.04 s** after the takeover; on the 100 ms default the hand-written unit had it
was **2.8–3.0 s**. The plugin reconnected to the core **462 ms** after its
disconnect, and the core re-registered the renderer:

```
16:08:37.891  plugins: plexamp disconnected
16:08:38.352  plugins: plexamp is a renderer and arbitration carries it
```

**ADR-0090's "one switch controls the pair" worked for the first time today.**
Stopping the player now stops the plugin and starting it starts both — it never
did before, because `Wants=` was under `[Service]`, where systemd's answer is
*"Unknown key 'Wants' in section [Service], ignoring."*

## The storm did not happen

[Finding 013 §1](013-phase2c-attack-test-and-spotify-reliability-defects.md) is
the reason this design needed testing rather than arguing: two attempts to stop
and restart a renderer around a release were shipped and reverted within a day
each, because the restarted process raced a still-busy device and burned through
`StartLimitBurst` on systemd's own clock until the unit stayed failed.

**Six back-to-back takeovers**, each holding the device four seconds and then
losing it, with no settling beyond what the device needed:

```
round 1  device freed 1.38s   plexamp n=2   squeezelite n=0  plugin n=0  core n=0
round 2  device freed 1.37s   plexamp n=3   squeezelite n=0  plugin n=0  core n=0
round 3  device freed 1.48s   plexamp n=4   squeezelite n=0  plugin n=0  core n=0
round 4  device freed 1.34s   plexamp n=5   squeezelite n=0  plugin n=0  core n=0
round 5  device freed 1.42s   plexamp n=6   squeezelite n=0  plugin n=0  core n=0
round 6  device freed 1.42s   plexamp n=7   squeezelite n=0  plugin n=0  core n=0
```

**One takeover, one restart, nothing failed.** The mechanism that made it a storm
for squeezelite is absent: a restarted Plexamp does not open the ALSA device
until it is told to play, so there is no failed-open to retry.

Separately, **eight `SIGKILL`s a second apart produced four restarts** — a kill
landing inside `RestartSec` is a no-op against a unit that is already restarting
— and the unit stayed `active/running`, `Result=success`. Four is comfortable
against the burst of 20 the unit now carries and uncomfortably close to the 5 it
had, which is why it was raised.

## Correction: plex.tv presence does not flip, and should not

[Finding 088 §2](088-making-plexamp-behave-like-the-other-renderers.md) measured
plex.tv's `presence` going True → False within ≤10.5 s of the unit stopping, and
**ADR-0091's consequences used that to claim the stale "connected" clears on its
own. That claim is wrong**, and this is the correction: with
`Restart=on-failure` the player is back in about a second, far inside the
timeout, so `presence` stays `True` throughout a takeover. Measured immediately
after one.

That is the right behaviour — a player you cannot see is a player you cannot cast
back to — and it means the thing that actually changes is elsewhere:

| what a controller reads | after a takeover |
|---|---|
| plex.tv `presence` | **`True`** — still listed, still castable |
| PMS `/status/sessions` | **`size=0`** — the session is gone |
| the player's own timeline | **`state="stopped" time="0"`**, no play queue |

So the player ends up exactly where squeezelite ends up when something takes the
device from it: present, idle, holding nothing. **Whether a phone's own chrome
stops saying "connected" on the strength of that is not measured here** — there
was no phone in the loop — and it is George's to observe.

## What this does not establish

- **One direction.** Every takeover was plexamp → lms. The reverse, and takeovers
  involving Spotify or Bluetooth, are unmeasured.
- **No phone.** Every acquisition was `playMedia` from this session and every
  takeover was the core's `activate` endpoint. The complaint that started this
  work is about what a phone shows, and that is unobserved.
- **Not from an image.** Files were copied onto a running device; the image still
  pins the plugin at `v0.2.0` by checksum, so **nothing measured here is in a
  build**. Shipping it needs a plugin release and a stage bump.
- **Seven takeovers, not a distribution.** No percentiles, and nothing about
  behaviour over hours. Finding 013 §1's recurrence appeared *two hours* into
  ordinary use, after 35 clean scripted rounds — six rounds is not evidence
  against that, only against the immediate version of it.
- **Nothing about audio.** Whether the handover is audibly cleaner, or whether a
  killed player clicks, was not listened for.
