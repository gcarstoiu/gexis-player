# ADR-0160 — The player in Home Assistant

**Status:** **Accepted** — 2026-10-24 (George: D1 our own integration, D4 a
repository of its own, D3 with the dashboard and visualiser switches, D7 a
Home Assistant in Docker that hears nothing on the network). Phase 19,
`ph-home-assistant`. Built 2026-10-24 (*Measured*, below).

## Context

Each player already has what Home Assistant needs, open on the LAN with no
authentication (ADR-0022, ADR-0028) and marked stable in the OpenAPI file:
`/state` (pushed, ADR-0018), `/transport/{command}`, `/volume`,
`/volume/mute`, `/renderer/{id}/activate`, `/panel/standby/{action}`,
`/panel/dashboard/{action}`, `/peppy/{action}` and `/player/status`. It
announces `_gexis._tcp` on port 8090 with no TXT records (ADR-0136).
Missing: a stable id (`/player/status`'s `instance` is new at every start),
and whether the player has a screen (`headless` is only in `/settings`).

Home Assistant, read 2026-10-24 (core `dev` at 2026.11.0.dev0;
contributors.home-assistant.io, hacs.xyz):
- A custom integration needs `manifest.json` (with `version`),
  `__init__.py`, `config_flow.py` and a full `translations/en.json`. Its
  manifest may list `zeroconf` service types; a discovered device must be
  confirmed by the user and needs a unique ID;
  `_abort_if_unique_id_configured(updates=...)` follows an address change.
- `media_player`: artwork is proxied by Home Assistant unless
  `media_image_remotely_accessible`; the position is `media_position` with
  `media_position_updated_at`. The closest precedent for a screen is Fully
  Kiosk's `screen_on` switch, beside its other entities.
- MQTT has no `media_player` platform, and its discovery needs broker
  credentials on the device, which then publishes Home Assistant's
  entities.
- HACS: one integration per repository, in `custom_components/<domain>/` at
  its root, with `hacs.json`; its default catalog wants full GitHub
  releases, `brand/icon.png`, hassfest and the HACS action passing, and
  reviews take months. **From Home Assistant 2026.11 HACS is built in, as
  Settings → Marketplace**, reading the same catalog (not released on
  2026-10-24). Since 2026.3 an integration ships its own `brand/` images.
- Core: Bronze on the quality scale, a PyPI library for the device's API,
  and a product with an established user base; the Marketplace first is
  recommended.
- The built-in *Squeezebox (Lyrion Music Server)* integration (polling)
  already lists every Lyrion player, ours included, as a media player, with
  no source and no screen. With both set up, a player shows twice.

## Decisions

**D1 — Our own integration, not MQTT** (George, 2026-10-24). Domain
`gexis`, named *Gexis Player*, `integration_type: device`, `iot_class:
local_push`: one WebSocket to `/state` per player, the POST routes for
commands. The owner installs it and confirms each player; the player
changes nothing in Home Assistant (George, 2026-10-21).

**D2 — Found by `_gexis._tcp`, or added by address.** The manifest lists
`_gexis._tcp.local.`; the discovery step reads `GET /player/status` from the
announced address for the id and name, then asks the owner to confirm. A
user step takes an address for a player discovery does not reach (and for
D7). The id is the unique ID, so a new address updates the entry.

**D3 — What Home Assistant gets** (George, 2026-10-24: the phase's list,
plus the dashboard and the visualiser):
- **A media player:** playing, paused or idle (never off: the player has no
  power state of its own); title, artist, album, artwork, duration and
  position; play, pause, next and previous as `controls.available` allows;
  shuffle and repeat where the renderer declares them; volume and mute,
  unless the output is fixed (`fixed_output`); the source, chosen from the
  installed sources that can be activated.
- **Switches, on a player with a screen:** *Screen* (on is lit; off is
  display standby, ADR-0135), *Dashboard* (ADR-0156; unavailable with no
  dashboard address) and *Visualiser*.
- Nothing else: no settings, updates, restart, reset, uploads, library
  browsing. The API being open (ADR-0028) is no reason to expose more.
- While the socket is down the entities are unavailable, and it reconnects.

**D4 — Its own public repository** (George, 2026-10-24):
`gcarstoiu/gexis-player-homeassistant`, GPL-3.0 like the player,
`custom_components/gexis/` with `brand/` icons, `hacs.json`, versioned and
released on its own (from 0.1.0). Installed first as a custom repository
(HACS, or the Marketplace from 2026.11), then submitted to the default
catalog. Core: not now.

**D5 — The player's side** (this repository, `ph-home-assistant`):
`/player/status` gains `id` and `screen`. `id`: the first 16 hex digits of
SHA-256 over `gexis:` and the board's serial number
(`/proc/device-tree/serial-number`), null off a Pi - the same after a
rename, a reflash or a factory reset, and not the serial itself.
`screen`: false when headless. The announcement is unchanged. The
integration needs a player with `id`; an older one is refused with *update
the player first*.

**D6 — Documents.** The manual, FAQ, README and technical guide say how to
add a player in Home Assistant, the version needed, and that with the
Lyrion integration also set up the player shows twice. The integration's
README carries the same steps.

**D7 — Tested in Docker, without discovery** (George, 2026-10-24). A
throwaway Home Assistant in Docker on the build computer, bridge network,
hearing nothing on the LAN; a test player added by address, after checking
it is not in use. Discovery is first seen on George's own Home Assistant,
when he chooses. In the integration's repository: Home Assistant's test kit
(`pytest-homeassistant-custom-component`), hassfest and the HACS action on
every push. Criterion 3 measured as Finding 109 measured Lyrion: underruns
and XRUNs during playback with Home Assistant connected and commanding.

## Settings (ADR-0022)

None: nothing to set on the player.

## Measured (sofapi, 2026-10-24)

Core and player 1.4.0+git49.c4af394, ui 1.4.0+git24.e505054; Home Assistant
2026.10.3 in Docker, bridge network, no `default_config` (zeroconf, SSDP,
DHCP not loaded); the integration 0.1.0 (17 tests, hassfest clean), sofapi
added by address.

- One media player and the three switches; *Dashboard* available (an address
  is set on sofapi). No errors in either log.
- **Criterion 2:** the player's own pause, play, next and volume reached
  Home Assistant in 0.53-0.64 s (polled every 50 ms); title, artist,
  position and artwork shown, the artwork through Home Assistant's proxy
  (`image/jpeg`, from sofapi's own Lyrion server: the loopback address
  rewritten).
- **From Home Assistant:** source, play, pause, next, volume and each switch
  over and back, each seen within 0.7 s.
- **Not seen:** the artwork changing with the album (the queue was one
  album); criterion 1 (discovery: George's own Home Assistant).
- **Criterion 3** (the same evening): 46 minutes of playback with Home
  Assistant commanding every 40-80 s - 0 underruns, 0 XRUNs, counted by
  squeezelite's output logging ([Finding 137](../findings/137-playback-with-home-assistant-connected.md)).

## Unverified

- The Marketplace in 2026.11 as described before its release.
- Artwork from an online source (Spotify's), through Home Assistant's proxy.
