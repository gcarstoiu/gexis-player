# ADR-0154 — Four more weather icon sets

**Status:** **Accepted** — 2026-10-19, George, from previews: *Modern* and
*Futuristic* as first shown, *Photographic* and *Atmospheric* from a second
round on a realistic set (*"We keep both A and B"*); the music set dropped;
the four names, their order in *Weather icons* and the plan below confirmed
(*"Yes. Agreed"*).

## Context

*Weather icons* offers three sets, Solid, Duotone and Neon (ADR-0047), all
built from the design's DOM shapes in `WeatherIcon.svelte`. George asked for
three more - *"one more realistic one, one modern and one futuristic"* - and
for one connected to music. Four were previewed (Realistic, Modern,
Futuristic, Music); he dropped Music, kept Modern and Futuristic, and asked
for the realistic one to be *"realistic"*: three more were previewed, and he
kept two. Each preview covered every condition the screen draws, day and
night, with the moon in its phase (ADR-0153).

## Decision

1. **Four sets join the three**, in this order in *Weather icons*: Solid,
   Duotone, Neon, **Modern, Futuristic, Photographic, Atmospheric**. The
   default stays Solid. (ADR-0022, appended 2026-10-19.)
2. **Each as previewed** (the preview pages are the reference):
   - **Modern** - frosted glass over colour: a warm gradient sun, a violet
     moon, translucent clouds with a white edge and a soft coloured shadow,
     rounded drops, soft snow dots.
   - **Futuristic** - a heads-up display: thin cyan-to-magenta lines, a sun
     of rings turning opposite ways, scan lines inside the clouds, rain as
     falling data, hexagon snow, a hatched moon, an occasional glitch.
   - **Photographic** - the real Sun and Moon from NASA photographs (public
     domain: the Moon from the Lunar Reconnaissance Orbiter, NASA/GSFC/
     Arizona State University; the Sun from the Solar Dynamics Observatory's
     HMI, NASA/SDO), the Moon lit to its phase; clouds lit by a lighting
     model over fractal noise, darker underneath; rain as fine streaks, snow
     as six-armed crystals, branching lightning, fog banks.
   - **Atmospheric** - the same clouds, rain, snow, lightning and fog, with
     a drawn white-hot sun with bloom and a faint lens flare, and a drawn
     moon with a mottled surface and a halo.
3. **The moon at night applies to all four** as to the first three
   (ADR-0153): the same phase, the same mirroring south of the equator.
4. **The photographs ship with the player** and are named in *Credits*
   (`notices.json`, `THIRD-PARTY.md`) with their sources, though public
   domain asks for none.
5. **Measured before all four are built.** Photographic's lit clouds go on
   sofapi's idle screen first, and processor use is measured animated and
   still, as Finding 118 measured the first sets. If they cost too much,
   each icon is drawn once as a picture when the player is built, and the
   screen only moves the pictures.

## Consequences

- `WeatherIcon.svelte` grows four sets; the new ones are drawn as SVG,
  where the first three are DOM shapes.
- The image carries two small photographs (about 14 KB together at the
  previews' size).
- Not decided here: whether *Weather icon motion* Static is the default for
  the heavier sets - that waits for the measurement.
