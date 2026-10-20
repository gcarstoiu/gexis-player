# Finding 130 — A USB-to-optical adapter: four rates, a silent trap at 88.2 and 176.4 kHz, and what each source does with it

**Date:** 2026-10-20. **For:** Phase 16 (`ph-optical`): what the player does
with a USB-to-optical adapter before its decision record is written.

## Scope

- **Adapter:** Realtek "USB SPDIF Adapter", USB ID `0bda:4e27`, ALSA card id
  `Adapter`, on sofapi (Pi 4, gexis-core and -ui `1.2.0+git22`/`+git23`).
- **Receiver:** the SMSL DAC's optical input, its display showing the rate it
  receives, listened to by George. Not tested: a sound bar, a receiver that
  takes only 44.1 or 48 kHz, a second adapter model.
- **Method:** the adapter's descriptors from `/proc/asound/Adapter/stream*`;
  the rate it really ran at from `pcm0p/sub0/hw_params` while playing. Test
  tones (440 Hz, -20 dBFS, 24-bit) played straight to the card with `aplay`,
  and as FLAC files through Lyrion (served from sofapi, nothing added to the
  library). Plexamp with real music: an album at 24/88.2 from the library,
  started by George; its playing position read from Plexamp's own timeline.
- **Not tested:** AirPlay, Spotify and Bluetooth through the adapter (they
  send only 44.1 or 48 kHz, which the adapter takes); DSD; the adapter's
  second device beyond its descriptor.

## Results

1. **What it takes:** 44.1, 48, 96 and 192 kHz, 16 or 24 bits, stereo. **No
   88.2 or 176.4 kHz.** No volume control: its only control is a mute switch
   (`PCM Playback Switch`), so the player offers Software or Fixed volume. A
   second device takes only 48 kHz with "Bits: 0" - typical of a path for
   encoded surround (IEC 61937); not confirmed.
2. **Asked for a rate it lacks, the card runs at the next one up, without an
   error:** 88.2 kHz ran at 96, 176.4 at 192 (`hw_params`; no message from
   `aplay`). Sent that way the music plays about 9 % fast and a semitone and
   a half high. **Heard by George**, twice: tones 3 and 5 of the sequence
   were higher, and the SMSL showed 96 and 192 for them.
3. **Lyrion (Squeezelite) plays silence for those two rates**, with Software
   and with Fixed volume: the adapter opens and never runs, and Squeezelite
   logs `alsa_open:506 unable to get period size: Invalid argument` every 5 s.
   44.1 kHz played. Confirmed by George (*"no playback"*).
4. **Plexamp converts 88.2 kHz to 96 kHz correctly.** The adapter ran at 96 kHz
   (the SMSL showed 96; George: *"sounds fine"*); Plexamp's position kept pace
   with the clock (30.00 s in 30.00 s), and **a whole track of 184.81 s took
   184.72 s** - played fast it would have taken about 170 s.
5. **In the library behind sofapi** (Lyrion and Plex share it): 59 tracks at
   88.2 kHz on five albums, none at 176.4 or 352.8, of 66,212. Through Lyrion,
   these are the silent ones on this adapter.
6. **Aside:** after Squeezelite restarted (a change of volume type), it joined
   a different Lyrion server than before - sofapi's own instead of the one on
   the network. It has no server fixed and takes whichever answers first.

## What follows

Phase 16's decision record: what the player does with a rate the card lacks
(convert in its own chain, as Plexamp does for itself), the adapter's volume
type, its *Tested* mark, its second device. The server Squeezelite joins is a
separate matter.

## After ADR-0155 (2026-10-20, 11:00)

`gexis-core`, `-player` and `-system` `1.2.0+git33` from branch `ph-optical`
on sofapi, the core restarted; Squeezelite ran `-R -u vEX`. The same tones
through Lyrion, Software volume, into the SMSL, George listening:

| Tone | The adapter ran at | Squeezelite's CPU |
|---|---|---|
| 44.1 kHz | 44.1 kHz, untouched | 1 % |
| 88.2 kHz | **192 kHz**, converted | 2 % |
| 176.4 kHz | **192 kHz**, converted | 1 % |
| 96 kHz | 96 kHz, untouched | 2 % |

All four played at the same pitch (George: *"Heard. All good"*). *Output*
showed the adapter *Tested*. Not checked on the device: the Fixed default
(sofapi has Software stored, which is kept); DSD.

