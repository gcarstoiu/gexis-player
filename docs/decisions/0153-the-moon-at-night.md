# ADR-0153 — The moon at night

**Status:** **Accepted** — 2026-10-19, George: the moon in place of the sun
for the current weather between sunset and sunrise, in its real phase; one
design per icon set chosen from previews (*"C, A, B"*: Solid C, Duotone A,
Neon B).

## Context

The idle and waiting screens show the current weather with an icon in the
set *Weather icons* names (Solid, Duotone, Neon; ADR-0047). The sets draw a
sun for *clear*, *mostly clear*, *partly cloudy*, *showers* and *snow
showers*, day or night: George's photo of sofapi at 20:43 on 19 October showed
a sun and *Clear* under a sunset of 18:02. He asked for *"a moon in its
correct phase for the day of the month and location, following the general
style for the different icon sets"*, and for previews first. Four designs per
set were shown; he chose one each.

## Decision

1. **Between today's sunset and sunrise, the current weather's sun becomes
   the moon.** Only where a sun is drawn: clear, mostly clear, partly cloudy,
   showers, snow showers. Overcast, rain, fog and the rest draw no sun and
   are unchanged. **The forecast days keep their sun**: each describes a
   whole day.
2. **Night is decided by the screen's own clock** against today's sunrise and
   sunset, which the core sends as moments (`sun.rise_at`, `sun.sets_at`,
   seconds since 1970, from the provider's times and the place's UTC offset)
   beside the `HH:MM` it already sends. The moon comes at sunset, not at the
   next forecast fetch (every 15 minutes). Without them (an old core, a
   provider that sent none), it stays day.
3. **The phase is worked out from the date** - the moon's age in a mean
   synodic month (29.530588853 days) from the new moon of 6 January 2000,
   18:14 UTC. Off by at most about a day from the real phase, which no icon
   this size can show; no service is asked. The shape is drawn exactly: the
   lit fraction, not the nearest of eight pictures.
4. **The place decides which side is lit**: waxing, the right side north of
   the equator and the left side south of it, waning the reverse. The core
   sends `south` (the place's latitude below zero). The tilt of the crescent,
   which also varies with latitude and the hour, is not drawn.
5. **One design per set, in the set's own manner**:
   - **Solid** (C): a pale flat disc, its dark part a faint shape, a few
     darker maria on the lit part, two small stars that twinkle where the
     sun's rays would turn.
   - **Duotone** (A): a shadow disc offset behind the moon, the dark part
     deep blue-grey, the lit part pale, pulsing as the duotone sun does.
   - **Neon** (B): nothing filled - the disc a faint cyan ring, the lit edge
     a glowing cyan line, two small yellow stars.
   At new moon the faint disc or ring is all that shows, so the icon is never
   empty. With a cloud, the moon sits where the sun does, smaller and up to
   the left. *Weather icon motion* off stills it as it stills the sun.
6. **No setting.** Proposed to George as always on (2026-10-19); no row for
   ADR-0022's inventory.

## Consequences

- `weather.py` asks the provider for nothing new (`utc_offset_seconds` comes
  with every answer); `IdleWeather` in the OpenAPI file gains `south`,
  `sun.rise_at` and `sun.sets_at`.
- `WeatherIcon.svelte` gains the moon; the idle screen passes night, phase
  and hemisphere to the current conditions' icon only.
- Not covered: a place whose time zone differs from the player's still gets
  its night right (moments, not clock times); polar day and night, when the
  provider sends no sunrise or sunset, stay day.
