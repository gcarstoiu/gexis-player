# ADR-0156 — A Home Assistant dashboard on the screen

**Status:** **Accepted** — 2026-10-21 (George: decisions 1-5 below, *"1. Yes
2. Yes 3. Edge tab 4. Your suggestion"*, and on the idle page *"Why would we
retire it?"*). Phase 18, `ph-ha-dashboard`. Nothing built yet.

## Context

George, 2026-10-21: *"I need to be able to control devices from the screen
for a specific room. The dashboards are created in home assistant and should
be displayed on the screen on command or replacing the idle screen on a
schedule. During this time, playback is not affected and the dashboard stays
up until it's dismissed. Everything in the dashboard is actionable."*

What exists:

- **The idle page** (Phase 4d, `idle_url` in `core.toml`, set at flash time):
  any web page as the idle screen, in an `<iframe>` inside the panel's own
  page (`IdleScreen.svelte`), sandboxed, with a layer over it that takes the
  first touch and brings the player back. Look, don't touch.
- **The player's API** (Phase 15, ADR-0152): every route documented, which
  Home Assistant can call with a `rest_command` today.
- **Phase 21, `ph-home-assistant`**: the other direction - the player inside
  Home Assistant as a media player. Not needed for this.

Home Assistant, as shipped, refuses to be framed by another origin
(`http: use_x_frame_options`, on by default, sends `X-Frame-Options:
SAMEORIGIN`), and its pages need a signed-in user. Neither is in the
player's hands. Read from Home Assistant's documentation, not tried here.

## Decision

1. **One dashboard per player, its room's**, built in Home Assistant and
   shown full screen on the panel, every part of it usable. The player
   holds only its address.
2. **It comes up four ways:**
   - a **dashboard button** on the panel - in the bar's pull-down tray beside
     Home and the visualiser, and beside the visualiser button on other
     screens - shown once an address is set;
   - the **same button on the phone page**, as the *Screen* button is;
   - **Home Assistant itself**, through the API (`POST /panel/dashboard/show`
     and `/hide`), so an automation can put it up;
   - **a schedule**: during the times set, the dashboard stands where the
     idle screen would - the same grid of hours, quarters and days as the
     standby times (ADR-0135). Outside them the idle screen is as it is.
3. **While it is up:**
   - **playback is untouched**: music goes on, and starting, stopping or
     changing tracks does not take it down;
   - **it stays until dismissed**: the idle timeout, the visualiser's
     automatic start and the takeover animation do not replace it;
   - **every touch is the dashboard's**: no layer over it.
   - **Over it** still: the volume drawer on a change from elsewhere, and the
     setup, update and screen-confirm screens.
   - **Display standby wins**: at a standby time the screen goes dark as
     always, and comes back to the dashboard.
4. **Dismissed by an edge tab** (George: *"Edge tab"*): a small tab on one
   edge of the screen, the only part of it that is not the dashboard's; also
   by the phone's button and the API. When its scheduled time ends, the
   normal idle screen follows.
5. **Inside the player's page** (George: *"Your suggestion"*): an `<iframe>`
   in the panel's own page, as the idle page is, so the player keeps the
   edge tab, the volume drawer and everything over it. This needs one line
   in Home Assistant's configuration (`http: use_x_frame_options: false`),
   documented in the manual. A window of its own beside the kiosk was the
   alternative: no change in Home Assistant, but a second browser, window
   placement and focus to manage (as with the visualiser, Findings 125, 131).
6. **Signing in is Home Assistant's**: its *trusted networks* lets the player
   in without a login (George, 2026-10-21: *"Trusted networks"*), set up by the
   user in Home Assistant; signing in once - typing from the phone, which
   already types into the panel - with the session kept in the kiosk's
   profile is the fallback. Both documented; the player stores no Home
   Assistant password or token.
7. **The idle page stays** (George: *"Why would we retire it?"*): it is a
   different thing - a page to look at while idle, set at flash time. When
   both are set, the dashboard wins during its scheduled times and the idle
   page shows outside them.

8. **The player changes nothing in Home Assistant** (George, 2026-10-21: *"I
   wouldn't start making changes to other services from our player. Lyrion is
   the only one as it's part of the library and playing path. This dashboard
   is not."*). The two changes it needs - `use_x_frame_options: false` and
   trusted networks - are the user's to make in their own Home Assistant; the
   manual says what and where, and the panel says which one is missing when
   the dashboard cannot show.

## Settings (ADR-0022, appended 2026-10-21, confirmed by George)

| Setting | Mark |
|---|---|
| Dashboard address | [N] |
| Dashboard instead of the idle screen, and its times | [N] |
| Dashboard button on the panel | [N] |

## To settle while building

- Where the edge tab sits on each layout (standard, bars) and how it looks
  over a dashboard of any colour; whether it hides after a while.
- What the panel shows when the address does not answer, or Home Assistant
  refuses the frame or asks for a login: a sentence saying which, and the
  way back - never a blank screen.
- Whether a dashboard's own header and sidebar can be hidden without a
  custom card; the manual says what was found.
- The bar's 1480 × 320: a dashboard built for that shape; the manual says so.
- The API's two routes in the OpenAPI file (ADR-0152) and their state on the
  `/state` socket, so the phone's button shows whether it is up.

## Unverified

- That `use_x_frame_options: false` and *trusted networks* behave as their
  documentation says on a current Home Assistant; to be tried against a real
  one before the ADR's decision 5 is built on.
- How Chromium keeps a framed Home Assistant's sign-in (third-party storage
  is partitioned by the top-level site): whether it survives a reboot.
