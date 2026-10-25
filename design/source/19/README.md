# Phase 19: the Home Assistant card and the D-pad's focus

From `design/briefs/19-ha-card-and-dpad-focus.md` (2026-10-25), with
ADR-0160 and ADR-0161. Open `HA Card Board.dc.html` and `D-pad Focus.dc.html`
over HTTP from this folder (`cd design && python3 -m http.server 8080`).

**George's picks, 2026-10-25:** the card in the player's look (**1b**), the
**teal** focus ring (**2b**), and **Jump** (no glide).

New tokens are at the end of `../../tokens.css`, under *Phase 19*, extracted
from these files.

| File | What it is |
|---|---|
| `HA Card.dc.html` | The card. One component; every region below is marked `data-gexis-card="…"`. |
| `HA Card Board.dc.html` | Both looks, the sizes and forms, and the twelve states. |
| `Focus Ring.dc.html` | The focus ring. One element, given the focused control's box. |
| `D-pad Focus.dc.html` | The three rings on six backgrounds, the travel, and the ring over the locked screens. `#shot=F05` mounts one artboard by id. |
| `Now Playing`, `Settings`, `Lyrion Standard`, `Bar Frame` | The locked designs, unchanged copies, so the focus board runs here. |
| `png/` | One picture per state (below). |

---

## The card

### Regions (component boundaries)

| `data-gexis-card` | Holds | Shown |
|---|---|---|
| `root` | The card. `container-type: inline-size`: it lays itself out by its own width. | always |
| `switcher` | Player mark 36 px, name 16/500, chevron; state line 13 px with the source mark at 14 px in the source's colour. | always; the chevron and the menu only with more than one player |
| `switcher-menu` | *Gexis players* (12 px label), one row per player, 56 px: mark 28, name 15/500, state 13. The player shown has the fill and a check in `--gx-accent`. A tap outside closes it. | while open |
| `unreachable` | *Can't reach &lt;name&gt;* and *Home Assistant reconnects when the player is back on the network.* Takes the place of everything under the switcher; the mark drops to 0.45. | player unreachable |
| `now-playing` | `what-plays`, `position`, `transport`, `volume` or `volume-fixed`. | reachable |
| `what-plays` | Artwork `clamp(96px, 28cqi, 128px)`, radius 10; title 18/500, two lines; artist and album 14 px, one line each. | always |
| `position` | 4 px bar in the source's colour; times 12 px, tabular. | a track with a position (not Bluetooth) |
| `transport` | Shuffle 44, previous 48, play/pause 56 on `--gx-play`, next 48, repeat 44. | a track whose source has transport |
| `volume` | Mute 44, slider 40 px tall (radius 12), the level. Muted: *Muted*, fill at 0.35. | output not fixed |
| `volume-fixed` | Padlock and *Fixed output · the volume is set on the amplifier* (compact: *Fixed output · set on the amplifier*). | fixed output |
| `screen` | *On the player's screen*, `quick-actions`, `dpad`. | a player with a screen |
| `quick-actions` | Home, Now playing, Lyrics: three 58 px tiles. | with `screen` |
| `dpad` | Back (44 px pill) and the round pad `clamp(168px, 44cqi, 216px)`: Up, Down, Left, Right, OK (34 % in the middle). A press shows *Sent Up* under it for 1.2 s. | full form; compact on request |

### Forms

- **Full:** `now-playing` is `flex: 1 1 300px` and `screen` `flex: 1 1 260px`
  in one wrapping row, so below about 580 px the screen controls sit under
  what plays and above it beside it. No breakpoint is written; the wrap does
  it.
- **Compact:** artwork 56 px (radius 8), title 16, artist 14, previous / play
  / next inline (44 / 48 / 44), a 3 px position bar, volume 32 px tall
  (radius 10). Quick actions are 44 px squares, then a *D-pad* button with a
  chevron that opens a 160 px pad under them. No shuffle, repeat, album or
  times.

### States (the card's own rules)

- **Playing / paused:** the play control's shape alone (pause glyph while
  playing).
- **Nothing playing:** title *Nothing playing* in the second ink, no artist
  or album, a note glyph in the empty well, no position or transport; Now
  playing and Lyrics at 0.38 and inert (the route refuses them, ADR-0160 D3).
- **No screen:** no `screen` region (no quick actions, no D-pad).
- **Fixed output:** `volume-fixed` in place of `volume`.
- **Fewer controls:** shuffle and repeat only for Lyrion and Plexamp; Spotify
  and Bluetooth have previous / play / next; a source with no transport has
  no `transport` region. A control the source lacks is removed, never greyed.
- **Unreachable:** state line *Unavailable*, `unreachable` region.
- **Long titles:** title clamps at two lines, artist and album at one, all
  with an ellipsis.
- **No artwork, and Bluetooth always:** the well shows the source's mark at
  40 px in the source's colour.
- **One player:** no chevron, no menu.

### What Home Assistant gives it (ADR-0160 D3, ADR-0161 D7)

The `media_player` for what plays, its state and source, position, transport
as `supported_features` allows, volume and mute (absent when fixed); the
`button` entities for Home, Now playing and Lyrics; the `remote` entity for
the D-pad (`remote.send_command` with `up`, `down`, `left`, `right`, `ok`,
`back`). A player with no `remote` and no buttons is drawn as *no screen*.
Unavailable entities are *unreachable*.

The player's look draws the artwork blurred behind the card (11 px blur,
saturate 1.3, `--gexis-card-bleed` 0.55, under `--gexis-card-bleed-scrim`).
That is drawn by Home Assistant's browser, not on the Pi.

---

## The focus

### Region

`Focus Ring.dc.html` draws one element, `data-focus-ring="ring"`, in a top
layer (`--focus-z`), over the focused control's box: `x`, `y`, `w`, `h` and
its corner radius `r`, in page pixels. It never takes part in layout, so
nothing moves or resizes; it moves with `transform`, and it has no blur.

- **Outside** (buttons, tiles, covers, round controls): `--focus-out` beyond
  the box; radius `r + --focus-radius-add`; round stays round.
- **Inset** (rows, and anything under 12 px from a neighbour):
  `--focus-inset` inside the box, radius `r − --focus-inset-radius-sub`, at
  least 4 px.
- **Slider:** the ring takes the whole track, with an arrow at each end
  (`--focus-arrow-*`). While Left or Right changes the value, that arrow steps
  out `--focus-arrow-nudge` and the other dims to `--focus-arrow-dim`. Up and
  Down leave the slider.
- **Selection stays:** a selected row keeps its teal, a tab its underline, a
  toggle its state. The dark keylines keep the teal ring apart from teal
  under it.
- **Shows** at the first key press, on the control focused last on that
  screen or its main one (ADR-0161 D4); a touch hides it.
- **Travels by jumping:** drawn on the next control at once.

---

## Pictures, `png/`

**`card-states/`** at 2×, the card alone: `La` playing · Lyrion, `Lb` paused,
`Lc` nothing playing, `Ld` no screen, `Le` fixed output, `Lf` Spotify (no
shuffle or repeat), `Lg` Bluetooth with no transport, `Lh` unreachable, `Li`
long titles, `Lj` no artwork · Plexamp, `Lk` the switcher open with three
players, `Ll` one player.

**`card-sizes/`** at 2×: `Sa` phone 390 full, `Sb` phone compact, `Sc` compact
with the D-pad open, `Sd` column 300, `Se` column 500, `Sf` wall tablet 760
full, `Sg` wall tablet compact with the D-pad open.

**`focus/`** at 1×, at the screen's size: `2b-on-six-backgrounds`; `F01` Home
tile (Simple), `F02` Lyrion's menu tile (Extended), `F03` library row, `F04`
album in a grid, `F05` play/pause, `F06` the volume button, `F07` the Lyrics
tab, `F08` a Settings row, `F09` a toggle, `F10` a slider focused, `F11` the
slider while Right is held (60 → 72 %), `F12` a button in a sheet, `F13` the
volume drawer; on the 11.9″ bar (the 1850 × 400 page at 0.8, 1480 × 320)
`B01` the rail's play control, `B02` a tray button, `B03` a library tile; on
the 7.9″ bar (1280 × 400) `B04`–`B06` the same.

The screens under the ring are the locked designs as they render. Two things
in them are not about the ring:

- In the Settings pictures (`F08`–`F12`) two-word row titles wrap over their
  notes (*Output mode*, *Maximum volume*) and values break (*Variabl e*).
  `Settings.dc.html` opened on its own does the same. It is locked, so it is
  left as it is.
- `F11` shows the sheet without the dimmed backdrop `F10` has, because of the
  drag that sets 72 %.

The glide (not chosen) has no picture.
