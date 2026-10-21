# Finding 133 — Glass against our visualiser: cheaper on every skin measured, at a third of the memory

**Date:** 2026-10-21. **For:** George (*"Can you have a look at foonerd
repos. I believe he just took over glass which should cut the processor time
from what I remember."*, then *"Yes. Let's learn"* and *"Do a thorough test
and let's have as complete results as possible"*).

This replaces the first version of this Finding, written the same evening
from a short silent run, whose needle-meter figures for ours were taken with
the needles at rest (LESSONS 80).

## What Glass is

foonerd's Rust replacement for PeppyMeter Screensaver (MIT; its analyser
Apache-2.0), release 0.10.33 (`glass-0.10.33-armv8.tar.gz`, SHA-256 checked,
the sums' Ed25519 signature verified with the key in its repository). It reads
PeppyMeter themes as they are, draws through SDL2 (OpenGL on Wayland here),
takes its levels from an ALSA plugin of its own (`glasstap`, inside the audio
process, writing a ring under `/dev/shm`) and the player's state from a
Volumio plugin's socket. The repository went public on 2026-09-24: one
contributor, 648 commits and over a hundred releases by 2026-10-17 (three that
day), one star, no issues filed.

## Scope

- **Devices:** ShelvesPi (Pi 4, 64-bit, 1480 × 320 bar on HDMI-A-1,
  gexis-player `1.3.1+git25`, `gexis-skins-1480x320 1.2.0+git33`) and sofapi
  (Pi 4, 1280 × 800 panel on HDMI-A-1 and a TV on HDMI-A-2, gexis-player
  `1.3.1+git28`), labwc 0.20.2.
- **Nothing installed or changed for good.** Glass ran from `/tmp` as `pi`
  with a private home and `.asoundrc`. Changed for the test and put back,
  each checked afterwards: the visualiser's skin, rotation, timeout and stop
  settings; Lyrion's queue position, pause, volume, repeat and power; the CPU
  governor; `/run/gexis/attenuation` (below), which the core rewrote itself at
  the restoring volume change.
- **Ours** drew with real music through Lyrion (volume 5, so the rooms stayed
  quiet), its whole state - title, art, position, play state. **The meter's
  volume cut was held at 0 dB** (`/run/gexis/attenuation`): our needles follow
  half of it (`meter_follow`), which at volume 5 held them at the bottom. On
  ShelvesPi the needles then moved with the music near 0 dB (checked by
  screenshots 0.5 s apart). **On sofapi they did not move at all**: the level
  from squeezelite's own tap reads zero on its HDMI output (Open, below), so
  sofapi's figures for ours carry no needle work.
- **Glass** drew the same skin from the same pack files, fed the player's
  state by a bridge of ours speaking its channel protocol from
  `/run/gexis/nowplaying.json` (title, artist, album, art, position, play
  state, next track - all shown), and levels by a 44.1 kHz test signal (pink
  noise with a tremolo and a sweep) through `glasstap` to a null sink.
- **Matched work:** both at 30 frames a second; turning parts at 8 redraws a
  second in 6° steps (ours *Stepped*, Glass `rotation.quality = medium`).
  **As configured:** ours *Smooth* (ShelvesPi's own setting) against Glass's
  shipped default (custom, 25 a second).
- **Measured** over 60 s after 10 s to settle, per process (user + system time
  of every thread, as % of one core) and resident memory; the system's busy
  share of all four cores; the V3D GPU's busy share; SoC temperature and clock.
  CPU pinned at 1.8 GHz (`performance`) unless said; three skins also under
  the shipped `ondemand`. Surface commits a second counted from libwayland's
  own debug log for both (`WAYLAND_DEBUG=client`), in separate runs. No
  throttling in any run (`get_throttled` 0x0, 64-72 °C).
- **Not measured:** power (the Pi 4 has no rail readout); Glass in our real
  audio chain (its tap measured on its own, below); a Pi 3 or Pi 5; skins at
  other sizes; Glass under our standby, dashboard and touch handling; the
  layers only we draw (fanart, badges) beyond what the skins show.

## Results

### 1. ShelvesPi, 1480 × 320, matched, 1.8 GHz

| Skin | Ours | Glass | Glass's tap | Compositor, ours / Glass | GPU, ours / Glass | Memory, ours / Glass |
|---|---|---|---|---|---|---|
| Accuphase (needles) | 13.7 % | 4.0 % | 2.6 % | 3.2 / 2.7 % | 8.2 / 6.3 % | 258 / 93 MB |
| Marschal (spectrum) | 19.4 % | 3.1 % | 2.6 % | 3.9 / 2.5 % | 10.1 / 5.3 % | 252 / 86 MB |
| Marschal S+M | 22.0 % | 3.2 % | 2.6 % | 6.7 / 3.0 % | 17.4 / 7.0 % | 252 / 89 MB |
| Thorens (turntable) | 26.8 % | 6.2 % | 2.7 % | 7.5 / 3.2 % | 19.0 / 7.4 % | 253 / 95 MB |
| Pioneer Gold (turntable) | 17.8 % | 5.1 % | 2.7 % | 4.2 / 2.8 % | 10.5 / 6.7 % | 255 / 95 MB |
| Akai 77 (tape) | 16.8 % | 5.1 % | 2.7 % | 4.0 / 1.6 % | 10.0 / 4.2 % | 260 / 89 MB |

Ours' own tap is the peppyalsa scope inside squeezelite (squeezelite whole:
2.3-2.8 %). With Glass's tap counted, Glass is 2.1 to 3.8 times cheaper on every
skin (2.1 times on the needle meter, 3 to 3.8 on the spectrum and Thorens);
the compositor and the GPU work less behind it too.

### 2. ShelvesPi, as configured (ours *Smooth*, Glass's default)

| Skin | Ours | Glass + tap |
|---|---|---|
| Thorens | 45.2 % | 8.1 + 2.6 % |
| Pioneer Gold | 36.1 % | 6.7 + 2.6 % |
| Akai 77 | 30.3 % | 8.6 + 2.6 % |

### 3. ShelvesPi under the shipped `ondemand` governor (matched)

| Skin | Ours | Glass + tap | Clock |
|---|---|---|---|
| Accuphase | 23.4 % | 7.1 + 5.5 % | about 1.0 GHz |
| Thorens | 39.9 % | 10.6 + 5.3 % | about 1.2 GHz |
| Akai 77 | 24.7 % | 8.7 + 5.5 % | about 1.1 GHz |

Both cost more as the clock drops (the share of a slower core); the order
stays.

### 4. sofapi, 1280 × 800, the 1280 × 720 packs - ours without needle work

| Skin | Ours, matched | Glass + tap, matched | Ours *Smooth* | Glass default + tap |
|---|---|---|---|---|
| Pioneer Gold | 26.4 % | 11.7 + 2.7 % | 73.3 % | 18.3 + 2.8 % |
| Pioneer PLX-500 | 26.9 % | 12.6 + 2.7 % | 84.2 % | 19.8 + 2.8 % |
| Streamer CD | 18.1 % | 8.7 + 2.6 % | - | - |
| Akai 77 black | 25.4 % | 12.5 + 2.7 % | - | - |
| Revox B77 | 25.1 % | 14.9 + 2.8 % | 67.2 % | 25.9 + 2.9 % |

Ours' memory grew as skins were shown, 364 MB to 502 MB over the run (each
turning skin's frames kept); Glass's stayed 93-114 MB. These five are among
the eight of Glass's own benchmark (Pi 5, 1280 × 720, an older release: 38-44
% each, against 70-84 % for the Python engine); here Glass's default came to
18-26 % on a Pi 4 with release 0.10.33.

### 5. The taps, on their own (ShelvesPi, a null sink, 1.8 GHz)

| Signal | peppyalsa | glasstap default (128 bands × 2, 8192 window) | asked for 32 bands × 1, 2048 | asked for 256 × 2, 16384 |
|---|---|---|---|---|
| 44.1 kHz, 16-bit | 0.5 % | 2.6 % | 1.0 % | 5.3 % |
| 96 kHz, 32-bit | 0.8 % | 5.4 % | 2.0 % | 11.2 % |
| 192 kHz, 32-bit | 1.5 % | 10.4 % | 4.0 % | 21.8 % |

`aplay` alone into the null sink: 0.0-0.2 %. Glass's tap runs in the audio
process; at high rates its default costs more than any skin's drawing above.
The demand is written by Glass's own plugin per theme; without it the default
applies.

### 6. Smoothness, start, stability

- **Frames.** Glass held 29.9 frames a second in every run on one painting
  thread (its own `GLASS_PROFILE`), repainting 1-12 % of the bar a frame
  (ShelvesPi) and 9-32 % of the panel (sofapi). Surface commits a second,
  ours / Glass: Accuphase 24.5 / 21.7, Marschal S+M 55.3 / 25.7, Thorens
  52.8 / 29.9, Akai 33.4 / 13.6 (ours presents each layer on its own, so its
  count is not its frame rate).
- **Start.** Ours: ready in 3.0 s (ShelvesPi, 2.6 s of processor) and 7.5 s
  (sofapi, 7.1 s) - it loads every skin of the size; 151-169 MB when ready.
  Glass: its window in 0.25-0.35 s, sixty frames drawn by 2.3-2.4 s, 0.6-1.2 s
  of processor, 96-113 MB - one theme only.
- **Over time.** Thorens, five and ten minutes each: ours 26.6-28.5 % and
  Glass 6.2-6.5 % (+ 2.6-2.7 %), each minute; memory grew by about 1-2 MB in
  ten minutes on both.

### 7. What each draws

From the screenshots, both drew every skin whole: records and reels turning,
tonearms, CDs, needles, spectrum bars, art, time, the track's text. The
differences: ours sets the text in the skins' own fonts with our badges and
ellipsis; Glass, with the font folder this test gave it, fell back to a
monospaced face, overlapping in places and nearly unreadable on the white
PLX-500 - a configuration of the test, not measured further. Ours drew a black
box over part of the spectrum on Marschal S+M (Open).

## What this says

- **Glass is cheaper on everything measured here,** with its tap counted:
  2.1 to 3.8 times on ShelvesPi and 1.4 to 1.8 on sofapi (where ours drew no
  needles) at matched work, 2.3 to 4.2 times against our *Smooth*
  rotation, at a fifth to a third of the memory, and it starts in a fraction
  of the time. The compositor and the GPU were less busy behind it on
  ShelvesPi; on sofapi it was mixed (the compositor busier behind Glass on
  four of five skins, the GPU on three). Its tap is the one place it costs more, and it is in
  the audio process.
- **Taking it would be a project, not a swap:** the tap into the audio chain
  for every output (an ADR; and the HDMI chains of ADR-0055 and Finding 116 to
  prove again), our state over its channel (the bridge here is a sketch), its
  start, stop, standby and dashboard under the core in place of `wlrctl`
  raise and hide, the fonts, and our own layers (badges, fanart, the text
  layer) - none tried. And it is one person's month-old project releasing
  several times a day.
- **Some of the gap is ours to close:** *Smooth* rotation costs ours 1.7 to 3.1
  times *Stepped*; ours keeps every skin of the size loaded.

## Open

- **sofapi's needles get no level on HDMI 2** (software volume): the level from
  squeezelite's peppyalsa scope read zero throughout while the spectrum read
  small values (2026-10-21, at Lyrion volume 5; not checked at a normal
  volume). Whether the needles move there in everyday use is not known.
- **Ours, Marschal S+M on 1480 × 320:** a black box over part of the spectrum
  bars behind the title (one screenshot pair).
