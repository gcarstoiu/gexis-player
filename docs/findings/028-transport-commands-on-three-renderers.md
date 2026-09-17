# Finding 028 — Transport commands on all three renderers: what works, what each reports back, and when Next cannot work

**Date:** 2026-09-16
**Question:** ADR-0037 §5. Which transport commands does each built-in renderer
accept, does it report the result back, and in which states can a command not
work (so its button is disabled)?
**System:** `gexis` on image `v0.2.1-179-g67193d5`, freshly flashed. Commands sent
from the device's shell straight to each renderer's API. **No product code
involved:** the core only observed, through its published state.

- **LMS:** server `192.168.178.188`, player `gexis`. A 12-track playlist, then a
  TuneIn station. JSON-RPC `slim.request`.
- **Spotify:** go-librespot v0.9.0, local API `127.0.0.1:3678`, a playlist
  started from George's phone.
- **Bluetooth:** George's Pixel 10 Pro, BlueZ `org.bluez.MediaPlayer1` via
  `busctl`.

**Scope, stated up front:**

- **Speakers were off for every round.** Everything below is what the
  renderers and the core *reported*, plus what George *saw* on his phone. None
  of it is what was heard. Audible checks (resuming radio after a pause, the
  dropout when a stream restarts) are deferred to George's validation of the
  Phase 6 PR.
- **Timing is coarse.** State was sampled 2 to 8 s after each command, except
  where noted, so "follows" means "within that interval". It is not a latency
  measurement.
- **One phone for Bluetooth.** AVRCP support varies by phone and by the app
  playing on it.

## Result

**Every command worked on every renderer.** There were no refusals, errors or
disconnections. What differs is previous, what each renderer reports back,
and where Next cannot work.

| | play / pause | next | previous | shuffle / repeat | reported back |
|---|---|---|---|---|---|
| **LMS** | `pause 1` / `pause 0` | `button jump_fwd` | **`button jump_rew`**, not `playlist index -1` | `playlist shuffle 0/1/2`, `playlist repeat 0/1/2` | all of it, including playlist index and length |
| **Spotify** | `/player/pause`, `/player/resume`, `/player/playpause` | `/player/next` | `/player/prev` | exist in the API (not shown, by design) | transport and track; shuffle and repeat in `/status`; **no "has next"** |
| **Bluetooth** | `Pause`, `Play` | `Next` | `Previous` | `Shuffle`, `Repeat` properties, writable on this phone (not shown, by design) | status, position, track; the position arrives **late** |

## LMS

- **Pause and resume.** `mode` flips; the core's transport follows, and its
  position is anchored at the pause (55.87 s against LMS's 55.9).
- **`playlist index -1` always goes back a whole track**, even 12 s in.
  **`button jump_rew` does what the LMS apps do:** at 19.5 s it restarted the
  track, at about 2 s it went to the previous one. **Previous uses
  `jump_rew`.**
- **Next never stops at the end of a playlist.** With repeat *off*, `+1` on the
  last track went to track 1 and kept playing, and `-1` on the first went to
  the last. **George's "disabled at the end of the queue" case therefore does
  not arise for an LMS playlist.**
- **Next cannot work when the playlist holds one item.** On a radio station
  (`playlist_tracks` 1, `remote` 1), `jump_fwd` and `jump_rew` both stayed on
  the station and restarted the stream (`time` reset to about 5 s). The button
  would do something, but nothing the user asked for, so **Next and Previous
  are disabled when `playlist_tracks` ≤ 1.**
- **Pause works on a radio stream:** `mode=pause`, and `time` holds and then
  continues. Whether the audio resumed or jumped back to live is unheard.
- **Shuffle has three states:** 0 off, 1 songs, 2 albums. Turning it on
  reorders the playlist so the current track becomes index 0. **The design's
  toggle is two-state**, so step 5 must choose a mapping (proposed: on = songs,
  and albums shows as on).
- **Repeat numbering differs from the design's order:** 0 off, **1 one song, 2
  all**. The design's off → all → one is a UI order, not LMS's numbers.
- **Every skip was read as a forced track change** (ADR-0036), which is correct.
  No pause triggered a takeover or release.

## Spotify

- **All five commands returned 200 and took effect.** `/status` and the core's
  transport followed each one.
- **George watched the phone throughout:** it followed every step and **never
  showed gexis as disconnected**. [Finding 014](014-lms-to-spotify-first-attempt-race.md)'s
  failure (`/player/resume` playing audio without the Connect handshake) did
  **not** occur. That failure was a resume *after a takeover*, with no live
  session; this was a resume *within* a live session. The distinction matters
  and is what makes Play safe here.
- **Previous is native:** at 8 s `/player/prev` restarted the track (2.4 s
  after), at about 2 s it went back a track. Nothing to do on our side.
- **go-librespot has no "has next".** Next stays enabled whenever Spotify is
  playing or paused.
- Each `next` and `prev` logged `will_play (acquisition …)` while Spotify was
  already active. No takeover followed; it is harmless, and noted only so it
  does not surprise a later reader of the log.
- **Defect:** the core's position stayed at 0.0 through pause and resume while
  `/status` had 35 s, 41 s and 49 s. The adapter takes a position only from
  `metadata` and `seek` events. Recorded in DEVELOPMENT.md Phase 6 step 2.

## Bluetooth

- **The player exposes** Play, Pause, Stop, Next, Previous, FastForward, Rewind
  and Press/Hold/Release; Status, Position, Track (Title, Artist, Album,
  Duration, TrackNumber, NumberOfTracks), and writable Shuffle and Repeat.
- **Pause and play:** the status flips, the core follows, and the core's
  position was kept (49.51 s).
- **Next works.** **"Has next" cannot be derived:** TrackNumber went 1 → 7 → 6
  with NumberOfTracks 160 — not sequential. Next stays enabled whenever
  Bluetooth is playing or paused.
- **Previous restarts the track, and the phone reports it late.** It was sent
  at 20.8 s. BlueZ's `Position` kept extrapolating (21.9, 23.0, 24.1 s) for
  about 3 s, then read 4.2 s on the same title; the `PropertiesChanged` for
  Position arrived **about 4 s after the call**. A first run sampled at +2 s
  had read this as "ignored"; George could not tell from the phone, and the
  redo, sampled every second with the D-Bus signals captured, settled it. A
  second Previous within about 3 s goes back a track.
- **Consequence for the panel:** after Previous on Bluetooth the progress bar
  keeps counting for up to about 4 s before it snaps back. ADR-0037 §4 shows
  the reported state, so this is not masked.
- **Corrects an assumption in `peppy.py`:** "Bluetooth publishes no position"
  is false for this phone.

## Addendum, same day: timing on the panel

Measured with a recorder on the device timestamping every `/state` message
against the commands and the renderers' own signals:

| | play reaches the panel | pause reaches the panel |
|---|---|---|
| LMS | 0.5 s | 0.5 s |
| Spotify | ~5 ms after go-librespot's event, ~0.1 s after the command | same |
| Bluetooth, panel command | 0.2-0.5 s | **4.5 s** (two runs) |
| Bluetooth, **phone's own button** | — | **about 6 s** (George's count) |

- **The Bluetooth pause delay is the phone's report, not our pipeline.** The
  core forwards the `Status` change within about 0.1 s.
- **A2DP gives no earlier signal.** On four pauses from the phone,
  `MediaTransport1.State` went `idle` 3.1-3.2 s *after* `MediaPlayer1.Status`
  went `paused`. On play, the stream went `active` only 30-50 ms before the
  status. A 1.8 s pause never idled the stream at all.
- **A panel command is masked since the same day:** the play/pause icon flips
  on press (ADR-0037 §4 amendment). **A pause from the phone is not, and
  cannot be:** nothing reaches us before the phone's report. George recorded
  it as an issue to look at later. Open question: does the audio itself stop
  at the tap, or also about 5 s later? That needs the speakers on.

## Addendum 2: it is the app, not the phone

Same day, 22:07-22:10. Same Pixel, Bluetooth, two apps, with BlueZ's own
signals and every `/state` change recorded next to the panel's commands:

| app playing on the phone | Previous: report of the restart | second Previous within ~2 s | pause from the panel: `paused` reported |
|---|---|---|---|
| **Spotify** | 0.2-0.5 s | back a track, 0.3-0.6 s | 0.2 s |
| **Plexamp** | 0.2 s | back a track, 0.6 s | **not reported at all** for 18 s (tap at 22:10:07; next report was a track change) |

- **The late and missing Bluetooth reports come from the Plexamp app**, not the
  Pixel or BlueZ. The earlier rounds that measured 4-4.5 s for Pause and
  Previous were Plexamp. George's report, that Previous "never goes to the
  previous track", fits a late restart report: the second tap landed after the
  app's window and restarted again.
- **Previous works on Bluetooth** with both apps, and George confirmed it on the
  panel.
- With Plexamp, the panel's icon flips on press and returns to "playing"
  after 8 s when no confirmation arrives. That is the designed fallback
  (ADR-0037 §4 amendment), and it is what George saw as lag.

## Addendum 3: repeat on LMS is slow to reach the Lyrion app

2026-09-17. George: repeat changed from the panel took **6-8 s** to show in
his phone app; shuffle showed promptly, and a repeat change from the phone
reached the panel promptly. Measured from the device, three times: LMS had
applied a panel repeat change **0.02 s** after the command, and the panel
showed it at 0.5 s. **George confirmed it is the app:** the same change shows
promptly in **Squeezer**, and slowly in the **Lyrion** app. Nothing on our
side to change.

## What this settles for ADR-0037

| renderer | declares | Next/Previous disabled when |
|---|---|---|
| LMS | play, pause, next, previous, shuffle, repeat | `playlist_tracks` ≤ 1 |
| Spotify | play, pause, next, previous | never (no signal) |
| Bluetooth | play, pause, next, previous | never (no reliable signal) |

**Not measured, and why:**

- **Seek:** not in the design.
- **Spotify and Bluetooth shuffle and repeat:** the design shows them for LMS
  only.
- **LMS with an empty playlist:** there is then nothing to be active, so no
  transport row.
- **Commands while paused, other than Play:** a next from paused was not
  tried.
- **A second Bluetooth phone.**
