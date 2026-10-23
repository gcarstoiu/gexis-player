# ADR-0158 — DSI screens

**Status:** **Proposed** — 2026-10-23. Phase 17, `ph-dsi` (George, 2026-10-23:
*"Start phase 17"*). Nothing built yet. The decisions marked **Decision for
George** below are his; the rest is settled by what bedroompi showed.
**Amends, once accepted:** [ADR-0109](0109-other-screens.md) (*HDMI only, for
now*), [ADR-0135](0135-display-standby.md) (screen off on a DSI panel),
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

## Decisions for George

**D1 — Which screens this phase brings in.**
- **(a) The ones the firmware detects by itself**: every listed model on the
  Touch Display v1 overlay (`vc4-kms-dsi-7inch`, 23 entries - the original,
  the Hosyond 5" and 7", BIGTREETECH and others), the Hosyond 7" marked
  tested; and the Touch Display 2 (`vc4-kms-dsi-ili9881-7inch`), listed
  untested, if the firmware detects it as well [to check from Raspberry Pi's
  documentation before listing it].
- **(b) Also the DSI screens that need an overlay written** (Waveshare's
  DSI panels and the rest, 44 entries): a `config.txt` writer with a
  way back if the panel stays dark, none of it testable here.
- **Recommendation: (a).** It needs no write to the boot partition, and the
  one panel on the bench stands for the whole class: they answer the same
  driver the same way. (b) comes back when a screen of that kind is on the
  bench, as ADR-0109 said of DSI.

**D2 — What a detected panel is called**, since the player cannot tell
which maker's it is.
- **(a) One entry for the class**: *7" DSI touch screen, 800 x 480
  (Raspberry Pi Touch Display or compatible)*, recognised by setup and shown
  in Settings; the makers' models stay in the list and apply the same thing.
- **(b) The tested model's name**, Hosyond 7" DSI, for any such panel - the
  original Touch Display would be shown as a Hosyond.
- **(c) The original's name**, Raspberry Pi Touch Display, for any such
  panel - marking it tested on the strength of a clone.
- **Recommendation: (a).** It is true of every panel it will be shown for,
  and ADR-0109's rule (recognition suggests only a tested model) holds: the
  class is what was tested.

**D3 — Which is the screen when HDMI is connected too.**
- **(a) The DSI panel, whenever it is connected**; an HDMI port carries
  sound (black, ADR-0141 D2) unless *Screen port* chooses it (ADR-0147 D1,
  the choice wins: a TV). *Screen port* then lists *DSI* beside *HDMI 1* and
  *HDMI 2*, and *Settings → Display* names each: *DSI - screen (7" DSI touch
  screen)*, *HDMI 1 - sound (AV receiver)*. With a TV chosen, the DSI panel
  is black and its touch ignored, as a panel on the other HDMI port is today.
- **(b) Ask in setup and Settings whenever both are connected.**
- **Recommendation: (a).** A panel on the ribbon is almost always the
  screen, and Phase 17's reason for being is HDMI left free for sound.

**D4 — How display standby turns a DSI panel off.**
- **(a) The backlight off** (`bl_power`), the output kept on and the black
  cover drawn: the picture comes back as fast as the backlight, and the
  touch keeps reaching the compositor.
- **(b) The output off**, as on HDMI: the panel driver powers the panel and,
  through it, the backlight down [inference from the driver]; coming back
  re-initialises the panel, which may take as long as the 3 s George found
  too much on 2026-10-20 (`wlopm`).
- **Recommendation: (a)**, if measurement agrees: both are timed on
  bedroompi before building.

**D5 — A brightness setting.** ADR-0022 holds *Screen brightness* as [N]
(*"brightness is a separate question"*), and the registry has its row
(`brightness`, 10-100 %, not shown).
- **(a) Show it where the backlight can be set**: on a DSI panel, hidden on
  an HDMI screen, where nothing can set it. 10-100 %, default 100 %, applied
  at once and kept across restarts.
- **(b) Not in this phase.**
- **Recommendation: (a)**: it is the one thing a DSI panel can do that the
  HDMI screens cannot, and the row is already designed.

**To confirm with George:** the panel's maker and model as written on it or
its box (Hosyond 7" DSI, 800 x 480?).

## Settings (for ADR-0022, on George's confirmation; not appended)

| Row | Mark | Proposal |
|---|---|---|
| Screen brightness | [N] -> [R] | D5 (a): Display, shown only on a screen whose backlight the player can set (a DSI panel today); 10-100 %, default 100 % |
| Screen port | [N], options extended | D3 (a): *DSI* listed beside *HDMI 1* and *HDMI 2* when a DSI panel is connected |

No other new setting: rotation, standby and *Attached screen* are the
existing rows, applied to `DSI-1`.

## To measure before building (bedroompi, with George's say-so)

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
  needs its overlay written would show nothing and fall under D1 (b).
