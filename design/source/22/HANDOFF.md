# Handoff: gexis multiroom — Phase 22, 2026-10-28

## Overview

Grouping gexis players so they play the same music in sync (ADR-0166,
`design/briefs/22-multiroom.md`): on the phone remote's *Gexis players*
list, in the panel's volume drawer and the bar's tray, the grouped mark on
Now Playing, and the group volume. George's picks: **1a** Join and Remove on
each row, **2a** the volume drawer and the tray, **3a** the mark centred
midway between the progress bar and the play control.

Target repo: `gcarstoiu/gexis-player` (Svelte 5 UI over a Python core).

## Production wins — read this first

**The screens under these additions must not change from what is in
production.** The panel and bar artboards are drawn over pictures of the
design files, and on the bars those pictures do not match production
(strip, transport, tray). Do not restyle, move or resize anything in
production to match an artboard. Build only what Phase 22 adds:

1. the grouped mark (panel, bar, phone),
2. the group in the panel's volume drawer and the bar's tray,
3. the group on the phone's *Gexis players* list and the group volume sheet.

Place them by the rules in the spec (midway between, beside, under), not by
artboard pixels. Where a picture and production disagree, production wins.

## About the design files

The `.dc.html` files are **design references built in HTML**: interactive
prototypes, not production code. Recreate them in the repo's own
environment (Svelte 5 components, the project's state and tokens). Do not
ship or copy their markup.

```
cd design && python3 -m http.server 8080
# http://localhost:8080/source/22/Multiroom%20Board.dc.html
# add #shot=1a-1,2a-3 to render only those artboards
```

## Fidelity

**High** for the additions: colours, type, spacing, states, words and
behaviour are final. Everything underneath them is production's.

## Read

- `design/source/22/README.md` — the spec: component boundaries, rules,
  words, each surface.
- `design/tokens.css` — Phase 22 at the end.
- `design/source/22/png/` — one PNG per state, named by artboard id
  (1a-*, 2a-*, 3a-*, S1–S5).

## Rules decided in design (not in ADR-0166)

- The leader can't be removed and has no Leave; it ends grouping with Undo
  group, which asks first and keeps the music on the leader.
- The *All* slider moves every variable member by the same step; its mute
  mutes every member. Fixed members keep their mute.
- Joining stops a player's own music without asking, and takes it out of
  any other group.
- Each member keeps its own equaliser.
- The leader going off leaves the others grouped and silent.

## Data

Check against `design/data-contract.md` and add, marked NEW: group
membership and leader per player, join / remove / leave / undo, per-member
level and mute, group level as a relative step, and a *joining* state.
Phase 21's open change still stands: mute works when the output is fixed.

## Files

```
HANDOFF.md                                   this file
design/tokens.css                            every token; Phase 22 at the end
design/BUNDLE-README.md                      bundle index, Phase 22 section added
design/fonts/                                Nunito Sans, IBM Plex Mono (SIL OFL)
design/source/22/README.md                   the spec
design/source/22/Multiroom Board.dc.html     the final board, every state
design/source/22/Phone Remote Multiroom.dc.html   phone remote + group
design/source/22/Multiroom Panel.dc.html     panel drawer and bar tray + group
design/source/22/multiroom-data.js           sample players and status words
design/source/22/Now Playing.dc.html         locked, unchanged copy
design/source/22/Settings.dc.html            locked, unchanged copy
design/source/22/eq/                         pictures of the locked Now Playing
design/source/22/png/                        one PNG per state
design/source/22/eq-data.js, support.js, *.webp, *.svg, *.png   runtime, samples
```

Unpack `design/` over the repo's `design/`.
