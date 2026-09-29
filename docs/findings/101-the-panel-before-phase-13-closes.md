# Finding 101 — The panel before Phase 13 closes: criterion 0's revisit

**Date:** 2026-09-29
**Question:** [ADR-0076](../decisions/0076-criterion-0-closes-with-the-opens-below-the-floor.md)
closed Phase 9 criterion 0 with the screen opens below Phase 7a's floor
(*under 2 % dropped, no interaction below 55 fps*) and set a revisit before
Phase 13: retake [Finding 067](067-what-the-panel-presents-at-the-end-of-criterion-0.md)'s
table, bring George's verdict from use, and pull the lever only if the opens
still fall short **and still matter**.
**Scope:** the Pi 4 and 10" panel that is `gexis`, on the second card (then
`sofapi4`: image 755-g6eb6439 with `phase-13`'s UI and core deployed by hand -
the setup screens, nothing that changed the panel's other screens since
Finding 067). `tools/panel-frames.py` as at `phase-13`, `--runs 12
--playback playing`, the kiosk's debug port on for the run and off afterwards
(checked: `kiosk.env` identical to before, port 9222 closed). Music: an album
through LMS, *John Williams Legacy*. Frames as `drawn/s`
(`DrawToScheduleOverlay`), as in Finding 067. **Not measured:** the queue
rail's scroll (the queue the panel was sent held one item, so there was
nothing to scroll - the tool said so rather than measuring a still list); a
phone; gexis's own card.

## George's verdict, after four days of use

*"Everything seems really snappy. Quite happy."* (2026-09-29). This is the
evidence ADR-0076 deferred to.

## The scrolls still meet the floor

| | 2026-09-25 | **2026-09-29** |
| --- | --- | --- |
| new music | 59.2 / 0.00 % | **58.4 / 0.00 %** |
| artist grid | 58.2 / 0.00 % | **58.3 / 0.00 %** |
| browse pane | 58.2 / 0.00 % | **58.5 / 0.00 %** |
| artist page | 56.9 / 0.00 % | **58.5 / 0.00 %** |
| settings | composited | composited, 182-188 px with no repaint |
| queue rail | 59.5 / 0.00 % | not measured (one item) |

Still screens: **49.9 drawn/s, 0.00 %**, as before (the progress bar).

## The opens are where they were

| (drawn/s / dropped, median of 12) | 2026-09-25 | **2026-09-29** |
| --- | --- | --- |
| queue rail open | 52.7 / 3.18 % | **54.5 / 1.58 %** |
| artist page open | 41.6 / 5.63 % | **45.5 / 2.42 %** |
| artist grid open | 41.8 / 4.92 % | **43.5 / 3.33 %** |
| albums open | 41.7 / 5.26 % | **37.8 / 5.41 %** |
| radio open | 41.3 / 4.27 % | **37.5 / 7.14 %** (one run at 21 %) |
| playlists open | 37.5 / 5.31 % | **35.6 / 5.56 %** |
| home open | 37.5 / 2.50 % | **34.2 / 1.28 %** |
| settings open | 30.2 / 4.00 % (7 of 12 usable) | **26.4 / 12.00 %** (8 of 12 usable) |

**Every open is still below 55 drawn/s**, and five of eight still drop more
than 2 %. Against Finding 067 the picture is the same within run-to-run spread:
three opens a little better (queue rail now under 2 % dropped, artist page and
grid), four a little worse, none by a margin the spread does not cover.
**Settings open is the outlier and the thinnest**: 8 usable runs, as in 067's
7, so its 12 % is soft - but it is the lowest drawn/s on the panel both times.

The measured lever is unchanged from Finding 067: roughly 190 ms of a ~280 ms
transition is the home screen's cards and covers being torn down.

## What it bears on

- **Criterion 0's revisit has both of its inputs**: the opens still fall short
  of the floor by about as much as when it was waived, and the person who has
  lived with the panel finds it snappy. Whether that closes the revisit or
  pulls the lever is George's call (ADR-0076).
- **Settings open** is the one to watch if anything is.
