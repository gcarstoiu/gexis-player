# Finding 055 — What the panel presents, after the design sweep

**Date:** 2026-09-24
**Question:** Phase 9 criterion 0 step 1. [Finding 034](034-what-the-panel-presents.md)'s
table is void twice over — its idle control was measuring a queue rail left
open by the run before it, and 9a–9k have since rebuilt the screens it
measured. Nothing can be judged against it.
**Scope:** `gexis`, 2026-09-24, image `v0.2.1-455`, **music playing
throughout**, `tools/panel-frames.py` at `cbd344f` driving
`tools/panel-touch.py`. **Fifteen scenes, twenty runs each.** Frame fates
come from the compositor's `PipelineReporter`, never from the page; input is
a finger through `/dev/uinput`. **Everything on the panel**, per George's
ruling of the same day, not only the three screens 034 measured. **Not
measured:** the visualiser (a separate process, not Chromium's frames), the
idle screen, first boot, and anything on a phone.

**The target** (Phase 7a criterion 4): **under 2% of frames dropped and no
interaction below 55 fps.**

## The table

| scene | fps median | dropped median | min–max | partial | frames/run |
| --- | --- | --- | --- | --- | --- |
| idle-control | 58.8 | **3.43%** | 0.00–10.84 | 0.00% | 86 |
| home-open | 37.4 | 16.08% | 12.86–25.35 | 5.63% | 70 |
| new-music-scroll | 31.5 | 24.56% | 19.74–29.27 | 1.26% | 80 |
| artist-grid-open | **14.9** | 0.00% | 0.00–12.90 | 0.00% | 29 |
| **artist-grid-scroll** | 26.8 | **49.64%** | 41.98–55.56 | 4.20% | 68 |
| queue-rail-open | 43.0 | 14.29% | 9.59–29.17 | 1.41% | 71 |
| queue-rail-scroll | 50.0 | 11.39% | 1.27–26.92 | 0.00% | 78 |
| settings-open | 26.2 | 11.27% | 0.00–16.22 | 3.03% | 34 |
| **settings-scroll** | — | — | — | — | **composited: 718–763 px moved, no repaint asked for** |
| albums-open | **57.7** | 4.88% | 3.12–12.90 | **49.16%** | 62 |
| albums-scroll | 35.5 | 27.08% | 17.14–34.25 | 1.37% | 71 |
| playlists-open | 45.0 | **5.63%** | 4.23–9.86 | 0.00% | 71 |
| radio-open | 31.5 | 12.68% | 11.27–15.71 | 0.00% | 71 |
| artist-page-open | 44.4 | 20.74% | 15.15–31.91 | **33.84%** | 68 |
| artist-page-scroll | 20.9 | 30.12% | 24.05–32.91 | 0.00% | 79 |

## What it says

**Nothing on the panel meets the target.** One scene passes, and it passes
by not drawing: Settings' list is already-rasterised text, so dragging it is
a compositor transform with nothing to repaint.

**The list scrolls are the work**, and they are the four worst dropped
figures: the artist grid at **49.6%**, the artist page at 30.1%, the album
pane at 27.1%, New Music at 24.6%. That is the evidence for criterion 0's
step 4 being list work rather than anything else.

**ADR-0041 is confirmed on the one screen that had a scrim.** The queue rail
was Finding 034's worst at **13.9 fps / 75.2% dropped**; it is now **50.0
fps / 11.4%**. Removing `backdrop-filter` did what Finding 037 predicted and
the rail is now the *best* of the scrolls — still short of 55 fps, and no
longer the problem.

**The artist grid is unchanged.** 034 measured 50.7% dropped; it is 49.6%
now. It never had a scrim, so nothing that has landed since was ever going
to help it. **917 artists in one list is the single biggest item in this
criterion.**

**Two scenes are slow without dropping anything.** `artist-grid-open` runs
at 14.9 fps with **0% dropped** over only 29 frames a run, and
`settings-open` at 26.2 over 34. Few frames, none of them late: these are
transitions that take a long time to ask for anything, not frames arriving
late. They need a different instrument question than the scrolls do.

**Two scenes present frames with something missing.** `albums-open` reports
**49.2% partial** and `artist-page-open` 33.8% — a frame that arrived
without all of its content. Both are screens that open onto artwork.
Nothing here says which content; that is step 3's job.

**Even the idle panel misses the dropped target**, at 3.43% median against
2%, with one run disturbed by a track change. It is nowhere near Finding
034's void 71%, and *an idle panel is idle* still holds — but "idle" is not
"free", and a 2% budget leaves little room for whatever this is.

## The instrument, and four more faults

Extending the harness from three screens to fifteen found four faults
**before any number was taken**, each the same shape as Finding 034's five:
a selector believed to mean what it appears to mean.

1. **Settings' Back is not a `.btn`.** A run that ended inside a settings
   picker could not get out, and every scene after it failed on the wrong
   assertion.
2. **A scroll scene that does not return to the top measures the end of a
   list.** Settings' Display section runs out in one swipe; every run after
   the first dragged against a stop and reported 31 frames of
   `NO_UPDATE_DESIRED`, which reads as *smooth*.
3. **"Nothing drawn" looked identical to "nothing moved".** Each run now
   records how far its scroller travelled, which is what lets the
   composited-scroll row above say something true instead of failing.
4. **Three scrims are mounted on a clear screen**, at full size with
   `opacity: 0`. The guard added after 034's void idle control would itself
   have blocked every idle measurement, for a different wrong reason.

And one that cost a whole run: **a scene's failure took the other fourteen
with it.** Twenty minutes of completed results were in memory when the last
scene raised on a wrong selector. Each scene now fails alone.

## What this does not settle

- **No cause is attributed.** Every number here is *what*, not *why*; step 3
  is one number per candidate.
- **Nothing was compared with Finding 034 except the two scenes whose
  screens did not change**, and even those ran on a rebuilt panel.
- **The visualiser and the idle screen are unmeasured**, and the visualiser
  cannot be measured with this instrument at all.
- **One run in three scenes was disturbed** by a track change and is left in
  the distribution rather than dropped, flagged in the output.
