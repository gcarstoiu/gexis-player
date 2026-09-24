# Finding 059 — Every scroll on the panel pays for the background's blur

> **Corrected 2026-09-24, the same day, by
> [Finding 061](061-the-background-wants-a-layer-of-its-own.md).** Three
> rows below — `will-change: transform`, `contain: paint` and
> `translateZ(0)` on `.bg` — were written with the selector
> `[aria-hidden='true'] .bg`, **which matches nothing**: `.bg` *is* the
> element carrying `aria-hidden`, not a descendant of one. Those variants
> measured the page unchanged while wearing a variant's name. With the
> selector fixed, **`will-change: transform` on `.bg` takes the artist grid
> from 27.8 fps to 52.9** — as good as deleting the blurs — and is
> pixel-identical. So the paragraph below claiming a cached layer *cannot*
> help is wrong, and so is the reasoning built on it. The `.weave` and
> `.bleed` variants **are** descendants of `.bg` and did apply, so every
> blur result here stands.

**Date:** 2026-09-24
**Question:** Criterion 0 step 3. [Finding 058](058-what-the-scrolls-are-not.md)
eliminated eight candidates for the scrolls and named none. This names it.
**Scope:** `gexis`, 2026-09-24, music playing, one library, one artwork.
Medians of 8 runs per cell (15 for the baseline). Every variant was applied
to the live page and removed. **Not settled: the look** — that is George's,
and the screenshots are with this record.

## The answer

**`filter: blur()` on `PanelBackground`.** Two of them, behind every screen:
a `blur(70px)` weave and a `blur(72px) saturate(1.7)` bleed of the artwork.
Suppress both and the artist grid goes from **25.6 fps / 33.81% dropped** to
**54.4 fps / 1.61%**.

The panel does not pay for this while it sits still — Finding 057's still
screens are 0.00% at 49.9 fps, because nothing is damaged and the previous
frame is reused. It pays whenever something damages a large area, and a
scroll damages the whole scroller.

## Why the eight candidates were all negative

A blur is re-evaluated over the region a frame damages, expanded by its own
radius. So the cost is **the damaged area**, and nothing about what is in
it. That is exactly what Finding 058 measured without being able to explain:
emptying the tiles, cutting the list from 39,751 px to 6,013, stopping the
photo fetches and removing all 917 observers changed nothing, because none
of them changes the area being redrawn.

With one gesture — 170 px over 420 ms, the same everywhere — the panel
orders itself by how much of it a scroller covers:

| scroll | viewport | moved | dropped | fps |
| --- | --- | --- | --- | --- |
| artist grid | 1222 × 600 | 182 px | **32.26%** | 25.6 |
| artist page | 908 × 550 | 183 px | 28.36% | 30.0 |
| queue rail | 417 × 597 | 179 px | 17.91% | 34.8 |
| browse artists | 535 × 250 | 183 px | 10.00% | 44.2 |
| new music | 1220 × 237 | 185 px | 9.68% | 43.4 |
| settings | 990 × 708 | 181 px | *composited, nothing repainted* | |

**And the queue rail is the control.** `.rail` sits on
`--bg-panel: #16232c`, fully opaque, so it occludes the blur beneath it.
Removing the background moves the grid 19 fps and the rail 0.6:

| | artist grid | queue rail |
| --- | --- | --- |
| as it ships | 27.7 fps / 31.58% | 36.4 fps / 17.60% |
| background removed | **48.4 fps / 5.48%** | 35.8 fps / 16.96% |

The rail's own 17.9% is its rows, and is a separate question.

## Four things that do not fix it

> **This section is the one that was wrong — see the correction above.**
> Three of its four rows selected nothing. The corrected measurement is in
> [Finding 061](061-the-background-wants-a-layer-of-its-own.md); what
> survives here is the last row, which used `.weave`/`.bleed` and did apply.

| on the artist grid | dropped | fps | |
| --- | --- | --- | --- |
| as it ships | 33.81% | 25.6 | |
| `.bg { will-change: transform }` | 30.55% | 25.5 | **void — matched nothing** |
| `.bg { contain: paint }` | 31.58% | 25.5 | **void — matched nothing** |
| `.bg { transform: translateZ(0) }` | 31.11% | 27.8 | **void — matched nothing** |
| `will-change` on the blurs themselves | **44.97%** | 26.2 | stands |

Promoting the two *filtered* elements to layers of their own made it worse,
which is real and is not the same test as promoting their parent.

**And a smaller radius does not fix it either.** A 9 px blur costs nearly
what a 70 px blur costs; it is the filter's existence that is dear:

| blur | artist grid | browse pane |
| --- | --- | --- |
| 70/72, as it ships | 24.4 fps / 31.05% | 43.4 fps / 14.25% |
| 35/36 | 29.6 / 24.21% | 45.8 / 8.03% |
| 18/18 | 27.9 / 23.13% | 46.1 / 7.12% |
| 9/9 | 30.1 / 25.77% | 48.4 / 7.24% |
| **`filter: none`** | **43.7 / 6.79%** | **57.8 / 0.00%** |
| hidden entirely | 47.0 / 5.59% | 51.6 / 0.00% |

**Making the scroller opaque "fixes" the percentage by making the panel
worse.** It reads 0.00% dropped — at 13.9 fps, half the frame rate it had.
The compositor stopped asking for frames it could not deliver, so none were
dropped. Percent dropped is not the outcome; delivered frames are.

| on the artist grid | dropped | fps |
| --- | --- | --- |
| as it ships | 31.58% | 27.7 |
| opaque background on the scroller | 0.00% | **13.9** |
| opaque on the scroller and its rows | 0.00% | **12.8** |
| `will-change: transform` on the scroller | 0.00% | **13.9** |

**And CSS cannot fake a downscale.** `width: 12px; transform: scale(133)`
stays sharp: Chromium rasterises a scaled element at its *final* size from
the full-resolution source, so the small intermediate never exists. The
screenshot reads "ROD STEWART / ANOTHER COUNTRY" in the background.

## What does fix it

**Hand the browser a small picture instead of a filter.** The artwork URL
carries its own size — `cover_500x500_o.jpg` — so a 16 px cover stretched
over the panel *is* a blur, drawn as a texture blit with no filter at all.
Measured on the artist grid, with the weave's filter dropped too:

| artist grid | dropped | fps |
| --- | --- | --- |
| as it ships | 32.84% | 27.4 |
| **16 px bleed, no filter anywhere** | **6.50%** | **44.7** |
| background removed entirely (the ceiling) | 5.63% | 45.7 |

That is the whole of it: **within 1 fps of removing the background, with the
background still there** — and superseded the same day by a one-line change
that costs nothing at all
([Finding 061](061-the-background-wants-a-layer-of-its-own.md)).

Two costs, both visible in the screenshots beside this finding:

- **`saturate(1.7)` is a filter as well.** Keeping it gives back 41.2 fps
  instead of 43.0 — about two frames for the bleed's warmth.
- **The weave loses its blur.** It is a 48 px diagonal repeating gradient
  between `#3f5a6d` and `#2e4453`, and under the screens' veils the banding
  is not visible at 3.2× brightness. It is also *static*, so it can be baked
  into an image and keep its blur exactly, at no per-frame cost.

## What this does not settle

- **The look.** Both changes are visible in principle and neither is mine to
  make. Screenshots at source sizes 8/12/16/24/32/64 are in the session's
  scratch; 16 px is the closest match to the shipped blur.
- **The queue rail's own 17.9%.** It is immune to the background and still
  drops frames. Different question, not yet asked.
- **Why every list scrolls on the main thread at all.** Finding 032 saw
  `SCROLL_MAIN_THREAD` everywhere and blamed its own synthesised touches;
  with real touches through `/dev/uinput` it is still
  `SCROLL_MAIN_THREAD` everywhere, so that caveat is now resolved in the
  other direction. Whether composited scrolling is reachable here is
  untested.
- **Anything about a phone.** One panel, one device.
