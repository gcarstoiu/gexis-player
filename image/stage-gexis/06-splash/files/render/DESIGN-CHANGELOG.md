# gexis boot frames — changelog

## Issue 2 — proportions corrected

**Replaces the whole set. All 100 frames are new files; the filenames,
ranges and playback rules are unchanged, so nothing on the device side needs
to change except the images.**

Seeing issue 1 on the panel, the wordmark read as too large and the mark as
too small. That was not an export fault — the frames were a faithful scale-up
of the approved screen design, which had deliberately made the wordmark the
dominant element. It was the design decision that was wrong at panel size,
so the proportions were re-cut and the set re-rendered.

| | issue 1 | **issue 2** |
|---|---|---|
| mark across | 187 px | **364 px** |
| `gexis` | 96 px | **72 px** |
| `SOUND` | 22 px | **30 px** |
| tile / gap / radius / glyph | 64 / 15 / 17 / 34 | **115 / 27 / 31 / 62** |

Typeface, weights, colours, timings, frame count, frame rate and both range
boundaries are identical to issue 1.

**Unchanged and re-verified:** 1280×800, fully opaque, ground exactly
`#101a21`, pulse wrap 100 → 51 pixel-identical (0 / 255), intro → pulse join
0.009 mean against ~0.3 for an ordinary interior step.

**One property no longer holds:** max non-ground is 9.8% (frame 80), against
the ~8% the brief asks for. It is a direct consequence of the larger mark.
See *Deviation* in `README.md` — including what to cut first if 8% is hard.

### Note on the first issue-2 package

The package handed over before this one carried issue-1-era frames by
mistake: the renderer had been re-cut but the PNGs that went into the zip
had not been replaced, so the device showed a small mark under a large
wordmark. Every frame in this package has been measured off disk after
writing — geometry, canvas size, alpha and ground colour — rather than
trusted from the render step.

## Issue 1

First delivery. Two ranges, intro 1–50 played once then pulse 51–100 looped.
