# ADR-0152 — A documented public API

**Status:** **Accepted** — 2026-10-19, George, for Phase 15 (`ph-api`):
shown in both places, *"Allowed for all"* to be tried, a setting *"next to
the debug logs one"*. One point open: what the API promises to keep (below).

## Context

Everything the panel and the phone do goes through the core's API: 92 HTTP
routes in `wsserver.py`, 90 of them the API's and two the UI's own files (48
GET, 42 POST, a PUT and a DELETE, counted 2026-10-19), and the live state over
WebSockets (`/state`, the touchpad's
channel). It is open to the home network without a login (ADR-0028, as
ADR-0022 accepted the trusted LAN). What it is is written down only in
pieces: the technical guide's route tables, the decision records, the code.
Anyone building on it - Home Assistant (Phase 17), an app, a control surface,
a plugin author - has to read the code. The idea *Documented public API* was
a Must on the Roadmap; George put it before room correction (2026-10-19).

## Decision

1. **One OpenAPI 3.1 file is the API's description**, written by hand and
   kept with the core (`core/src/gexis_core/api/openapi.json`), so it ships
   with the player. JSON rather than YAML: Swagger UI reads either, and JSON
   needs no new library on the player or in the tests (the core has no YAML
   parser). every route, what it takes, what it answers, its errors,
   and the decision record it comes from. aiohttp, which the core is built
   on, does not generate one, and its add-on libraries for it are thinly
   maintained.
2. **A test keeps the file and the code together**: it lists every route the
   core registers and fails when one is missing from the file, or the file
   names one the core does not have. A description that drifts from the code
   is worse than none.
3. **The live state's messages are JSON Schema in the same file**
   (`components`), and the WebSocket channels are described in a page of the
   technical guide. AsyncAPI, OpenAPI's sibling for events, is not taken on
   for two channels.
4. **Shown in two places** (George: *"Both"*):
   - **on GitHub**, a static page built from the file at each release, for
     reading without a player. It cannot try routes: a public HTTPS page may
     not call a player on the home network's plain HTTP;
   - **on the player**, at `/api`, with the file at `/api/openapi.json`.
5. **On the player every route can be tried** (George: *"Allowed for all"*),
   against that player - restart, reset and update included, which the API
   already allows anyone on the network (ADR-0028); the page only makes it a
   button.
6. **Behind a setting, `api_explorer`** (*API explorer*), in System after
   *Debug logs*, off by default (George: *"Yes, a setting shown next to the
   debug logs one. You can give it a name."*; ADR-0022 [N]). Off, `/api` and
   its file are not served; the API itself is unchanged either way.
7. **The viewer is Swagger UI**, which tries routes, on both pages, served
   from the player's own files - the player cannot count on the internet -
   and named in Credits (ADR-0099) with its licence (Apache 2.0).

## Open (George)

- **What the API promises.** Some routes are the panel's own plumbing
  (`/panel/painted`, `/touch`, the setup network's), others are what an
  integration needs (state, transport, volume, settings, library).
  Proposed: every route documented; those an integration may rely on
  marked *stable* - changed only with notice in the release notes and kept
  working for a release - and the rest marked *internal*, free to change.

## Consequences

- A change to a route changes the file in the same commit, or the test
  fails.
- The image carries Swagger UI's files (a few MB, to be measured).
- Home Assistant (Phase 17) is built against the documented API.
