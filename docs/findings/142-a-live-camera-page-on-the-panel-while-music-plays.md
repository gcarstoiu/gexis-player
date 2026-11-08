# Finding 142 — A live camera page on the panel while music plays

**Date:** 2026-11-07. **For:** Phase 35 (`ph-ha-page`): the measurement
before the ADR - what a Home Assistant page of live cameras costs a Pi 4
while music plays. One run; no more were wanted (George, 2026-11-07).

## Scope

- **Device:** sofapi, a Raspberry Pi 4 Model B (Rev 1.5, 1.8 GHz),
  gexis-player 1.14.0, Chromium 156 under labwc, on Wi-Fi; HiFiBerry DAC2 HD.
- **Music:** George's, from Lyrion through Squeezelite, at 44.1 kHz (S32_LE
  at the DAC, a 40 ms buffer in 10 ms periods). No 192 kHz music was to hand.
  Equaliser and room correction off: the plain path.
- **The page:** a Home Assistant view made for TVs, seven cameras live over
  WebRTC (H.264), muted, no sound. Framed over the panel by an iframe added
  through DevTools with the dashboard's sandbox, as Phase 35 would frame it;
  not the built feature.
- **The run:** 2 minutes of music alone, 25 s for the page to settle, 5
  minutes with the page, 1 minute after it was removed.
- **Read:** `/proc/stat` every second, per process, Chromium's grouped by
  process type; the DAC's ALSA status 20 times a second (its state and
  `avail_max`); temperature, throttling, clock and free memory every 10 s;
  the video elements' sizes and frame counts at the start and end of the 5
  minutes; the browser's GPU information. Numbers only: nothing else read from
  the page, no screenshots.
- **What the DAC readings cannot see:** an underrun the player recovers from
  between two reads (50 ms apart), and a gap further up, where Squeezelite
  runs short and plays silence. George listened; no dropout was reported in
  the session.
- **Not tested:** 192 or 96 kHz; the equaliser's or room correction's stage
  (about 5 % of a core at 192 kHz, Finding 138); fewer cameras or the
  doorbell's one; longer than 5 minutes (Phase 35's default limit is 10);
  Ethernet; another Pi 4, a bar or another screen.

## Results

1. **The music kept playing at the DAC, with half the margin.** Every
   reading showed it running (2,350 alone, 5,737 with the page); no underrun.
   How empty the 40 ms buffer came (`avail_max`, of 1,764 frames):

   | | Music alone | With the page | After |
   |---|---|---|---|
   | Emptiest | 956 (18 ms left) | 1,320 (**10 ms left**) | 912 (19 ms left) |
   | 99th percentile | 892 | 964 | 892 |

2. **The page took about 1.6 cores more.** Averages over each phase, as a
   share of one core unless marked:

   | | Music alone | With the page | After |
   |---|---|---|---|
   | All four cores (of 100 %) | 19 % | 59 % (86 % peak second) | 21 % |
   | Chromium's renderer | 15 % | **105 %** | 16 % |
   | Chromium's GPU process | 20 % | 60 % | 22 % |
   | Chromium's network service | - | 6 % | - |
   | Squeezelite | 4.7 % | 8.5 % | 4.8 % |
   | The Wi-Fi driver's worker | 0.7 % | 4.4 % | 1.0 % |

   The busiest core reached 92.5 % with the page. Free memory went from
   2.4 GB to 2.0 GB.

3. **The temperature was still climbing.** 64 °C with the music alone,
   **74 °C at the end of the 5 minutes**, its highest reading, and 67 °C a
   minute after. Nothing throttled (`get_throttled` 0x0 throughout); the Pi
   4's firmware starts slowing the processor at about 80 °C.

4. **H.264 is decoded in software.** The browser lists no video decoding
   profiles (`SystemInfo`, `videoDecoding` empty) although its feature
   status says `video_decode: enabled`. The GPU process opened the Pi's
   decoder (`/dev/video10`, twice) while the page was up and not before;
   whether any stream went through it is not established, and the
   renderer's 105 % is where software decoding runs.

5. **Most pictures kept coming, with frames dropped, and two nearly
   stopped.** Frames over the 300 s by the video elements' own counts
   (`getVideoPlaybackQuality`): frames a second counts every frame received,
   the dropped ones included.

   | Size | Frames a second | Dropped |
   |---|---|---|
   | 1280 x 960 | 19.6 | 3.4 % |
   | 1280 x 720 | 14.7 | 7.2 % |
   | 1280 x 720 | 14.8 | 6.4 % |
   | 1280 x 720 | **3.0** | 7.3 % |
   | 640 x 360 | 24.5 | 14.7 % |
   | 640 x 360 | 24.9 | 12.4 % |
   | 640 x 360 | **0.5** | 15.8 % |

   For the two slow ones, a stalled stream and a reconnect (which starts a
   new count) cannot be told apart from two readings. Three of the seven
   came at 1280 x 720, not the 640 x 360 their streams were thought to have.

## What it means for Phase 35

- Seven live cameras fit beside music on the plain path at 44.1 kHz, but
  they halve the DAC's margin. A higher rate and the equaliser's or room
  correction's stage add to the load and were not measured; the ADR should
  not assume they fit.
- Heat is what to watch over the 10-minute default: 74 °C and rising after
  5 minutes, on this Pi.
- Fewer cameras, and 640 x 360 streams in place of 1280 x 720, should cost
  less (a 720p frame has 2.25 times the pixels); not measured.
- The ADR should say what the player does when the load is too much, and
  that one camera page per screen is the case it was measured for.
