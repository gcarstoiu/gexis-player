# Finding 116 — The meter over software volume on HDMI: squeezelite runs and the levels arrive

**Date:** 2026-10-07. **For:** George's question, *"with software on hdmi,
shouldn't now peppy work as well?"* HDMI carries no meter since 2026-09-23
(`outputs.render`): with `meter` straight over `plug`, go-librespot aborted on
`pcm_meter.c:1222: snd_pcm_scope_s16_get_channel_buffer: Assertion
's16->buf_areas' failed` and squeezelite logged `_write_frames:615 mmap_commit
error` ten times a second and played silence. With software volume (ADR-0124,
ADR-0127) the chain could be `meter → softvol → plug → card` instead.

## Scope

- **Device:** `guestpi` (Pi 4, IQaudIO Pi-DAC PRO, 13.3" Waveshare on HDMI 1),
  gexis-core 0.9.3+git38. Volume on Software, output switched to HDMI 1 by the
  player, then `output.conf` edited by hand to put `type meter` (with the
  peppyalsa scope) in front of each softvol PCM; squeezelite restarted.
- **Played:** LMS (squeezelite) only, 44.1 kHz tracks, about 35 s, one track
  change. **At LMS volume 0**, the software control at 0 (−90 dB) throughout:
  silent.
- **Not tested in the first run:** go-librespot (needs a phone), bluealsa-aplay, 96 and
  192 kHz, and whether the visualiser receives *levels*: LMS at volume 0 sends
  a stream of zeros before the meter - the pipe held only zeros on the DAC's
  own metered chain too (the control). The unconnected HDMI 2 port, which would
  have made a test with real levels silent, refuses to open (`audio open error:
  Unknown error 524`).
- `aplay` through the same chains (silence, plain and mmap) ran clean - and so
  did the September chain, `meter` straight over `plug`, so `aplay` does not
  reproduce that failure and is no evidence either way.

## Results

1. **squeezelite played through `meter → softvol → plug → hw:vc4hdmi0`**: the
   HDMI PCM `RUNNING` as IEC958_SUBFRAME_LE at 44.1 kHz for the whole run and
   across the track change; **no `mmap_commit` error, no assertion**, in its
   journal.
2. **The peppyalsa scope was live**: squeezelite held the meter FIFOs open, and
   the meter pipe delivered 200 bytes a second - all zeros, as the stream was.

## Second run, at LMS volume 30 (George: *"I can temporarily put the volume higher"*)

- **Method corrected.** Reading `/run/gexis/meter.fifo` with `cat` gave zeros
  on the DAC's own working chain too, at a level where the visualiser moves: it
  races `gexis-meters`, the pipe's real reader, and proves nothing. Read
  instead: the meter service's WebSocket (`ws://127.0.0.1:8091/meter`), which
  is what the visualiser is fed, for 6 s. Its needle levels are already scaled
  by the volume (ADR-0057), so at −26 dB they sit near 0; **the spectrum bands
  are the sign of music arriving**.
- **Control, the DAC's own chain** (`meter → softvol → hw:IQaudIODAC`), LMS at
  30, software level 256 (−26 dB): 172 messages, bands e.g.
  `[12, 13, 9, 7, 4, 0, …, 4, 9, 0]`.
- **HDMI, `meter → softvol → plug → hw:vc4hdmi0`**, same level: 172 messages,
  bands e.g. `[5, 4, 2, 3, 4, 1, 0, 0, 0, 2, 5, …, 5, 9, 0]`; HDMI `RUNNING`;
  no mmap error or assertion from squeezelite.

## What it means

**For LMS, the visualiser works on HDMI with software volume**: the September
squeezelite failure did not recur with `softvol` between `meter` and `plug`,
and the levels reach the visualiser as they do on the DAC. **go-librespot is
still untested** - it was the renderer that aborted in September - as are
bluealsa-aplay and rates above 44.1 kHz.
