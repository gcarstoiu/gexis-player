# Finding 120 — A USB DAC: the SMSL

**Date:** 2026-10-12. **Asked by:** George (*"Since now I have an usb DAC
attached lets test it so we can cover this angle as well"*).

## Scope

- **DAC:** George's SMSL USB DAC on sofapi (Pi 4), USB 2.0 high speed, id
  `152a:85dd`; it reports itself as manufacturer "SMSL", product "SMSL USB
  AUDIO", and names no model. Gexis 0.10.2 previews (`+git49` to `+git65`).
- **Measured:** what it reports (sysfs, `/proc/asound/cardN/stream0`, `aplay
  --dump-hw-params`); one second of digital silence through the player's own
  `output` at every rate and sample format, and native DSD straight to `hw:`
  and through `output`; ALSA's `type linear` widening, played and compared
  sample by sample; generated test tones (440 Hz at -30 dBFS, 20 s, made with
  sox) played through George's Lyrion server, reading the card's `hw_params`
  each time.
- **With George's own use:** Spotify Connect played on it earlier the same day
  (S32_LE, 44.1 kHz), the amplifier on the wrong input at first.
- **Not measured:** the analogue output (no analyser); Bluetooth, Plexamp and
  uploaded renderers on it (Bluetooth is George's test); DSD from a real
  file; volume in DSD.

## Results

1. **Found by itself**, as card `AUDIO`; no volume control of its own (only
   *SMSL Internal Clock Validity*), so Hardware is greyed and the volume is
   Software or Fixed. Shown since this day as *SMSL USB DAC*, with "USB 2.0 ·
   up to 768 kHz / 32-bit · native DSD" under it.
2. **32-bit only.** It offers `S32_LE` (two alternate settings, 32 and 24
   significant bits, both in 32-bit containers) and `DSD_U32_BE`, 44.1 to
   768 kHz. Through `output`, silence at all ten rates (44.1, 48, 88.2, 96,
   176.4, 192, 352.8, 384, 705.6, 768 kHz) opened the card at that rate in
   `S32_LE`; `S16_LE`, `S24_LE` and `S24_3LE` were refused at every rate
   ("Sample format non available").
3. **Widening is exact.** `type linear` to `S32_LE`, under the meter alone
   and under meter and software stage, played 16, 24 and 32 bits at 44.1 and
   192 kHz with no fault. Captured to a file: 96,000 random samples at 16 bits
   and at 24 bits, each equal to the input shifted left - none different.
4. **Through Lyrion** (Squeezelite, Fixed volume):

   | File | Lyrion reports | Card opened at |
   |---|---|---|
   | FLAC 16 / 44.1 | 44100 / 16 | S32_LE, 44.1 kHz |
   | FLAC 24 / 96 | 96000 / 24 | S32_LE, 96 kHz |
   | FLAC 24 / 192 | 192000 / 24 | S32_LE, 192 kHz |
   | FLAC 24 / 352.8 | 352800 / 24 | S32_LE, 352.8 kHz |
   | FLAC 24 / 384 | 384000 / 24 | S32_LE, 384 kHz |
   | WAV 32 / 384 | 384000 / 32 | S32_LE, 384 kHz |
   | WAV 32 / 705.6 | 705600 / 32 | **S32_LE, 44.1 kHz** |
   | WAV 32 / 768 | 768000 / 32 | **S32_LE, 44.1 kHz** |

   Up to 384 kHz the rate reaches the card unchanged; above it the card
   opens at 44.1 kHz, so the file plays some sixteen times too slow. Where
   in the hand-over the limit sits was not traced.
5. **Native DSD reaches the card directly**: `DSD_U32_BE` at 88.2, 176.4,
   352.8 and 705.6 kHz (DSD64 to DSD512) opened `hw:AUDIO` at that rate.
   **Through `output` it aborts**: `pcm_meter.c:1222:
   snd_pcm_scope_s16_get_channel_buffer: Assertion 's16->buf_areas'` - the
   visualiser's meter cannot take DSD. Today nothing sends DSD (Squeezelite
   runs without `-D`).

6. **After ADR-0143** (Squeezelite told 44.1-384 kHz, sofapi rebooted on
   `+git71`): FLAC 192 and 384 kHz unchanged as before; the 705.6 and 768 kHz
   WAV files, served over HTTP, **did not play** - Lyrion stopped rather than
   convert them - instead of playing at the wrong speed. A file in a Lyrion
   library at those rates was not tried.

7. **Native DSD through Lyrion, after ADR-0144** (`+git76`, peppyalsa `-4`,
   volume Fixed): generated DSF files (a 1 kHz sine through a second-order
   sigma-delta modulator, 0.25 of full scale; decoded by ffmpeg as exactly
   1000.0 Hz) played over HTTP opened the card in `DSD_U32_BE` at 88.2 kHz
   (DSD64), 176.4 kHz (DSD128) and 352.8 kHz (DSD256); a 24/192 FLAC after
   them opened it in `S32_LE`, 192 kHz, Squeezelite running throughout.
   Switched to Software, Squeezelite came back without `-D` and through the
   software stage; to Fixed, with it again. The first peppyalsa guard
   (`snd_pcm_format_linear`) let DSD through to the same abort - DSD formats
   count as unsigned, so linear; the second uses the s16 scope's own list.

## What it means

ADR-0143: a 32-bit-only card is widened (so Bluetooth plays on it), and
Squeezelite is told rates up to 384 kHz on a card above that. DSD needs the
meter and the software stage kept out of its way (ADR-0144).

## A mistake on the way

The first attempt at result 4 used Lyrion's `playlist preview`, expecting it
to restore the queue; it replaced it, and the files did not play because the
server could not resolve the `.local` name they were served under (LESSONS
69).
