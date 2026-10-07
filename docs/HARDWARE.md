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
| **Audio** | A DAC HAT from the player's list, or a USB DAC | HiFiBerry DAC2 HD | ADR-0117 (Phase 13d) gives every DAC one of three states. **Tested:** the HiFiBerry DAC2 HD (`hw:sndrpihifiberry`, the bench board throughout). **Built, its board test owed:** the IQaudio DAC+, chosen under *Sound card board*. **Known:** the rest of the list (from Volumio's, corrected - Finding 106), **untested**. **Detected:** a USB DAC works as any class-compliant card, **untried**. DSD: neither tested board plays it. |
| **Screen** | None (the player runs without one) | An HDMI touch screen from the tested list | HDMI only (ADR-0109). **Tested on the hardware** (Phase 13b, closed 2026-10-04): Waveshare 10.1" HDMI LCD (B), 1280 x 800, with or without its case; a 13.3" at 1920 x 1080; the Waveshare 7.9" bar (1280 x 400) and 11.9" bar (1480 x 320), both landscape. **Listed, untested:** 800 x 480, and a bar at 0°. DSI and DPI screens: not supported. |
| **Network** | Wi-Fi | Wi-Fi or Ethernet | `gexis` runs on Wi-Fi. Internet is needed for updates, skin packs, and anything a plugin downloads (Plexamp, the Lyrion server). **Untested:** whether Wi-Fi power saving, on in the image, delays the phone's touchpad (2026-10-06: the bursts measured came from the core, not the network). |
| **Phone** | None (the panel works by touch) | A phone with a current browser, on the same network | The phone page (ADR-0101): Settings, the mini player and the touchpad (ADR-0121), tried on George's phone. No app to install. |
| **Power** | Raspberry Pi's 5 V 3 A USB-C supply | Same | Raspberry Pi's own recommendation for the Pi 4; not measured here. |
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

## Not covered yet

- The visualiser's load at 1920 x 1080 (ADR-0111 decision 12).
- Any Pi 4 other than 4 GB; any other model.
- Temperatures at idle and with the visualiser, and with or without a case.
- DACs other than the HiFiBerry DAC+ HD (Phase 13d).
- The other optional plugins - Plexamp, the Beszel hub - beyond the memory
  they used on `gexis`.
