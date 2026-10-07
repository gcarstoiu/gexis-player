# Finding 114 — The IQaudio Pi-DAC PRO

**Date:** 2026-10-07. **Asked by:** George (ADR-0117's board test, 13d):
*"6. you can do now"*.

## Scope

- **Board:** George's IQaudio board, on a second Pi 4 (`guestpi`), Raspberry Pi
  OS kernel `6.18.50+rpt-rpi-v8`, Gexis `0.9.2+git73`. **It is a Pi-DAC PRO,
  not the DAC+** that ADR-0117 planned to test: its HAT EEPROM reads vendor
  *IQaudIO Limited*, product *Pi-DAC PRO*, id `0x0008`. The DAC+ itself
  stays untested.
- **Measured here:** how the board is found; the output chain; the volume
  control and its scale; the rates and formats the card accepts through the
  player's own `output`, with silence (no sound); a Lyrion MP3 and a Lyrion
  FLAC, 20 % volume, a few seconds each; the de-emphasis setting.
- **Not measured:** Spotify, Bluetooth and Plexamp through this board (each
  needs a phone or the app); the analogue output itself (no analyser); taking
  back a chosen board that is not fitted (ADR-0117's third test); the DAC+.
  George heard Spotify play through it after setup (2026-10-07).

## Results

1. **Found by itself.** The EEPROM loads the driver (`snd_soc_iqaudio_dac` with
   `snd_soc_pcm512x`); `config.txt` names no overlay. The card is
   `IQaudIODAC`. *Sound card board* reads *Found by itself*; *Output* reads
   *IQaudIO DAC — Known*. The card name is shared by five boards in the list
   (DAC+, DigiAMP+, OSA DACBerry PRO, ST400, and this one), so the name alone
   cannot say which board it is; the EEPROM can.
2. **The chain has nothing that converts:** `pcm.output` is the meter tap
   (transparent, Finding 003) straight onto `hw:IQaudIODAC`, as on the DAC2 HD.
3. **The volume is the card's own:** the `Digital` control, 0-207 in 0.5 dB
   steps, 207 = 0 dB. The player's volume drives it on its cubic curve:

   | Player | `Digital` |
   |---|---|
   | 100 % | 207, 0.0 dB |
   | 75 % | 194, -6.5 dB |
   | 50 % | 176, -15.5 dB |
   | 25 % | 148, -29.5 dB |
   | 10 % | 120, -43.5 dB |
   | 1 % | 91, -58.0 dB |
   | 0 % | 0, muted |

4. **Every rate reaches the card unchanged.** The card offers S16_LE, S24_LE,
   S32_LE, 8-384 kHz, two channels. Through `output`: 44.1, 48, 88.2, 96, 176.4
   and 192 kHz at 16 bits each opened the card at that rate and format; 24 bits
   in a 32-bit container at 44.1, 96 and 192 kHz opened it at S32_LE and that
   rate. Packed 24-bit (3 bytes) is refused, not converted - as it should be
   with nothing converting.
5. **Lyrion:** a 320 kbit/s MP3 at 44.1 kHz and a 16-bit 44.1 kHz FLAC both
   opened the card at S32_LE, 44.1 kHz - decoded and zero-padded, not
   resampled; Lyrion's own volume stays at 100 %, the card's control moves.
6. **De-emphasis is off, though the switch reads "on".** The driver declares
   the control inverted (`SOC_SINGLE("Deemphasis Switch", PCM512x_DSP,
   PCM512x_DEMP_SHIFT, 1, 1)` in `sound/soc/codecs/pcm512x.c`, rpi-6.18.y): "on"
   is the enable bit clear. Register 7 read `00` with the switch on and `10`
   with it off. Nothing of ours sets it; there is no saved mixer state.
   *Analogue* is at 0 dB, *Analogue Playback Boost* off, the DSP program the
   default FIR filter.

## What it means

ADR-0117's acceptance items 1 and 4 hold for this board for Lyrion and for
anything that plays through `output`; Spotify, Bluetooth and Plexamp share that
path and were not measured on it. For the player to call this board *Tested*,
it has to recognise it as a Pi-DAC PRO - by its EEPROM, since the card name is
shared - which it does not do yet.

## A mistake on the way

A dump of the chip's registers before and after flipping the switch differed
in dozens of places: register 0 is the chip's page selector, and reading the
dump moves it, so the diff was mostly noise. Only register 7, read against the
driver's definition, was used.
