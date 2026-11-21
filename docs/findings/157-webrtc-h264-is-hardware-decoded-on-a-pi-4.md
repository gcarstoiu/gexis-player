# Finding 157 — A WebRTC H.264 stream is decoded in the Pi 4's hardware

**Date:** 2026-11-21. **For:** another Home Assistant session's report, the
same day, that a page with one camera was taken down for the heat on sofapi
after 1-3 minutes (ADR-0176 P8). George asked for hardware decoding to be
looked into before deciding what the heat guard should do. Run on sofapi at
his word, the player idle.

## Scope

- **Device:** sofapi, Raspberry Pi 4 Model B Rev 1.5, kernel 6.18.60+rpt.
  It runs Raspberry Pi's Chromium 156.0.8078.79-1~deb13u1+rpt1 with
  `rpi-chromium-mods` 20260211. `bcm2835_codec` is loaded and the decoder
  is `/dev/video10`.
- **How:** a second Chromium with its own profile in `/tmp`, started the way
  the screen's browser is: Wayland, `--use-angle=gles`,
  `--enable-gpu-rasterization`, the same render node. It ran as a small
  window on the screen for about a minute per run. In one page, it sent
  itself a 1280x720 canvas stream over WebRTC, encoded as H.264
  (constrained baseline, OpenH264) and decoded by the second peer
  connection. A fake camera made Chromium report the decoder in use
  (`getStats`: `decoderImplementation`, `powerEfficientDecoder`; withheld
  otherwise). Two runs: hardware decoding as the screen's browser has it,
  then forced off with `--disable-accelerated-video-decode`.
- **Not valid, and not used:**
  - two first runs without a window, where Chromium runs with the GPU
    switched off (`video_decode: disabled_software`) whatever the flags;
  - every CPU figure. The test's own software encoder kept the whole Pi at
    about 390 % of one core, and sofapi was at 84 °C with the soft
    temperature limit active (`0xe0008`), so no saving can be read from
    them.
- **Not tested:**
  - a camera's real stream through go2rtc (High profile, a camera's frame
    rate);
  - the screen's own browser;
  - more than one stream;
  - another Pi 4;
  - a Pi 5.

## Results

| Run | Decoder (`decoderImplementation`) | Power-efficient | The GPU process holds `/dev/video10` | Frames decoded |
|---|---|---|---|---|
| Hardware decoding as the screen's browser has it | `ExternalDecoder (V4L2VideoDecoder)` | yes | yes | 493 and 615 (two runs) |
| Forced off | `FFmpeg` | no | no | 496 and 530 |

The browser's own GPU report listed **no video decoding profiles** in either
run (`SystemInfo`, `videoDecoding` empty), with `video_decode: enabled` in
the first. An empty list therefore does not mean software decoding.

## What it means

- **One camera on the screen is most likely already hardware-decoded.** The
  screen's browser has the same build, flags and GPU path. A camera's own
  High-profile stream was not tried.
- **Finding 142's software decoding is explained differently.** It read the
  empty profile list as software decoding. Raspberry Pi's build keeps about
  two decoders at once since 152 rpt2
  ([raspberrypi/trixie-feedback#101](https://github.com/raspberrypi/trixie-feedback/issues/101)),
  so with seven cameras most streams fell back to software.
- **Hardware decoding does not make video free.** Each frame is still drawn
  and copied by the GPU; a patch to put page video on its own display plane
  is proposed upstream
  ([#109](https://github.com/raspberrypi/trixie-feedback/issues/109)).
- **The heat on 21 November came mostly from elsewhere.** sofapi stood at
  77.9 °C with no page showing: the screen's browser alone took about 0.9 of
  a core for what it showed, and the load averaged about 2.1 over four days.
  One stream took it past ADR-0176's 80 °C in a warm room.
