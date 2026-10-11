# ADR-0137 — Plugins are told when the output is Fixed

**Status:** **Accepted** — George, 2026-10-11: on Plexamp's slider still
working in Fixed, *"let's do b, and then a if nothing is found"*. (b), a
Plexamp setting that hides it, was looked for and is not there; this is (a).
**Builds on:** [ADR-0046](0046-fixed-output-hides-the-slider.md) (Fixed: full
level, the amplifier sets the volume), the plugin contract, version 1.

## Context

In Fixed every source plays at full level and its own slider changes
nothing - except Plexamp's. Plexamp's volume is a gain inside its own audio
engine, which the plugin leaves alone on purpose, so its app's slider really
lowers the sound in Fixed.

**Plexamp cannot be told to hide it** (read on sofapi, Plexamp 4.13.2): its
headless player builds the `controllable` list it advertises from a fixed
array that always holds `"volume"` - only *shuffle* is ever left out - and
the app shows its slider whenever that list holds it. Nothing among the
player's stored settings concerns volume. (The app has its own *Show volume*
switch, per phone, which no player can set.) A Plex forum request for a
"fixed volume" headless setting has no answer from Plex.

## Decision

1. **The core tells every plugin whether the output is Fixed**: a new
   core-to-plugin message, `{"t": "output", "id": n, "fixed": true}`, sent at
   `welcome` and whenever Fixed is put in force or taken out. Added within
   contract version 1: a plugin that does not know it answers `error`, which
   the core ignores.
2. **Plexamp's plugin keeps Plexamp at 100 while Fixed**: it sets 100 when
   told, and puts 100 back whenever its timeline shows another level. The
   app's slider still moves; the sound does not change - as Spotify's and
   Lyrion's sliders do in Fixed.
3. Out of Fixed, Plexamp's volume is left as the app sets it, as before.

## Consequences

- A gexis-plexamp release (0.4.5), and its pin moved here.
- The slider jumps back in the app: the one visible difference from the
  other sources, whose sliders stay where they were left.

## Amended 2026-10-11: within 0.2 s (plugin 0.4.6)

George: *"Can we make it faster than 1 second?"* Measured on sofapi with the
plugin's own `Plexamp` class, nothing playing, the level moved to 99 five
times: through the long poll alone it went back after **0.15 to 0.96 s** -
the poll does not always wake for a volume change and then runs out its
second. Asked every 0.2 s as well, while Fixed only: **0.06 to 0.20 s**.
Five local requests a second to Plexamp, only while the output is Fixed.
Not measured: how soon the app's own slider shows it.
