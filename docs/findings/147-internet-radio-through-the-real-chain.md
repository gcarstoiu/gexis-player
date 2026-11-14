# Finding 147 — Internet radio through a player's real chain: the stream's rate to the DAC, 22 kHz raised to 48, drops recovered, 5-7 % of a core

**Date:** 2026-11-14. **For:** Phase 31 (`ph-radio`),
[ADR-0180](../decisions/0180-internet-radio-without-lyrion.md) step 6: the
build on a player, after [Finding 146](146-mpv-as-the-radio-engine-on-a-pi-4.md)
measured mpv with a silent output.

## Scope

- **Device:** sofapi, a Raspberry Pi 4, Debian 13, the preview of `ph-radio`
  at 439ac89 (`gexis-core 1.16.2+git20.3f9d217`, mpv 0.40.0 from Debian,
  installed by the preview's dependency), on Wi-Fi. **Taken out of its group**
  for the test (George), so `output` was the player's own chain: the meter,
  then the loopback that CamillaDSP captures, room correction on, then the
  USB DAC (`AUDIO`). Grouped again afterwards; nothing was playing on either
  player before, during or after, and the level was lowered to 20 % for the
  test and put back (64 %, read back).
- **Stations:** six public ones from Finding 146 (Radio Paradise Main Mix AAC
  320 and Rock Mix FLAC, France Info AAC, Europe 1 MP3, Deutschlandfunk Opus
  mono, RTL HLS), played through the core's own route, one after another in
  one mpv; each 10 s to settle and 60 s measured. A 22.05 kHz mono tone, and
  the drop tests, served from the player itself on loopback at the stream's
  own pace (a burst of about ten seconds, then real time, as a station
  sends).
- **Read:** each open playback substream's `hw_params` (`/proc/asound`),
  mpv's user and system time and resident memory (`/proc/<pid>`), the
  core's `/state`.
- **Not tested:** another source taking the output and giving it back; a
  group (the radio in a group); the screens on the player (George's
  regression pass); Ethernet; another Pi.

## Results

### 1. The stream's own rate reaches the DAC; the stage runs

| Station | Loopback (mpv's) | DAC |
|---|---|---|
| RP Main Mix, AAC 320 | S32_LE, 44100, 2 | S32_LE, 44100, 2 |
| France Info, AAC | S32_LE, 48000, 2 | S32_LE, 48000, 2 |
| Europe 1, MP3 | S32_LE, 48000, 2 | S32_LE, 48000, 2 |
| Deutschlandfunk, Opus **mono** | S32_LE, 48000, **2** | S32_LE, 48000, 2 |
| RP Rock Mix, FLAC | S32_LE, 44100, 2 | S32_LE, 44100, 2 |
| RTL, HLS | S32_LE, 48000, 2 | S32_LE, 48000, 2 |
| **22.05 kHz mono tone** | S32_LE, **48000**, 2 | S32_LE, 48000, 2 |

- mpv plays 32-bit integers into `output` (the chain refuses float), at the
  stream's rate; the mono station leaves as two channels.
- **The 22.05 kHz stream was raised to 48 kHz** before the chain (*22050 Hz
  converted to 48000 Hz* in the core's log), with the equaliser's engine
  running: room correction applies to it (acceptance 4).

### 2. 5-7 % of a core through the real chain

- mpv, 60 s each after 10 s: **4.8-5.5 %** of one core for AAC, MP3, Opus and
  FLAC, **7.0 %** for HLS; one hour of RP Main Mix AAC 320 averaged **6.7 %**,
  and 7.0 % and 6.4 % in a later minute each.
- Finding 146 measured the same stations at 2.8-5.6 % with a silent output.
  The difference is the chain, which runs inside the player's own process:
  the visualiser's meter (an ALSA plugin) and the format conversion. Asking
  mpv for 32-bit itself changed nothing beyond the spread (6.4 % against 7.0 %):
  it already plays 32-bit.

### 3. Memory: flat over an hour, bounded across switches

- **One station for an hour:** 66 MB at the start, 69 MB from minute 20 to
  minute 60; no drop, no restart, the state *playing* throughout.
- **Ten switches between two stations:** 78 to 80 MB, flat from the third.
- Across the six stations in one process it rose from 67 to 110 MB: each new
  format (MP3, Opus, FLAC, HLS) loads what it needs once.

### 4. A cut recovers; a station that stays down stops with a message

The stream served from the player, then stopped (acceptance 5):

| Seconds | What happened |
|---|---|
| 1.3 | playing |
| 13.4 | **cut**: the server stopped |
| about 23 | the buffer ran out (not logged: the watchdog counts from here) |
| 31.7 | the server back |
| 33.0 | *reconnecting*, try 1 |
| 33.2 | playing again |
| 57.1 | **down**: the server stopped for good |
| 63.1 | the tries counted from 0 again (30 s of sound since the recovery) |
| 83.2, 93.3, 103.2 | *reconnecting*, tries 1, 2 and 3 |
| 113.4 | *not answering*; stopped |

### 5. Found and fixed during the test

- **No rate after a station at the same rate as the one before**: mpv reports
  a property only when it changes. The renderer now asks mpv once a station
  sounds (c15da4a7); a station without its codec or bitrate (one added by its
  address) takes mpv's. The tests' fake mpv was answering every set as a
  change, which is why its tests could not see it (Lesson 83); it now reports
  only changes.

## What it means for Phase 31

- **Acceptance 4 met** on this player: every stream reaches the stage at 44.1
  or 48 kHz, a 22 kHz one raised.
- **Acceptance 5 met**: a cut recovers, a station that stays down stops with
  *The station is not answering*.
- **Acceptance 7 is George's to read**: through the real chain the radio
  takes 4.8-7.0 % of a core, against the criterion's 3-6 % taken from Finding
  146's silent output. The difference is the chain every renderer plays
  through, inside its own process.
- No restart of mpv per station is needed: its memory is bounded.
