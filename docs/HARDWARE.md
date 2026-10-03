# Hardware

**Status: draft, being built** (George, 2026-10-03: *"a hardware
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
| **Storage** | 16 GB card (**calculated**) | 32 GB or more | The image is **4.9 GB** (0.8.4). `gexis`, with one skin pack and the Lyrion server holding a 61,362-file library, uses **8.3 GB**. Space for an update's downloads comes on top. |
| **Audio** | HiFiBerry DAC+ HD | HiFiBerry DAC+ HD | The only board tested (it is `hw:sndrpihifiberry`). Other DACs: Phase 13d, not yet supported. |
| **Screen** | None (the player runs without one) | An HDMI screen from the tested list | HDMI only (ADR-0109). Tested: Waveshare 10.1" HDMI LCD (B), 1280 x 800, with or without its case. The 13.3" and the two bar screens are listed as tested by ADR-0109 but not yet tried on the hardware. DSI and DPI screens: not supported. |
| **Network** | Wi-Fi | Wi-Fi or Ethernet | `gexis` runs on Wi-Fi. Internet is needed for updates, skin packs, and anything a plugin downloads (Plexamp, the Lyrion server). |
| **Power** | Raspberry Pi's 5 V 3 A USB-C supply | Same | Raspberry Pi's own recommendation for the Pi 4; not measured here. |
| **Cooling** | **Untested** | **Untested** | Under a 2-hour library scan `gexis` peaked at **75.9 °C** with no throttling (2026-10-03, Finding 109); its case and cooling were not recorded. Idle and visualiser temperatures: not measured. |

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
| **Memory** | 2 GB Pi: a library of about **34,000 files** (**calculated**) | 4 GB Pi: about **90,000 files** as set, **187,000** on Normal (**calculated**; 61,362 **tested** on both) | See below. A 1 GB Pi is not offered the server (ADR-0115 decision 18). |
| **Storage** | About **14 KB per file** on top of the player's needs (**calculated**) | The same | For 61,362 files: library database **151 MB**, artwork cache **670 MB** (Finding 109). |
| **Speed** | Every answer under 0.2 s on a 4 GB Pi (**tested**) | The same | Lists 25-70 ms, search 136-174 ms, covers 5-17 ms. A server on other hardware answered 2-5 times faster (Finding 109). |
| **Network** | Wi-Fi | Ethernet for a library on a NAS (**untested**: not compared) | The scans below ran over Wi-Fi from a NAS. |

### Memory, by library size

While it scans, Lyrion's scanner grows with every file, on top of about
**400 MB** for the server itself. How much per file depends on Lyrion's own
*Database Memory Config* (Finding 109, 61,362 files on `gexis`, 2026-10-03):

| Database Memory Config | Per file | Lyrion's peak for 61,362 files | Scan time | Search |
|---|---|---|---|---|
| Normal | about 13 KB | **1,191 MB** | 1 h 59 min | about 25 ms slower |
| High | about 27 KB | **1,876 MB** | 2 h 7 min | - |
| Maximum | as High (its scanner is High's) | not scanned | - | as High |

Everything else browsed at the same speed on all three. The player sets
**Normal on a Pi under 4 GB** and leaves Lyrion's own choice, **High**, on
4 GB and more (ADR-0115 decision 19); either can be changed on Lyrion's own
Performance page. The player keeps 1 GB for itself and gives Lyrion the rest
(decision 18):

| Pi 4 memory | Lyrion may use | As set | On Normal |
|---|---|---|---|
| 1 GB | - | not offered | - |
| 2 GB | about 0.8 GB | about 34,000 files (Normal) | the same |
| 4 GB | about 2.7 GB | about 90,000 files (High; 61,362 **tested**) | about 187,000 files (61,362 **tested**) |
| 8 GB | about 6.8 GB | about 240,000 files (High) | about 500,000 files |

All but the tested figures are **calculated**; the 2 GB and 8 GB rows assume
about 1.85 GB and 7.8 GB usable, as a 4 GB Pi reports 3.8 GB, and neither has
been checked. **A 4 GB player with a larger library than High fits** -
roughly 90,000 files and up - can switch to Normal and scan it (George,
2026-10-03). A library too large for the memory is not scanned in full; the
player says so on the server's row, with how many files fit, and on High how
many would on Normal (decision 18).

### Time

| | Measured on `gexis` (Pi 4, 4 GB, Wi-Fi, a NAS share of 61,362 files) |
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
