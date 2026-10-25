# The public API

Everything the player's own screen and phone page do goes through one HTTP
API, which apps, home automation and control surfaces can use too. Its full
description is an OpenAPI 3.1 file,
[`core/src/gexis_core/api/openapi.json`](../../core/src/gexis_core/api/openapi.json)
(ADR-0152); this page is the overview, and the two WebSockets in prose.

## Where, and who may call it

- **`http://<player>.local:8090`**, with the player's name in place of
  `<player>`, on the home network. The setup network's address while setting
  up is `10.42.0.1:8090`.
- **No login.** The API is open to the home network, as the player's
  settings are (ADR-0028, ADR-0022): anyone on it can call every route,
  restart and *Reset to factory settings* included.
- **Commands are plain HTTP** (`GET` to read, `POST`/`PUT`/`DELETE` to act);
  **what changes arrives on the `/state` WebSocket**. A command's `200` means
  *sent*; the effect is read from the next state.
- **Errors** answer with a status and `{"error": "<a sentence>"}`: `400`
  an invalid value, `404` an unknown thing, `405` not settable, `409` not
  possible now, `502` a service the player depends on (Lyrion) did not
  answer, `503` not wired up in this core.

## Seeing it, trying it

- **On the player:** switch on *Settings → System → API explorer* (off by
  default) and open `http://<player>.local:8090/api`. Swagger UI shows every
  route grouped by what it is for, and **every route can be tried** against
  that player - so *Execute* on a restart restarts it. Off, `/api` is not
  served; the API itself is the same either way.
- **The file itself** is `/api/openapi.json` on the player (with the release
  it runs as its version), or in the repository.
- **On GitHub:** a static page shows the file for each release, for reading
  without a player; it cannot try routes (a public HTTPS page may not call a
  player's plain HTTP on a home network).

## Stable and internal

Every operation carries `x-gexis-stability`:

- **stable** - what an integration may rely on: the state, playback,
  volume, sources, the library and radio, settings, backups;
- **internal** - the player's own pages and plumbing: setup and first use,
  the panel's signals, the problem and hardware reports. Free to change
  between releases.

A *stable* route changes only with notice in the release notes, and keeps
working for a release after (ADR-0152, decision 8).

## The live state: `GET /state`

A WebSocket. On connecting, the core sends the whole state at once, then the
whole state again **whenever anything in it changes** - never a diff, so a
client keeps nothing between messages. The client sends nothing on it;
commands go over HTTP. Its JSON is the schema `State` in the file:
`active` (the source playing, or null), `available`, `metadata` (title,
artist, album, artwork, position), `volume`, `controls` (which transport
commands work now), `sources`, `queue`, `pairing` (a Bluetooth request
waiting for an answer), `panel` (standby, what the screen shows), and the
first-use and update fields the player's own pages use.

## The touchpad: `GET /touchpad`

A WebSocket between a phone and the panel (ADR-0121). A connection from the
player itself is the panel; any other is a phone. A phone sends `move`,
`tap`, `text`, `key`, `scroll` and `zoom` messages, relayed unchanged to the
panel; the panel sends `over` and `focus`, relayed to the phones. Every
message is a JSON object with its kind in `t`; anything else, or a frame over
2048 bytes, is dropped, and with *Phone touchpad* off every relayed message
is dropped. `{"t":"ping"}` is answered `{"t":"pong"}`. The schemas
`PanelTouchpadFromPhone` and `PanelTouchpadFromPanel` give the fields. It is
*internal*: the phone page's own.

## The equaliser

ADR-0162, *internal* until Phase 20 closes (then *stable*). For the output in
use: `GET /equaliser` (the same object as `/state`'s `equaliser`: whether it
is on, the setting and its bands, the headroom, `fixed`, `dsd`, the presets
and the owner's settings); `PUT /equaliser` with `on`, `sel` (a preset's or
an own setting's key), `gains` (ten whole decibels, −12 to +12, low to high)
or `band` with `gain`; `POST /equaliser/settings {name}` saves the bands as
one of the owner's (up to ten); `PUT` and `DELETE /equaliser/settings/{key}`
rename and delete one. A refusal is a 400 with the sentence to show (*There
is a setting called Rock already.*). A band or a setting is heard at once;
`on` reopens the output.

## Home Assistant

The first client written against the file by someone other than the player's
own pages is the Home Assistant integration (ADR-0160), in its own
repository, [gexis-player-homeassistant](https://github.com/gcarstoiu/gexis-player-homeassistant).
It uses only *stable* routes: `GET /player/status` for the player's lasting
`id` (its unique ID in Home Assistant), `screen` and `idle_screen` (whether
the idle screen is switched on), `GET /state` (one WebSocket per player;
each source's `capabilities` give the controls it shows, `controls.available`
those that work now), `GET /panel/dashboard`, and the POST routes for the
transport, volume, mute, standby, the dashboard, the visualiser, the idle
screen (`/panel/idle/{action}`),
`/panel/go/{to}` (Home, Now Playing, Lyrics) and `/panel/key` (the D-pad's
up, down, left, right, ok and back, pressed on the panel's virtual keyboard;
ADR-0161). A player without `/panel/key` answers 404, and the integration
asks for it to be updated.
A player found by `_gexis._tcp` or added by address without an `id` is
refused as too old.

## Keeping the file true

The file is written by hand - aiohttp, which the core is built on, generates
none. `core/tests/test_openapi.py` fails when a route the core registers is
missing from the file, when the file describes a route the core no longer
has, when an operation lacks its summary, tags, stability mark or answers,
when a reference does not resolve, or when the file names a device or a home
address. **A change to a route changes the file in the same commit.**
