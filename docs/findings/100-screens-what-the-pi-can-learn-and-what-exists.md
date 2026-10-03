# Finding 100 — Screens: what the Pi can learn about one, and what exists for each size

**Date:** 2026-09-28
**Question:** Before Phase 13b (other screens): can the device recognise the
screen it drives — maker, model, resolution, size — and what already exists
for the sizes George wants (800×480, 1280×800, 1920×1080 at 13.3", and the
bars 1280×400 and 1480×320, both used landscape)? Visualiser skins per
resolution, and known screen configurations.

**Scope:** `gexis` (Waveshare 1280×800 HDMI panel, USB touch), read
2026-09-28 from `/sys/class/drm` and `/proc/bus/input/devices`, EDID decoded
by hand (no `edid-decode` on the image). **One screen only** — every other
statement about screens is from published lists, not hardware. Skin counts
from PeppyMeter's repository (`project-owner/PeppyMeter`, folders at its
default branch) and foonerd's catalog
(`foonerd/peppy_templates` at `f80c166a`, `catalog/index.json`, updated
2026-09-23). Screen presets from `foonerd/pi_screen_setup`,
`display_presets.json` version 1.5.9 (2026-03-24), MIT. **Not tested:** any
bar, any DSI screen, any other panel, rotation under labwc, whether each
catalog pack's licence allows shipping.

## What gexis's panel says about itself

| Source | Value |
|---|---|
| Connector | `card1-HDMI-A-1`, connected; EDID 256 bytes |
| EDID maker / name | `WAV` (Waveshare) / "WaveShare"; product code 0; year 2016 |
| Modes | preferred **1280×800**, also 1920×1080 |
| EDID size, basic block | **121 × 68 cm** (a 55" television) |
| EDID size, detailed timing | **294 × 165 mm** (a 13.3" 16:9 screen) |
| Touch controller | USB `0712:0010`, "WaveShare" |

- **Maker and resolution are reliable; physical size is not.** The two size
  fields disagree with each other and with the panel: cheap panels carry a
  television's EDID. Touch-target sizing in millimetres cannot come from EDID
  alone.
- **The touch controller's USB ID names the maker too**, independently of
  the display link.

## Visualiser skins, per resolution

> **Corrected 2026-09-30:** the table below shows Gelo5 at 1280 × 800 only,
> because only the set we ship was looked at. Gelo5 publishes a set for every
> size George has, in PeppyMeter.doc's release 2024.03.02: 1920 × 1080 (120
> skins, 325 MB), 1280 × 400 (120, 116 MB), 1480 × 320 (116, 99 MB), 800 × 480
> (60, 48 MB), also 1024 × 600, 1920 × 480, 1920 × 515 and 3840 × 2160 (found
> when George said *"More available from gelo5"*).

Skins are bitmaps for one exact resolution; none scales.

| Resolution | PeppyMeter stock | Gelo5 | foonerd catalog (packs / skin names) |
|---|---|---|---|
| 320×240 | 25 | – | – |
| 480×320 | 25 | – | – |
| 800×480 | 25 | – | 33 / ~100 |
| 1024×600 | – | – | 6 / ~106 |
| 1280×400 | 8 | – | 35 / ~172 |
| 1280×720 | – | – | 20 / ~251 |
| 1280×800 | – | **84 (shipped)** | 12 / ~109 |
| 1366×768 | – | – | 9 / ~186 |
| 1480×320 | – | – | 8 / ~175 (72 with spectrum) |
| 1920×440 / 480 / 515 / 550 / 720 | – | – | 12 / 5 / 11 / 8 / 1 packs |
| 1920×1080 | – | – | 17 / ~310 |
| 3840×2160 | – | – | 2 / ~31 |

The catalog counts are skin names summed over a pack's units, so a skin can be
counted twice; treat them as approximate. The 1280×720 packs are already
letterboxed onto the 1280×800 panel (ADR-0096), which is the precedent for an
in-between screen: the nearest set, letterboxed.

## Known screen configurations (foonerd's presets)

- **197 models**: 116 HDMI, 68 DSI, 13 DPI, over 20 makers (mostly Waveshare;
  Joy-IT, Adafruit, Elecrow, GeeekPi, UCTRONICS, Pimoroni and others).
- **Per model:** `native_resolution`, `recommended_rotation`, often
  `rotated_resolution` and `notes`, and the boot configuration: `config.txt`
  keys (`hdmi_group`, `hdmi_mode`, `hdmi_timings`, overlays with a rotation
  parameter) and a `video_mode` for `cmdline.txt`.
- **No recognition data**: no USB touch IDs, no EDID strings. Its
  "Auto Detect (EDID)" entry writes nothing. It is a list to choose from.
- **Against George's sizes:** 800×480 — 52 models; 1280×800 — 18 (Waveshare
  10.1" (B), Joy-IT 10.1"); 1920×1080 — 8 (Waveshare 13.3" HDMI LCD (H));
  1480×320 — Waveshare 11.9" HDMI and DSI, **listed as portrait 320×1480**;
  1280×400 — Waveshare 7.9" HDMI and DSI, **portrait 400×1280**, e.g.
  `hdmi_timings 400 0 220 32 110 1280 0 10 10 10 0 0 0 60 0 59400000 3`,
  `video_mode 400x1280M@60`, rotation 90.

**Both bar sizes are portrait panels driven sideways.** They need timings and a
mode line before they show anything properly, then a rotation.

**Not all of it applies here, as read, not measured:** gexis runs full KMS
(`vc4-kms-v3d`) with labwc. Under KMS the firmware's `hdmi_timings` /
`hdmi_mode` are understood not to apply; the kernel's `video=` mode and the
compositor's rotation do. Each preset used would be translated and tried on
the hardware, not copied.

## What it bears on

- Phase 13b's recognition is ours to build: EDID (maker, name, modes) and the
  USB touch ID suggest a model, the user confirms on the phone.
- The presets are the seed for a table of screens we support, MIT, credited.
- A skin set per screen family, picked by resolution; the picker offers only
  the current screen's.
