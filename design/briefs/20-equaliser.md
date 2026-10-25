# Brief for Claude Design — The equaliser (Phase 20)

Written 2026-10-25 for George to hand to Claude Design. Background, if you
want it: [ADR-0162](../../docs/decisions/0162-a-simple-equaliser.md) (the
equaliser, George's decisions of 2026-10-25). What is built and differs from
the earlier designs is in
[`IMPLEMENTED-DIFFERENTLY.md`](../IMPLEMENTED-DIFFERENTLY.md).

---

**Gexis Player** is a music player for the Raspberry Pi 4. It usually has its
own touchscreen (the "panel": 7" to 13.3", most often a 10.1" 1280 x 800, or a
wide *bar*, 11.9" 1480 x 320 or 7.9" 1280 x 400), and every player has a phone
page. It plays from a **Lyrion Music Server** and is also a **Spotify
Connect** speaker, a **Plexamp** player and a **Bluetooth** speaker. Every
source plays through the equaliser.

Please use the existing design (its tokens, type and components) and export
as before: the artboard HTML/CSS, a PNG per state, new tokens as CSS custom
properties, and component boundaries.

## What the equaliser is

- **Ten bands**: 31, 63, 125, 250, 500 Hz, 1k, 2k, 4k, 8k, 16k, each from
  −12 to +12 dB, 0 in the middle. A change is heard at once, while the band
  moves.
- **On / off.** Off, the sound is untouched (bit-perfect).
- **Presets**: Flat, Rock, Pop, Jazz, Classical, Electronic, Hip-hop,
  Acoustic, Vocal, Late night.
- **The owner's own**: up to ten, named - saved from the bands as set
  (*Save as…*), renamed, deleted. Listed with the presets. Moving a band away
  from a preset makes it *Custom* until it is saved.
- **Per output**: the DAC, HDMI and optical each remember whether it is on and
  which preset; the page says which output it is setting.
- **Headroom**: a boost lowers the overall level a little so it cannot clip
  (*Lowered by 4 dB so the boost cannot clip*). Under *Fixed volume* (an
  amplifier sets the volume) that note matters most.
- **Native DSD skips it**: while a DSD track plays, the equaliser stands aside
  and says so (*DSD plays untouched*).

## 1. The editor, in Settings → Audio → Equaliser

The whole of it: on / off, the ten bands with their values, the preset or
setting in use, the list of presets and the owner's own, *Save as…*, rename,
delete, and the headroom note.

**Sizes:**
- the panel, 1280 x 800 (and the 7" to 13.3" family);
- the bars, 1480 x 320 and 1280 x 400 (laid out at 1850 x 400 CSS px, drawn
  at 0.8);
- the phone (about 360-430 px wide), where ten upright sliders would be under
  the touch floor (44 logical px): rows, or another way that fits.

## 2. Quick change, close to the music

A small control that shows the preset in use and changes it, with on / off and
a way to the editor:
- **the phone's pull-up tray** (the one with the touchpad, Home, Playing,
  Lyrics and Meters, and the volume);
- **the panel's volume drawer** on Now Playing;
- **the bar's tray** (Home, the volume, the visualiser).

## States

- off; on with a preset; on with one of the owner's; *Custom* (bands moved,
  not saved);
- a band being dragged (its value shown);
- *Save as…* (naming), rename, delete (confirm), the list full at ten;
- the headroom note, with and without *Fixed volume*;
- DSD playing (the equaliser standing aside);
- a player without a screen (the phone only).
