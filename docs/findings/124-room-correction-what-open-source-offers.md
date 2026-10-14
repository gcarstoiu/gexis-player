# Finding 124 — Room correction: what open source offers, and the microphones

**Date:** 2026-10-14. **Asked by:** George (Phase 15, `ph-room-correction`:
*"we need to create a Dirac live alternative based on open source software
that we could use in our player"*, and a top 3 of microphones under €200 in
Germany).

## Scope

Desk research only: vendor pages, manuals, papers, source repositories and
shop pages, each opened (not taken from search snippets). Nothing was run on
a player. Prices are as seen on 2026-10-14. Not reachable that day:
dirac.com (HTTP 429), eBay.de (HTTP 403), several Thomann pages (HTTP 429).

## What Dirac Live does

From Dirac's own paper (Brännmark & Sternad, ISEAT 2015,
http://www.signal.uu.se/Publications/pdf/c1506.pdf) and Rotel's Dirac Live
training guide (Oct 2020):

- **Mixed-phase, multi-position least-squares inverse filters**: they
  minimise the weighted error over a set of listening positions, with a
  modelling delay, limited gain and limited pre-ringing at every position.
  The target is an impulse response, not just a magnitude curve.
- **Measurement**: 9, 13 or 17 positions in a sphere of at least 1 m, the
  first one being the sweet spot that sets level and delay; microphone
  pointing up with a 90° calibration file; level calibration first.
- **Design screen**: an automatic, editable target curve; "curtains" that
  set the band corrected; before/after and impulse views. About 7 ms of
  added delay. Part of the design runs on Dirac's cloud.
- **Tiers**: "Limited" corrects up to 500 Hz, "Full" the whole range;
  Bass Control (subwoofers together) and ART (20-150 Hz, using the other
  speakers) are paid extras.

## The open-source pieces

| Project | Does | Licence | State (2026-10-14) | For us |
|---|---|---|---|---|
| CamillaDSP | runs filters: FIR, biquads, delay, volume, resampler; websocket control | GPL-3.0 or MPL-2.0 | v4.1.3; v5.0.0-beta.1 on 2026-10-08 | **the engine**: aarch64 ALSA builds, used by moOde and Volumio on the Pi 4 |
| pycamilladsp | Python control of CamillaDSP | GPL-3.0 | v4.0.0 | fits the core |
| alsa_cdsp | ALSA plugin that starts CamillaDSP per sample rate | MIT | dormant since 2022 | one way to insert it |
| DRC-FIR | designs correction filters: mixed phase, pre-echo truncation, psychoacoustic target; sweep and deconvolution tools | GPL-2+ | 3.2.3 (2019), packaged for Debian trixie arm64 | Dirac-like design, but from **one** impulse response |
| PORC | designs mixed-phase filters (Carini's multipoint method, partly) | BSD-2 (file headers) | 2023, Python 2-era | reference code |
| pyfar | Python: sweeps, deconvolution, inversion, windowing | MIT | 0.8.1 | **base for our measurement code** |
| Rsantct/DRC | Python: sweep measurement, multi-position averaging, minimum-phase FIR | GPL-3+ | 2026-01 | reference; magnitude only |
| HiFiBerry roomeq | Pi measurement REST API, microphone table, parametric-EQ optimiser | MIT | 0.7.4 (2026-07) | reference; magnitude only |
| BruteFIR | convolution engine | ISC | "legacy, low maintenance" | fallback engine |
| REW, rePhase | measurement and design | closed freeware | — | **cannot be shipped** |

No open-source project does Dirac's multi-position mixed-phase design end to
end; that part would be ours.

## A Pi 4's capacity

The one published Pi 4 figure: CamillaDSP v0.5.0, 8 channels x 262k taps at
192 kHz, about 55 % CPU (its README; its issue #473 calls the benchmark
outdated, and v5 adds faster convolution). Stereo at 65k taps should cost a
fraction of that by CamillaDSP's own scaling rule, **to be measured on a
player with the visualiser running** before any figure is promised.

## Pitfalls on a Pi

- **Two clocks**: a USB microphone and the DAC drift apart; REW warns this
  distorts long sweeps' impulse and phase. There is no loopback with a USB
  microphone, so drift must be estimated from the recording (an acoustic
  timing reference) - ours to write.
- **48 kHz**: the UMIK-1 records only at 48 kHz; filters for other rates are
  derived by resampling (DRC's manual advises measuring at the native rate).
- **The output device**: the renderers hold `output`; a measurement must take
  it and play through the same chain as music, at a calibrated level.
- **Rate changes**: CamillaDSP needs a fixed capture rate - restarted per
  rate (alsa_cdsp) or fed through an ALSA loopback with rate adjust.
- **Bit-perfect and DSD**: correction ends bit-perfect output; CamillaDSP is
  PCM only, so DSD would bypass it.
- **An AV receiver** adds its own correction and delay unless set to Direct
  (not verified per receiver).

## A stack for the player (recommendation, for the ADR)

- **Run**: CamillaDSP, controlled from the core with pycamilladsp.
- **Measure**: our own Python on pyfar - sweeps, calibration file, levels,
  several positions, drift correction, taking the output device.
- **Design, in two tiers**: first, magnitude correction of the averaged
  positions, mostly cuts, below a set frequency (about what "Dirac Limited"
  does, without the time-domain part); then a Dirac-like mixed-phase design,
  starting from DRC-FIR and growing into our own multi-position design after
  the Dirac paper and Carini.

## The microphones (USB, under €200, Germany)

1. **miniDSP UMIK-1**: driverless USB Audio Class 1 on Linux (vendor); used on
   Raspberry Pis (ALSA list, noise_monitor project); its own 0° and 90°
   calibration files per serial; 24-bit at a fixed 48 kHz. New from €99
   ([Kleinanzeigen, commercial seller](https://www.kleinanzeigen.de/s-anzeige/-minidsp-umik-1-kalibriertes-usb-messmikrofon-neuware/3519353131-172-4392)),
   €134.90 ([md-sound](https://www.md-sound.de/MiniDSP-UMIK-1-Plug-Play-USB-Messmikrofon-Neu)),
   €149 with the shop's own calibration ([HiFi-Selbstbau](https://shop.hifi-selbstbau.de/produkt/minidsp-messmikrofon-umik-1/)).
   No second-hand units found that day.
2. **Dayton Audio iMM-6C**: about €45 ([SoundImports](https://www.soundimports.eu/en/dayton-audio-imm-6c.html)),
   per-serial calibration, Class 1 accuracy in audioXpress's test; one user
   report on Linux only; a USB-C plug needs an adapter on the Pi, and it
   shows up as a second sound card (it has a headphone output).
3. **Dayton Audio UMM-6**: per-serial calibration, works on Linux with quirks
   (stereo-only capture, its name has varied); out of stock in Germany that
   day ([SoundImports](https://www.soundimports.eu/en/dayton-audio-umm-6.html)).

For the build: find the microphone by its USB identity, not its ALSA name
(the UMIK-1's name carries its gain, "U18dB"); set its gain explicitly; use
only the frequency response from its calibration file.

## Not verified

The Pi 4 cost at our filter lengths; DRC-FIR's run time on a Pi 4; the iMM-6C
on Linux beyond one report; the UMIK-1 "V3" changes; receivers' bypass modes.
