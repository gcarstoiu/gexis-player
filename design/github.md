repo: gcarstoiu/gexis-player
branch: main

## Last sync

- 2026-09-30: Settings unlocked by George for two rows (Attached screen, Screen rotation) and they are in `Settings.dc.html`; the Screen step is merged into `Setup.dc.html`; `data-contract.md` brought up to date.

date: 2026-09-30T10:40:00Z
commit: 403d582330

### Updated in this project

- **design/ export refreshed**: `source/` carries the current Now Playing,
  Setup and Panel Setup, plus `source/13b/` with the chosen 13b designs.
  The plain slice now matches the source for Home, shuffle/repeat, the
  volume glyph and the right-group gap. README, screens.md and settings.md
  gained a "Changed 2026-09-30" section. `verify.html` is still to run on a
  local server.
- **13b settled** (George): Settings stays a tile on bars; Attached screen
  and Rotation confirmed; copy accepted as drawn.

## Sync 2026-09-30T10:02:38Z

### Updated in this project

- **Phase 13b, turns 3–9** (`design/briefs/13b-screen-families.md`, Finding
  100, ADR-0019, ADR-0036, `05-peppy/files/letterbox.py`): the Bar family
  (`Bar Frame`, `Bar Library`, `Bar Panels`), the visualiser surround, the
  phone's Screen step (`Setup Screen Step.dc.html`) and the Screen / Rotation
  rows (`Settings Screen Row.dc.html`), all in `Screen Families.dc.html`.
  Chosen so far: 1b, 1d, 7 mm floor, 5s (4b pulled down), 5c rail on the
  right, 7b, 7e, 8b, 8f.

## Sync 2026-09-30T06:16:52Z

### Updated in this project

- **Phase 13b, turn 1** (`design/briefs/13b-screen-families.md`, Finding
  100): `Screen Families.dc.html` with three height rules for the Standard
  family, two large-screen type treatments and the touch-target table.
  Artboards come from `Family Frame.dc.html`; the locked files are unchanged.

## Sync 2026-09-30T05:50:00Z

Incremental from `bddc817007...403d582330` (phase-13).

### Updated in this project

- **Queue rail**: no X; swipe a row left past 96px to remove it, with
  *Remove* uncovered behind it, and a one-time hint on first open
  (`QueueRail.svelte`, ADR-0062). Row press is opacity 0.62, as the panel.
- **Panel Setup** rebuilt from `SetupScreen.svelte`: one step at a time at
  two-metre sizes (join, phone connected, open the page, carry on, joining,
  done with the Lyrion card, could not join, Ethernet, did not start,
  starting). Old two-card version kept as `Panel Setup (two cards,
  2026-09-29).dc.html`.
- **Setup (phone)** from `SetupPage.svelte`: blurred weave backdrop, the
  mobile-data card on Welcome, Music as three Lyrion choices that gate
  Continue, Review's Library line, and Change returning to Review.

## Previous sync

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

**Drawn 2026-09-29T14:55Z on George's confirmation:** the home screen with
LMS off (ADR-0079, `WaitingHome.svelte`, `WaitingServices.svelte` `full`):
the marks at 1.8× (180px rings, 162px discs, 68/74px marks, 310px columns,
60px gap) with the manifest's names and statuses (Spotify · Listening,
Bluetooth · Pairable), a 64px Settings button 26px from the top right, and
"No sources" when every renderer is off. Now Playing's home button becomes
the 22×16 sliders glyph and opens Settings (`NowPlaying.svelte` `rootless`);
the artist line is inert. Tweak: `lms` = on / off / all off. Queue rail
swipe-to-remove and its one-time hint are behaviour only.

### Not carried, and why

- Turntable and tape skin names are picked out of the meter corpus by name;
  the image build's animated skins are not in the repo.
- QR codes are placeholders and the setup password is a sample.
- Beszel's Token note refers to "the key below", a row not in the pictures.
- `design/now-playing.html` / `.css` and `design/settings.md` predate all
  of this: the export needs regenerating from the design and
  `design/verify.html` running.

## Sync history

date: 2026-09-20T21:20:00Z

### Updated in this project

- Designed the first-boot setup page (`Setup.dc.html`) against ADR-0031.
- Vendored the brand package into `brand/`; the committed Plymouth frames predate the lettered mark and must be re-rendered.

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
| Now Playing (`Now Playing.dc.html`, `design/now-playing.html`) | `ui/src/screens/QueueRail.svelte`, `ui/src/App.svelte`, `ui/src/lib/state.js`, `design/marks/bluetooth.svg` |
| Settings (`Settings.dc.html`) | `core/src/gexis_core/settings_registry.json` (phase-13), `ui/src/screens/Settings.svelte`, `ui/src/screens/MiniPlayer.svelte`, `core/src/gexis_core/notices.json` (Legal, Credits), `core/src/gexis_core/skins.py` + `skins/templates*/meters.txt` |
| Setup, phone (`Setup.dc.html`) | ADR-0031 as amended, ADR-0104, `ui/src/screens/SetupPage.svelte` (phase-13); Screen step from the 13b brief |
| Panel Setup (`Panel Setup.dc.html`) | `ui/src/screens/SetupScreen.svelte` (phase-13) |
| Phase 13b families (`Screen Families Chosen.dc.html`, `Screen Families.dc.html`, `Now Playing Height Study`, `Family Frame`, `Bar Frame`, `Bar Library`, `Bar Panels`, `Settings Screen Row`; exported to `design/source/13b/`) | `design/briefs/13b-screen-families.md`, `docs/findings/100-screens-what-the-pi-can-learn-and-what-exists.md`, ADR-0019, ADR-0036, `image/stage-gexis/05-peppy/files/letterbox.py`, `ui/src/screens/QueueRail.svelte`, `ui/src/screens/SetupScreen.svelte` |
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
