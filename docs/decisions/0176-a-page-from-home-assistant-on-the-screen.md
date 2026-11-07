# ADR-0176 — A page from Home Assistant on the screen

**Status:** **Accepted** 2026-11-07 (George), Phase 35 (`ph-ha-page`).
Decisions 1-7 are George's; *How* is Claude's proposal, accepted as a whole
the same day, with P1's longest limit, P4, P5 and P8 chosen by George.
**Builds on:** [ADR-0156](0156-home-assistant-dashboard-on-the-screen.md)
(the dashboard, framed in the panel), [ADR-0160](0160-the-player-in-home-assistant.md)
(the integration), [ADR-0135](0135-display-standby.md) (standby),
[ADR-0161](0161-a-d-pad-on-the-panel.md) (the D-pad) and
[Finding 142](../findings/142-a-live-camera-page-on-the-panel-while-music-plays.md)
(what live cameras cost).

## Context

**What was asked** (George, 2026-11-07, from the Home Assistant side): Home
Assistant puts a page of its own on a player's screen for a while - live
cameras when the doorbell rings, for example - and takes it down again,
without touching the dashboard the owner set. Today the dashboard is the only
way (ADR-0156): one address in Settings, so such a page would replace it.

**What exists** (`docs/DEVELOPMENT.md`, Phase 35):
- The dashboard has most of the parts: a page framed in the panel's own page
  (`DashboardScreen.svelte`), the check that the site allows framing
  (`idle_page.probe`), Home Assistant's sign-in kept in the kiosk's profile,
  Back on a remote taking it down (`/panel/key`), the standby API.
- A plugin cannot do it: plugins add no API routes and no `/state` fields
  and draw nothing on the panel (`docs/PLUGIN-CONTRACT.md`).
- The visualiser is a window of its own over the kiosk (`peppy.py`), raised
  and minimised by the core; the dashboard minimises it and nothing raises
  it again.

**What it costs** (Finding 142, one run): seven cameras over music at
44.1 kHz on the plain path - no underrun at the DAC but half its margin,
about 1.6 cores more, 74 °C after 5 minutes and still rising; H.264 decoded
in software, as the Pi 4's Chromium lists no hardware profiles; 3-15 % of
frames dropped and two streams nearly stopped. 192 kHz, the equaliser's or
room correction's stage, fewer cameras and longer runs were not measured.

## Decisions (George, 2026-11-07)

1. **In the player, not a plugin.** A plugin would only pass the calls on to
   what the player has to build anyway.
2. **Over everything, and back to it after.** Over the music's screens, the
   idle screen, the dashboard and the visualiser, the music playing on.
   Taking it down returns to what was there. A screen in standby wakes for it
   and goes back to standby after.
3. **Any touch closes it**, through a layer over the page as on the idle
   screen; and so does Back on any remote. Home Assistant sees it gone.
4. **A time limit**: given in the call, else 10 minutes.
5. **A switch for each player, off by default** (*Settings → Display*). Home
   Assistant reads it and offers the screen only where it is on.
6. **The integration gets show and hide actions** and the page shown as
   state. This changes ADR-0160 D3 (*Nothing else*), which is amended there.
7. **Measured before this record** (Finding 142), one run and no more.

## How (Claude's proposal)

**P1 - The API.** Two open routes beside the dashboard's, in the OpenAPI
file (ADR-0152):
- `POST /panel/page/show` with `{"url": "...", "id": "...", "seconds": N}`.
  `url` is http or https; `id` is Home Assistant's name for the page
  (default `page`); `seconds`, from 10 to 3600, is the limit (default 600;
  the longest, 60 minutes, George's choice over none and over 10 minutes).
  The core checks the address as it does the dashboard's (`idle_page.probe`)
  before showing it, and refuses with the reason when the page cannot be
  framed or does not answer, so the action fails in Home Assistant with a
  sentence rather than a blank screen on the panel. Refused too: the switch
  off (403), a player with no screen (409).
- `POST /panel/page/hide`, with an optional `{"id": "..."}`: with an id it
  takes down only that page, so an automation never closes another's.
- A show while a page is up replaces it; the same id again restarts its
  limit (a second ring), and reloads only when the address differs.

**P2 - The state.** `/state` `panel.page`: `{"shown": bool, "id", "until"
(epoch seconds), "closed": {"id", "by"}}`, `by` one of `touch`, `key`,
`limit`, `asked` (the API), `replaced`, `heat` (P8), `off` (the switch).
The address is not repeated: the socket is open on the network, Home
Assistant knows what it sent, and an address can carry a token.
`/player/status` gains `pages` (the switch), as it carries `screen` and
`idle_screen` (ADR-0160 D5), and `panel.pages` follows the switch live.

**P3 - The layer.** A screen of its own in the panel (`PageScreen.svelte`),
above the idle screen (20) and the dashboard (11), below setup, pairing,
the update, *Keep this screen?* and the standby cover, which stay over it.
The frame is sandboxed as the idle page's is (`allow-scripts
allow-same-origin`: a page to look at, no forms or pop-ups), with the
touch layer of decision 3 over it. No player chrome: no tab, no title, no
hint. The panel underneath pauses its animations, as under the idle screen.
Home Assistant's sign-in is the dashboard's: the frame sits in the same
storage partition, so a player whose dashboard shows has the page's too
(seen on sofapi in Finding 142's run, where the page signed in by itself).

**P4 - Closing.**
- A touch anywhere closes it; that touch does nothing else.
- Any D-pad key closes it (`/panel/key`, before the key is pressed), as any
  touch does - the remote's version of decision 3; the key is not passed on
  (George, over Back only).
- The page never takes the focus, so a USB keyboard stays the panel's.
- The limit ends it; the switch turned off ends it.

**P5 - Back to what was there.** The page changes nothing underneath, so
taking it down shows what is there:
- The screens below stay mounted (they already do under the dashboard), and
  the idle countdown does not run while the page is up; it starts again
  when it goes.
- The visualiser, if up, is minimised (not stopped, so it returns at once)
  and raised again after; it does not raise itself while the page is up.
- **A person's request wins, the clock's waits:** a person asking the panel
  for something - the visualiser, the dashboard, a view from the phone -
  takes the page down first (`closed.by: asked`); what comes by
  itself - the idle countdown, the visualiser's timeout, a standby time -
  waits until it has gone (George, over the page holding against everything
  but a touch, a key, the limit and Home Assistant).

**P6 - Standby.** A screen in standby wakes for the page (the API's wake,
ADR-0135) and goes back to standby when the page goes, unless someone used
the screen meanwhile - a touch that is not the closing one, a key, or the
phone. A standby time that begins while the page is up waits for it.

**P7 - Groups and sources.** Nothing: the page is the screen's, not the
music's. A player in a group shows it alone.

**P8 - When it is too much** (Finding 142: heat over the 10 minutes). The
music comes first: if the processor reaches 80 °C - where the Pi 4's
firmware starts slowing it - or the firmware reports it throttled, the core
takes the page down (`closed.by: heat`) and logs it (George, over no guard).
The manual advises fewer cameras and the smaller streams for a player's
screen.

**P9 - The integration** (its own repository, a minor version):
- `gexis.show_page` (target: the player's media player; `url`, `id`,
  `seconds`) and `gexis.hide_page` (`id` optional), failing with the
  player's sentence when it refuses.
- A binary sensor *Page*, on while a page is shown, with `page_id` and the
  last close's `by` as attributes; unavailable while the player's switch is
  off, so dashboards and automations can tell where it works. The switch
  itself stays the player's (ADR-0160 D3: no settings from Home Assistant).
- It needs a player that reports `pages`; an older one is told to update.

**P10 - Documents.** The manual (Display, the Home Assistant chapter), the
FAQ, the technical guide (`core-and-state.md`), the OpenAPI file, README's
feature list and the integration's README: what it does, the switch, the
sign-in and framing it shares with the dashboard, and the advice of P8.

**As built** (2026-11-07, `ph-ha-page`):
- `panel.page` also carries `seq`, one more each time the panel has a page to
  load (a new one, or the same id at a new address): the panel fetches the
  address from `GET /panel/page`, which gives it to the panel only.
- A show is refused too while the room is being measured (409): the
  measurement takes the screen to say so and wants the processor quiet. A
  measurement's start takes a page down, as a person's request.
- A USB keyboard's key on the panel closes the page as a remote's does
  (`hide?by=key`, the panel's word only, as `?by=touch` is).
- The integration's actions are named *Show a page on the screen* and *Hide
  the page*; its version is 0.6.0, and it needs the player's 1.15.0.

## Considered and not chosen

- **As a plugin** (decision 1): a new plugin capability to draw on the panel,
  and a plugin to pass calls to it; more work for the same result.
- **An edge tab, as on the dashboard** (decision 3): the page's own controls
  would work, but a pop-up wants closing at a touch, and the camera card was
  made for TVs, without touch.
- **The address in `/state`**: see P2.
- **Only pages from the dashboard's site**: safer, but it ties the feature to
  a dashboard being set, and to one address for Home Assistant where owners
  use two (a proxy and `:8123`). The switch is the guard instead.
- **Showing what the panel would show for a page that cannot be framed**
  (the dashboard's way): a pop-up nobody asked for at the panel needs no
  sentence there; the caller does.

## Settings (ADR-0022)

Confirmed by George (2026-11-07), appended to ADR-0022 the same day:

| Setting | Mark | Notes |
|---|---|---|
| Pages from Home Assistant | [N] | On or off for each player, off by default; off refuses every page and closes one shown |
| Page time limit | [H] | 10 minutes when the call gives none |
| Longest time limit | [H] | 60 minutes a call may ask (P1) |
| Page heat limit | [H] | 80 °C, or the firmware throttling (P8) |

## Acceptance

From `docs/DEVELOPMENT.md`, Phase 35:

1. Home Assistant shows a page on a player with the switch on, over whatever
   is there, the music playing on; a screen in standby wakes for it.
2. A touch, Back, the time limit or Home Assistant takes it down; the panel
   returns to what it showed, standby included, and Home Assistant sees it.
3. With the switch off the player refuses, and Home Assistant offers nothing.
4. Live cameras while music plays at 192 kHz with room correction: no
   dropouts - recorded as a finding.

## Unverified

- Everything Finding 142 did not measure: 192 kHz, the equaliser's or room
  correction's stage beside the page, a run as long as the 10-minute limit,
  fewer cameras, a bar or another Pi 4 (acceptance 4 covers the first two).
- How Chromium keeps the framed sign-in across a reboot (ADR-0156's open
  question); not needed with trusted networks.
- Whether a frame that is replaced (P1) releases its streams at once, or
  holds them until Chromium collects it.
- The narrower sandbox of P3: Finding 142's run framed the page with the
  dashboard's (forms and pop-ups allowed too).
