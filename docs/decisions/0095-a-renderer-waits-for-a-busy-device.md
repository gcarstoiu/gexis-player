# ADR-0095 — squeezelite waits for a busy device instead of failing

**Status:** **Accepted, amended the same day to squeezelite only** — George, 2026-09-26: *"Option A - the recommended
one for alsa"*, then *"Let's go with c"*. **Amends [ADR-0009](0009-logical-output-device.md).** Built and
measured the same day. The first build (both renderers waiting) deadlocked on a
double press and was withdrawn; **the amended build (squeezelite only) is
measured below and deployed to `gexis`.**
**Date:** 2026-09-26
**Raised by:** [Finding 091](../findings/091-play-on-a-powered-off-lms-player.md)
(LMS: 5.5 s of silence after *play* on a powered-off player) and
[ADR-0091](0091-a-plugin-renderer-is-taken-off-the-device.md)'s amendment
(go-librespot losing a busy-device race, 1 in 12, leaving the phone's progress
bar at 0:00). [ADR-0093](0093-we-do-not-build-or-patch-the-renderers.md) rules
out changing either renderer.

## Context

Both failures have the same cause, and it is not in the renderers. The kernel
already supports waiting for a busy PCM: `snd_pcm_open` without `O_NONBLOCK`
sleeps on the PCM's `open_wait` queue until the holder closes (kernel
`sound/core/pcm_native.c`). **alsa-lib turns that off by default** -
`defaults.pcm.nonblock 1` in `alsa.conf` makes the hw plugin open with
`O_NONBLOCK` even when the application asked to block, then clear the flag
afterwards (`pcm_hw.c`), precisely so a busy device fails at once.

Both renderers ask to block. Measured on `gexis` with `strace`, 2026-09-26:

```
squeezelite   openat("/dev/snd/pcmC5D0p", O_RDWR|O_NONBLOCK|O_CLOEXEC) = 30
              fcntl(30, F_SETFL, O_RDWR|O_LARGEFILE) = 0
go-librespot  openat("/dev/snd/pcmC5D0p", O_RDWR|O_NONBLOCK|O_CLOEXEC) = 107
              fcntl(107, F_SETFL, O_RDWR|O_LARGEFILE) = 0
```

`O_NONBLOCK` on the open, cleared straight after: the application's blocking
request, overridden by alsa-lib's default. squeezelite then sleeps a fixed 5 s
after the failure (`output_alsa.c`); go-librespot does not retry at all.

## Decision

**A second logical device, `output_wait`, identical to `output` except that its
hw slave has `nonblock 0`.** squeezelite (`-o output_wait`) and go-librespot
(`audio_device: output_wait`) use it. A busy device then makes their open wait in
the kernel until the renderer being released lets go, and succeed.

```
pcm.output_wait {
    type meter
    slave.pcm { type hw card <card> nonblock 0 }
    scopes.0 peppyalsa
}
```

- **`output` is unchanged and stays the contract name** (ADR-0009). Plexamp
  (through `pcm.!default`), bluealsa-aplay and any plugin keep failing fast.
  Plexamp's open mode is not determinable from its source, and bluealsa-aplay
  stops draining its FIFO while blocked; neither is moved without evidence.
- **The card is still named, never indexed.** An inline slave takes `card` by
  its string id (alsa-lib `snd_config_get_card`).
- **Bit-perfect is untouched.** `nonblock` decides only whether the open waits.
- **Both heads are written by `outputs.render()`**, the metered one and the `plug`
  one for an output that needs conversion, so the choice of output (ADR-0055)
  carries to `output_wait` as it does to `output`. `pcm.output` stays first in
  the file, because `outputs.configured()` reads the card back from the first
  slave it finds.
- **`TimeoutStopSec=10`** on `squeezelite.service` and `go-librespot.service`.
  Both install SIGTERM handlers that restart an interrupted system call, so a
  renderer waiting for the device does not exit on SIGTERM; systemd would wait
  its default 90 s before SIGKILL. SIGKILL ends the wait at once (measured below).

## Measured before building (2026-09-26, `gexis`)

A temporary PCM of exactly this shape, Plexamp holding the DAC:

| | |
|---|---|
| the open | `openat(pcmC5D0p, O_RDWR|O_CLOEXEC)` - no `O_NONBLOCK` |
| after 2 s with Plexamp holding it | still waiting, `wchan` = `snd_pcm_open` |
| Plexamp killed at +2.1 s | the open returned and `aplay` played normally |
| a waiting process sent SIGKILL | gone in 0.046 s |

## Risks, and what is done about each

1. **A waiting renderer is invisible to arbitration.** It has no file descriptor
   yet, so `device_held_by` cannot see it; it takes the device whenever the
   current holder closes. In ordinary use this is exactly the point - the core
   is releasing the holder *because* this renderer asked. A *stray* waiter (one
   the core never acquired for) would need two renderers waiting at once, and is
   measured below before anything is built against it.
2. **squeezelite's control loop stalls while it waits** - it holds its output
   mutex across the open. LMS drops a player silent for 15 s; the waits here are
   under 2 s.
3. **A stop could hang.** Answered by `TimeoutStopSec` above.
4. **Nothing in the core opens `output_wait`.** `needs_plug` probes `hw:<card>`
   directly and stays fail-fast; a blocking probe would freeze the daemon.

## Measurement plan - before it is reported as working

1. `strace`: both renderers open `output_wait` without `O_NONBLOCK`.
2. Finding 091 again: *play* on a powered-off LMS while Plexamp holds the device -
   time to audio, LMS's reported positions, no `alsa_open:360` in the log.
3. Plexamp → Spotify through go-librespot's API ×10: no `Device or resource busy`.
4. Two waiters: *play* on LMS while a Spotify load is waiting.
5. `systemctl stop` of a renderer while it waits: under `TimeoutStopSec`.
6. `aplay -D hw:<card>` on a busy card still fails at once (`needs_plug`).

## Measured after building (2026-09-26, `gexis`)

| # | check | result |
|---|---|---|
| 1 | open flags | both renderers open `output_wait` **without `O_NONBLOCK`** |
| 2 | Finding 091, *play* on a powered-off LMS, Plexamp holding | **audio at +2.2 s, from 5.5 s**; no `alsa_open` busy errors (two before). The remaining 1.45 s is LMS's status-push filter. Positions still jump (0 → 14.1 → 0 → 15.3) until the stream starts |
| 3 | Plexamp → Spotify via go-librespot's API ×10 | **10 of 10**, no busy errors, device free after each |
| 6 | `aplay -D hw:<card>` on a busy card | fails in 0.055 s - `needs_plug` cannot hang |
| 4 | **two waiters: LMS *play* and a Spotify load at the same moment** | **deadlock**, below |

**The deadlock.** Plexamp held the device; LMS's *play* and a Spotify load
arrived together, so squeezelite and go-librespot both waited. The core acquired
Spotify (`will_play` came first) and freed the device - and **the kernel gave it
to squeezelite**, whichever waiter it wakes first, not the one the core chose.
go-librespot went on waiting, and **its whole API stalls while it waits**. The
core, still inside Spotify's acquisition, was handing Spotify its volume over
that API (ADR-0054 §5 as amended) with no timeout, so it hung - holding the
arbitration lock. LMS's power-on arrived 0.4 s later and could not be acquired.
It stayed that way for **68 s**, until LMS was powered off by hand; `aiohttp`'s
default would have held it for five minutes.

Two defects, both introduced by waiting rather than failing:

1. **The core calls a renderer's API while holding the lock, without a timeout**,
   and a waiting renderer does not answer.
2. **The kernel, not the core, decides which waiter gets the device.** Risk 1
   above said this needed two waiters at once; it does, and pressing play in two
   apps within a second or two is enough.

Neither is answered here. **Nothing ships until both are.**

**Hearing LMS's power-on sooner.** The core learns of it 1.45-1.5 s after the
press, which is LMS's own status-push filter; with this record, that delay is
most of what remains of Finding 091's gap. A plain CometD subscription or the
CLI's `listen` would report it at once. A separate change, after this one is
measured.

## Measured 2026-09-29: why neither obvious way stops LMS resuming at boot

After a restart LMS carried on playing (George: *"I was expecting it paused"*).
The core pauses a player the Lyrion server resumed, at its first start after a
boot (ADR-0022's [H] row "Playback when the device starts"). George asked for the
check to come first and squeezelite after it. **Both ways of doing that were
tried on the device and neither works**; this is kept so nobody tries them
again:

1. **Pause at the server before squeezelite connects.** With squeezelite
   stopped, the server still lists the player, takes `pause` and reports `mode
   pause` - and **when squeezelite reconnects the server sets it playing again**,
   within 1.5 s, the DAC running. The server restores what the player was doing
   when it dropped, whatever it was told in between.
2. **Hold the DAC at boot so squeezelite's blocking open (this record) waits.**
   squeezelite opens the device **when it starts, before it connects to the
   server** (its startup probe), so while the DAC was held it never connected,
   the core never saw it connect, and the two waited on each other until the
   hold's 30 s cap - after which the server resumed it and the core paused it
   about 1 s later. Worse than no hold; removed the same day.

**What stands:** the core waits until squeezelite **has connected** before it
pauses (a pause sent earlier is undone), then pauses. What reaches the speakers
in between is open, and George decides the next step (a DAC held at volume 0
until the check is the candidate).
