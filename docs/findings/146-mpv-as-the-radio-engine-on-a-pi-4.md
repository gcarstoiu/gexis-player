# Finding 146 — mpv as the radio engine on a Pi 4: every station played, at 3-6 % of a core

**Date:** 2026-11-13. **For:** Phase 31 (`ph-radio`),
[ADR-0180](../decisions/0180-internet-radio-without-lyrion.md) step 2: the
engine measured before it is built on (George asked for the test the same
day).

## Scope

- **Device:** sofapi, a Raspberry Pi 4 (1.8 GHz, `ondemand`), Debian 13,
  gexis-player `1.16.1+git145` (the 1.16.2 preview), on Wi-Fi. The panel's
  Chromium ran throughout; nothing else played (no card running at the start
  or end of any run).
- **mpv 0.40.0** from Debian 13's packages, unpacked under `/tmp` and run
  from there, not installed; the image's own FFmpeg libraries (7.1.5). Options
  as a renderer would set them: no video, no config, the back buffer off
  (`--demuxer-max-back-bytes=0`), 8 MiB ahead, a `User-Agent` of its own;
  controlled over its JSON socket.
- **Output: mpv's timed null output**, not the player's chain. sofapi leads a
  group, so its `output` feeds the group's loopback and the bar would have
  played the test. The decoding, the network and the timing are real; what
  the card receives is not measured here.
- **Stations:** eleven public ones, picked as the directory's most played
  for each codec (radio-browser.info, asked once per codec), named below.
- **Each station twice**, in a fresh process each time: the time to the
  first audio, then 10 s to settle and 60 s measured - the process's user
  and system time as a share of one core, its resident memory, playback
  having advanced the whole 60 s (it did, every run), the buffer and stalls
  sampled each second; the titles' shape (how many, whether *Artist -
  Title*), not their text.
- **Drops** through a relay on the player itself, between mpv and Radio
  Paradise's AAC stream: a **cut** (the connection closed), a **freeze** (open,
  no data) and the station **down** (closed, then 503 to every request). The
  playback position and mpv's own states read four times a second.
- **Not tested:** the player's chain (formats into it, the stage, a group);
  a stream at 32 kHz or below (none in the set); drops on HLS; the network
  itself lost; runs longer than 70 s; Ethernet; another Pi.

## Results

### 1. Every station played; 3-6 % of one core

| Station | Codec | Decoded | Bitrate | First audio | CPU, two runs | Memory | Titles |
|---|---|---|---|---|---|---|---|
| Europe 1 (FR) | MP3 | 48 kHz | 128 | 1.2 / 1.1 s | 4.3 / 4.8 % | 69 MB | yes |
| Classic Vinyl HD (US) | MP3, listed 320 | 48 kHz | 233-248 | 0.6 / 0.7 s | 5.6 / 5.5 % | 69 MB | yes |
| CNR-1 (CN) | MP3 | 48 kHz | 64 | 2.2 / 2.3 s | 4.9 / 4.8 % | 69 MB | none sent |
| France Info (FR) | AAC | 48 kHz | 193-195 | 0.7 / 0.9 s | 4.6 / 4.8 % | 65 MB | none sent |
| Radio Paradise Main Mix (US) | AAC | 44.1 kHz | 320 | 0.2 / 0.2 s | 4.3 / 5.0 % | 65 MB | yes |
| RMF FM (PL) | AAC, listed AAC+ | 44.1 kHz | 45-48 | 0.9 / 1.0 s | 3.6 / 3.7 % | 66 MB | yes |
| Metro FM (TR), from a `.pls` | AAC, listed AAC+ | 44.1 kHz | 63-64 | 2.2 / 2.1 s | 3.3 / 3.4 % | 80 MB | none sent |
| Deutschlandfunk (DE) | Opus in Ogg | 48 kHz, **mono** | 24 | 0.6 / 0.7 s | 3.5 / 3.9 % | 68 MB | none sent |
| Radio Paradise Rock Mix (US) | FLAC in Ogg | 44.1 kHz, 16-bit | 640-819 | 0.5 / 0.4 s | 4.1 / 3.6 % | 69 MB | empty |
| RTL (FR) | AAC in HLS | 48 kHz | 64 | 1.7 / 1.6 s | 3.7 / 3.7 % | 87 MB | none |
| CNR-1 (CN) | AAC in HLS | 48 kHz | 190-194 | 1.7 / 1.5 s | 4.7 / 2.8 % | 69 MB | none |

- **The spread between runs is about 2 points** (Radio Paradise Main Mix read
  4.3 and 5.0 %, then 3.1 and 3.2 % half an hour later), so the differences
  between stations above are mostly not real. Nothing stalled; the clock
  averaged 1.73-1.80 GHz, 65-74 °C, no throttling.
- **The `.pls` was read by mpv**: it became 74 stream addresses and the first
  played. (The script first took the playlist's hand-over for a failure; the
  station was run twice more with that fixed.)
- **Titles** came as ICY `StreamTitle` from 4 of the 9 ICY and Ogg stations,
  in *Artist - Title* form but for one of RMF FM's two. None came from the
  two HLS stations; whether those streams carry any was not established.
- **The buffer ahead while playing**, from the station's opening burst: 3 s
  (France Info) to 30 s (Metro FM), mostly about 10 s.

### 2. Resampling 44.1 to 48 kHz cost nothing measurable

Radio Paradise Main Mix with `--audio-samplerate=48000`: 3.2 and 3.2 %,
against 3.2 and 3.1 % without, mpv handing 48 kHz on. No station in the set
was at 32 kHz or below, so ADR-0180's resampling rule was not tried on one.

### 3. Drops: mpv's reconnect hides a cut; a freeze needs a short timeout

Times from the moment the stream was broken; about 9.7 s were buffered then.

| Case | mpv | What happened | Silence |
|---|---|---|---|
| Cut | as shipped | The buffer played out; *end of file* at 9.8 s, no retry | from 9.8 s on |
| Cut | reconnect on | Reconnected while the buffer played (2 runs) | none |
| Freeze | as shipped | Buffer out at 10.3 s; *end of file* at 60.2 s | 50 s, then stopped |
| Freeze | reconnect on | Buffer out at 10.3 s; reconnected at 60.4 s | 50 s |
| Freeze | reconnect on, `--network-timeout=5` | Reconnected; the buffer never fell below 4.6 s (2 runs) | none |
| Cut | reconnect on, timeout 5 s | As the cut above (1 run) | none |
| Freeze | as shipped, plus a 10 s watchdog | Reloaded at 20.3 s, sound at 20.8 and 21.1 s (2 runs) | 10.5-10.8 s |
| Down | reconnect on | One retry refused; *end of file* at 9.9 s | from 9.9 s on |
| Down | as shipped, plus the watchdog | *End of file* at 9.8 s; three reloads, at 19.9, 30.0 and 40.0 s, each refused at once | stopped at 40 s |

"Reconnect on" is FFmpeg's `reconnect`, `reconnect_streamed` and
`reconnect_on_network_error`, at most 4 s between tries. The watchdog is the
script's, as ADR-0180 describes it: no playback for 10 s, load the station
again, three times.

## What it means for Phase 31

- **mpv is confirmed as the engine**: every station played, `.pls` and HLS
  included, at 3-6 % of one core and 65-87 MB. PyAV is not needed.
- **Reconnect on and a 5 s network timeout** turn a cut and a freeze into no
  silence at all, on a station that buffers more than 5 s. The watchdog stays
  for the rest: a short buffer, and a station that is gone.
- **mpv reports a cut and a station gone as an ordinary end of file**: the
  renderer must take any end of a live stream as a drop, never as the end.
- **The watchdog counts from the playback stopping**, not from the drop: the
  buffer plays first, 3 to 30 s here.
- **A mono station decodes as one channel**: the renderer asks mpv for stereo.
- **Still to measure in the build**, on a player not in a group: the format
  and rate at the card, the stage, a group, a station at 32 kHz or below,
  and an hour's memory.
