# ADR-0141 — Picture and sound on different HDMI ports

**Status:** **Partly accepted** — 2026-10-12. D2 and D4 accepted and built
(George: *"I agree to both. Go ahead."*); D1, D3, D5, D6 still owed.
**Touches:** [ADR-0055](0055-which-output-the-device-plays-to.md) (Open §1),
[ADR-0109](0109-other-screens.md), [ADR-0127](0127-one-volume-row.md),
[ADR-0135](0135-display-standby.md).

## Context

George, 2026-10-12: *"we need to look at having different combinations of
sound output and hdmi output. For example output video on hdmi1, but audio in
hdmi2. Right now for video we don't even show the second hdmi port as not
connected."*

The Pi 4 has two HDMI ports (DRM `HDMI-A-1`, `HDMI-A-2`; ALSA `vc4hdmi0`,
`vc4hdmi1`). What the code does today (read 2026-10-12, not measured with two
ports connected):

- **Sound.** The Output row lists both ports, with "— nothing connected"
  from the port's hot-plug state (`outputs.py`, `_connected`). The note is
  display only: an unplugged port can still be chosen, and playback on it
  fails with error 524 (Finding 116).
- **Picture.** The screen is the *first connected* port (`screen_detect.seen`).
  Until the fix of 2026-10-12 everything after detection assumed `HDMI-A-1`.
  Nothing on the screen side names a port, so the second port never appears.
- **The compositor.** labwc has no output layout: with both ports connected
  it is expected (not measured) to extend the desktop across both. The second
  port then shows the boot artwork. Chromium stays on the screen's port, and
  the visualiser window is not pinned to any port.
- **The driver** [inference, vc4 behaviour, not recorded here]: HDMI sound
  plays only while that port is driving a picture, and never to a DVI-only
  device. So sound on HDMI 2 needs HDMI 2 switched on with *some* picture.
  Display standby, which turns off the screen's port, must never turn off the
  port the sound is on.

### What works today

| Picture | DAC / USB / jack | HDMI 1 | HDMI 2 |
|---|---|---|---|
| Screen on HDMI 1 | works | works through a screen with speakers; standby would cut it | expected to work, untested; HDMI 2 shows the boot artwork |
| Screen on HDMI 2 | works once the connector fix lands | the receiver on HDMI 1 is taken for the screen: needs this ADR | the screen's own port, as row 1 |
| No screen | works | untested: the console picture may keep the port alive | as HDMI 1 |

## Proposal

1. **The screen's port is detected, and asked only when unclear.** A port
   with a known panel (EDID matches a listed screen), or the only connected
   port, is the screen. When both ports are connected and neither is a known
   panel, setup and Settings ask which one is the screen. Everything that
   acts on the screen (layout, touch, the kiosk, the visualiser, standby)
   follows that one port.
2. **A port that carries sound only shows black** at a modest mode
   (1280×720 suggested [inference]: enough for full HDMI audio, light on the
   GPU). The kiosk and the visualiser are pinned to the screen's port.
3. **Settings shows both ports** in the Screen section, e.g. *HDMI 1 — screen
   (Waveshare 10.1")*, *HDMI 2 — sound (AV receiver)*, *HDMI 2 — nothing
   connected*. The Output row marks the screen's port the same way.
4. **Standby never turns off the port the sound is on.** When the screen's
   own port carries the sound, standby turns the backlight off where it can
   and otherwise shows black with the signal kept (the alternative ADR-0135
   already names).
5. **A port that disappears while chosen** (a receiver switched off) shows a
   notice in Now Playing. The player does not move the sound to another
   output by itself.
6. **Measure before building:** two ports connected on the bar (the panel
   plus a receiver or TV on HDMI 2). Measure the layout, sound on HDMI 2,
   standby, the receiver going into standby, and headless with HDMI sound.
   The results become a finding, and the proposal is corrected from it.

## Decisions owed by George

- **D1 — When:** before the first public release, or after it? Unchanged
  today: the screen-on-HDMI-1 cases work, and the HDMI-2 sound case is
  expected to work but is untested.
- **D2 — The screen's port:** detected and asked only when unclear (1), or
  always a choice in Settings? Either way it is a setting for ADR-0022's
  inventory [N].
- **D3 — What a sound-only port shows:** black (2), the boot artwork as
  today, or the now-playing screen as well.
- **D4 — The Screen section listing both ports (3):** yes or no.
- **D5 — A receiver that disappears (5):** a notice only, or fall back to
  another output.
- **D6 — Test hardware for (6):** is a receiver, sound bar or TV with HDMI
  in available to connect to the bar's second port?

## Out of scope

A TV as the screen (ADR-0109 amendment, 2026-10-12). Fixed volume with the
visualiser on HDMI (ADR-0055 §6) is a separate question, though a receiver
is the obvious case for it.

## Decided 2026-10-12: D2 and D4

George, asking *"how should I change screen to the other HDMI if I'm only see
the one screen in settings. Shouldn't we have two entries, similar to audio
output?"*, then *"I agree to both. Go ahead."*:

- **D4: the Screen section lists both ports** - *HDMI 1*, *HDMI 2*, each
  saying the screen by its model, another device by the name it gives, *sound*
  when the output is that port, or *Nothing connected*.
- **D2: the port is detected, and a choice only while both have something on
  them** (*Screen port*, ADR-0022). With one port connected the cable decides,
  as the fix of the same day made it (ADR-0109's amendment). Choosing the
  other port applies the same screen there: a restart and *Keep this screen?*.
- **Detection with both connected** (proposal 1, built): the applied port if a
  known panel is there; any port a known panel is on; the applied port; else
  the first connected. A chosen port therefore holds across starts, and a
  panel moved away from it is followed.
- **The kiosk window is pinned to the screen's port** whenever both ports are
  connected, not only off HDMI-A-1.

Still owed: **D1** (the rest before or after 1.0), **D3** (what a sound-only
port shows - today the boot artwork, as labwc extends the desktop onto it),
**D5** (a receiver that disappears), **D6** (hardware to test with).

