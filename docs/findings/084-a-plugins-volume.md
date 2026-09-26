# Finding 084 — A plugin renderer's volume, both directions

**Date:** 2026-09-25
**Question:** Phase 11 criterion 4 — *volume mechanism derived and measured* —
for a renderer the core has no code for. The contract carries `set_volume`
outbound and `volume` inbound; neither had ever been used.
**Scope:** `gexis`, `gcarstoiu/gexis-plexamp`, one track playing. Driven through
`POST /volume` (the panel's own route) and through Plexamp's `setParameters`.
One run of each direction. **The panel's slider was not touched by hand** and
the DAC's actual output was not measured — only what each side reports.

## Both directions work

```
=== 1. the panel's slider drives Plexamp
  plexamp before: volume="56"
  POST /volume 30 -> 200      plexamp now: volume="30"
  POST /volume 65 -> 200      plexamp now: volume="65"
=== 2. Plexamp's own change reaches the core
  set 45 on the player -> 200
    volume: plexamp -> hardware (45/100 -> 204/240)
```

The second line is the interesting one: the plugin noticed the player's level
had moved, said so, and the core put it through
`renderer_value_to_hardware_raw` onto the real mixer — **the same single curve
every other renderer goes through since 2026-09-23**, with nothing about
Plexamp in it.

## What it needed

- **`remote.register` for a plugin**, at connect rather than at startup, when
  the adapter declares `volume_managed`. The three built-ins are registered from
  the same shape in `__main__`; this is that shape, later.
- **`remote.forget`**, which did not exist. A channel left behind is a slider
  the panel keeps offering for a renderer that is not there, and its `send`
  would write into a closed socket.
- **`PluginAdapter.set_volume`**, which swallows a dead session the way
  `release` does: the volume path runs on every drag of a slider and is not a
  place to take the daemon down.

## The echo, which this project has met twice before

Findings 045 and 047 are both about a volume that read its own write back. Here
the shape is: the core sets the level, the plugin's next poll a second later
reads that same number off the player, and reporting it would tell the daemon
the *user* had changed something.

**The plugin remembers what it was told before it sends it**, so its own write
is not news. Measured as an absence: **3 volume log lines in 20 seconds**,
across two commanded changes and one made on the player.

## What this does not show

- **Nothing about the hardware curve being right for this renderer.** 45/100
  became 204/240 through the shared curve; whether that *sounds* right against
  Spotify at the same number is a listening judgement nobody has made.
- **No mute**, no volume during a takeover, no drag — one value at a time,
  three times.
- **Nothing about a Plex controller changing the volume**, which is the way a
  person would actually do it. The change in leg 2 was an API call.
