# Handoff: gexis first-use setup (part 1 + part 2)

## Overview
The phone-browser setup flow for a gexis player (Raspberry Pi + DAC + Waveshare 10.1″ panel).

- **Part 1 – get it working.** Runs on the player's own Wi-Fi hotspot. Network, new-or-backup, name, clock, output, screen, review, then the player joins the home network.
- **Part 2 – make it yours.** Runs from the home Wi-Fi at `http://<name>.local:8090`. How you listen (Lyrion / Plexamp / Spotify / Bluetooth), Lyrion location and folders, browse mode, Plexamp download + claim, Spotify, Bluetooth pairing, visualiser, waiting screen, idle screen, standby, review, then "Getting ready".

A live preview of the panel ("<name>'s screen") follows every choice.

## About the design files
The files here are **design references built in HTML**: a clickable prototype of the intended look and behaviour, not production code. Rebuild them in the target codebase (the gexis web UI) using its own framework, components and patterns. Open `Setup Prototype.dc.html` in a browser to click through. The left rail switches flow A/B, starts at part 1 or 2, phone or wide layout, and "Simulate" buttons fake device events (phone asks to pair, download finishes, claim code expires, install finishes).

`*.dc.html` files use a small template runtime (`support.js`). Markup is inline-styled HTML with `{{ }}` holes. The logic is the `class Component` at the bottom of each file, and **`renderScreen()`'s `switch (s.screen)` is the source of truth for every screen's copy and blocks.**

## Fidelity
**High fidelity.** Final colours, type, spacing, copy and interactions. Match them, mapping onto the existing gexis tokens where they already exist (`design/tokens.css` in the main handoff).

## Layout
- Page background `#0c1014`, text `#e9eef2`, font **Nunito Sans** (300–800), mono **IBM Plex Mono** (400/600/700) for labels.
- **Phone layout:** single column, max-width ≈ 420 px. Inside the column: crumb (mono 12 px, 0.2em tracking, uppercase, colour by section), title 30 px/800, sub 16 px at 72% ink, then the panel preview (where the screen has one), then the blocks stacked with a 14 px gap. The footer is fixed at the bottom: Back (ghost), optional alt (Skip / Do it later / Decline), primary Next (pill, section accent fill, ink `#0d151c`).
- **Wide layout (≥ tablet):** preview moves to a left column with a "<name>'s screen" label. Form on the right.
- Hero screens (Welcome, Joining, Getting ready, Kept the defaults) hide Back and use the party / success art.

## Screens (ids from the prototype, codes shown in the rail)
### Part 1
| id | code | Title | Notes |
|---|---|---|---|
| p1welcome | 1.0 | Set up gexis | Info note "About a minute", warn note "Keep mobile data off" |
| p1net | 1.1 | Join your network | Network list with signal bars, password field for secured nets, "Scan again" |
| p1start | 1.2 | New player or backup? | Radio list |
| p1backup | 1.2b | Upload a backup | File pick → uploaded row tagged Ready |
| p1name | 1.3 | Name the player | Field + "Becomes" summary (address slug, speaker-list name) |
| p1clock | 1.4 | Set the clock | Read from phone, "Choose by hand", 24 h / 12 h segmented |
| p1output | 1.5 | Choose the output | HiFiBerry DAC+ HD (Recommended), Headphones, HDMI 0/1 |
| p1screen | 1.6 | Is this your screen? | Waveshare 10.1″ (Tested) / Another / Headless. Headless removes the screen steps from part 2 |
| p1review | 1.7 | Check it over | Summary rows, tap to edit, then return |
| p1join | 1.8 | <name> is joining <net> | Address card, spinner, auto-advances to part 2 after 4 s in the prototype |
| p1restore / p1restored | 1.7b / 1.8b | Restore path | |

### Part 2 (order is computed by `p2Path()`)
`listen → [mix] → [lyrion → folders] → [browse] → [plexamp → plexsign] → [spotify] → [bluetooth] → [visualiser → wait? → idle → standby] → review → done`

- **listen (5A0) – How will you listen?** No preselection, so Next stays disabled until a pick is made. Options: My music + streaming (Lyrion, Spotify, Bluetooth), Plex + streaming, Streaming only, then a separate "Or mix your own" group with My own mix. Each option shows its source icons. Lyrion discovery has already finished when the page loads. If found, the tile footer reads "Lyrion found on <net> · 192.0.2.10:9000"; if not, "No Lyrion found on <net> · Set it up on the next screen". Wide layout preview: an animation where the panel and two speakers sit on top, with one source at a time below cycling Lyrion → Plexamp → Spotify → Bluetooth (12 s loop, 3 s each) and notes rising at irregular intervals into the panel.
- **mix (4A1m)** Toggles: Lyrion, Plexamp, a "Library service" ghost row (Next phase), Spotify, Bluetooth.
- **lyrion (5A2) – Where should Lyrion run?** Only shown when none was found. The "No Lyrion found" status carries "Add its address" inline, which expands to an address field. Then This player / Another machine, with a "who does what" split.
- **folders (5A3) – Where is your music?** Music folder / USB / Network share. Network share runs discovery (spinner 1.8 s), then a server list, then sign-in or a share list, then Add, with "Add by address" as a fallback.
- **browse (5A4) – Browse on the screen.** Extended / Simple / Off with a sketch preview.
- **plexamp (X1).** The intro explains the two steps (download, then sign in with a claim code). Skip or Download. Download moves straight to plexsign.
- **plexsign (X2) – Sign in to Plex.** One stable screen: progress bar, "Open plex.tv/claim" button, info note, claim field (read-only until the install finishes), skip text. States: downloading, code, expired (warn note), ok (success status and a hint to pick the player in the Plexamp phone app). Nothing on the page moves around between states.
- **spotify (5A5).** Toggle plus a mock of the Spotify device list ("Phone", the player highlighted).
- **bluetooth (5A6).** Always discoverable while enabled. Waiting state is a spinner with "Waiting for a phone". On a pair request a large 6-digit code appears with Decline / Accept. Paired phones are listed with a forget action.
- **visualiser (5A7) – While music plays.** Toggle, "Starts after" 2/10/30 min, skin grid (VU, Spectrum, VU+spectrum, Turntables, Tapes, All), an animate toggle and rpm for turntables and tapes. With the visualiser off, the preview shows the chosen browse mode.
- **wait (5A8w) – While it waits.** Only when there's no Lyrion browse (no Lyrion, or browse Off). The preview mirrors the real waiting home: wallpaper, clock/date/player top left, settings button top right, "Start music from your phone" with one tile per **selected** source (Lyrion highlighted, "Starts on play"; others "Listening" / "Pairable"). Options: Clock toggle; Background Gexis wallpapers / Black.
- **idle (5A8) – When nothing plays.** Idle toggle, Background (Gexis wallpapers / Artist pictures / Black). Wallpaper styles are multi-select checkbox pills (Calm / Colourful / Psychedelic) and at least one must stay on; the preview switches to the style just enabled, or the next enabled one. Clock and Weather toggles, **Weather off by default**. When it's on, the location field becomes required (placeholder "e.g. Lisbon, Portugal").
- **standby (5A9) – Off at night?** Toggle plus a list of intervals (from/until with a time picker, and a day chip row). Removing the last interval turns the toggle off.
- **review (5A10) – Your setup.** Hub rows that open each step and come back. Order: Music, Folders, Browse, Plex, Spotify, Bluetooth, Visualiser, While it waits, When idle, Standby.
- **done – <name> is ready.** Success art (speakers, panel, ✓ badge, pulsing notes). Then **one section per installed thing**, each made of a heading, a card (progress bar with an inline small ✓ status underneath once done) and an info note:
  - Lyrion: "Folders added, scan started", with the note "A large library can take hours to scan…"
  - Plexamp: "Signed in to Plex" or "Not signed in yet"
  - Visualiser: "Skins ready", with "starts after N min"

  Then a divider, then the ok note "Everything you set up here can be run again or changed in Settings → System → Personalise." The footer has Close.
- **later – Kept the defaults.** Reached from "Do it later" on listen.

## Interactions
- Back walks `path()`. When a step was opened from a review list, Back/Next return to that review (`ret`). Editing Music from review walks the dependent steps (mix/lyrion/folders/browse/plexamp/plexsign).
- Skip marks a step "Skipped" in review.
- Pills: single-select are round pills with an accent fill. Multi-select have 10 px radius, a checkbox square and an accent outline, plus "· pick any" after the heading.
- Animations (CSS keyframes in each file's `<helmet>`): `fuSpin` spinner, `fuBar` bars, `fuRing`/`npRing` pulsing rings, `fuCycle` source rotation, `pmRiseA/B` notes, `pmPump` woofers, `fuNeedleA/B` VU needles.

## State
All state is listed in `init()` in `Setup Prototype.dc.html`. The derived flags are in `d(s)`: lyr, plex, spo, bt, headless, `wait` (show the waiting screen step), `here` (Lyrion installs on this player) and `marks` (the selected sources, in order).

## Design tokens
Section accents (`C`): music `#b0bcc4`, lyr `#9fb4e8`, fold `#f2a48f`, browse `#8fd9a8`, spo `#7ed6bc`, bt `#d8c88f`, scr `#c8a2d8`, idle `#e8a0b4`, stby `#8fc4d8`, plex `#e0a758`, rev / ok `#7ed6bc`. Part 1 accents (`P1C`): Network `#8fc4d8`, Start `#b0bcc4`, Name `#e8a0b4`, Time `#c8a2d8`, Output `#7ed6bc`, Screen `#8fd9a8`, Review `#f2a48f`.
Note tones: info bar `#8fc4d8`, ok bar `#7ed6bc`, warn `#e0a758` on `rgba(224,167,88,0.08)`.
Surfaces: card `rgba(255,255,255,0.05)` with a 1 px `rgba(233,238,242,0.1)` border. Radii are 14–16 px for cards, 999 px for pills and buttons, 10 px for multi-select chips.

## Assets
`gexis-mark.svg`, `icon-lyrion.svg`, `icon-spotify.png`, `icon-bluetooth.png`, `artist-photo.webp`, `wallpapers/calm/c148381086.webp`, and `art/pd-kandinsky7.jpg` / `art/pd-starry.jpg` (public-domain stand-ins for the Colourful / Psychedelic wallpaper styles). **There's no Plexamp icon yet**, so a "P" placeholder is used.

## Files
- `Setup Prototype.dc.html` – the whole flow (screens, logic, state).
- `Panel Mini.dc.html` – the panel preview in every `kind` (lib, simple, now, wait, clock, off, flow, setup, viz, vu, vs, turn, tape…).
- `Phone Device List.dc.html` – the Spotify device-list mock.
- `support.js` – the runtime that opens the prototypes in a browser.

## Open points
- `Now Playing.dc.html` (locked) still has the older waiting screen. The setup preview follows the newer layout from `First Use.dc.html`.
- Plexamp status copy and the Settings path for Plex sign-in are placeholders.
