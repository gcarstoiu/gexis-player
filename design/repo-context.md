repo: gcarstoiu/gexis-player
branch: main

## Last sync

date: 2026-09-29T11:25:00Z

Source: all of `design/IMPLEMENTED-DIFFERENTLY.md` and the pictures in
`design/implemented/`, checked against the panel's own code where the
document is silent: `ui/src/screens/*.svelte` and
`core/src/gexis_core/settings_registry.json` on `phase-13` (PR #37), which
is `main` plus first-time setup. The panel is the point of truth where the
two differ.

### Updated in this project

- **Settings** is regenerated from the registry: every surfaced row, in its
  order, with its copy, options, units and conditions. Gone: `boot_volume`,
  `per_renderer_volume`, `handoff_threshold`, `weather_key`,
  `idle_minmax`, and the Ethernet / Wi-Fi connection pair (not on the
  panel). New: Output, Starting volume, the sweep rows, background brightness
  and interval, wallpaper topics (`multi`), Clock, Clock format, the three
  needle / spectrum tweaks, the animated-skin rows, confidence, and the
  Plugins and System categories with Legal and Credits readers. `skin_corpus`
  has its six words. A list row reads out its value (the connected network),
  not a count. A plugin's download line, 3px bar and amber Retry / Remove
  pills are the panel's own. The phone's mini player follows
  `MiniPlayer.svelte`, including the larger sheet it opens into.
- **Now Playing**: no pulse on either source badge (Finding 056); the
  transition screen appears at once and only fades out; the volume glyph is
  the drawer's 30px one on now playing and the mini strip, and fixed output
  shows the padlock in its place (ADR-0046); the mini strip shrinks to 0.995
  on press instead of lightening, and library cards shrink instead of
  dimming; the artist About block has no More/Less — the text is the toggle
  and a bottom fade shows only when it is cut. Also the gexis Bluetooth mark
  and the 12 h clock.
- **Setup (phone)** is rebuilt from `SetupPage.svelte`: the gexis mark as
  the image the panel uses (the header had been drawn with the brand
  component, whose colour tokens were not loaded — the misspainted icon),
  "Join your network" with no Ethernet / Wi-Fi cards, the cable case as
  `overLan`, pill buttons, the Continue button in the step's accent, and the
  panel's copy throughout.
- **Panel Setup** is rebuilt from `SetupScreen.svelte`: its crumb, copy,
  sizes, card accents and the four heroes plus the Ethernet card.

### Checked, not inferred (2026-09-29T11:40Z)

Byte comparison of every file in the repo's `design/` (phase-13) against
this project:

- **Replaced in the repo, now taken here:** `album-art.webp` (Kandinsky,
  *Several Circles*) and `artist-photo.webp` (Gottlieb, Three Deuces, 1947),
  both public domain, replacing two unsourced photographs of real people; and
  `icon-bluetooth.png`, now gexis's own square B1 mark. Copied to the root,
  `design/source/` and `design/assets/`, with `assets/SOURCES.md`,
  `marks/bluetooth.svg`, `IMPLEMENTED-DIFFERENTLY.md`, `BUNDLE-README.md`
  and `briefs/`. The interim `mark-bluetooth.svg` is deleted; Now Playing
  draws `icon-bluetooth.png` at the size asked for, as `SourceMark` does.
- **Identical:** icon-spotify, icon-lyrion, support.js, tokens.css,
  geometry.json, fonts, brand/, now-playing.html/.css/.js, verify.html.
- **The repo's design/source/ DCs** are our 2026-09-20 export: Now Playing
  byte-identical, Settings and Setup from before the Ethernet / Wi-Fi
  connection change, which the panel never took.

Every recorded decision in App, Library, QueueRail, IdleScreen, VolumeDrawer,
PairingFrame, WaitingHome and WaitingServices was then read and checked
against Now Playing. Carried in addition: home cards press to 0.975; the idle
credits line along the bottom ("Weather data by Open-Meteo.com", "Photos from
Pixabay", an artist picture by name; core/weather.py, wallpapers.py); and
`idleClock` off, where the time and date go and the panel is a picture
frame. Already matching: New Music at 0.60, Play / Shuffle on playlist and
artist pages, Play album + Add to queue, singular counts, no row press, no
station count on Radio, waiting marks 38/38/41 in 100px rings, no New
playlist.

**Found on the panel and not drawn:** the home screen with LMS off
(ADR-0079, `WaitingHome.svelte`: the waiting marks full-screen, a Settings
button top right, and "No sources" when every renderer is off), and with it
Now Playing's home button becoming Settings and the artist line no longer a
link. Queue rail swipe-to-remove and its one-time hint are behaviour only.

### Not carried, and why

- Turntable and tape skin names are picked out of the meter corpus by name;
  the image build's animated skins are not in the repo.
- QR codes are placeholders and the setup password is a sample.
- Beszel's Token note refers to "the key below", a row not in the pictures.
- `design/now-playing.html` / `.css` and `design/settings.md` predate all
  of this: the export needs regenerating from the design and
  `design/verify.html` running.

## Sync history

date: 2026-09-19T06:38:47Z

### Updated in this project

- Replaced the invented visualizer skin list with the real corpus: 71 section names from `skins/templates/meters.txt` and 13 from `skins/templates_spectrum/meters.txt`, verbatim.
- Confirmed against `core/src/gexis_core/settings_registry.json` that `skin` is a new key — the registry defines only `skin_corpus` and `skin_rotate`.
- Read `core/src/gexis_core/skins.py` for how the corpus is parsed and how meters link to spectrum sections by name.

date: 2026-09-18T20:41:29Z

### Updated in this project

- Brought the mockups in line with the shipped panel from George's implementation diff (Phase 9 sweep prep).
- Removed every `backdrop-filter: blur()` behind scrims and sheets (ADR-0041 / Finding 037: 24.5ms a frame against a 16.7ms budget).
- Screen swaps are no longer animated, and press feedback scales instead of filling.
- Added the licence attribution lines and made the artist About block More/Less.

## Screen map

| Project screen | Repo files |
|---|---|
| Now Playing (`Now Playing.dc.html`, `design/now-playing.html`) | `ui/src/App.svelte`, `ui/src/lib/state.js`, `design/marks/bluetooth.svg` |
| Settings (`Settings.dc.html`) | `core/src/gexis_core/settings_registry.json` (phase-13), `ui/src/screens/Settings.svelte`, `ui/src/screens/MiniPlayer.svelte`, `core/src/gexis_core/notices.json` (Legal, Credits), `core/src/gexis_core/skins.py` + `skins/templates*/meters.txt` |
| Setup, phone (`Setup.dc.html`) | ADR-0031 as amended, ADR-0104; branch `phase-13` (PR #37) |
| Panel Setup (`Panel Setup.dc.html`) | `ui/src/screens/SetupScreen.svelte` (phase-13) |
| Design tokens (`design/tokens.css`) | none yet — `App.svelte` carries its own throwaway styles |
| Data contract (`design/data-contract.md`) | `ui/src/lib/state.js`, `ui/vite.config.js` |
| Brand package (`brand/`) | none yet — the Plymouth boot frames in the image build predate the lettered mark |

## Open for the sweep

How the attribution line should look, how the two API-key rows present,
whether an unblurred sheet needs a darker scrim, and whether volume stays a
modal.

## Notes

- Access is read-only: this project cannot commit. `design/` is generated
  here and downloaded, then unpacked into the repo.
