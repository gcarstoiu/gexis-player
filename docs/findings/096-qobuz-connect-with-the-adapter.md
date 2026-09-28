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

## Still owed

- George's retest of all five.
- A release of gexis-qobuz and the pin bump in stage `08-qobuz`.
- Upstream (Pibuz): the late, bursty event stream, the missing `TrackStarted`,
  and a release of the card on pause without the 2 s. Worth reporting once the
  retest confirms the rest.
