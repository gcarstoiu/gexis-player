# Re-rendering the boot frames

`../theme/boot-0001.png` … `boot-0100.png` are produced here, not imported.
This directory exists because importing them twice produced two wrong sets.

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
with one constant changed.

## The one constant

`frame.js` lines 35 and 37, `PL.w1s` and `PL.w2s`, are the wavefronts' radius
as a multiple of `ringD/2` = 211 px. They started at `0.52` → **110 px**,
inside a mark whose tile diamond reaches `D/2` = **182 px**, so each ring was
born behind the mark and drawn as arcs cut by the tiles for the first quarter
of its travel. That is what George reported as "small lines in the pictogram
with each pulse".

`render.mjs` rewrites both to **0.93** → **196 px**, which clears the tiles by
14 px. The defect came back in the first place because the mark grew (tile
edge 28 → 115 design px at `2d446d5`) and the ring radii did not grow with it:
**if the mark is ever resized, this number moves with it.**

## Running it

```sh
cd image/stage-gexis/06-splash/files/render
npm install @napi-rs/canvas
mkdir -p fonts && cd fonts
curl -sSLO 'https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz,wdth,wght%5D.ttf'
mv 'BricolageGrotesque[opsz,wdth,wght].ttf' BricolageGrotesque.ttf
curl -sSLO 'https://raw.githubusercontent.com/google/fonts/main/ofl/dmmono/DMMono-Medium.ttf'
cd ..
node render.mjs 0.93 ../theme
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
  scores 12/36 and 24/36 on the frames where it is worst

`DESIGN-CHANGELOG.md` is Claude Design's, kept verbatim as the record of what
they believed they sent. It describes the redelivery as a correction; it is
not one.
