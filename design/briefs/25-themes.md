# Brief for Claude Design — Themes (Phase 25)

Written 2026-10-28 for George to hand to Claude Design, to draw several
themes from. Background, if you want it: `docs/DEVELOPMENT.md`, Phase 25
(`ph-themes`); how a theme ships and is chosen is decided in its ADR, after
these designs.

---

**Gexis Player** is a music player for the Raspberry Pi 4. It has its own
touchscreen (the *panel*: 7" to 13.3", most often a 10.1" 1280 x 800), or a
wide *bar* (1480 x 320 or 1280 x 400), and every player has a phone remote.
All three are one web app, built from your designs: one set of colours today,
dark, in `design/tokens.css`.

## What a theme is here

**A theme is a complete set of values for the named tokens in
`design/tokens.css`** (112 today), applied at once to the panel, the bars and
the phone. Nothing else: a theme changes how the existing screens look, not
what is on them or where.

## What a theme can change

- **Every colour the screens take from a token**: the grounds (`--bg-*`, the
  diagonal weave behind everything), the text levels (`--ink`, `--ink-strong`
  ... `--ink-quiet`, the hairlines and resting fills), the accents
  (`--accent-lms`, which is also "active / yes", Spotify, Bluetooth, the
  artist line, warn, OK, not connected, Display), the play button
  (`--play-fill`), the D-pad's focus ring (`--focus-*`), the phone remote's
  and the group's own tokens (`--remote-*`, `--group-*`).
- **The two fonts** (`--font-ui`, `--font-mono`), if openly licensed (OFL or
  similar) and shipped inside the player - it never fetches a font. Today:
  Nunito Sans (variable) and IBM Plex Mono.
- **The type scale** (`--t-*`, `--track-*`), **corner roundness** (`--r-*`),
  **control sizes** (`--ctl*`), within the floors below.
- **Motion** (`--ease`, `--dur*`): how quickly things move, not what moves.

## What it cannot change

- **Layout and structure**: where things sit, which controls a screen has,
  the screens themselves. Each family (panel, bar, phone) has its own layout
  in code; a theme that moves something is a redesign, not a theme.
- **Other people's marks**: the Spotify icon (Spotify's own), the Lyrion
  logo, Plexamp's mark and colour (from its plugin), AirPlay's colour (from
  its plugin). Our Bluetooth and AirPlay marks are pictures drawn in a fixed
  colour today: a theme that wants them in other colours says so, and they
  become drawn marks.
- **Content**: covers, artist photos, wallpapers, and the idle screen's
  pictures.
- **What other software draws**: Lyrion's own menus' content and icons, a
  Home Assistant dashboard shown on the panel (it follows Home Assistant's
  theme), the API explorer.
- **Separate pieces**, which a theme may be paired with but not restyle
  through tokens: the visualiser's skins (bitmap meters and spectra, drawn by
  their own engine), the boot splash (an image shown before the app starts),
  the weather icon sets.

## Technical limits

- **A Raspberry Pi 4 draws it.** Animate only position and opacity - never
  layout, filters or blur - and only one region at a time. The blurred cover
  behind Now Playing is drawn once and stays still; a moving blur or
  gradient costs the visualiser its frames (the idle screen measured 45-58 %
  CPU with its animations running, against 4-6 % with them paused).
- **Readability**: text 15 px and under needs a contrast of 4.5 : 1 on the
  ground it sits on, larger text 3 : 1 - for every text token on every ground
  it is used on, the cover's blur included. On the panel nothing under 24 px
  is content (it is read from arm's length); the small mono labels are
  chrome.
- **Touch**: nothing smaller than 44 px; the round controls are 60, 68 and
  92 px today.
- **Colours must stay apart**: each source's accent from the others and from
  warn / OK / not connected; the focus ring from every ground and accent; the
  play button is one fixed colour, never the source's.
- **The cover is the ground on Now Playing**: blurred and darkened behind the
  text. How much it is darkened is a value in the code today; a theme that
  wants another names it (it becomes a token), and holds its contrast over a
  white cover and a black one.

## A light theme

Possible, and the largest of them: every text level today is light ink with
transparency on dark, the blurred cover is darkened, and the visualiser's
skins are dark. A light theme is the tokens' values turned round, checked on
every screen, with its own darkening of the cover (or none) - please treat it
as its own piece of work, not a swap of values.

## Please send, for each theme

- **Its name** and one line on its character.
- **A complete `tokens.css`**: every token, same names; a new token only
  where a value no token carries is needed, named and explained.
- **Artboards with the demo library** (public-domain music only, never a
  real library), at the real sizes: the panel's Now Playing (with a bright
  and a dark cover) and its library home, the volume drawer, Settings, the
  waiting screen; the bar's Now Playing and its tray; the phone remote and
  its Settings.
- **Its contrast figures**: each text token on each ground it is used on.

## Not for this round

How themes ship (built in, or a file a user adds), how one is chosen in
Settings, and how many there are: decided in Phase 25's ADR once the designs
are in.
