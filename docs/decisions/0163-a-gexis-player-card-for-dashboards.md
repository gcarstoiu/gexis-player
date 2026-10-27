# ADR-0163 — A Gexis Player card for Home Assistant dashboards

**Status:** **Accepted** — 2026-10-25, Claude, the decisions delegated by
George (he asked for the card to be built from his design with the choices
around it left to Claude, and shown to him to verify). **Built** the same day
and released in the integration's 0.3.0 (George asked for the release, to
check it). Phase 19
(`ph-home-assistant`), criterion 7. Builds on
[ADR-0160](0160-the-player-in-home-assistant.md) (the integration) and
[ADR-0161](0161-a-d-pad-on-the-panel.md) (the D-pad, its `remote` entity).
The design: `design/source/19/` (`HA Card.dc.html`, `HA Card Board.dc.html`,
its README), George's pick the player's look (1b).

## Context

- George, 2026-10-25, after trying the integration: from a dashboard, move
  between the players, and have the quick actions and a D-pad there. Home
  Assistant's own media card shows one entity and nothing of the screen.
- The design gives one component with marked regions (`data-gexis-card`), a
  full and a compact form laid out by the card's own width
  (`container-type: inline-size`), twelve states, and a token chain that
  falls back to Home Assistant's theme.

## Decisions

**D1 — Shipped inside the integration.** The card is a file of the
integration (`custom_components/gexis/frontend/gexis-player-card.js`); the
integration serves it and adds it to Home Assistant's frontend when it loads
(`add_extra_js_url`), so it is in the card picker as *Gexis Player* with
nothing else to install or register. *Rejected:* a second HACS repository of
the *Dashboard* type - a second install, and a card that can be out of step
with the integration it reads.

**D2 — A plain web component, one file.** No build step and no dependency:
the design's markup and styles in a shadow root, its tokens as written in
`design/tokens.css` (*Phase 19: the Home Assistant card*). The player's look
by default; `look: home-assistant` drops the card's own block and follows the
theme (the design's 1a), as the token chain allows.

**D3 — Its options.** `entity` (a Gexis media player; without it, the first
by name), `form` (`full` or `compact`, default `full`) and `look`. Set in the
card editor (Home Assistant's own form) or in YAML.

**D4 — Which players, and their controls.** The players are the integration's
media players. A player's buttons (Home, Now playing, Lyrics) and its
`remote` are found through its device. The switcher lists every player with
its state line, as the phone's switcher does (*Playing · Spotify*); the one
chosen stays until the page reloads.

**D5 — Everything through Home Assistant's own services**:
`media_player.*` for transport, volume and mute, `button.press` for the
quick actions, `remote.send_command` for the D-pad. The card never calls a
player itself.

**D6 — What a player lacks is left out** (the design's rule: removed, never
greyed): no `remote` and no buttons is *no screen*; buttons without a
`remote` (a player not yet updated) shows the quick actions without the
D-pad; no volume support is *Fixed output*; Now playing and Lyrics are inert
while their buttons are unavailable.

## Decisions taken while building (Claude, delegated by George, 2026-10-25)

1. **The fonts ship beside the card** (`frontend/fonts/`, Nunito Sans and IBM
   Plex Mono with their SIL Open Font Licence texts) and are added to the
   page once, in the player's look only: a shadow root cannot declare a font.
2. **`after_dependencies`, not `dependencies`**, for `frontend` and `http`:
   Home Assistant sets both up first anyway; without a web server nothing is
   registered.
3. **The switcher's order**: the card's own player first, then the others by
   name, fixed while switching (the design's).
4. **Each control by what the player supports**: shuffle and repeat each on
   their own; repeat cycles off, all, one, with the design's repeat-once
   mark.
5. **A failed call** shows Home Assistant's own notification.
6. **Real buttons**; the volume bar is a slider a keyboard moves (Left,
   Right, 5 %); Escape closes the switcher.
7. **The source's mark by its name** (Lyrion, Spotify, Bluetooth, Plexamp);
   another source shows its name with no mark.
8. **Bluetooth** shows its mark for the artwork and no position, as drawn.
9. **A `remote` that is unavailable** hides the D-pad, as no remote does.
10. **The album line is the album only**: Home Assistant carries no year,
    which the design's sample shows.

## Changed after George's check (2026-10-25, integration 0.4.0)

After trying the card on his Home Assistant, George asked for the player's
rule on the transport and for the idle screen and the meters:

11. **The transport is the source's** (amends D6): a control the source has
    is shown, and greyed while it cannot be used now, as on the player
    (ADR-0037 §3). The media player's features are the active source's
    `capabilities` controls; `available_controls` says which work now.
12. **The phone's Panel views**: Meters, Room (the dashboard) and Idle join
    Home, Now playing and Lyrics, each left out where the phone leaves it
    out - Meters without meters on the output, Room until the dashboard's
    address is set, Idle while the idle screen is switched off. They are the
    integration's switches (a new *Idle screen* one, through
    `/panel/idle/{action}`); one that is up has the accent's outline.
13. **Whether the idle screen is on** reaches Home Assistant as
    `idle_screen` on `/player/status`; a player without the field offers it.
14. **The editor says the defaults** (Full, the player's look) under *Form*
    and *Look*, and a new card is made with them.

## Following the phone remote (2026-10-27, integration 0.5.0)

George, 2026-10-27, through the session working on his dashboards: the full
form in the player's look should look like the phone's remote
([ADR-0164](0164-the-phone-remote.md), item 11) without its Remote /
Settings switch, centred at a sensible width; a defect, the card defined
before the Home Assistant app's scoped element registry is in place, so the
app shows *Custom element doesn't exist*; and the card's address to change
with every version, so phones fetch it again. Asked, he decided:

15. **The touch area is the D-pad alone**: Home Assistant sends the D-pad's
    keys and cannot move a pointer, so no Trackpad and no pad switch. Its
    corners are the remote's: Home, Lyrics, Back, Meters.
16. **The equaliser in Home Assistant**: a switch (on or off) and a select
    (the setting: the presets and the owner's), per player, for the output
    in use; the card's EQ button opens a sheet with both.
17. **Built now**, after 1.7.0, for the integration's next release; George
    sees it before it is released.

Claude's decisions, for George's confirmation:

- **C1 — The full form is the remote's layout** in both looks (the player's
  colours, or Home Assistant's theme); the compact form stays as it is.
- **C2 — Centred, at most 440 px wide**, and narrower in a narrow column.
- **C3 — Without a screen**: the remote's large cover, a bar that seeks where
  the source does (the media player gains seeking, through
  `POST /transport/seek`), the larger transport.
- **C4 — Fixed volume is the panel's locked row**, with mute where
  ADR-0165 offers it: the media player reads `fixed_mute`.
- **C5 — What the screen shows is known only through the switches**: Meters,
  Room, the idle screen and Standby light up; Home, Lyrics and Playing do
  not. No *Sent* line under the D-pad: the screen is the feedback, as on
  the phone.
- **C6 — The EQ sheet has its switch and settings only**: no headroom note
  and no *Edit bands*, which are the player's; it closes by its handle or a
  tap above it.
- **C7 — The card defines itself once the scoped registry is in place**,
  defining again a few times after, as the request described; the version
  in its address is the integration's, raised with every release.

**Released in 0.5.0** the same day at George's word, after he saw it from
mocked entities. **Built** 2026-10-27 on the integration's `card-remote`: `switch.<player>_equaliser` and `select.<player>_equaliser_setting`
(`presets` and `own` as attributes; *Custom* shown, never chosen), the media
player's seeking and Fixed mute, the card's full form; integration tests 48
passed, its checks green. Checked from mocked entities at 340, 480 and 900
wide in both looks - every state above, the sheet, the menu - and each
press's service call; in the throwaway Home Assistant against sofapi, the
new entities and, in its own frontend, the card defined 86 ms after the page
(the registry polyfill at 52 ms), once in the picker. Not tried: the Home
Assistant app, where the defect was seen.

## Settings (ADR-0022)

None: the card's options live in the dashboard, not on the player.

## To check before it is called done

- Every state of the design, from mocked entities, against its picture.
- In a Home Assistant in Docker: the card in the picker, its editor, and each
  control reaching the player.
- The phone, a dashboard column and a wall tablet.
