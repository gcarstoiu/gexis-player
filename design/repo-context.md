repo: gcarstoiu/gexis-player
branch: main

## Last sync

date: 2026-09-19T06:38:47Z

### Updated in this project

- Replaced the invented visualizer skin list with the real corpus: 71 section names from `skins/templates/meters.txt` and 13 from `skins/templates_spectrum/meters.txt`, verbatim.
- Confirmed against `core/src/gexis_core/settings_registry.json` that `skin` is a new key — the registry defines only `skin_corpus` and `skin_rotate`.
- Read `core/src/gexis_core/skins.py` for how the corpus is parsed and how meters link to spectrum sections by name.

## Sync history

date: 2026-09-18T20:41:29Z

### Updated in this project

- Brought the mockups in line with the shipped panel from George's implementation diff (Phase 9 sweep prep).
- Removed every `backdrop-filter: blur()` behind scrims and sheets (ADR-0041 / Finding 037: 24.5ms a frame against a 16.7ms budget).
- Screen swaps are no longer animated, and press feedback scales instead of filling.
- Added the licence attribution lines and made the artist About block More/Less.

## Screen map

| Project screen | Repo files |
|---|---|
| Now Playing (`Now Playing.dc.html`, `design/now-playing.html`) | `ui/src/App.svelte` (replaced wholesale in 4c), `ui/src/lib/state.js` |
| Settings (`Settings.dc.html`) | `core/src/gexis_core/settings_registry.json` (row inventory), `core/src/gexis_core/skins.py` + `skins/templates*/meters.txt` (skin corpus) |
| Design tokens (`design/tokens.css`) | none yet — `App.svelte` carries its own throwaway styles |
| Data contract (`design/data-contract.md`) | `ui/src/lib/state.js`, `ui/vite.config.js` |

## Open for the sweep

Four items from the diff still want designing rather than porting: how the
attribution line should look, how the two API-key rows (`listenbrainz_token`,
`fanart_key`) present, whether an unblurred sheet needs a darker scrim, and
whether volume stays a modal.

## Notes

- Access is read-only: this project cannot commit. `design/` is generated
  here and downloaded, then unpacked into the repo.
- `ui/src/App.svelte` is a deliberate Phase 4b skeleton that says in its own
  comment it gets replaced in 4c. The export is that replacement.
