# Finding 096 — Qobuz Connect with the adapter: what George found, and why

**Date:** 2026-09-28
**Question:** George's first round with gexis-qobuz 0.1.0 in place (ADR-0098).
He found five things. What causes each, and which of them are ours?

**Scope:** `gexis`, Pibuz 2.5.1, gexis-qobuz 0.1.0, and then the rework
deployed by hand. George's tests were made from the Qobuz and Spotify apps on
his phone. Claude measured on the device, through Pibuz's own API and CLI, with
no phone:
- Pibuz's event stream and `/api/now-playing`, timestamped side by side, over
  three skips, a double skip and two seeks;
- the release time after `pause`, `stop` and SIGKILL, read the way the core's
  release ladder reads it (the unit's own descriptors on the playback PCM),
  three times for each command;
- the same with `audio.alsa_buffer_ms` at 500 and at 200.

**Not measured:** Spotify taking over after the rework. It needs the phone,
and so does any playback: after a restart, Pibuz has no Qobuz credential until
the app casts to it again (`auto-connect: no handed-over credential yet`), and
`pibuz play album:… / artist:… / track:…` then answers *not found*. George's
retest is the verification of all five.

## George's report (2026-09-28)

1. When skipping, the panel kept the previous track: *"I am listening now to
   Dire Straits but the panel is showing Amnesia by MP3. After 30 seconds it
   corrected itself."* It was a normal skip.
2. Volume, two separate levels (ADR-0098's A), is right. It should be the same
   for Plexamp (Finding 095, amended).
3. The progress bar does not follow a jump made on the phone.
4. When Spotify takes over, its first track refuses to play; the next track
   works. *"I think that is busy."*
5. After a takeover *from* Spotify, the first Qobuz track plays with nothing on
   the panel: no artwork, no progress bar.

## What was found

### Pibuz's event stream is late, bursty, and misses track changes (1, 3, 5)

- **Events arrive in bursts, seconds late.** Three `PositionUpdated` frames
  covering four seconds of playback reached the client in the same
  millisecond. The same happened with `curl -N` and with a Python reader, so
  it is not the client.
- **After a skip, `/api/now-playing` had the new track within 1 s. The
  stream's `QueueUpdated` and `TrackStarted` arrived 6 s later.**
- **A second skip, 6 s after the first, produced no `TrackStarted` at all.**
  The stream sent `QueueUpdated` for the new track, then `QueueUpdated` back
  to the old one, then position updates carrying the *new* track's duration.
  Pibuz itself settled on the new track about 6 s later. The adapter changed
  the track only on `TrackStarted`, so it kept the old one until the next
  one. **That is finding 1.**
- **A seek sends nothing on the stream.** The position in `/api/now-playing`
  reaches the new point **about 5 s after the seek** (110, 112, 114, then 205).
  That delay is Pibuz's own, since it keeps a 6 s decoded ring. The adapter
  sent a position only when something else changed, or every 10 s, so the
  panel's playhead ran on from the old point. **That is finding 3.**
- **Finding 5** is most likely the same cause. At 09:57 the core killed Pibuz
  (below), and it came back with a saved session. At 10:01 George cast to it,
  and the core's log shows a clean acquisition, but no metadata can be traced
  to it. A resumed session need not send `TrackStarted`, and the adapter had
  no track without one. It was not reproduced, for want of the phone.

### Pibuz keeps the card 2 s after a pause or a stop (4)

| Command | Answered | Card free |
|---|---|---|
| `pause` | 0.003-0.117 s | 2.040, 2.061, 2.137 s |
| `stop` | 0.002 s | 2.086 s |
| `pause`, `alsa_buffer_ms` 500 | 0.046 s | 2.061 s |
| `pause`, `alsa_buffer_ms` 200 | 0.054 s | 2.064 s |
| SIGKILL | — | **0.027 s** |

The 2 s is fixed inside Pibuz: its buffer size does not move it, and none of
its settings names it. `dac_keepalive_ms` is silence between tracks, not
this.

The core's log from George's test shows the consequence. At 09:57:21 Spotify
announced `will_play` and the core released Qobuz. The pause did not free
the card within the 1.5 s polite grace, so the core signalled it and the card
was free at 1.7 s. go-librespot opens the card 0.26-0.52 s after a transfer
and does not retry (ADR-0091's amendment), so **its first track was lost; a
skip opened the card again and played. That is finding 4.**

**Finding 094's "a paused Pibuz holds no descriptors on the card" was true
only after 2 s.** In its test 3, the pause came well before Spotify.

### A killed Pibuz comes back clean

Under SIGKILL, systemd restarted Pibuz in 2 s (`Restart=on-failure`), and
gexis-qobuz (`BindsTo=`) came back with it. Pibuz then reported:
- `stopped`, with no queue;
- the card not held;
- not the active device in Qobuz Connect;
- still advertised to the app (mDNS, pairing on :8183).

**It did not resume by itself**, unlike Plexamp's saved queue (ADR-0091's
amendment). George's cast at 10:01 reached exactly such a restarted Pibuz, and
it played.

## What changed (gexis-qobuz, deployed by hand; not released)

- **Pibuz is asked, not listened to.** `/api/status` is polled every 0.5 s;
  only it has `loading`, and it carries the track id and the position.
  `/api/now-playing` (artwork, album, shuffle, repeat) is asked when the
  track id changes, or when its answer is 2 s old. The event stream is no
  longer read. The adapter then costs 0.20 CPU-seconds per 30 s idle, about
  0.7 % of one core. Asking both endpoints every poll cost 0.32.
- **A position away from where the playhead should be is sent at once.** More
  than 3 s away counts, reckoned from the last anchor and whether it was
  playing.
- **Release answers at once, and the ladder's polite grace is 0**, gexis-plexamp's
  ladder for the same race. The core checks the card once and sends SIGKILL.
  The pause and the stop still go, in the background, for a Pibuz that was not
  holding the card, which the core leaves running. **What the user sees:** after
  a takeover, the Qobuz app shows the device gone from the session. It stays in
  the device list, and a cast to it plays.
- Tests: 13 pass, including one case for each of findings 1, 3, 4 and 5.

## Found while testing the Spotify cap (2026-09-28)

- **Every Spotify takeover from Qobuz raised `KeyError: 'qobuz'`** in the core.
  The SIGKILL takes gexis-qobuz down with Pibuz (`BindsTo=`), and the core
  forgets the plugin before the acquisition's last step, which then looked it
  up. Spotify had already been given the device, so it played. Fixed in
  `arbitration.py` with a test that fails without the fix. **Not yet deployed**,
  because deploying restarts the core.
- **Spotify's starting cap** (ADR-0054 §5, amended 2026-09-28) was verified
  with the setting at 30 %:
  - DAC at 50 %: the DAC came down to 30 % (209 → 188) before Spotify played;
  - DAC at 20 %: it stayed at 20 %.

  The setting is back at 60 %.
- **The test interrupted George**, who cast Qobuz at 10:33:51 and was
  retesting. The core restart (10:34:35) and the Spotify takeover (10:35:03)
  were Claude's.

## George's retest (2026-09-28, after 10:40)

Everything worked except one thing, which was dangerous. **After a Spotify
takeover from Qobuz, the first volume press on the phone took the DAC to full
scale** (`spotify -> hardware (100/100 -> 240/240)` at 10:42:44). George
turned it down before he could tell how loud it was.

The cause is the `KeyError` above, one step earlier. The SIGKILL went out at
10:42:33.249, and gexis-qobuz disconnected at .479. The ladder's poll then
looked up the forgotten renderer's unit, raised, and **the acquisition died
before its volume step.** Spotify was never capped or told a level, so its
slider stayed at go-librespot's 100. At 10:35 the same takeover had worked,
because the card was confirmed free before the disconnect. It is a race.

**Fixed** (LESSONS 44):
- the supervisor keeps every renderer's unit after it is forgotten, and the
  ladder polls by unit;
- a release that fails in any way is logged, and the takeover goes on to the
  volume step and the incoming renderer's retry.

Two tests reproduce the sequence and fail without the fix. **Not deployed at
the time of writing: George was listening.**

## George's retest, second part (2026-09-28, 10:47)

**Spotify → Qobuz failed:** the app showed Qobuz playing and advancing, but
Spotify stayed on the speakers. The core received no acquisition from
Qobuz at all. Pibuz retried the busy card 9 times over 6 s, gave up, and
told the app it was playing.

**Measured, card held by a stand-in playing silence:** for the whole 6 s of
retries, `/api/status` said `paused`, `/api/now-playing` said not playing,
and the event stream sent nothing. The one sign was
`audio.command_in_flight: "PlayStreaming"`, from 11 ms after the play until
Pibuz gave up. The event-stream adapter (0.1.0) would have missed this too.
Pibuz's engine commands, read from its binary: `PlayStreaming`, `Pause`,
`Resume`, `SetVolume`, `ReinitDevice`, `ReleaseDevice`.

**Fixed:** a `PlayStreaming` or `Resume` in flight reads as `loading`. The
same stand-in test afterwards: `acquire: qobuz` **0.52 s after the play.**

**The artwork going back and forth while skipping** ("something from David
Bowie"), which George was not sure was ours:
- The panel shows the adapter's artwork, and when that is absent, the
  enrichment's `album_art`. A stale or wrongly matched lookup there would
  look exactly like this.
- The adapter also had a weakness: just after a skip, `/api/status` can name
  the new track while `/api/now-playing` still has the old one. It then took
  the old detail for up to 2 s.
- Fixed: a detail is taken only when it names the status's track.
- **Not yet established which of the two George saw.** A recorder on gexis
  logs every picture the panel receives next to Pibuz's own answer, while
  George skips.

## Still owed

- George's retest of all five.
- A release of gexis-qobuz and the pin bump in stage `08-qobuz`.
- Upstream (Pibuz): the late, bursty event stream, the missing `TrackStarted`,
  and a release of the card on pause without the 2 s. Worth reporting once the
  retest confirms the rest.
