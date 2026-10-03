# Finding 106 — What is known about DACs without owning them

**Date:** 2026-10-01
**Question:** George: *"how can we make sure we support more DACs without me
having to go and buy and test each? Is there a repo of DACs and their
capabilities that can be checked?"*

**Scope:**
- **Read, not measured:** public repositories and this repository's code. No
  DAC other than the DAC2 HD on the bench was run.
- **Commits as read on 2026-10-01:**
  - moOde: `moode-player/moode` develop @ cb63a186d4.
  - Volumio: `volumio/volumio3-backend`, `dacs.json` last changed c82d2341a3.
  - Raspberry Pi kernel: `raspberrypi/linux` rpi-6.12.y @ a553c4648f and
    rpi-6.18.y @ 7044e8a79a.
- **Counts:**
  - Volumio's and moOde's rows were counted by hand from their files.
  - The kernel's audio overlays are a keyword count filtered by hand:
    approximate.

## What gexis assumes about a DAC today

- **The output is already found, not named.**
  - `outputs.discover()` reads `aplay -l`.
  - The volume control is the first `* Playback Volume` in `amixer contents`.
  - `aplay --dump-hw-params` says whether a `plug` layer is needed, and
    `output.conf` is written for the card chosen.
- **Only a board that loads its own overlay is seen.** Nothing writes an
  audio `dtoverlay=` into `config.txt`, so only HATs with an EEPROM work.
- **The hardware volume scale is the DAC2 HD's.** `volume.py`: `HARDWARE_MAX
  = 240`, `DB_MIN = -120`, `DB_STEP = 0.5`, used at start-up in `__main__.py`.
  Any control with another range is driven with wrong raw values.
- **The DAC2 HD is named in places:** `alsa.CARD_ID = "sndrpihifiberry"`,
  `config.mixer_name = "DAC"` as a fallback, and `docs/ARCHITECTURE.md`.

## The lists that exist

| Source | Rows | Holds | Licence |
|---|---|---|---|
| Volumio, `app/plugins/system_controller/i2s_dacs/dacs.json` | 108 (98 for the Pi) | overlay, ALSA card name, mixer (61 rows), EEPROM name (17), I²C address, init script (9), reboot needed | GPL-3.0-only (`package.json`, `LICENSE.md`) |
| moOde, `var/local/www/db/moode-sqlite3.db.sql`, table `cfg_audiodev` | 75 (68 I2S) | name, chip, interface, overlay and its options; **no mixer, no DSD** (moOde hardcodes mixer exceptions in `alsa.php`) | GPL-3.0 |
| Raspberry Pi kernel, `arch/arm/boot/dts/overlays/README` | about 71 audio overlays (6.12) | what can be loaded, with parameters | GPL-2.0 (kernel) |

- **Volumio identifies boards itself:** `/proc/device-tree/hat/product`,
  then I²C probes, then a match against its table.
- **moOde's "long list"** is mostly every overlay on the card that declares
  `sound-dai-cells`, not tested boards.
- **Quality of Volumio's data, seen in passing:**
  - `iqaudio-dacplus` appears twice, once with the card name and once
    without;
  - one overlay string carries a trailing space.

  It needs reading, not only importing.

## George's two DACs, in Volumio's list

| Board | Overlay | Card | Mixer | EEPROM name | Script |
|---|---|---|---|---|---|
| HiFiBerry DAC2 HD | `hifiberry-dacplushd` | `sndrpihifiberry` | `DAC` | "DAC 2 HD" | none |
| IQaudIO DAC Plus | `iqaudio-dacplus` (`,unmute_amp` in one row) | `IQaudIODAC` | `Digital` | none listed | `iqamp-unmute.sh` |

The two differ in every field that matters: overlay, card, mixer, whether
the board names itself, and the script. Between them they exercise
self-identification and the overlay picker, and two volume scales.

## What the device can learn by itself

- **Card and device:** `aplay -l`.
- **The board, if it has an EEPROM:** `/proc/device-tree/hat/{product,vendor}`.
- **Formats, rates and channels:** `aplay --dump-hw-params`.
- **Volume controls and their dB range:** `amixer contents`, whose
  `dBscale` line gives the minimum and the step - the numbers `volume.py`
  hardcodes.
- **USB DACs:** `/proc/asound/cardN/stream0` lists what the device declares;
  class-compliant ones need no list. Not tried on gexis.

**What hw_params cannot say:** for I2S, it reports what the driver
*permits*, not what the board's clocks and analogue stage really play. Pops,
muting, DSD and init scripts are judged by ear, on the board.

## Decided (George, 2026-10-01)

1. **Its own phase, after 13b** (*"For sure its own phase after 13b"*).
2. **Seeded from Volumio's list**, so the combined work stays at GPL-3.0
   (*"We will use the volumio one which means staying at 3.0. fine as of
   now."*). Credited in `THIRD-PARTY.md` when it is used.
3. **Tested: the DAC2 HD and the IQaudio DAC+**, the two George owns.
