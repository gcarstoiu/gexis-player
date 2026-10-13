# Finding 121 — Multichannel to an AV receiver

**Date:** 2026-10-13. **Asked by:** George (*"Now that I can connect to an av
system - can you check the support for Multichannel tracks, both pcm and
dsd?"*).

## Scope

- **Receiver:** a Sony AV receiver on sofapi's HDMI 2 (it names itself "SONY
  AVSYSTEM"); the player's output switched to *HDMI 2* for the test and put
  back on the SMSL USB DAC after, volume type Software.
- **Files:** generated (sox; `tools/dsd-test-file/dsfgen.c` for DSD), a
  different quiet tone on each channel: 5.1 FLAC and WAV at 24/48, 7.1 FLAC at
  24/96, 5.1 DSF at DSD64 (decoded by ffmpeg as six channels, 5.1 layout).
  George's own DSD folder in Lyrion holds 27 files, all stereo (DSD64, 256,
  512 and their PCM versions), by file size over rate and duration.
- **Played through:** Lyrion (Squeezelite), streamed over HTTP; what reached
  the card read from `/proc/asound/vc4hdmi1/pcm0p/sub0/hw_params`.
- **Not measured:** which two of the channels Squeezelite kept (no capture);
  Plexamp or any other source with multichannel files; a file in a Lyrion
  library rather than a stream.

## Results

1. **The receiver takes** (its ELD): LPCM up to 8 channels, 32-192 kHz, 16/20/24
   bits; AC-3 and DTS 6 channels; DD+, TrueHD and DTS-HD 8 channels; DSD
   ("One Bit Audio") 6 channels at DSD64 only.
2. **The Pi's HDMI takes** `IEC958_SUBFRAME_LE`, 2 to 8 channels, 32-192 kHz:
   multichannel PCM is possible at the card. It has no way to send one-bit
   audio, so **DSD over HDMI is always converted to PCM**.
3. **Through Lyrion, everything arrives as two channels:**

   | File | Lyrion reports | Card opened at |
   |---|---|---|
   | 5.1 FLAC 24/48 | 48000 / 24 | 2 channels, 48 kHz |
   | 5.1 WAV 24/48 | 48000 / 24 | 2 channels, 48 kHz; Squeezelite logged "pcm_decode:416 unsupported channels" |
   | 7.1 FLAC 24/96 | 96000 / 24 | 2 channels, 96 kHz |
   | 5.1 DSD64 | (stream) | 2 channels, 192 kHz PCM |

   Squeezelite plays two channels: the Squeezebox protocol it speaks carries
   two. A multichannel FLAC plays two of its channels and drops the rest
   (centre and surrounds are not folded in - not a downmix); a multichannel
   WAV does not decode.

## What it means

Multichannel cannot reach the receiver through Lyrion at all, and what it does
with a multichannel file today loses channels without saying so. The other
sources (Spotify, Bluetooth) are stereo by nature. Multichannel to a receiver
needs a renderer that outputs more than two channels, and the chain checked
for it; DSD to a receiver over HDMI is PCM whatever is done.
