# Re-rendering the boot screen

`../theme/still.png` is produced here, not imported. This directory exists
because importing the artwork twice produced two wrong sets.

## The boot screen is a still

**George, 2026-09-20**, after three boots of the 100-frame animation:
*"lets remove the animation and have a still instead ... no rings but the
faded hallow in the background"*.

```sh
node render.mjs ../theme/still.png     # the still that ships
node render.mjs ../theme               # all 100 frames, if the animation ever returns
```

The still is **frame 100**, pixel-identical to frame 51: the pulse's rest
state, so it carries the mark, the wordmark, `SOUND` and the faded halo and no
wavefronts. `01-run.sh` installs that one file as both the plymouth theme's
image **and** `/usr/share/gexis/panel-background.png`, the compositor's
wallpaper, and asserts they are identical — so the splash and what is behind
the compositor cannot be two different pictures.

What it bought beyond being what was asked for: plymouth holds one image
instead of a hundred, which retires ADR-0043's open question about ~400 MB of
decompressed frames rather than answering it, and there is no longer a loop
whose wrap must be pixel-identical or a join that must be invisible.

**Not** a dramatically smaller initramfs, though it was claimed as one before
it was measured. Across the four rebuilds of 2026-09-20:

| theme directory | `initramfs8` |
|---|---|
| 4.1 MB, the `c77d4e3` frames | 21,671,242 |
| 3.3 MB, re-rendered frames | 20,905,271 |
| 2.8 MB, wavefronts faded | 20,018,347 |
| **40 KB, the still** | **18,507,411** |

2.8 MB off an 18.5 MB image whose bulk is kernel modules — worth having, not
worth citing as a reason.

**The animation is still renderable and is not built.** Everything below
describes it, and the three constants still matter to the still because the
still is one of its frames — but the wavefront numbers now only affect frames
that nothing ships. Deleting the ability to rebuild the sequence would make
going back an import, and importing is what produced two wrong sets.

## Why this is not an import

Claude Design delivers a zip of 100 PNGs plus the renderer that made them.
Two deliveries in a row were wrong in opposite directions, and neither was
caught by reading the changelog that came with it:

| set | proportions | wavefronts |
|---|---|---|
| `2d446d5` (delivered 2026-09-19, redelivered 2026-09-20) | correct — mark larger | **clipped by the tiles** |
| `c77d4e3` (shipped to the device) | **wrong — wordmark larger** | correct |

The 2026-09-20 package is pixel-identical to `2d446d5`, frame for frame,
despite a changelog describing it as the correction for it. So neither
delivered set is usable, and the frames in `../theme/` are rendered here from
`frame.js` — Claude Design's own renderer, which arrived in that package —
with three constants changed.

## The three constants

All three exist because the mark grew at `2d446d5` (tile edge 28 → 115 design
px) and the wavefronts were never re-fitted to it. **If the mark is ever
resized again, all three move with it.**

**1. Where a ring is born.** `PL.w1s` / `PL.w2s` are the radius as a multiple
of `ringD/2` = 211 px. They started at `0.52` → **110 px**, inside a mark
reaching **168.8 px**, so each ring was drawn behind the tiles and cut into
arcs for the first quarter of its travel — George: "small lines in the
pictogram with each pulse". Now **0.93** → **196.3 px**, clearing by 27.5 px.

> 168.8 px, not `DIA/2` = 181.5 px. The tiles are *rounded* squares, so their
> corners fall short of the ideal diamond's points:
> `(T+G)/2·√2 + ((T/2−R)·√2 + R)` = 100.2 + 68.6. 181.5 is the safe
> over-estimate; 168.8 is the truth.

**2 and 3. Where a ring stops being visible.** `PL.w1o` / `PL.w2o`. The mark
centre is **297.8 px** from the top of the screen — it sits high so the
wordmark and `SOUND` fit beneath — while the rings ran to **401 px**. So 20 of
the 50 pulse frames had an arc sliced flat by the top edge. George saw it on
the panel, 2026-09-20: *"the rings were slightly clipped"*.

**Fixing 1 made this worse and it was not noticed**: pushing every ring 86 px
further out took the top-edge clipping from 16 frames to 20. The two were
traded, and only the one being fixed was measured.

Each opacity track's zero-crossing now lands at the frame where the ring is at
293 px — the top edge less half the 8.2 px stroke — so the wave dissipates
before it reaches the edge rather than being cut by it: `74 → 41.3` and
`86 → 54.3`. George chose this over capping the travel, which would have kept
the rings visible as long but made the ripple tighter.

**The cost, and it is real:** the rings now fade out by 54% of the pulse
instead of 86%, so the loop ends in **0.88 s of complete stillness** and 41 of
the 100 frames are exact duplicates, up from 26. The pulse reads calmer. It
also means a *frozen* frame is harder to tell from the animation — which
helps ADR-0043's amendment and hurts nothing, but is worth knowing.

## Running it

```sh
cd image/stage-gexis/06-splash/files/render
npm install @napi-rs/canvas
mkdir -p fonts && cd fonts
curl -sSLO 'https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz,wdth,wght%5D.ttf'
mv 'BricolageGrotesque[opsz,wdth,wght].ttf' BricolageGrotesque.ttf
curl -sSLO 'https://raw.githubusercontent.com/google/fonts/main/ofl/dmmono/DMMono-Medium.ttf'
cd ..
node render.mjs ../theme
python3 finish.py ../theme
```

`finish.py` drops the unused alpha channel and recompresses; without it the
frames on disk are not the frames committed here. It re-reads every frame
afterwards and fails if the recompression was not lossless.

**The fonts are not vendored** (a new vendored dependency is George's call, not
a side effect of a frame fix). Both are SIL OFL 1.1. Verify what you fetched:

```
413e7357809ddd12fd80a96a8a396de0e401638d4acd3cb3e37532f0472ac682  BricolageGrotesque.ttf
fd327daf461db87b44a87def475d251bf03b997f7c07d9680592d75dbbfaad0b  DMMono-Medium.ttf
```

## What rendering here costs

Rendering with `@napi-rs/canvas` is not Claude Design's rasteriser. Measured
against their own PNGs, rendering `frame.js` **unmodified** (ring start `0.52`):

```
mean absolute difference   0.40 / 255
pixels differing by > 12   0.5 – 0.6 %
```

and every one of those pixels is on a glyph outline or a tile edge. Geometry,
ring radii, glow, layout and colour are identical. That comparison is the
reason to trust the modified render: the only thing this environment changes
is text antialiasing, and it changes it the same way in all 100 frames.

## What must still hold afterwards

`01-run.sh` fails the build unless exactly 100 frames land, and installs
`boot-0100.png` as the panel wallpaper, so frame 100 must stay the pulse's
rest state. `../theme/gexis.script` hardcodes `INTRO 1–50`, `PULSE 51–100`,
`FRAMES 100` and 25 fps against plymouth's 50 Hz tick. Re-verify rather than
assume — that is how both wrong sets got through:

- 100 contiguous frames, 1280×800, alpha unused, ground exactly `#101a21`
- pulse wrap 100 → 51 **pixel-identical**, not merely close
- intro → pulse join far below the pulse's own interior step
- **the mark wider than the wordmark**, measured as separate bands rather than
  as one bounding box — `c77d4e3` read the union bbox, and the 311 px it
  reported as "the mark" was the wordmark
- **the ring unbroken**: bin the moving pixels by angle and require all 36
  ten-degree sectors to carry ring, on every pulse frame. A clipped ring
  scores 12/36 and 24/36 on the frames where it is worst. **Restrict the bin
  to radii outside the mark** — run over the whole canvas it counts the glow
  and scores 36/36 through a clip
- **the ring inside the canvas**: no moving pixel in row 0, row 799, column 0
  or column 1279, on any pulse frame. This is the check that was missing, and
  its absence is why a set that clipped 20 frames against the top of the
  screen was measured as clean and shipped to the device

`DESIGN-CHANGELOG.md` is Claude Design's, kept verbatim as the record of what
they believed they sent. It describes the redelivery as a correction; it is
not one.
