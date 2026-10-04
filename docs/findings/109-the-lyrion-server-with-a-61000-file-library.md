# Finding 109 — The Lyrion server with a 61,000-file library

**Date:** 2026-10-03
**Question:** What does the Lyrion server plugin (ADR-0115) cost a Pi 4 with a
real library - memory, time, heat - and how fast does it answer? What does
Lyrion's own *Database Memory Config* (`dbhighmem`) change? How does it
compare with a Lyrion server on other hardware?

**Scope.** `gexis`: Raspberry Pi 4 Model B rev 1.5, 4 GB (3,795 MB usable),
on **Wi-Fi**, Gexis Player 0.8.4 with core previews, Lyrion 9.1.1 run at the
lowest CPU and I/O priority (ADR-0115). The library: George's NAS share
`//Tower.local/Music` over SMB, mounted read-only, **61,362 files** (61,347
songs, 4,571 albums, 7,313 artists once scanned). Sampled every 15 s: the
unit's cgroup memory (own memory - `anon` - and file cache apart), each
Lyrion process's RSS, CPU time, load, temperature, Lyrion's scan progress.
Speeds: `lyrion_bench.py` (scratch) - eight requests, each ten times after
one warm-up, one at a time, median and slowest. The other server: George's
`192.168.178.188`, *Lyrion Music Server (Docker)* 9.1.1, 61,225 songs; its
hardware was not recorded.

**Not measured:** a Pi 4 with other than 4 GB, or any other model; a wired
network; the cost of browsing a whole large library on Maximum. (Playback
during a scan was measured later the same day - see the end.)

## The scans

| | Run A: High (Lyrion's own choice) | Run B: Normal |
|---|---|---|
| Started | 10:42:35, by adding the share | 14:10:10, `wipecache` |
| Reading the files | 82 min | 77.5 min |
| Whole scan | **2 h 7 min** | **1 h 59 min** |
| Lyrion's own memory, peak | **1,876 MB** | **1,191 MB** |
| Of it the scanner | 1,666 MB | 954 MB |
| Scanner growth per file | about 27 KB (24.8 over the whole read) | about 13 KB |
| Files per second while reading | 14.0-14.2 | 14.8-14.9 |
| Load, mean / highest | 3.2 / 4.65 | 3.2 |
| Temperature, highest | 75.9 °C, no throttling | 75.9 °C, no throttling |
| Stopped for memory | no - with the limit raised to 3 GB at 11:50 | no |

- **The scanner grows with every file**, in a straight line, and gives the
  memory back when it ends (Lyrion's own memory 242 MB idle afterwards).
  The server itself stayed at about 207 MB throughout.
- **Run A would have been stopped** by ADR-0115's 2 GB `MemoryMax`: the
  unit pressed the limit 1,513 times (cache reclaimed each time) and was
  heading for it with its own memory alone; the limit was raised to 3 GB for
  the run (`systemctl set-property --runtime`). Hence decision 18.
- **Normal against High** comes from `Slim/Utils/SQLiteHelper.pm` and
  `DbCache.pm`: High gives the scanner a 20,000-page cache (4 KB pages,
  checked) and keeps temporary tables in memory. The halving was not
  expected from the cache alone; temporary tables are the likely cause, not
  proved.
- Lyrion processor time: 29 min over A's 2.5 h of sampling, about a fifth of
  one core on average: the scan waits on the share.
- Lyrion's card use afterwards: library database **151 MB**, artwork cache
  **670 MB** (868 MB cache folder in all).

**A check with nothing changed** (started by itself after run A - see below):
**26 min**: 3 min walking the share, 21 min looking for artist pictures,
the rest covers and the database.

## Two things found on the way

- **The core asked for a second scan.** Lyrion scans a folder added to its
  `mediadirs` by itself (`Slim/Utils/Prefs.pm`); the core also sent
  `rescan`, so run A was followed by the 26-minute check. Removed
  (commit 9f15693).
- **A folder taken out of `mediadirs` wipes the whole library** and scans
  everything (`Slim/Utils/Prefs.pm`); the core took an unmounted share out.
  A NAS off at a start would have cost a full scan. Now a saved share stays
  (ADR-0115 decision 16).

## Speeds

Median ms, ten requests each, the player's server idle. **From a computer on
the network** (where a phone is):

| Request | gexis, Normal | gexis, High | gexis, Maximum | other server |
|---|---|---|---|---|
| Server status | 15 | 14 | 13 | 7 |
| Artists, first 100 | 70 | 69 | 68 | 14 |
| Albums, first 100 + artwork | 38 | 37 | 39 | 12 |
| Albums, newest 100 | 34 | 35 | 36 | 12 |
| Search "love" | 172-174 | 146 | 154 | 37 |
| One album's tracks | 14 | 14 | 14 | 7 |
| Cover, 300 px | 17 | 17 | 17 | 10 |
| Material's first page | 34 | 48 | 33 | 14 |

**On the player itself** (where its own screen asks): Normal / High /
Maximum / other - status 9 / 10 / 9 / 12; artists 60 / 60 / 59 / 21; albums
28 / 28 / 28 / 18; search 164-165 / 136 / 146 / 34; one album's tracks
9 / 9 / 9 / 7; cover 5 / 5 / 5 / 17; Material 26 / 26 / 26 / 14.

- **The three settings browse alike;** only search differs, Normal about
  25 ms slower than High. Maximum was no faster than High, and the server's
  own memory stayed at 253 MB on it - its cache fills only with what is read.
- **The other server answers 2-5 times faster** on lists and search; the
  player's own server is faster only for covers asked from the player
  itself. Every answer from the player's server was under 0.2 s.
- High was measured after run A and its check; Normal and Maximum after
  run B. High and Maximum within about 10 ms of each other is within what
  repeating these runs moved.

## Lyrion's own advice, against these numbers

Lyrion labels High *"recommended for machines with 1+ GB RAM"* and Maximum
*"recommended for libraries with more than 50,000 tracks and machines with
2+ GB RAM"* (`strings.txt`). On a Pi 4 the measurements point the other way
for scanning: a 61,000-file library needed 1.9 GB on High (and so on
Maximum) and 1.2 GB on Normal.

## For the hardware requirements

With the player keeping 1 GB for itself (ADR-0115 decision 18) and Lyrion
about 400 MB before its first file, a scan fits about
`(memory - 1 GB - 400 MB) / per-file` files - **calculated**, from these
runs:

| Pi 4 | Lyrion may use | Normal (13 KB a file) | High (27 KB a file) |
|---|---|---|---|
| 2 GB | about 0.8 GB | about 34,000 | about 16,000 |
| 4 GB | about 2.7 GB | about 187,000 | about 90,000 (61,362 tested) |
| 8 GB | about 6.8 GB | about 500,000 | about 240,000 |

The 2 GB and 8 GB rows assume about 1.85 GB and 7.8 GB usable; neither was
checked. Decision 19 makes Normal the first setting under 4 GB.

## Playback while the server scans (Phase 13e criterion 2)

Measured on `gexis` the same evening, 21:20-22:06: music from George's other
Lyrion server (the Docker one) through the player's own Lyrion client
(squeezelite) to the HiFiBerry DAC+ HD, while the player's own Lyrion server
scanned the 61,362 files from scratch (`wipecache` at 21:26:10, Database
Memory Config High, the 2,771 MB limit). Gaps were counted by the client
itself: its output logging was turned up for the test (`-d output=info`), and
it logs **"output underrun"** and **"XRUN"** when the sound card runs dry -
that logging was shown working by its "track start" line for every track.

| | Before the scan (5 min) | During the scan (40 min) |
|---|---|---|
| Tracks played | 2 | 10 |
| Underruns or XRUNs | **0** | **0** |
| Load average | about 3.1 | mean 4.7, highest 7.05 |
| Temperature | 72.5-73 °C | highest **79.8 °C**, no throttling |

- **Nothing reached the output**: no underrun and no XRUN in 46 minutes of
  playback, 40 of them under the heaviest load the server makes. Lyrion's
  lowest CPU and I/O priority (ADR-0115) held.
- **The temperature came within 0.2 °C of 80 °C**, where a Pi 4 begins to
  slow itself down. It did not here; a warmer room or a closed case would.
  Cooling belongs in the hardware recommendations.
- **Not measured:** what was heard - George listening is the other half of
  the criterion; other renderers (Spotify, Bluetooth, Plexamp) under the same
  load; the 30-file-a-second end of a scan on a faster share.
