# Hardware

**Status: draft, being built; brought up to date 2026-10-06** (George, 2026-10-03: *"a hardware
recommendation document, with minimum and recommended hardware, with the
lyrion Server as a separate entry as in end it is optional"*; ADR-0111
decision 12). Every line names what it rests on. **Tested** means run on the
hardware named; **calculated** means worked out from a measurement, not run;
**untested** means neither, said so it is not mistaken for either.

So far everything has been run on **two Raspberry Pi 4 Model B with 4 GB**
(`gexis`, rev 1.5, 3,795 MB usable; `sofa-pi`, 3,796 MB). Nothing has been run
on a 1, 2 or 8 GB Pi 4, or on any other model.

## Gexis Player

| | Minimum | Recommended | What it rests on |
|---|---|---|---|
| **Computer** | Raspberry Pi 4 Model B | Raspberry Pi 4 Model B | The only model the player is built and tested for. Pi 5, Pi 3, Pi 400 and Compute Module 4: **untested**. |
| **Memory** | 2 GB (**untested**) | 4 GB (**tested**) | The player's own processes use about **700 MB** with a screen attached (measured on `gexis`, 2026-10-03: the visualiser 283 MB, the screen's browser about 226 MB, Plexamp 62 MB, the core 34 MB, the rest under 25 MB each). A 1 GB Pi would leave little room: **untested**. |
| **Storage** | 16 GB card (**calculated**) | 32 GB or more | The image is **5.1 GB** (0.9.2; 4.9 GB at 0.8.4). `gexis`, with one skin pack and the Lyrion server holding a library of tens of thousands of files, uses **8.3 GB**. Space for an update's downloads comes on top. |
| **Audio** | None beyond the Pi: its HDMI (a sound bar or AV receiver) or its headphone jack | A DAC HAT from the player's list, or a USB DAC; on the bench the HiFiBerry DAC2 HD | ADR-0117 (Phase 13d) gives every DAC one of three states (a fourth, *Reported*, from owners' feedback, ADR-0126). **Tested:** the HiFiBerry DAC2 HD (`hw:sndrpihifiberry`, the bench board throughout). **Tested:** the IQaudIO Pi-DAC PRO, recognised by its EEPROM - every rate from 44.1 to 192 kHz reaches it unchanged, its own volume control is used; Lyrion, Spotify, Bluetooth and Plexamp measured, and a chosen board that is not fitted taken back by itself (Finding 114). The IQaudIO DAC Plus itself: **untested**. **Known:** the rest of the list (from Volumio's, corrected - Finding 106), **untested**. **Detected:** a USB DAC works as any class-compliant card, shown by its maker: an SMSL USB DAC (USB 2.0) **tested** on 2026-10-12 (Finding 120): found by itself; 32-bit only, every rate from 44.1 to 768 kHz reaching it unchanged, 16- and 24-bit sources widened to 32 bits without changing a sample (ADR-0143); through Lyrion unchanged up to 384 kHz (a 705.6 or 768 kHz file served over the network does not play); no volume control of its own, so Software or Fixed; **native DSD** (DSD64, 128, 256) from Lyrion with the volume Fixed, reaching it unconverted (ADR-0144). Bluetooth and Plexamp on it: **tested**. **Tested:** a **USB-to-optical adapter** (Realtek *USB SPDIF Adapter*, USB `0bda:4e27`) into the SMSL's optical input, 2026-10-20 (Finding 130, ADR-0155): 44.1, 48, 96 and 192 kHz reach it unchanged, heard and on the SMSL's display; it lacks 88.2 and 176.4 kHz, so Lyrion converts those to 192 kHz (until ADR-0155 they played silence) and Plexamp converts them itself; no volume control, so Fixed to start with, Software if chosen. **Untested:** a sound bar or receiver on optical, and any other adapter model. DSD on the HATs: neither tested board plays it; a DSD file is converted to PCM for them, and for any DAC whose volume is not Fixed. |
| **Screen** | None (the player runs without one) | An HDMI touch screen from the tested list | HDMI only, on either port (ADR-0109; HDMI 2 seen with a TV on sofapi, not with a touch screen). With a screen on one port and a sound bar or receiver on the other, *Settings → Display* lists both and the screen's port can be chosen; the other port shows black, and if it carries the sound and disappears, the headphone jack stands in (ADR-0141). Seen on sofapi with a Sony receiver on HDMI 2; switching the receiver off and on: **untested**. **Tested on the hardware** (Phase 13b, closed 2026-10-04): Waveshare 10.1" HDMI LCD (B), 1280 x 800, with or without its case; a 13.3" at 1920 x 1080; the Waveshare 7.9" bar (1280 x 400) and 11.9" bar (1480 x 320), both landscape; the **HMTECH 7" HDMI Monitor, 800 x 480, no touch** (sofapi, 2026-10-20: recognised by its EDID, *Keep this screen?* answered on the phone; the first 800 x 480 screen on the hardware, which found Chromium restoring a stored window size at the wrong scale - fixed); the **HMTECH 10.1" HDMI Monitor, 1024 x 600, no touch** (sofapi, 2026-10-20; its EDID reads Dell TLD1280; the list's HMTECH 10.1" is the touch model, so this one has its own entry). **Listed, untested:** every other HDMI screen in the player's list, and a bar at 0°. DSI and DPI screens: not supported (DSI is planned next but one, `ph-dsi`). **A TV as the screen** (ADR-0147, George, 2026-10-13): chosen under *Settings → Display → Screen port*, run at 1920 x 1080 from the modes the TV offers, set at boot and again by the compositor (a 4K TV scales it up), *Keep this screen?* answered on the phone since a TV has no touch; a touch panel on the other port is switched off. Seen on sofapi with an LG TV on HDMI 2 behind a Sony receiver: the third try, 2026-10-14, passed - the TV at 1920 x 1080, the panel on HDMI 1 fully off, TV standby keeping the music. Behind a receiver, the TV is named by the receiver (*SONY AVSYSTEM*). Turned off and on, the receiver first offers 640 x 480 alone; the player sets 1920 x 1080 again within a few seconds (2026-10-14, forced by hand; the TV itself turned off and on: to see). |
| **Network** | Wi-Fi | Wi-Fi or Ethernet | `gexis` runs on Wi-Fi. Internet is needed for updates, skin packs, and anything a plugin downloads (Plexamp, the Lyrion server). **Untested:** whether Wi-Fi power saving, on in the image, delays the phone's touchpad (2026-10-06: the bursts measured came from the core, not the network). |
| **Phone** | None (the panel works by touch) | A phone with a current browser, on the same network | The phone page (ADR-0101): Settings, the mini player and the touchpad (ADR-0121), tried on George's phone. No app to install. |
| **Power** | Raspberry Pi's 5.1 V 3 A USB-C supply | Same, and a screen on its own supply where it has a port for one | Raspberry Pi's own recommendation for the Pi 4. **Measured, 2026-10-08/09:** an 11.9" bar powered from the Pi's USB, on a phone charger, reset the Pi eleven times within seconds of each start; on a better supply the resets stopped, but `vcgencmd get_throttled` still read `0x50000` (5 undervoltage dips in 7.5 minutes, mostly while the screen was touched). **No USB extension cable on the supply:** on 2026-10-13/14 the same bar on Raspberry Pi's own 5.1 V supply, through a USB extension, read undervoltage *continuously* (`0x50005`, the CPU held throttled); plugged in directly it read `0x0` for its first 28 minutes. If the supply's cable does not reach, extend the mains side instead. A Pi 4 with a 13.3" screen read `0x0` over two days. |
| **Cooling** | **Untested** | A heatsink or fan (**calculated**) | Playing music while the Lyrion server scanned, `gexis` reached **79.8 °C** - 0.2 °C below where a Pi 4 starts slowing itself down - without throttling (2026-10-03, Finding 109); a scan alone peaked at 75.9 °C. Its case and cooling were not recorded. Idle and visualiser temperatures: not measured. |

### Skin packs, by screen size

Each screen size installs one pack, with the user's consent (ADR-0111). Its
size counts toward storage:

| Screen size | Download | Installed |
|---|---|---|
| 1920 x 1080 | 461 MB | 491 MB |
| 1280 x 800 | 223 MB | 235 MB |
| 1280 x 400 | 71 MB | 76 MB |
| 1480 x 320 | 71 MB | 75 MB |
| 800 x 480 | 48 MB | 51 MB |

From the packages built for 0.8.4. **Not yet measured:** how hard the
visualiser works the Pi at 1920 x 1080 (ADR-0111 decision 12), which may raise
the recommendation for the largest screens.

## Lyrion Server (optional)

A plugin, off unless switched on (ADR-0115). It serves a music library from a
USB disk, the player's own Music folder or a network share. It is what asks
most of the hardware, and most of what it asks grows with the size of the
library.

| | Minimum | Recommended | What it rests on |
|---|---|---|---|
| **Memory** | 2 GB Pi: a library of about **34,000 files** (**calculated**) | 4 GB Pi: about **90,000 files** as set, **187,000** on Normal (**calculated**; a library of tens of thousands of files **tested** on both) | See below. A 1 GB Pi is not offered the server (ADR-0115 decision 18). |
| **Storage** | About **14 KB per file** on top of the player's needs (**calculated**) | The same | The library database and the artwork cache together, for the tested library (Finding 109). |
| **Speed** | Every answer under 0.2 s on a 4 GB Pi (**tested**) | The same | Lists 25-70 ms, search 136-174 ms, covers 5-17 ms. A server on other hardware answered 2-5 times faster (Finding 109). |
| **Network** | Wi-Fi | Ethernet for a library on a NAS (**untested**: not compared) | The scans below ran over Wi-Fi from a NAS. |

### Memory, by library size

While it scans, Lyrion's scanner grows with every file, on top of about
**400 MB** for the server itself. How much per file depends on Lyrion's own
*Database Memory Config* (Finding 109, measured on `gexis` with a library of tens of
thousands of files, 2026-10-03):

| Database Memory Config | Per file | Scan time, against High | Search |
|---|---|---|---|
| Normal | about 13 KB | about 6 % shorter | about 25 ms slower |
| High | about 27 KB | - | - |
| Maximum | as High (its scanner is High's) | not scanned | as High |

Everything else browsed at the same speed on all three. The player sets
**Normal on a Pi under 4 GB** and leaves Lyrion's own choice, **High**, on
4 GB and more (ADR-0115 decision 19); either can be changed on Lyrion's own
Performance page. The player keeps 1 GB for itself and gives Lyrion the rest
(decision 18):

| Pi 4 memory | Lyrion may use | As set | On Normal |
|---|---|---|---|
| 1 GB | - | not offered | - |
| 2 GB | about 0.8 GB | about 34,000 files (Normal) | the same |
| 4 GB | about 2.7 GB | about 90,000 files (High; **tested** below that) | about 187,000 files (**tested** below that) |
| 8 GB | about 6.8 GB | about 240,000 files (High) | about 500,000 files |

All but the tested figures are **calculated**; the 2 GB and 8 GB rows assume
about 1.85 GB and 7.8 GB usable, as a 4 GB Pi reports 3.8 GB, and neither has
been checked. **A 4 GB player with a larger library than High fits** -
roughly 90,000 files and up - can switch to Normal and scan it (George,
2026-10-03). A library too large for the memory is not scanned in full; the
player says so on the server's row, with how many files fit, and on High how
many would on Normal (decision 18).

### Time

| | Measured on `gexis` (Pi 4, 4 GB, Wi-Fi, a NAS share of tens of thousands of files) |
|---|---|
| First scan | **2 h 7 min**: 82 min reading the files, 45 min covers, artist pictures, search index and artwork |
| Scan with nothing changed | **26 min**: 3 min checking the files, 21 min artist pictures |
| Processor | about a fifth of one of the four cores on average; the scan waits on the network more than on the processor |

The first scan starts by itself when a folder is added. **Untested:** whether
a scan can be heard in music playing at the same time - Lyrion runs at the
lowest priority so that it should not be (ADR-0115), and Phase 13e's criterion
2 is that check.

## Sound cards and screens, as tested and reported

*Tested* means played and measured on the project's own hardware, or reported
working by at least one owner with none against (George, 2026-10-18: two
states, as on the player); the *Reports* column says which. A problem an owner
reported shows on the player as a line under the model; a model with no mark
is on the player's list, untested. Owners send feedback from
*Settings → System → Hardware feedback*; accepted feedback reaches this table
and the player through a reviewed change (ADR-0126).

<!-- hardware-reports:begin (tools/hardware-reports.py writes this table) -->

| Sound card | Tested | Reports |
|---|---|---|
| 52Pi NVDAC |  |  |
| 52Pi NVDAC [Pi5] |  |  |
| Adafruit MAX98357 |  |  |
| Adafruit UDA1334A |  |  |
| Allo BOSS |  |  |
| Allo BOSS [Pi5] |  |  |
| Allo BOSS2 |  |  |
| Allo DigiOne |  |  |
| Allo Katana |  |  |
| Allo Piano |  |  |
| Allo Piano 2.1 |  |  |
| ApplePi DAC |  |  |
| AudioInjector bare I2S |  |  |
| AudioInjector Isolated |  |  |
| AudioInjector Pro |  |  |
| AudioInjector Stereo |  |  |
| AudioInjector Ultra 2 |  |  |
| Audiophonics I-Sabre ES9028Q2M |  |  |
| BassFly-uHAT |  |  |
| BassFly-uHAT with I2S Mic |  |  |
| BassMantis-uHAT |  |  |
| BassMantis-uHAT with I2S Mic |  |  |
| BassOwl-HAT |  |  |
| ChipDip DAC |  |  |
| Dion Audio Loco V2 DAC-AMP |  |  |
| Fe-Pi Audio |  |  |
| Generic I2S DAC |  |  |
| Google voiceHAT |  |  |
| HiFiBerry Amp |  |  |
| HiFiBerry Amp100 |  |  |
| HiFiBerry Amp100 [Pi5] |  |  |
| HiFiBerry Amp2 |  |  |
| HiFiBerry Amp2 [Pi5] |  |  |
| HiFiBerry Amp3 |  |  |
| HiFiBerry Amp4 |  |  |
| HiFiBerry Amp4 [Pi5] |  |  |
| HiFiBerry Amp4 Pro |  |  |
| HiFiBerry Amp4 Pro [Pi5] |  |  |
| HiFiBerry DAC |  |  |
| HiFiBerry DAC Plus |  |  |
| HiFiBerry DAC Plus [Pi5] |  |  |
| HiFiBerry DAC Plus ADC |  |  |
| HiFiBerry DAC Plus ADC PRO |  |  |
| HiFiBerry DAC Plus ADC PRO [Pi5] |  |  |
| HiFiBerry DAC Plus DSP |  |  |
| HiFiBerry DAC+ Pro |  |  |
| HiFiBerry DAC+ Pro [Pi5] |  |  |
| HiFiBerry DAC2 HD | Tested |  |
| HiFiBerry DAC2 Pro |  |  |
| HiFiBerry DAC2 Pro [Pi5] |  |  |
| HiFiBerry Digi |  |  |
| HiFiBerry Digi+ Pro |  |  |
| HiFiBox DAC |  |  |
| HiFiBox DAC [Pi5] |  |  |
| Innomaker Amp |  |  |
| Innomaker Amp Pro |  |  |
| Innomaker Dac |  |  |
| Innomaker Dac [Pi5] |  |  |
| Innomaker Dac Pro |  |  |
| Interlude Audio Analog Hat |  |  |
| Interlude Audio Digital Hat |  |  |
| IQaudIO DAC Plus |  |  |
| IQaudIO Pi-DAC PRO | Tested |  |
| IQaudIO Pi-Digi+ |  |  |
| IQaudIO Pi-DigiAMP+ |  |  |
| JustBoom Amp Boards |  |  |
| JustBoom DAC Boards |  |  |
| JustBoom Digi Boards |  |  |
| Mamboberry LS DAC+ |  |  |
| Melopero DAC ZERO |  |  |
| Melopero DAC ZERO [Pi5] |  |  |
| MERUS™ Amp piHAT ZW |  |  |
| NanoSound DAC |  |  |
| NanoSound DAC [Pi5] |  |  |
| Orchard Audio PecanPi DAC |  |  |
| Orchard Audio PecanPi+ DAC |  |  |
| OSA DACBerry ONE+ |  |  |
| OSA DACBerry ONE+ [Pi5] |  |  |
| OSA DACBerry PRO |  |  |
| pHAT BEAT |  |  |
| pHAT DAC |  |  |
| PI 2 Design 502DAC |  |  |
| PI 2 Design 502DAC [Pi5] |  |  |
| PI 2 Design 502DAC Pro |  |  |
| PI 2 Design 502DAC Pro [Pi5] |  |  |
| PI 2 Design 503HTA Hybrid Tube Amp |  |  |
| Picade HAT |  |  |
| Pisound |  |  |
| R-PI DAC |  |  |
| Raspberry Pi DAC+ |  |  |
| Soekris dam 1021 |  |  |
| Speaker pHAT |  |  |
| ST400 Dac (PCM5122) - Amp |  |  |
| TauDAC - DM101 |  |  |
| Terra-Berry DAC 2/3 |  |  |
| Volumio Zero ES9039 DAC |  |  |
| Waveshare WM8960 Audio HAT |  |  |
| wisdPi Hifi DAC |  |  |
| wisdPi Hifi DAC [Pi5] |  |  |

| Screen | Tested | Reports |
|---|---|---|
| Adafruit 10.1" HDMI IPS (1280x800) |  |  |
| Adafruit 5" Display Backpack (800x480) |  |  |
| Adafruit 5" HDMI (800x480) |  |  |
| Adafruit 7" HDMI (1024x600) |  |  |
| Adafruit 7" HDMI (800x480) |  |  |
| Adafruit 7" HDMI IPS (1280x800) |  |  |
| BIGTREETECH HDMI5 V1.0 (800x480) |  |  |
| BIGTREETECH HDMI7 V1.0 (1024x600) |  |  |
| BIGTREETECH HDMI7 V1.2 (1024x600) |  |  |
| Elecrow 5" HDMI (800x480) |  |  |
| Elecrow 7" HDMI (1024x600) |  |  |
| Freenove 7" HDMI (1024x600) |  |  |
| GeeekPi 10.1" HDMI (1024x600) |  |  |
| GeeekPi 10.1" HDMI (1280x800) |  |  |
| GeeekPi 11.6" HDMI (1366x768) |  |  |
| GeeekPi 5" HDMI (800x480) |  |  |
| GeeekPi 7" HDMI (1024x600) |  |  |
| GeeekPi 7" HDMI (1280x800) |  |  |
| Generic (1280x720) |  |  |
| Generic (1920x1080) |  |  |
| Generic 1024x600 HDMI |  |  |
| Generic 1280x800 HDMI |  |  |
| Generic 1366x768 HDMI (HD Ready) |  |  |
| Generic 30Hz (3840x2160) |  |  |
| Generic 480x320 HDMI |  |  |
| Generic 60Hz (3840x2160) |  |  |
| Generic 800x480 HDMI |  |  |
| HMTECH 10.1" HDMI Monitor (1024x600) | Tested |  |
| HMTECH 10.1" HDMI Touchscreen (1024x600) |  |  |
| HMTECH 7" HDMI Monitor (800x480) | Tested |  |
| Hosyond 10.1" HDMI Display-H (1024x600) |  |  |
| Hosyond 10.1" HDMI Display-S (1024x600) |  |  |
| Hosyond 10.1" HDMI Display-Y (1024x600) |  |  |
| Hosyond 5" HDMI Display-B (800x480) |  |  |
| Hosyond 7" HDMI Display-C (1024x600) |  |  |
| Hosyond 7" HDMI Display-H (1024x600) |  |  |
| Hosyond 8.8" HDMI Bar (480x1920) |  |  |
| Joy-IT 10" HDMI LCD V2 (1280x800) |  |  |
| Joy-IT 10.1" HDMI LCD Version B (1280x800) |  |  |
| Joy-IT 10.1" IPS HDMI V3 (1280x800) |  |  |
| Joy-IT 5" HDMI LCD V2 (800x480) |  |  |
| Joy-IT 7" HDMI LCD V2 (1024x600) |  |  |
| Kuman 7" HDMI (1024x600) |  |  |
| Kuman 7" HDMI (800x480) |  |  |
| LCDwiki 3.5" HDMI (480x320) |  |  |
| LCDwiki 4" HDMI-C (480x800) |  |  |
| LCDwiki 5" HDMI (800x480) |  |  |
| LCDwiki 7" HDMI-B (800x480) |  |  |
| LCDwiki 7" HDMI-C (1024x600) |  |  |
| Longruner 5" HDMI (800x480) |  |  |
| Longruner 7" HDMI (1024x600) |  |  |
| Pollin 5" HDMI 800x480 Touch (pre-2020) |  |  |
| Seeed Studio 10.1" HDMI (1366x768) |  |  |
| Seeed Studio 10.1" HDMI IPS (1200x1920) |  |  |
| Seeed Studio 10.1" HDMI IPS (1280x800) |  |  |
| Seeed Studio 5" HDMI (720x1280) |  |  |
| Seeed Studio 7" HDMI (1024x600) |  |  |
| Seeed Studio 7" HDMI (720x1280) |  |  |
| Seeed Studio 7" HDMI IPS (1280x800) |  |  |
| Spotpear 10.1" HDMI (1024x600) |  |  |
| Spotpear 4" HDMI (480x800) |  |  |
| Spotpear 5" HDMI (1024x600) |  |  |
| Spotpear 7" HDMI (1024x600) |  |  |
| Spotpear 7" HDMI (1280x800) |  |  |
| Sunfounder 10.1" HDMI (1024x600) |  |  |
| Sunfounder 7" HDMI (1024x600) |  |  |
| UCTRONICS 3.5" HDMI (480x320) |  |  |
| UCTRONICS 5" HDMI (800x480) |  |  |
| UCTRONICS 7" HDMI (1024x600) |  |  |
| UCTRONICS 7" HDMI (1024x768) |  |  |
| Waveshare 10.1" HDMI LCD (1024x600) |  |  |
| Waveshare 10.1" HDMI LCD (B) (1280x800) | Tested |  |
| Waveshare 10.1" HDMI LCD (D) (1024x600) |  |  |
| Waveshare 10.1" HDMI LCD (E) (1024x600) |  |  |
| Waveshare 10.1" HDMI LCD (F) (1024x600) |  |  |
| Waveshare 10.1" HDMI LCD (G) (1024x600) |  |  |
| Waveshare 10.1" HDMI LCD (H) (1024x600) |  |  |
| Waveshare 10.5" HDMI AMOLED (2560x1600) |  |  |
| Waveshare 11.6" HDMI LCD (H) (1920x1080) |  |  |
| Waveshare 11.9" HDMI LCD (320x1480) | Tested |  |
| Waveshare 13.3" HDMI LCD (H) (1920x1080) | Tested |  |
| Waveshare 15.6" FHD Monitor (B) (1920x1080) |  |  |
| Waveshare 15.6" HDMI LCD (1920x1080) |  |  |
| Waveshare 2.8" HDMI LCD (H) (480x640) |  |  |
| Waveshare 3.5" HDMI LCD (480x320) |  |  |
| Waveshare 3.5" HDMI LCD (E) (640x480) |  |  |
| Waveshare 4" HDMI LCD (480x800) |  |  |
| Waveshare 4" HDMI LCD (H) (480x800) |  |  |
| Waveshare 4.3" HDMI LCD (480x272) |  |  |
| Waveshare 4.3" HDMI LCD (B) (800x480) |  |  |
| Waveshare 5" HDMI AMOLED (960x544) |  |  |
| Waveshare 5" HDMI LCD (800x480) |  |  |
| Waveshare 5" HDMI LCD (B) (800x480) |  |  |
| Waveshare 5" HDMI LCD (G) (800x480) |  |  |
| Waveshare 5" HDMI LCD (H) (800x480) |  |  |
| Waveshare 5" HDMI LCD (H) V4 (800x480) |  |  |
| Waveshare 5.5" 2K HDMI LCD (1440x2560) |  |  |
| Waveshare 5.5" HDMI AMOLED (1080x1920) |  |  |
| Waveshare 6" HDMI AMOLED (1080x2160) |  |  |
| Waveshare 7" FHD HDMI Monitor (1080x1920) |  |  |
| Waveshare 7" HDMI LCD (1024x600) |  |  |
| Waveshare 7" HDMI LCD (B) (800x480) |  |  |
| Waveshare 7" HDMI LCD (C) (1024x600) |  |  |
| Waveshare 7" HDMI LCD (H) (1024x600) |  |  |
| Waveshare 7.9" HDMI LCD (400x1280) | Tested |  |
| Waveshare 8.8" HDMI Side Monitor (480x1920) |  |  |
| Waveshare 9.3" HDMI LCD (1600x600) |  |  |

<!-- hardware-reports:end -->

## Not covered yet

- The visualiser's load at 1920 x 1080 (ADR-0111 decision 12).
- Any Pi 4 other than 4 GB; any other model.
- Temperatures at idle and with the visualiser, and with or without a case.
- DACs other than the HiFiBerry DAC2 HD and the IQaudIO Pi-DAC PRO.
- The other optional plugins - Plexamp, the Beszel hub - beyond the memory
  they used on `gexis`.
