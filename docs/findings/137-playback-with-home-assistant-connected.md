# Finding 137 — Playback with Home Assistant connected and commanding

**Date:** 2026-10-24. **For:** Phase 19's criterion 3 (ADR-0160): nothing the
integration does disturbs playback, measured as Finding 109 measured the
Lyrion server.

## Scope

- **Device:** sofapi, Raspberry Pi 4, the Phase 19 preview (core and player
  1.4.0+git49.c4af394), music through its own Lyrion client (squeezelite)
  from George's Lyrion server, repeat on, volume 60 %.
- **Home Assistant:** 2026.10.3 in Docker on the build computer, bridge
  network, no discovery; the integration 0.1.0, sofapi added by address, its
  `/state` WebSocket open throughout.
- **Commands from Home Assistant**, one every 40-80 s, in turn: volume down
  1 % and back, pause 3 s and play, next track, screen off 10 s and on, the
  visualiser up 30 s, nothing - 54 steps, 20:02-20:48.
- **Gaps counted by the client itself**, as in Finding 109: squeezelite's
  output logging turned up for the test (`-d output=info`, a runtime drop-in,
  removed after), shown working by its "track start" line for every track.
- **Sampled with each step:** load average, temperature, throttling.
- **Not measured:** what was heard; a player on Wi-Fi under other load; more
  than one Home Assistant connected.

## Result

| | 46 min, 16 tracks |
|---|---|
| Underruns | **0** |
| XRUNs | **0** |
| Playing after each step | 54 of 54 |
| The player unavailable in Home Assistant | never |
| Load average | mean 2.25, highest 3.58 |
| Temperature | 64.2-68.1 °C, no throttling |

Nothing the integration did reached the output. Criterion 3 holds for this
scope.
