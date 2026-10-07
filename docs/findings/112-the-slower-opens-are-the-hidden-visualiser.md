# Finding 112 — The slower screen opens are the hidden visualiser

**Date:** 2026-10-06
**Question:** George, after 0.9.2: *"measure the speed of the panel - we need to
make sure it stays as snappy as it was before."* A first run showed four screen
opens dropping two to three times the frames of
[Finding 101](101-the-panel-before-phase-13-closes.md) (29 September). Is that
the UI, and if not, what?
**Scope:** `gexis` (Pi 4, 4 GB, rev 1.5, 1.8 GHz), the 10.1" 1280 x 800 panel,
image of 2026-10-02 with 0.9.2 and its preview packages; Chromium
154.0.8037.92. `tools/panel-frames.py`, `--runs 12 --playback playing`, music
through Lyrion, the kiosk's debug port on only for the runs (`kiosk.env`
checked identical afterwards each time, port closed). Every comparison below
is **two legs run back to back on the same device**, so the conditions they
share are the same; the comparison with Finding 101 is not like for like (it
ran on another card, an older image and Chromium, and another album). Raw
output in [data/112/](data/112/). **Not measured:** a phone; a bar screen;
skins without motion or a fanart frame (below).

## Four comparisons

Frames drawn per second / median share dropped, 12 runs each.

**1. 0.9.2 against Finding 101.** Scrolls unchanged (58-60 drawn/s, 0 %);
Settings and Radio opens better (0 % against 7-12 %); Home, the artist grid,
Albums and the artist page worse (4-10 % against 1-5 %).

**2. The kept library (ADR-0122) off and on.** Not the cause: off, the same
opens drop as much or more (the artist grid 15.5 % off, 9.7 % on).

**3. The UI of 29 September against 0.9.2's, on today's device.** Not the
cause: the old UI is no faster - Home 17.6 % against 2.3 %, the artist grid
11.3 % against 9.8 %, the artist page 8.1 % against 9.1 %. **The UI did not
regress; the device's conditions changed.**

**4. The visualiser's service stopped and running** (same UI):

| Open | Stopped | Running |
| --- | --- | --- |
| Home | 42.3 / 0.8 % | 45.7 / 3.4 % |
| Artist grid | 51.2 / **1.4 %** | 47.3 / **8.2 %** |
| Queue rail | 49.3 / 1.3 % | 47.9 / 2.5 % |

With it stopped, the opens are as good as Finding 101's or better.

## Why

The visualiser runs **hidden but drawing** (ADR-0019: started with the panel,
minimised, so it appears with a finished frame). [Finding 025](025-peppy-entry-has-no-visible-construction.md)
measured it at 8 % of one core while minimised. Measured here from
`/proc/<pid>/stat` over 10 s: **57 % of a core while music plays, 3 %
paused**. The selected skin is a turntable in the *Fanart* corpus with
*Motion* on and *Rotation: Smooth*: the record is redrawn every frame (ADR-0096,
27 September) and the artist's photos crossfade in its frame (ADR-0112, 2
October) - all of it presented to a window nobody sees. Load average about 3 on
four cores while playing.

A main-thread trace of the panel's renderer during the opens (five each,
`5-main-thread-trace.json`) shows the work an open costs: Home about 340 ms,
the artist grid about 780 ms (timers - its rows drawn in chunks, by design -
script, compositor commits, paint), Albums about 270 ms. With a core taken by
the visualiser, that work finishes later and frames are missed.

**Heat is not it:** the processor stayed at 1.8 GHz through every leg, 71-78 °C;
`get_throttled` 0x80000 records that the soft limit was reached once since boot,
not during the runs.

## What it means

The panel's own code is not slower than on 29 September. While music plays, a
hidden visualiser with a moving skin takes over half a core, and the panel's
screen opens drop 3-8 % of frames instead of about 1 %. A still skin, or the
visualiser not drawing while hidden, should give that back; the first is
untested, the second is a change to ADR-0019 for George to decide.

`panel-frames.py` was mended on the way: a tap now brings its target into view
(Home's cards scroll sideways, and Settings' card was off the glass), and the
artist grid is retried once while Home is still arriving.

## After the change (2026-10-07)

George chose to stop drawing while hidden; ADR-0019 was amended and built
(`/run/gexis/visualiser-shown`). Measured on `gexis` with the same moving
fanart skin: the hidden driver takes **6 % of a core while music plays**
(57 % before; 1 % paused, 54 % shown). Shown on request in 0.3 s, its first
frame complete (screenshot 50 ms after the request: needles, record, photo and
the current title all drawn).

The whole interaction set, 12 runs each and every one usable
(`6-hidden-not-drawing.txt`; the tool now ignores the library ADR-0122 keeps
hidden, which had made it tap a card nobody could see):

| Open | 29 Sep (Finding 101) | 0.9.2 | Hidden, not drawing |
| --- | --- | --- | --- |
| Home | 34.2 / 1.3 % | 48.4 / 4.3 % | 45.7 / 1.2 % |
| Artist grid | 43.5 / 3.3 % | 37.3 / 9.7 % | 50.5 / 2.0 % |
| Albums | 37.8 / 5.4 % | 37.6 / 9.0 % | 50.5 / 3.0 % |
| Artist page | 45.5 / 2.4 % | 44.8 / 9.1 % | 49.6 / 1.9 % |
| Playlists | 35.6 / 5.6 % | 41.3 / 7.1 % | 51.5 / 1.0 % |
| Queue rail | 54.5 / 1.6 % | 47.1 / 3.3 % | 49.7 / 1.0 % |
| Settings | 26.4 / 12.0 % | 43.1 / 0.0 % | 45.0 / 0.0 % |
| Radio | 37.5 / 7.1 % | 51.1 / 0.0 % | 48.7 / 3.9 % |

Every scroll 58.4-58.5 drawn/s, 0 % dropped. Every open is now at or below
Finding 101's, Radio excepted (3.9 % against 7.1 % then and 0 % in 0.9.2: its
runs range widely, as they did on 29 September). The processor ran at 1.8 GHz
in 36 of 38 samples; the two lower ones are the governor at rest between runs.
