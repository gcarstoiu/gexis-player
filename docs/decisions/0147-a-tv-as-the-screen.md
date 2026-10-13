# ADR-0147 — A TV as the screen, by choosing its port

**Status:** **Accepted** — 2026-10-13, decisions D1-D5 by George; the How is
filled in as it is built.
**Amends:** [ADR-0141](0141-picture-and-sound-on-different-hdmi-ports.md) (D2:
the Screen port choice), [ADR-0109](0109-other-screens.md) (decision 5: *Keep
this screen?* on the panel only), and George's ruling of 2026-10-12 that a TV
as the screen was out of scope.

## Context

George, on sofapi (the Waveshare 10.1" panel on HDMI 1, an LG TV on HDMI 2):
*"I can't change to hdmi 2 on sofapi."* Four times between 17:31 and 17:53
on 2026-10-13, choosing *Screen port → HDMI 2* moved the screen's settings to
HDMI 2 and restarted; at boot the screen check found the known panel on HDMI 1
by its EDID, logged *"waveshare-10.1-hdmi-b moved from HDMI-A-2 to HDMI-A-1;
the picture is unchanged, so it is kept"*, and put everything back. A known
panel's position outranked the choice (`screen_detect.seen`: the applied port
only if a known panel is there, else any known panel), and nothing said so.

Asked what the picker should do with a port whose device is not a supported
screen, George chose **"Let the choice win"** over greying it out - which, as
the question said, means a TV is the screen.

## Decisions (George, 2026-10-13)

- **D1 — The choice wins.** A port chosen under *Screen port* is where the
  picture goes, whatever is on the other port, as long as something is
  connected to it. Detecting a known panel's position still decides when
  nothing was chosen (a cable moved), as before.
- **D2 — Now, before 1.0** (over a phase of its own after the release).
- **D3 — *Keep this screen?* is answered from the phone** on a screen without
  touch: the phone page shows *Keep* and *Go back* while the TV counts down;
  with no answer the player goes back, as on a panel.
- **D4 — A TV runs at 1920x1080 at most**: its own mode up to 1080p, so the
  1920x1080 skin packs fit and the Pi 4's browser stays light; the TV scales
  it to its full screen.
- **D5 — The panel left on the other port is black, its touch ignored**, as a
  sound-only port is (ADR-0141 D3), so a stray tap does nothing on the TV.

## How

- **D1:** `Applied.chosen`, written to screen.json's `current` by
  `_choose_screen_port`; `screen_detect.seen()` returns that port first while
  something is connected to it, so the boot check (`screen_watch.moved`) no
  longer moves the screen back. Going back (`revert`) restores the screen
  before, without the mark, and detection follows a panel again. The screen
  applied is the one on the chosen port (`screen_watch.target`): the panel
  recognised there, else the device by its own mode; the panel's rotation
  goes back with it to its port.
- **D4:** `screens.fitted`: a 16:9 screen larger than 1920 x 1080 is
  `other-1920x1080-capped`, whose `video=HDMI-A-n:1920x1080` puts the kernel
  on the TV's 1080p mode; any other shape keeps its own mode (a size it does
  not offer would be calculated). New screens found at start take the same
  cap.
- **D3:** `screen_detect.has_touch`: a fingerprint naming a USB touch device.
  Without one the question carries `phone: true`; the core accepts the
  answer from the phone then (from the panel only otherwise, ADR-0109
  decision 2); the phone page shows *Keep this screen?* with *Go back* and
  *Keep* and the countdown; the panel's own says to answer on the phone.
- **D5:** screen.env's `GEXIS_SCREEN_TOUCH_USB` and `GEXIS_PANEL_TOUCH_USB`;
  `gexis-kiosk-start` switches off, in labwc's configuration, the input of
  every known panel that is not the screen, by the name
  `/proc/bus/input/devices` gives it (labwc 0.20.2 takes a device name as a
  `<libinput><device category>`). The panel's output stays black (ADR-0141
  D3).
- Display standby already turns off whichever port screen.env names, a TV's
  included.
- The port lines name a screen in no list by the name it gives ("LG TV").

Tests: `core/tests/test_tv_screen.py`.

## Unverified

When written: everything on a device - the LG TV on sofapi's HDMI 2 at
1080p, Keep from the phone, the panel's touch off, standby on the TV.

## Amended 2026-10-13: after George's test on sofapi

George, with the LG TV on HDMI 2 behind the Sony receiver: the picture
*"not that good - text is choppy and not the entire image is shown"*; *"If I
put the TV on standby the music stopped"*; the panel *"had its backlight on
and its touch resulted in actual touches"*; at the restart *"some smaller
black screen with what looked like command lines overlapped part of the
logo"*.

Found on the device:
- **The TV was set up as `other-640x480`**: the screen applied was read from
  the EDID's first timing, which the receiver gave as 640 x 480 at that
  moment (1280 x 720 later; it also names itself *SONY AVSYSTEM* or *LG TV*
  as it wakes). Page scale 0.5.
- **The music did not stop**: Lyrion played on. The sound output was HDMI 2
  through the receiver, and display standby turned that HDMI output off -
  HDMI's sound rides on its picture.
- **labwc's per-device switch did not hold**: the panel's touch device was
  named in `<libinput><device category="WaveShare  WaveShare ">` with
  `sendEventsMode no`, the name matched, and touches still arrived.

Decided (George, the same day, on the options):
- **D4 as amended — 1080p from the TV's own list**: `screen_detect.tv_mode`
  takes 1920 x 1080 from the kernel's mode list (`card*-HDMI-A-n/modes`), else
  the largest 16:9 mode below it, and the screen is `other-WxH-capped`, whose
  kernel `video=` holds the mode whatever a receiver says at a start.
- **Standby on a port carrying the sound: black, sound on**
  (`standby.carries_sound`): the output stays on, the panel's black cover is
  the standby. A port without the sound is turned off as before.
- **D5 as amended — the panel switched off**: screen.env's
  `GEXIS_OUTPUTS_OFF` names the ports with a known touch panel while the
  screen has no touch; the kiosk turns them off with `wlr-randr` (the
  backlight goes dark). Its touch is ignored by a udev rule the boot's screen
  check writes in `/run/udev/rules.d` (`LIBINPUT_IGNORE_DEVICE`, libinput's
  own); the labwc block is gone.

And, found with it: **a chosen port is not asked about at the start**
(`screen_watch.at_start`), since a receiver renaming the TV read as a
different screen attached.

**Open:** the console text over the boot logo on the TV - looked at once
the TV runs at 1080p; possibly the kernel's console drawn at another
screen's size. And whether the TV crops the edges (overscan) at 1080p: TVs
do unless set to *Just Scan* / *Original*.
