# Finding 090 — What a refused play looks like, and why Plexamp could never take the device

**Date:** 2026-09-26
**Question:** George: *"Cannot takeover with plexamp. The plexamp mobile app fails
to playback."* Reported immediately after ADR-0091 landed, so the first question
was whether that caused it; the second was what a fix could key on.
**Scope:** `gexis`, Plexamp headless 4.13.2, ADR-0091's changes deployed by hand.
The contended attempts were driven by this session's `playMedia`, **not by
George's phone**, though the failure was first seen on his phone and the player's
log of that attempt is quoted below. One direction, one holder at a time.

## It is not ADR-0091, and it is not Spotify

George's own attempt, from the player's log — the phone (`192.168.178.61`) sends
`createPlayQueue`, the player cannot start, and the phone gives up half a second
later:

```
16:47:32  HttpServer: [192.168.178.61] GET /player/playback/createPlayQueue …
16:48:12  BASS: Resetting device (soft: 0, force: 0, initialized: 1).
16:48:12  WARNING - BASS: Couldn't start, so we're not doing a soft configure.
16:48:12  …/:/timeline?state=error…
16:48:13  HttpServer: [192.168.178.61] GET /player/playback/stop commandID=98
```

`go-librespot` held the DAC at the time (`fuser /dev/snd/pcmC5D0p` → PID 34334,
`state: RUNNING`), having opened it at 16:36:15 and kept it since. **The core
logged no arbitration at all** during the attempts.

Reproduced deliberately against LMS instead, which has nothing to do with
ADR-0091 or with Spotify:

```
pcm RUNNING, held by squeezelite
playMedia -> 200
pcm RUNNING, held by squeezelite      <- Plexamp never started
core saw no plexamp acquire at all
```

**So the defect is general and pre-existing**: every ADR-0091 commit is on the
release path, and this is the acquisition path. The circle is that **Plexamp must
open the ALSA device to start playing, and the plugin's only evidence of an
acquisition is playback starting** — so a busy device means no playback, no
acquisition, nothing asked of the core.

### Finding 085's five takeovers were from a renderer that had let go

[Finding 085](085-the-takeover-gaps-and-the-controls.md) records *"LMS → Plexamp:
0.2 s, five times, no variance"*, which reads like a takeover from a playing
renderer. It was not. Its own scope says *"Playback was started by API calls,
never by a phone"*, and it lists Spotify and Bluetooth as unmeasured because they
*"need a phone"*. LMS can be the active renderer in the core's model while
squeezelite has already released the device via `-C 1` (ADR-0027: power, not
playback), and that is the state those five were measured in. **A takeover from a
renderer that actually held the device was never tested until today.**

## The 409 on the way: `activate` was implemented and never declared

`POST /renderer/plexamp/activate` answered **409**, because the core checks the
declared `controls` and the plugin left `activate` out of that list while handling
it in `command()` from its first version. The core was right on what it had been
told. Declaring it makes the route answer `200 {"activated": "plexamp"}`.

**It is not the fix.** It is a panel path, not the phone's, and it plays *what is
already queued* — a freshly restarted Plexamp has an empty queue, so activating it
does nothing. Confirmed: 200, and the device stayed `closed`.

## What the plugin can key on, measured on two channels

A 150 ms sampler saw **one** distinct timeline across a whole contended attempt
and reported nothing had happened. That was wrong, and it is `docs/LESSONS.md`
42's trap in a new costume: the interesting state lasts ~50 ms. The
change-driven long poll the plugin already uses — `poll?wait=1`, which returns on
change — catches it, as does the SSE stream:

```
t+0.14s  POLL  {'state': 'error', 'playQueueID': '2929', 'playQueueItemID': '102680',
                'key': '/library/metadata/91795', 'ratingKey': '91795'}
t+0.14s  SSE   {'state': 'error', 'playQueueID': '2929', 'key': '/library/metadata/91795'}
t+0.18s  SSE   {'state': 'stopped', 'playQueueItemID': '', 'type': ''}
t+0.19s  POLL  {'state': 'stopped'}
```

**The refused timeline carries everything needed to issue the play again**, in
full:

```
{'state': 'error', 'duration': '328228', 'time': '0',
 'playQueueItemID': '102681', 'key': '/library/metadata/91795',
 'ratingKey': '91795', 'playQueueID': '2930', 'playQueueVersion': '2',
 'containerKey': '/playQueues/2930', 'type': 'music', 'itemType': 'music',
 'volume': '64', 'shuffle': '0', 'repeat': '0',
 'machineIdentifier': '4548551a…', 'protocol': 'https',
 'address': '192-168-178-191.….plex.direct', 'port': '32400'}
```

## A plain play is not enough

With the device free again (`pcm closed`, 1.8 s after LMS was paused):

```
GET /player/playback/play -> 200
pcm='closed'          <- nothing resumed
```

**The queue goes with the error**, so a retry has to re-issue `playMedia` with the
parameters above rather than just pressing play. This is what makes
[ADR-0092](../decisions/0092-a-play-queue-is-an-acquisition.md) §3 carry
parameters instead of a verb.

## Measured after the fix, the same day

**Scope for this section only:** ADR-0092's implementation deployed by hand to
`/opt/gexis-plexamp`, one contended takeover with squeezelite *playing*, driven by
this session's `playMedia` rather than by a phone.

```
t+0.13s  pcm RUNNING, held by squeezelite
t+0.33s  pcm closed,  held by nobody
t+0.55s  pcm RUNNING, held by node          <- Plexamp

plexamp was asked for play queue 2931 and could not start - asking for the device
acquire: plexamp takes the device (was lms)
release[lms]: polite stop freed the device (0.2s)
the device is free; playing what was refused
```

**0.55 s from the controller's request to Plexamp holding the device**, and 236 ms
from the plugin noticing to the play being issued again. The uncontended path was
checked for a double play and has none: one acquire, no re-issue, playing in
0.54 s.

## What this does not establish

- **The diagnosis above was taken before the fix**; the section immediately above
  is the only part measured after it, and it is one takeover in one direction.
- **Not from George's phone**, except the first log quoted. Every deliberate
  reproduction used this session's `playMedia` against the player's own port. The
  phone's `createPlayQueue` may differ in ways that matter.
- **One holder at a time, one direction.** LMS holding, then Spotify holding, both
  losing to Plexamp; nothing about Bluetooth, and nothing about two attempts at
  once.
- **Nothing about how long the error state lasts in general.** ~50 ms in the runs
  observed, on an idle device; a busier one may differ, and the fix must not
  depend on catching a window.
