# ADR-0158 — DSI screens

**Status:** **Accepted** — 2026-10-23 (George, the same evening: *"Start
phase 17"*, then his answers to D1-D5 below). Phase 17, `ph-dsi`. Nothing
built yet; the measurements listed below come first.
**Amends:** [ADR-0109](0109-other-screens.md) (*HDMI only, for now*; a
choice that is applied at the next start now writes `config.txt` too),
[ADR-0135](0135-display-standby.md) (screen off on a DSI panel),
[ADR-0141](0141-picture-and-sound-on-different-hdmi-ports.md) and
[ADR-0147](0147-a-tv-as-the-screen.md) (which output is the screen).

## Context

The player drives HDMI screens only. ADR-0109 left DSI out on 2026-10-01
because a DSI screen *"needs its own `dtoverlay` in `config.txt`, which
applying does not write and nothing here can test"*; `screens.INTERFACES` is
`{"hdmi"}`, and 68 of the vendored list's entries are DSI. A DSI screen
plugs into the Pi's ribbon connector and leaves both HDMI ports free, for a
receiver, a sound bar or a TV.

George has one now: a **7" DSI touch panel, 800 x 480**, on bedroompi (Pi 4
Rev 1.4, gexis 1.4.0, flashed from the 1.1.1 image and updated). He wrote its
maker as "Hoysund"; the player's list has **Hosyond 7" DSI Display (800x480)**
(`hosyond-7-dsi`), and the card's previous screen was a Hosyond 5" HDMI, so
it is most likely that maker [to confirm with George]. He chose *HMTECH 7"
HDMI Monitor (800x480)* in Settings and it *"worked out of the box"*.

## Measured on bedroompi (2026-10-23, read only: nothing installed or changed)

- **The firmware found it by itself.** `config.txt` is Raspberry Pi OS's own
  (`display_auto_detect=1`, which our image does not touch; no `dtoverlay`
  for a screen). The firmware log: `Loaded overlay 'vc4-kms-dsi-7inch'` right
  after `vc4-kms-v3d-pi4`. That overlay is the one for the original
  **Raspberry Pi Touch Display (v1)**; the firmware loads it when a panel
  answers on the DSI connector's I2C bus at the Touch Display's address.
- **It answers as a Touch Display v1.** On the DSI I2C bus (`i2c-10`):
  `10-0045` bound to `rpi_touchscreen_attiny` (the Touch Display's power and
  backlight microcontroller, whose driver refuses a chip whose ID register is
  not one of the Touch Display's [from the driver's source as remembered, not
  re-read here]), `10-0038` bound to `edt_ft5x06`. The
  bridge is `toshiba,tc358762`, the panel node `raspberrypi,7inch-dsi`.
- **No EDID, no maker, no model.** DRM connector `card1-DSI-1`: connected,
  one mode 800x480, EDID 0 bytes. labwc lists `DSI-1`, Make and Model
  `(null)`, physical size 154 x 86 mm - the driver's fixed figure for the
  Touch Display, not read from the panel. **Nothing the Pi can read tells this
  panel from the original Touch Display** or from any other panel built to
  answer as one. The original itself is not on the bench, so "reads the
  same" is from the drivers, not compared.
- **Touch: an I2C controller, not USB.** `10-0038 generic ft5x06 (79)`,
  `/dev/input/event4`, a touchscreen to udev (`ID_INPUT_TOUCHSCREEN=1`),
  reporting `BTN_TOUCH` (so the core's `TouchWatch` would see it). It has no
  USB vendor and product, which every touch fingerprint in
  `screen_detect.FINGERPRINTS` and every touch-off udev rule (ADR-0147 D5)
  is written in.
- **A backlight the player can set.** `/sys/class/backlight/10-0045`: type
  `raw`, `max_brightness` 255, at 255; `brightness` writable by `video`,
  `bl_power` by root (the core runs as root). Neither was written.
- **Outputs:** `DSI-1` connected; `HDMI-A-1` and `HDMI-A-2` disconnected.

### Why the HMTECH choice half-works

It works because nothing about it reaches the DSI panel. The firmware brings
DSI-1 up whatever Settings says; Chromium fills the only output; the layout
is right because the HMTECH 7" is 800 x 480 too (Standard at scale 0.625, the
size tested on sofapi on 2026-10-20). Touch works because labwc's
`<touch mapToOutput="HDMI-A-1"/>` names an output that does not exist, so
labwc does not tie the touch to any output [inference from labwc's
behaviour: touch works, per George], and because the touch-off rules list
USB devices only.

What does not work, all of it aimed at `HDMI-A-1`:
- **The 180° rotation is never applied**: the kiosk logs *"could not turn
  HDMI-A-1 to 180"* at each start (18:57:53, 19:00:45). The picture is upside
  down on George's stand.
- **Display standby cannot turn the screen off**: the core logs *"wlr-randr
  refused to turn the screen on: unknown output HDMI-A-1"* (19:50:52). Off,
  the panel draws its black cover, with the backlight still at 255.
- **The kiosk's background** (`swaybg -o HDMI-A-1`) has no output to go to.
- ***Keep this screen?* goes to the phone**: the HMTECH has no touch by its
  fingerprint, so the player believes this screen has none.
- **A receiver on HDMI would become the screen** [from the code, not tried]:
  `screen_connector()` in `gexis-kiosk-start` and `screen_detect.seen()` look
  only at HDMI ports and take a connected one.

## Settled by the evidence

1. **No `config.txt` writes for a panel the firmware detects.** For the Touch
   Display v1 and the panels that answer as one, the image as it is brings
   the panel up; the player only has to recognise it. Phase 17's criterion 1
   (*"nothing edited by hand"*) holds for this class already.
2. **A DSI panel is seen as a DRM connector, `DSI-<n>`**, beside the HDMI
   ports: `screen_detect.ports()` reads `card*-DSI-*` as well as
   `card*-HDMI-A-*`, with its mode from `modes`, no EDID. Its fingerprint is
   the connector, the mode, and the panel's own I2C devices: the backlight
   controller (`rpi_touchscreen_attiny` at `0045`) and the touch
   (`edt_ft5x06` at `0038`) under the DSI bus. A new kind of fingerprint
   beside the USB one.
3. **Rotation the way the HDMI screens are turned**: `wlr-randr --output
   DSI-1 --transform`, and `<touch mapToOutput="DSI-1"/>` so the touch turns
   with it - the route the bars have used since ADR-0109 (a 90° turn, touch
   following). The overlay's own `rotation=` parameter would need a
   `config.txt` write and is not used. Rotation stays 0° / 180° for a
   landscape panel.
4. **Layout from the size, as now**: 800 x 480 is Standard at 0.625. A
   portrait panel such as the Touch Display 2 (720 x 1280) is turned 90° and
   used at 1280 x 720, Standard at scale 1 (ADR-0109 decision 6) [not on the
   bench].
5. **Touch is the panel's own once it is known as a DSI panel**: `has_touch`
   and `touch_recognised` take the I2C touch device as the USB one is taken,
   so *Keep this screen?* is answered on the panel. Where a touch has to be
   ignored (ADR-0147 D5: a TV chosen), the rule names this device by its
   input name or sysfs path, not a USB ID.
6. **Everything aimed at "the screen's connector" accepts `DSI-<n>`**: the
   kiosk's connector check (`^HDMI-A-[0-9]+$` today), the background, the
   window rule, standby's output, `screen.env`, `screen.json`. A DSI panel
   gets no `video=` line: its mode is the panel's only one.

## Decided (George, 2026-10-23)

**D1 — Every DSI screen in the list.** George: *"For all that we have in
the dsi list that we deferred until now."* Not only the panels the firmware
detects: every DSI model the list holds, as ADR-0109 lists every HDMI one.
Of the list's 68 DSI entries, 63 remain after ADR-0109's own filters (no
square panels, a case listed as its panel); **60 are offered**:
- **23 on the Touch Display v1 overlay** (`vc4-kms-dsi-7inch`): brought up
  by the firmware itself (*Settled by the evidence* 1), nothing written;
- **37 with an overlay of their own** (Waveshare's DSI panels, the Touch
  Display 2 on `vc4-kms-dsi-ili9881-7inch`, the generic ones): the player
  writes it (*Applying a DSI screen*, below);
- **3 left out**: Waveshare's 4.3" rev 1, BIGTREETECH's PiTFT50 v1.0 and
  DFRobot's 5" v1.0. Their list entries (`emit_dsi_overlay: false`) run
  them only with `vc4-kms-v3d` removed, and the player's compositor needs
  the KMS driver that removes.

The Hosyond 7" is tested (on bedroompi); every other DSI model is listed
untested, as the untested HDMI screens are.

**D2 — A model picked from the list shows its own name.** George: *"If
the user selects from a list shouldnt we display that name?"* - yes. The
name shown, in setup and in *Settings → Display*, is the model chosen. Only
a panel recognised and not yet chosen (setup's suggestion, before anyone
picks) needs a name the player can stand behind, since nothing it reads
tells the makers apart: it is suggested as **7" DSI touch screen, 800 x 480
(Raspberry Pi Touch Display or compatible)**, and choosing a maker's model
from the list instead names that one from then on. The class entry and
the 23 models apply the same thing (nothing written).

**D3 — The DSI panel is the screen, and the user can switch.** George:
*"Agreed. User can still switch if he wants though."* With a DSI panel
connected it is the screen, and the HDMI ports carry sound (black,
ADR-0141 D2). *Screen port* lists *DSI* beside *HDMI 1* and *HDMI 2*; an
HDMI port chosen there wins (ADR-0147 D1: a TV), with the DSI panel then
black and its touch ignored, and choosing *DSI* again goes back.
*Settings → Display* names each output: *DSI - screen (<the model>)*,
*HDMI 1 - sound (AV receiver)*.

**D4 — Standby turns the backlight off.** George: *"Agreed"*: `bl_power`
off, the output kept on and the black cover drawn, so the picture comes
back as fast as the backlight and the touch still reaches the compositor.
If the measurements below show the backlight does not go dark that way, the
output off (as on HDMI) is the fallback, and George hears which.

**D5 — Screen brightness, where it can be set.** George: *"Agreed"*: the
registry's `brightness` row (10-100 %, default 100 %) is shown on a screen
whose backlight the player can set - a DSI panel today - and hidden on an
HDMI screen. Applied at once, kept across restarts. Display standby's
backlight off is separate from it: waking returns to the brightness set.

**Still to confirm with George:** the maker and model on the panel or its
box (Hosyond 7" DSI, 800 x 480?), so the tested mark goes on the right
entry.

## Applying a DSI screen that needs its overlay (settled, Claude)

`config.txt` is read only at boot, as `cmdline.txt` is, and ADR-0109's
apply already writes `cmdline.txt` (`video=`) with a restart and *Keep this
screen?*. A DSI model's overlay goes the same way:
1. **One block of our own at the end of `config.txt`**, under `[all]`,
   between `# gexis screen (ADR-0158) - written by the player` and
   `# end gexis screen`: the model's `dtoverlay` (and `dtoverlay_2` where the
   list has one), as the list gives them. Nothing else in `config.txt` is
   changed, `display_auto_detect=1` included. A model on
   `vc4-kms-dsi-7inch`, an HDMI screen or no screen leaves the block empty.
2. **Written as `cmdline.txt` is** (`_replace_durably`: a copy, synced,
   renamed over), and only when it changes.
3. **Choosing such a model restarts the device** and asks *Keep this
   screen?*, as any screen choice that needs the next boot does. Not kept,
   or never drawn (`NEVER_DRAWN_S`), it goes back: the block as it was, and
   another restart. A wrong overlay leaves the panel dark, which is the
   case this exists for.
4. **The overlay's own `rotation=` is not used**; rotation is the
   compositor's (*Settled by the evidence* 3).

## Settings (ADR-0022, appended on George's confirmation)

| Row | Mark | What |
|---|---|---|
| Screen brightness | [N] -> [R] | D5: Display, shown only on a screen whose backlight the player can set (a DSI panel today); 10-100 %, default 100 %, at once |
| Screen port | [R], options extended | D3: *DSI* beside *HDMI 1* and *HDMI 2* when a DSI panel is connected; the DSI panel is the default, an HDMI port chosen wins |

No other new setting: rotation, standby and *Attached screen* are the
existing rows, applied to `DSI-1`.

## To measure before building (bedroompi, with George watching the panel)

- **Touch at 180°** with `mapToOutput="DSI-1"`: a tap at each corner lands
  where the finger is.
- **The backlight**: `bl_power` off and on (dark? how fast back?);
  `brightness` steps visible over 10-100 %; the output off (does the backlight
  go dark? how long to come back?). The watts saved, if a meter is to hand.
- **With a receiver or TV on HDMI**: all outputs up together (DSI and two
  HDMI on a Pi 4 [inference from the hardware's three display channels]),
  the sound on HDMI with the DSI panel as the screen (Phase 17 criterion 2).
- **A card flashed from the image** with the panel attached: setup's Screen
  step recognises it (criterion 1).

## Unverified

- That the original Touch Display v1 reads exactly as this panel does (not
  on the bench).
- That the firmware detects the Touch Display 2 without a `config.txt` line.
- That a panel built to answer as a Touch Display always does: one that
  does not shows nothing until its model is chosen and its overlay written.
- **Every overlay-written model** (37): that its overlay, as the list gives
  it, brings it up beside `display_auto_detect=1` on a Pi 4. None is on the
  bench; the way back (*Applying a DSI screen*, step 3) covers a wrong one.
- That the Touch Display 2 and the other portrait panels come up turned to
  landscape with touch following (*Settled by the evidence* 4).
