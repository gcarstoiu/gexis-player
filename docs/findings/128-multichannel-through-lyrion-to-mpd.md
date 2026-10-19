# Finding 128 — Multichannel through Lyrion to MPD

**Date:** 2026-10-19. **Asked by George** (Phase 15, `ph-mpd`): can Phase 15
be smaller - Lyrion's library and apps playing to MPD on the player, which
carries more than two channels, instead of MPD as a second library?
(ADR-0151, idea 2.)

**Answer:** yes for PCM. Through Lyrion's *UPnP/DLNA bridge* plugin and
upmpdcli, a 5.1 and a 7.1 file reached the receiver as 6 and 8 channels. DSD
did not play through the bridge.

## Scope

- **Tested:** sofapi (Raspberry Pi 4, 4 GB, Debian 13), output HDMI 2 to the
  Sony AV receiver of Finding 121 (`vc4hdmi1`). Installed for the test and
  removed after (52 packages, none of the player's touched; Lyrion's plugin
  list put back): Debian's `mpd` 0.24.4 and `mpc`, upmpdcli 1.9.17 with
  `libupnpp17` and `libnpupnp13` from its author's repository (signature,
  package list and package hashes checked), Lyrion's *UPnP/DLNA bridge*
  plugin (`UPnPBridge`) in the player's own Lyrion server 9.1.1.
- **MPD's output:** `plughw:CARD=vc4hdmi1,DEV=0`, no mixer, adapting format,
  rate and channels only where the card refuses (`auto_* yes`; with them off
  every open failed - the card takes only IEC958 subframes, which `plug`
  converts to).
- **Files:** generated, a different quiet tone (-24 dB) on each channel:
  stereo FLAC 24/48, 5.1 FLAC 24/48, 5.1 WAV 24/48, 7.1 FLAC 24/96, 5.1
  DSF DSD64 (`tools/dsd-test-file/dsfgen.c`).
- **Played as Finding 121 played them:** streamed over HTTP from the player
  itself (`http://127.0.0.1:8765/...`), not from a Lyrion library.
- **Read:** MPD's log (`decoder: audio_format`, `output: opened`) and what
  the card was opened at (`/proc/asound/vc4hdmi1/pcm0p/sub0/hw_params`).
- **Not tested:** which speaker each channel reached (no capture, nobody
  listening per channel); files from a Lyrion library; long play, seeking,
  gapless; volume through the bridge; the bridge's own settings beyond its
  defaults; DSD with any change to Lyrion's or the bridge's settings.

## Measured

**A. MPD alone** (`mpc play`):

| File | MPD decoded | Card opened at |
|---|---|---|
| Stereo FLAC | 48000:24:2 | 2 ch, 48 kHz |
| 5.1 FLAC | 48000:24:6 | 6 ch, 48 kHz |
| 5.1 WAV | 48000:32:6 | 6 ch, 48 kHz |
| 7.1 FLAC | 96000:24:8 | 8 ch, 96 kHz |
| 5.1 DSF | dsd64:6, converted to 352800:24:6 | 6 ch, 192 kHz |

**B. Through Lyrion** (`playlist play` on the bridged player
*SofaPi MPD test-UPnP/AV*):

| File | What MPD was sent | MPD decoded | Card opened at |
|---|---|---|---|
| Stereo FLAC | `bridge-1.flac` | 48000:24:2 | 2 ch, 48 kHz |
| 5.1 FLAC | `bridge-2.flac` | 48000:24:6 | 6 ch, 48 kHz |
| 5.1 WAV | `bridge-3.flac` | 48000:24:6 | 6 ch, 48 kHz |
| 7.1 FLAC | `bridge-4.flac` | 96000:24:8 | 8 ch, 96 kHz |
| 5.1 DSF | nothing | - | not opened |

## What it means

- **The bridge keeps the channels.** It sends MPD every file as FLAC (the
  WAV arrived as `bridge-3.flac`), lossless, so 24 bits and all channels
  survive. A Lyrion library and Lyrion's apps could play multichannel
  through MPD with no second library.
- **DSD does not pass as the bridge comes.** Lyrion logged *"Couldn't create
  command line for dsf playback"*: it has no conversion for DSF to the
  bridged player, which, unlike our Squeezelite, does not take DSD. Whether a
  bridge or transcoding setting fixes it is not tested.
- **The bridge also adopts every UPnP renderer on the network** - the
  receiver itself appeared as a Lyrion player, *Receiver* - so a real setup
  would limit it to the player's own MPD.
- **Volume through the bridge needs a mixer on MPD**; with none, upmpdcli
  logged *No mixer* on every track.
- MPD alone does everything ADR-0151 asked of it on HDMI, DSD included
  (as PCM, at the card's 192 kHz).
