# Finding 128 — Multichannel through Lyrion to MPD

**Date:** 2026-10-19. **Asked by George** (Phase 15, `ph-mpd`): can Phase 15
be smaller - Lyrion's library and apps playing to MPD on the player, which
carries more than two channels, instead of MPD as a second library?
(ADR-0151, idea 2.)

**Answer:** yes, with two settings and one fix. Through Lyrion's *UPnP/DLNA
bridge* plugin and upmpdcli, 5.1, 7.1 and 5.1 DSD reached the receiver as 6
and 8 channels - but only with the bridge passing files through untouched
(its default decodes them, and keeps two channels), DSD added to its formats,
and the centre and LFE channels swapped back before the HDMI port (addendum
below, checked by ear).

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

- ~~**The bridge keeps the channels.**~~ **Wrong, found by ear the same
  afternoon (addendum):** the card opening at 6 and 8 channels showed the
  stream's width, not what was in it. In its default mode the bridge sent six
  channels with four of them silent. Only in pass-through mode do all
  channels carry sound.
- ~~**DSD does not pass as the bridge comes.**~~ It does not by default; with
  DSD added to the bridge's formats and pass-through mode it does (addendum).
- **The bridge also adopts every UPnP renderer on the network** - the
  receiver itself appeared as a Lyrion player, *Receiver* - so a real setup
  would limit it to the player's own MPD.
- **Volume through the bridge needs a mixer on MPD**; with none, upmpdcli
  logged *No mixer* on every track.
- MPD alone does everything ADR-0151 asked of it on HDMI, DSD included
  (as PCM, at the card's 192 kHz).

## Addendum, the same afternoon: by ear, and DSD

George at the receiver (a 5.1 speaker system, the receiver on *Direct*);
everything installed again for it and removed after (57 packages with
`espeak-ng`, used only to make spoken test files; Lyrion's plugin list and
the bridge's settings file put back). Spoken files: each channel says its
name in turn, 3 s apart, -12 dB.

| What | Heard |
|---|---|
| 5.1 through Lyrion, the bridge in its default mode (`auto`) | front left and right only. The receiver showed **3/2.1** (5.1 received): the bridge decodes with a Squeezelite-based decoder, which keeps channels 0 and 1 (Finding 121), and re-encodes six channels with four silent |
| `speaker-test -c 6` straight to HDMI 2, through `hdmi:` and through `plughw:` | every channel from its own speaker, both ways; the first call (front left) missed while the receiver locked on |
| 5.1 through Lyrion, the bridge set to pass files through (`<mode>thru</mode>`) | fronts and rears right; the centre voice quiet and distorted |
| A voice in the file's LFE channel alone, through MPD | clearly from the **centre** speaker |

- **Centre and LFE are swapped.** A file's 5.1 is front left, front right,
  centre, LFE, rear left, rear right; the Pi's HDMI port is opened with the
  map `FL,FR,LFE,FC,RL,RR` (`Playback Channel Map`, read while playing).
  MPD sent the file's order, so the centre went to the subwoofer and the LFE
  to the centre speaker. `speaker-test` reads the map and was right. A real
  setup swaps channels 3 and 4 (counting from 1) before the port; 7.1 the
  same, not checked by ear (the system is 5.1).
- **DSD passes once the bridge is told it can**: `dsf,dff` added to the
  bridge's `<codecs>`, and `thru` mode. With the formats added but the mode
  left at `auto`, Lyrion sent the file and the bridge's decoder refused it
  (*"Decoder does not support file format"*). With both, MPD received the
  file untouched (`bridge-1.dsf`), decoded `dsd64:6`, and the card opened at
  6 channels, 192 kHz.
- In `auto` mode the bridge also caps rates at 96 kHz (`<sample_rate>`);
  in `thru` mode nothing is decoded or resampled on the way - not measured
  with a file above 96 kHz.
- **Volume:** MPD with a software mixer at 100 % plays the file unchanged;
  Lyrion's volume through the bridge was not exercised.
