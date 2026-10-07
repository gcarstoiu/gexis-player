# Finding 115 — Software volume: unchanged at 0 dB, and where it sits on HDMI

**Date:** 2026-10-07. **For:** ADR-0124 (software volume), which said both
questions here were *to be measured, not assumed*.

## Scope

- **Device:** `guestpi` (Pi 4, kernel `6.18.50+rpt-rpi-v8`, alsa-lib
  `1.2.14-1+rpt1+deb13u1`), idle. Everything in a private ALSA configuration
  (`~/.asoundrc`, removed after); nothing of the player's was used or changed.
- **Question 1:** does ALSA's `softvol` at its top (0 dB) pass every sample
  unchanged? Method as Finding 003: seeded white noise played through `softvol`
  into `snd-aloop`, captured on the loopback's other side, compared sample by
  sample; three runs each at 44.1 kHz S16_LE, 96 kHz S32_LE and 192 kHz S32_LE
  (24-bit noise in a 32-bit container); and the same nine runs straight into the
  loopback with no `softvol`, as the control (Finding 004).
- **Question 2:** on an HDMI output, which needs `plug` for its IEC958 format,
  can `softvol` sit in front of it? Silence at 48 kHz through
  `softvol → plug → hw:vc4hdmi0`, on the connected HDMI port.
- **Not measured:** `softvol` together with the meter tap (Finding 003 measured
  the meter alone); levels below 0 dB beyond a sanity check; an HDMI receiver's
  sound.

## Results

1. **Not one sample changed in value at 0 dB**, in any of the 18 runs. Every
   difference between what was sent and what came back was a block of samples
   received as zeros near the end of the capture - 328 to 1,034 at 44.1 kHz,
   768 at 96 kHz, 1,536 at 192 kHz - and the **same blocks appear with no
   `softvol` at all**: the loopback's own artefact, as Finding 004 found.
2. **Below 0 dB the samples change**, as they must: at 50 % the noise's
   opening could not be found in the capture.
3. **On HDMI, `softvol` in front of `plug` works:** the port opened as
   IEC958_SUBFRAME_LE, 2 channels, 48 kHz, and the control was created on the
   HDMI card (`vc4hdmi0`), 0 dB at 100 %.

## What it means

ADR-0124's chain holds: **`meter → softvol → card`** on an output that needs
nothing converted - and at 100 % (0 dB) playback stays bit-perfect - and
**`softvol → plug → card`** on HDMI, where there is no meter (the meter crashes
over `plug`, `outputs.render`) and nothing was bit-perfect to begin with.

*Left over:* the test's control (`SVHdmi`) stays on the HDMI card until
`guestpi` next restarts - ALSA keeps a user control while its card exists. It
is not used by anything.
