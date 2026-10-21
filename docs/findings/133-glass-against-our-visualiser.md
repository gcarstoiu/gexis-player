# Finding 133 — Glass against our visualiser: on the meters alone, no saving to speak of

**Date:** 2026-10-21. **For:** George (*"Can you have a look at foonerd
repos. I believe he just took over glass which should cut the processor time
from what I remember."* — then *"Yes. Let's learn"*).

## Scope

- **What Glass is:** foonerd's Rust replacement for PeppyMeter (MIT; the
  analyser Apache-2.0), release 0.10.33, `glass-0.10.33-armv8.tar.gz`, its
  SHA-256 checked and the sums' Ed25519 signature verified against the key
  in its repository. It reads PeppyMeter themes, draws through SDL2 (OpenGL
  on Wayland here), and takes its levels from an ALSA plugin of its own,
  `glasstap`, which writes a ring under `/dev/shm`.
- **Device:** ShelvesPi (Pi 4, 64-bit, 1480 × 320 bar on HDMI-A-1, governor
  `ondemand`, 1.8 GHz), gexis-player `1.3.1+git25` (the 2026-10-21 preview,
  canvas driver), `gexis-skins-1480x320 1.2.0+git33`, labwc 0.20.2.
- **Nothing installed or changed for good:** Glass ran from `/tmp`, as `pi`,
  with a private home and a private `.asoundrc` (`HOME` pointed at the trial
  folder); the system's ALSA chain and services were not touched. The
  visualiser's skin settings were set for the test and put back (revision
  22); the trial folder was removed.
- **Signal:** 200 s of pink noise with a tremolo and a sweep (44.1 kHz,
  16-bit, peak 0.48, RMS 0.10), fed in real time to `aplay` into a `null`
  sink — silent — through a `meter` PCM with our `peppyalsa` scope for ours,
  and through `type glasstap` for Glass. Both drawing loops at 30 frames a
  second. Needles checked moving in both (two screenshots 0.5 s apart).
- **Measured:** CPU from `/proc/<pid>/stat` (user + system, every thread)
  over 30 s, as a share of one core; resident memory. The `aplay` process
  carries the tap, as squeezelite would.
- **Not measured, and why it matters:**
  - **Real playback.** The core did not see anything playing, so our
    turntable skin did not turn its platter (Glass's did, from the levels).
  - **Glass's player state.** Glass reads the track, art and transport from
    a Volumio plugin's socket, which we do not have: it drew no title, no
    art, no clock. Ours drew all of them. So the two pictures were not the
    same work, the turntable skin least of all.
  - Spectrum skins, other sizes, sofapi, a Pi 5, longer runs, the start-up
    cost.

## Results

1. **A needle meter (`01G5_Accuphase`):**

   | | drawing | its tap (audio process) | together | memory |
   |---|---|---|---|---|
   | Ours | 7.9 % | 0.6 % (peppyalsa) | 8.5 % | 238 MB |
   | Glass | 5.1 % | 5.0 % (glasstap) | 10.1 % | 92 MB |

   Glass draws the meter for about 3 points less; its tap costs about 4
   points more, in the audio process.
2. **A turntable (`103G5_Thorens`):** ours 16.7 % + 0.7 %, Glass 8.7 % +
   4.2 % — **not comparable**: ours scrolled the track line and showed the
   art with the platter still, Glass turned the platter with neither (Scope).
3. **The tap's cost follows what it is asked to measure.** With no demand
   file it measures 128 bands a channel from an 8192-sample window (5.2 % of
   a core alone); asked for 32 bands of one channel from 2048 (what a needle
   skin could ask), 1.8 %. peppyalsa's scope alone: 0.8 %.
4. **Memory is Glass's clear gain:** about 90 MB against about 235 MB, shown
   or hidden (ours keeps its process and every skin's pictures loaded; hidden
   it uses 1.2–2.3 % of a core).
5. **It works on our system as it is:** it listed and drew our packs from
   `/opt/gexis-peppy/packs` unchanged, its graphics probe passed (V3D, EGL on
   the bar's card), and its window came up over the bar's whole output under
   labwc.
6. **Levels read differently.** On the same signal Glass's needles stood near
   −30 dB on the Accuphase scale and ours near −45 dB: the two taps condition
   the level differently (Glass: a 500 ms fall, then its own conditioning).

## What this says

- The author's figures (38 % of a core against 70 %, 122 MB against
  1030 MB; Pi 5, 32-bit, Volumio's PeppyMeter) compare Glass with a
  PeppyMeter that redraws far more than ours does. Our driver already draws
  only what changed, so on a needle meter the drawing saving here was about
  3 points of one core, and the default tap took it back.
- What Glass would bring is memory, and probably the heavy skins — a
  turning platter and scrolling text — which this test could not compare
  fairly. That needs a run with music playing through Lyrion and Glass fed
  the player's state.
- Taking it would mean: the tap in the audio chain (a system ALSA change,
  an ADR), feeding it the player's state over its socket, its start and stop
  under the core in place of `wlrctl` raise and hide, and the visualiser's
  layers of our own (badges, fanart, the canvas) — none of which was tried.
