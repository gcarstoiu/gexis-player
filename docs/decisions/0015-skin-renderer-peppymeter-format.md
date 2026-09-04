# ADR-0015 — Skin renderer targets the PeppyMeter/Volumio extended format

**Status:** Accepted (one implementation decision deferred to a spike)
**Date:** 2026-09-04
**Relates to:** ADR-0011 (meter data transports), ADR-0014 (distinct screens)

## Context

The Peppy screen renders community skins. The value is in the skin ecosystem —
Gelo5's 1280x800 set for Volumio — so consuming that format unmodified is the
point, not an implementation convenience.

ADR-0014 established that the skin renderer needs the playback model, not just
level data, which is why it lives in the presentation layer where the state
WebSocket already exists.

This record specifies what the renderer must consume. Everything in §Schema was
established by direct inspection of the three configuration files, not from
documentation.

## Decision

**The skin renderer consumes the PeppyMeter/Volumio extended format unmodified,
in the browser, at 1280x800.**

Skins are not converted, pre-processed, or re-authored. A skin folder from the
community drops in and works.

## Corpus

Three files, two corpora, 84 skins total:

| File | Sections | Contents |
|---|---|---|
| `templates/meters.txt` | 71 | meter-only skins |
| `templates_spectrum/meters.txt` | 13 | meter + spectrum skins |
| `templates_spectrum/spectrum.txt` | 13 | spectrum definitions |

Meter type distribution across all 84: **circular 66, linear 18.** Nothing else.
All `channels = 2`. All `ui.refresh.period = 0.033` (30 fps).

The 13 spectrum skins are all circular — linear appears only in the meter-only
corpus.

## Linkage between meter and spectrum

**By explicit name, not by position.** Each section in the spectrum corpus
carries:

```
spectrum.name = Free
```

which references a section in `spectrum.txt`. Verified: **13 of 13 resolve, zero
orphans.** The names are not identical to the meter section names — `104G5_Lyngdorf
S+M` references `Lyng`, `108G5_Kenwood Rev S+M` references `Kenwoo` — so
positional or fuzzy matching would break. The reference is exact and must be
treated as such.

## Visibility flags are authoritative

```
meter.visible     True on 10, False on 3
spectrum.visible  True on 13
```

**Three skins carry a complete circular meter definition and set `meter.visible
= False`.** They display spectrum only. The renderer must honour the flag and
must not infer intent from the presence of meter keys.

## Schema

### Common to all skins

```
meter.type          circular | linear
channels            2
ui.refresh.period   0.033
screen.bgr          full-screen JPG
bgr.filename        meter background PNG
fgr.filename        overlay PNG (optional — present on 54 of 71 meter-only)
indicator.filename  needle or bar sprite
meter.x, meter.y    meter placement
```

### Circular

```
steps.per.degree            2 or 4
start.angle, stop.angle     e.g. 49 / -49
left.origin.x/y             needle pivot, left channel
right.origin.x/y            needle pivot, right channel
distance                    meaning not established — see Unverified
```

Two skins override angles per channel with `left.start.angle`,
`left.stop.angle`, `right.start.angle`, `right.stop.angle`.

### Linear

```
left.x, left.y              bar origin, left channel
right.x, right.y            bar origin, right channel
direction                   bottom-top (5 skins) — otherwise horizontal
indicator.type              single (2 skins)
position.regular            step count, normal range
position.overload           step count, overload range
step.width.regular          per-step advance
step.width.overload         per-step advance in overload
```

### Spectrum

```
spectrum.x, spectrum.y      placement
origin.x, origin.y          bar origin within the spectrum background
bgr.filename                spectrum background
bar.filename                single bar sprite
bar.width, bar.height       bar sprite dimensions
bar.gap                     spacing between bars
reflection.type             image.extended (8 of 13) or empty (5)
reflection.filename         usually a second bar sprite
reflection.gap
topping.height              peak-hold cap height
topping.step
steps                       bar count — 15, 20, 25 or 30
fgr.filename                overlay (only 1 of 13 uses it)
```

Referencing sections also carry `spectrum.size` as `width,height`.

### Extended layout — `config.extend = True` on every skin

```
albumart.pos, albumart.dimension
albumart.mask               JPG mask (5 skins)
albumart.border             (meter-only corpus)
playinfo.title.pos          x,y,weight
playinfo.artist.pos         x,y,weight
playinfo.album.pos          x,y,weight (optional)
playinfo.*.color            per-element (spectrum corpus)
playinfo.*.maxwidth         per-element (spectrum corpus)
playinfo.center             bool
playinfo.text.center        bool (4 skins)
playinfo.maxwidth
playinfo.type.pos/.color/.dimension    source or codec badge
playinfo.samplerate.pos     x,y,weight
time.remaining.pos, time.remaining.color
font.size.digi/.light/.regular/.bold
font.color
```

**The two corpora have different key sets.** The union is the schema; neither
file alone defines it. The spectrum corpus adds per-element colour and maxwidth
and `albumart.mask`; the meter-only corpus adds all the linear keys and
`albumart.border`.

## Rendering model

Layers, explicit in the data, mapping to stacked DOM layers:

```
screen.bgr          full-screen JPG          static
bgr.filename        meter background PNG     static
indicator           needle / bar / spectrum  30 fps
fgr.filename        overlay PNG              static
albumart + text     from playback state      per track
```

**Only the indicator layer changes per frame.** A circular needle is a CSS
`transform: rotate()` on an `<img>` — GPU-composited, with no repaint of the
static layers. PeppyMeter blits sprites on the CPU, which is where its cost
comes from.

## Validation

**Every skin in the corpus is parsed on every commit.** Unknown `meter.type`
values or unknown keys fail the build. This is how a new skin pack breaking the
renderer gets found, rather than by a user seeing a blank screen.

---

## Resolved

### Absent fields: the layer does not render

**Where a metadata field is absent, its layer is not drawn at all.** No blank
rectangle, no placeholder box. `screen.bgr` shows through the gap.

*Rationale:* the skin author chose what sits behind the artwork and the text.
Respecting that choice produces a coherent screen; a grey placeholder rectangle
produces a broken one. This is the only option of the three considered that
treats the skin as a design rather than as a template with holes.

Applies to artwork, album line, remaining time and the source badge alike.

### Enrichment fills the gaps where it can

The enrichment service (ADR-0012) should supply as much as possible so the
absent-field path is rare rather than routine. But the gaps split into two
kinds, and only one is closeable:

| Field | Enrichable | Source |
|---|---|---|
| title, artist | already supplied | renderer |
| album | **yes** | MusicBrainz lookup on artist + title |
| artwork | **yes** | Cover Art Archive, keyed on a resolved release |
| sample rate | **no** | a property of the stream, not of the recording |
| remaining time | **no** | needs duration and position from the renderer |
| source badge | always available | ours |

So for Bluetooth, enrichment can close the artwork and album gaps. **The sample
rate and remaining time gaps are permanent** — no lookup can produce them, and
inventing them would violate ADR-0012's additive-only rule.

One nuance on sample rate: Bluetooth does have a decode rate, but it is the
codec's rate, not the source's. Displaying "44.1 kHz" beside a lossy stream
would be true and misleading. Whether to show it is left to ADR-0019.

#### Consequence: late arrival on a display-only screen

Enrichment is asynchronous and must not block rendering (ADR-0012). On the
Peppy screen this means artwork can appear one or two seconds after a track
starts, popping into a gap that was showing `screen.bgr`.

The renderer therefore **fades the artwork layer in** rather than switching it,
and holds the previous track's artwork until the replacement resolves rather
than clearing to a gap on every track change. A gap that appears and fills is
more disruptive on a passive display than on an interactive one, because the
user is watching it rather than using it.

Enriched artwork receives the same `albumart.mask` treatment as
renderer-supplied artwork. The mask is a property of the skin, not of the
source.

## Deferred to implementation

### `steps.per.degree` — decide by looking at it

Values in the corpus are 2 and 4. PeppyMeter pre-renders rotated needle sprites
at that granularity, so the needle moves in visible increments. A browser
rendering continuous rotation would be smoother than the original.

**This is not decidable from the configuration.** Several of these skins are
period reproductions of specific hardware, and whether the stepping reads as
authentic or as a rendering artefact is a matter of appearance.

**Decision deferred to a spike**, with the test defined now so it is not
improvised later:

1. Render one circular skin at `steps.per.degree = 2` and one at 4, both
   quantised and continuous, at 1280x800 on the target screen.
2. Compare against PeppyMeter rendering the same skin, so the reference is the
   original rather than a memory of it.
3. Decide, and record the outcome as an amendment to this record.

Implement it as a toggle regardless, since the difference is one line and the
spike needs both paths anyway. Whether the toggle survives as a user setting is
part of what the spike decides.

## Blocked — assets not yet inspected

These do not block the decision but do block implementation:

- **Needle sprite authoring convention.** Pivot location, transparent margins,
  single image or strip. Needed before `left.origin.x/y` and `distance` can be
  interpreted correctly.
- **Font faces.** The skins specify four weights and assume faces the Volumio
  plugin supplies. Wrong faces means wrong metrics and text overflowing
  `playinfo.maxwidth`.
- **The `playinfo.type` icon set.** `playinfo.type.color` with a 40x40 or 50x50
  dimension reads as a tinted source or codec badge; the source of the icons is
  unknown.

## Unverified

- **The meaning of `distance`** (values include 100 and 140) on circular skins,
  where both needle origins are already given explicitly.
- **The meaning of `spectrum.size`.** It is not derivable from bar geometry: for
  `Free`, 25 bars at width 30 with gap 9 gives 966 px, but `spectrum.size` is
  `933,176`; for `Naim`, 15 bars at width 11 with gap 4 gives 221 px against
  `364,280`. Likely a clip region or the background image dimensions, but this
  is inference, not a finding.
- **`reflection.type = image.extended`** — assumed to mirror the bars below the
  baseline, from the key name and the presence of a second sprite. Not confirmed.
- Whether `bar.height` is the sprite height or the maximum bar extent.
- Per-frame cost of the layered browser approach at 1280x800 on a Pi 4.
