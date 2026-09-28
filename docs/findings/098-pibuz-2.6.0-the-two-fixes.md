# Finding 098 — Pibuz 2.6.0 (dev build): both fixes we asked for work on gexis

**Date:** 2026-09-28
**Question:** Pibuz's author answered our issues the night he stopped
publishing binaries (Finding 097): an `external` volume mode
([#3](https://github.com/PhilipVinc/pibuz/issues/3)) and an honest failure when
the card stays busy ([#2](https://github.com/PhilipVinc/pibuz/issues/2)). Do
they work on gexis? George: *"Can we build pibuz 2.6 and check the fixes?"*

**Scope:** `gexis` with gexis-qobuz 0.2.0 and a **dev build** of Pibuz 2.6.0,
cross-compiled with `image/tools/build-pibuz-dev.sh`. 2.6.0 is not tagged, so
the build is `main` at 8184ba3: the version bump plus one commit of fixes on
top. It was installed through the normal switch-on path from a device-only pin,
and published nowhere. George cast from the Qobuz app on his phone. **Not
tested:** a real Spotify takeover on 2.6.0; seek after pause-suspend; the other
five fixes in 8184ba3.

## #2: a busy card fails honestly

Qobuz was paused. A stand-in (`aplay` of silence on `output`) held the card,
and a play was sent through Pibuz's API.

- **During the retries,** `/api/status` said `paused`, with
  `command_in_flight: "Resume"`. The adapter reads that as wanting the card
  (gexis-qobuz 0.2.0's `WANTS_THE_CARD`), so a real takeover would free the card
  inside the window. Qobuz already held the device, so the core logged nothing,
  correctly.
- **After 9 retries (about 6 s) it gave up and stayed `paused` on the same track**,
  with the reason in `last_errors.stream`: *"ALSA Direct failed: Device busy …
  Device may be in use or inaccessible."*
- **George: *"Part #2 worked fine"***. The app showed the track paused, not
  playing silence as 2.5.x did (Finding 094, test 2). Play then worked once the
  card was free.

## #3: `external` volume leaves the signal alone

Measured as in Finding 095: the pre-DAC meter tap (peppyalsa on `output`,
linear 0-100), with `gexis-meter` stopped for the minute; Pibuz's volume set to
0.10 and 0.34 through its API, six passes of 2 s each after 0.8 s to settle.

| Pibuz volume | `software` (control) | `external` | `external`, order alternated |
|---|---|---|---|
| 0.10 | 0.00 | 28.3 | **34.7** |
| 0.34 | 0.85 | 33.3 | **35.0** |

- **In `software` mode Pibuz attenuates in its own engine,** about 30 dB down
  at 0.34 against full scale.
- **In `external` mode the level does not follow the volume.** The first
  external run measured the low setting first on every pass while the music
  built. With the order alternated, 34.7 against 35.0 is inside the music's
  own variation.
- **George: the Qobuz app's slider no longer changes the loudness; the panel's
  does.**
- **The mode is read at start-up and at connect**, not live. Setting it on a
  running Pibuz changed nothing until a restart, which ends the Qobuz session
  (George cast again).
- **With `external`, the app's level is reported but not applied.** On George's
  cast Pibuz reported 1.0, the app's own level.

## What this makes possible, and what it asks

- **Qobuz can share one volume number with the panel, as Spotify does**
  (ADR-0054). Pibuz plays bit-perfect, and the app's slider moves the DAC
  through the core. It needs gexis-qobuz to declare `volume_managed`, report
  Pibuz's level and set it through `/api/playback/volume`.
- **It brings Spotify's hazard with it.** On a cast the app's level arrives as
  it is: 1.0 here, which the core would put on the DAC. A starting cap like
  `spotify_start_max` would be needed for Qobuz too.
- A decision for George: keep Qobuz's two separate levels (ADR-0098's A, today),
  or change to one number now that it is possible.

## State left on gexis

- Pibuz 2.6.0 dev build, with `qconnect.volume_mode external`.
- The panel at 35 % (from 60 %, lowered for the test).
- With the adapter still unmanaged, the Qobuz app's slider does nothing until
  this is decided or put back.
