# ADR-0171 — Themes

**Status:** **Proposed** 2026-11-01, Phase 25 (`ph-themes`). The five themes
are George's choice from Claude Design (2026-10-28); everything below is
Claude's proposal until George decides the points under *For George*.
Amends [ADR-0016](0016-plugins-as-separate-processes.md): themes are not
something plugins provide (decision 1).

## Context

**The design** (Claude Design's handover of 2026-10-29, unpacked over
`design/`): five themes - Bauhaus and Sage (light), Velvet, Ink and Gauge
(dark) - each a complete set of values for the names in `design/tokens.css`
(`design/themes/tokens-<id>.css`, 223 declarations). Today's theme stays and
is not one of them. *Production wins*: no layout, size, copy or behaviour
changes; a theme is a token set. Three additions: a token `--cover-veil` for
the cover's darkening behind Now Playing, today a literal; our Bluetooth mark
drawn in each theme's `--accent-bluetooth`; a mono font per theme (Space Mono,
Martian Mono, Red Hat Mono, JetBrains Mono, Chivo Mono, all SIL OFL 1.1), not
in the bundle. How themes ship and are chosen is left to this record.

**Production**, found on 2026-11-01:
- **Most colours do not come from the tokens.** `ui/src/styles/tokens.css`
  holds 109 of the design's 222 names; the components hold 2,031 colour
  literals beside it (hex, `rgb()`, `rgba()`, `hsl()`; the most in
  personalise's small panel, 303, the first-use pages, 258, Settings, 144,
  Library, 128, the bar's library, 97). A theme written as token values
  reaches only what reads the tokens.
- **Three cover veils, not one.** The design draws Now Playing's
  (`rgba(22,36,46,0.3)` to `rgba(14,23,30,0.86)`), which the bar's Now
  Playing and library and the phone remote share. Library and the equaliser
  use a stronger one (0.62 to 0.93), the keep screen, setup, first use and
  the equaliser a stronger still (0.72 to 0.96).
- **The design scales three monos; the token files do not.** `themes.js`
  sets the mono's sizes at Bauhaus 0.96, Sage 0.9 and Ink 0.95 of today's
  in every artboard; the handover's text names Sage's alone, and the token
  files carry no scale.
- **The fonts are on fontsource 5.3.0**, the version the UI takes Nunito Sans
  and IBM Plex Mono from. Space Mono has 400 and 700 only, as in the
  references; the UI asks for 300, 400, 600 and 700.
- **A theme row exists, hidden**: ADR-0022's inventory, `theme` in
  `settings_registry.json` under Display, `surfaced: false`, offering Deep
  Teal, Faded 80s and Graphite.
- **ADR-0016 lists themes among what plugins provide**, and a plugin is a
  process. A theme has none.
- **The first paint is today's ground**: `ui/index.html` sets `#101a21` and
  `color-scheme: dark` before any stylesheet, so that nothing flashes white
  between the boot animation and the UI (ADR-0043).

## Proposed (Claude)

1. **Themes are part of the UI, not plugins.** Six themes ship in the
   bundle; ADR-0016's list loses *themes*. A theme from elsewhere, if ever,
   is a later decision.
2. **One file per theme**, `ui/src/styles/themes/<id>.css`, a
   `:root[data-theme="<id>"]` block copied from
   `design/themes/tokens-<id>.css` with tokens.css's one change (fontsource's
   name for Nunito Sans). Choosing one sets `data-theme` on the page: no
   reload, no restart.
3. **Today's theme through the tokens first, with nothing changed on
   screen.** Every colour literal on a screen that follows the theme (4)
   becomes the design token whose value it is; a name the UI lacks is copied
   from `design/tokens.css`; a literal with no token is listed in this record
   with where it is, and given a token only once its theme values are
   settled. Checked by screenshots of the mocked screens - the panel at the
   page sizes the kiosk gives the 10" and 7" panels, the bar, the phone -
   taken before and after and compared pixel by pixel: identical.
4. **What follows the theme**: what the design draws (the panel's Now
   Playing, library, volume drawer, Settings and waiting screen; the bar's
   Now Playing and tray; the phone remote and its Settings) and the screens
   it does not draw that are built from the same tokens (the equaliser,
   groups, search, Lyrion's levels, the keep screen, setup, first use,
   personalise's small panel). **Not themed**:
   the visualiser (Phase 25's criterion 4), the boot animation, the weather
   icons, the test pattern, and the Home Assistant card, which has its own
   tokens in its own repository.
5. **The veils as tokens**: `--cover-veil` as drawn, and the two stronger
   ones as `--cover-veil-strong` and `--cover-veil-deep`, today's values in
   today's theme. In a theme each is drawn in its `--bg-base`, at the larger
   of today's alphas and the theme's.
6. **The mono's size as the artboards have it**: a token `--mono-scale`
   (Bauhaus 0.96, Sage 0.9, Ink 0.95, the rest 1), applied where a mono size
   is set. The artboards are what George chose from.
7. **The fonts from fontsource 5.3.0**, the weights the references load,
   bundled. Each face is declared once; the browser loads only the face in
   use; nothing is fetched from outside the player.
8. **Our Bluetooth mark drawn**, from `design/marks/bluetooth.svg`, its
   stroke `var(--accent-bluetooth)`. The other marks stay as they are.
9. **Chosen in Settings → Display** (the existing row), default today's
   theme, applied at once; kept by the core with the player's settings and
   sent with its state, so the panel, the bar and the phone remotes of that
   player show it. The first paint stays today's ground (the boot animation
   is not themed); a light theme takes over when the UI starts.
10. **Nothing automatic at night.** A light theme stays light; standby
    (ADR-0135) and the brightness setting are unchanged.
11. **The design folder stays `design/source/28`**, as exported: its files
    name each other by that path. `design/README.md` says 28 is Phase 25.

## Decided (George)

- **Decision 1, built in** (2026-11-01): the six themes are part of the
  player, as (1) proposes; no theme plugins in this phase.
- **Decision 2, per player** (2026-11-01): each player has its own theme,
  and its screen and every phone remote on it show that one, as (9)
  proposes; a change anywhere shows everywhere for that player.

## For George

To be asked one at a time:
- **Today's theme's name**, Deep Teal in the inventory, and the row's options
  (ADR-0022, appended only once confirmed).

## Settings (ADR-0022)

`theme`: today's row, surfaced, its options today's theme and the five; the
row's text to be confirmed by George before it is appended.

## Measured before it is called done

- Today's theme pixel-identical before and after the token pass (3).
- Each theme on every drawn screen from mocked data, compared with its
  artboard in `Theme Spec.dc.html`.
- Every text token at its contrast floor on each theme's grounds and over a
  white and a black cover under the veil, re-measured from the built UI (the
  handover's check, *re-check after implementing*).
- A theme changed on the panel shows on the bar and a phone remote of the
  same player without a reload.
