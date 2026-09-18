# ADR-0038 — Library and radio on the panel: the designed screens only, read through the core, played on LMS

**Status:** Proposed — awaiting George's read
**Date:** 2026-09-17
**Raised by:** Phase 7 (library browse), plan agreed with George 2026-09-17
**Amends:** [0030](0030-library-typed-radio-slimbrowse.md) — narrows its typed
screen list to what is designed, corrects how Podcasts is excluded, and
settles Radio Now Playing. `docs/DEVELOPMENT.md` Phase 7 criterion 1.
**Builds on:** [0020](0020-library-browse-tree.md) (the core proxies, artwork
comes straight from LMS), [0027](0027-lms-power-as-arbitration-mechanism.md)
(how LMS takes the device), [0028](0028-ui-serving-and-command-channel.md)
(one process, REST), [0033](0033-idle-and-home.md) (Home is the no-renderer
screen), [0037](0037-transport-commands.md) (a `200` means sent; the result is
read from `/state`)

## Context

ADR-0030 chose typed queries for the library and SlimBrowse for radio, and
listed eleven typed screens it had verified the server could fill. The designs
(`design/screens.md`, `design/data-contract.md`) draw a different, smaller set:
a library root, a three-pane Browse, an artist grid, an artist page, an album
page, playlists, radio, a mini strip, and a queue rail on now playing. Seven of
ADR-0030's lists — Album Artists, Composers, Genres, Years, Compilations, Songs,
Music Folder — have no design.

Parts of the designs also need data LMS does not have (artist photos, the
artist page's About, Popular and Similar) or an input the panel cannot take
without a keyboard (naming a new playlist, ADR-0029).

None of the library data exists in the core today. The panel shows a
placeholder when no renderer is active, and Now playing's Home and Queue
buttons are disabled and marked `data-unwired="phase-7"`.

## Decision

### 1. The designed screens, and nothing else (George, 2026-09-17)

*"Just what is designed. The other screens are out of scope."*

| Screen | Contents in Phase 7 |
|---|---|
| **Library root** (Home) | Five cards — Browse, Artists, Playlists, Radio, Settings — the New Music strip, and the design's waiting-service indicators |
| **Browse** | Three panes: artists, that artist's albums, the album's tracks, each with row actions (§3) |
| **Artist grid** | Grouped under letter headers with the `#`, A–Z jump rail; letters with no artists dimmed and inert |
| **Artist page** | Name and discography (§2) |
| **Album page** | Artwork, title, artist, year, tracks with durations, Play all |
| **Playlists** | Name, track count, and the tracks |
| **Radio** | The `radios` subtree, up to four levels, in our own rows (ADR-0030) |
| **Mini strip** | On every screen but now playing; play/pause through ADR-0037's route |
| **Queue rail** | On now playing, LMS only; George, 2026-09-17: in Phase 7 |

The seven undesigned lists are **out of scope**, not deferred to a later step
of this phase. ADR-0030's verification of them stands as a record of what the
server can do.

**"Artists" means Album Artists** (George, 2026-09-17): `artists
role_id:ALBUMARTIST`, 916 on this server, in the artist grid and Browse's
artist pane.

**Playlists are the LMS library's own, not a plugin's** (George, 2026-09-17:
*"Playlists in general should only be from LMS library,"* not third-party
add-ons). All 98 playlists LMS returned on 2026-09-17 were Qobuz playlists
(`qobuz://` URLs); none was local. On this server, the Playlists screen and
the queue rail's playlist chooser are therefore empty until a library playlist
exists. ADR-0030 counted one playlist on 2026-09-14; what that one was is not
recorded.

### 1a. Filing and grouping follow LMS (George, 2026-09-17)

*"Keep LMS behaviour. However it does it, we do it as well."*

- **Artist order and letter headers are LMS's.** LMS files by its sort name:
  174 of the 916 album artists sit under a letter other than their displayed
  name's first (David Bowie under B, Louis Armstrong under A). It ignores
  leading articles ("The Beatles" under B) and folds accents in the order.
  This replaces `design/data-contract.md`'s own folding rule.
- **The discography is grouped by LMS's `release_type`, as LMS gives it.**
  Measured across all 4,554 albums: ALBUM 3,968, ALBUM COMPILATION 293,
  ALBUM LIVE 95, ALBUM SOUNDTRACK 88, SINGLE 38, EP 34, and a tail of
  combinations (EP LIVE, ALBUM COMPILATION DJ MIX, …).
- **Left for step 6, to show George:** LMS's letter key (`textkey`) is not
  folded for two artists, `Ç` and `Í`, although the order puts them inside C
  and I. The design's rail is `#`, A–Z.

Navigation is the design's: Back on every screen below the root, Home beside
it below the first level, the mini strip back to now playing. Settings is
reached from the root card. Home is the library root; ADR-0033 already put it
there for `active: null`, and now playing's Home button opens it too.

### 2. Without enrichment (George, 2026-09-17)

- **Artist grid:** the artist's initial in the circle where the design has a
  photo. LMS has no artist photos.
- **Artist page:** name and discography only. About, Popular and Similar are
  Phase 8 enrichment (ADR-0012); their blocks are not drawn until then.

### 3. Row actions: play now, add to queue, add to playlist

**Creating playlists is not supported** (George, 2026-09-17), in Phase 7 or
later. It needs a name typed on the panel, which ADR-0029 allows only with a
USB keyboard. George is asking Claude Design to remove playlist creation from
the design.

**Add to playlist adds to any LMS library playlist** (§1). It picks an
existing playlist and needs no typing.

The queue rail's empty state offers a playlist chooser (data contract); that is
a play-now on a playlist, not a creation.

### 4. Playing from the library is how LMS takes the device

A play-now from the panel is an LMS `load`. On a powered-off player, **LMS
powers itself on** — its own documented behaviour since ADR-0010, confirmed on
hardware in ADR-0027 and exercised against Spotify in Finding 019. The core
sends no `power 1`, keeping ADR-0027's "we never power on". Arbitration sees an
ordinary LMS acquisition. This is what the design means by "starting playback
from the library activates LMS as a side effect".

ADR-0027's known cost of plain `play` — the position restarts from zero — does
not apply: a `load` starts new content.

**Verified 2026-09-17** (Finding 029): a `load` on a powered-off player powers
it on, over a playing Spotify session too. The core's resume after that
takeover was wrong for new content; Phase 7 step 1a fixes it.

### 5. The panel talks to the core; the core talks to LMS

Same process and origin as every other route (ADR-0028). The panel never sends
an LMS command.

- **Reads** are `GET` routes under `/library/…` and `/radio/…`, paged with
  `offset` and `limit`. The core runs the typed queries (ADR-0030) and returns
  the fields the screens need, not LMS's reply.
- **Actions** are one `POST` route taking what to act on (album, artist, track,
  playlist, radio item), the action (§3), and a target playlist where one
  applies. A `200` means sent; what happened is read from `/state`
  (ADR-0037 §1). `409` when the action cannot be taken, `502` when LMS refused
  or was unreachable.
- **Radio:** the core walks the SlimBrowse subtree and hands the panel an
  opaque handle per item. The panel sends the handle back to open or play it.
  The core only acts on handles it issued from `["radios","menu:radio"]`, so
  the network-reachable API (ADR-0028: unauthenticated by decision) never
  becomes a way to send LMS arbitrary commands.
- **Queue:** `/state` carries the queue for LMS — upcoming tracks, and the
  playlist they came from — because it changes on its own and the rail must
  follow it. What LMS reports for "came from" is measured in step 1.

Route names may move while the steps build them; the split — reads paged,
one action route, handles for radio, queue on `/state` — is the decision.

**Actions as built (step 5, 2026-09-18):** `POST /library/action` with
`{"kind": "album"|"artist"|"track"|"playlist", "id": <int>, "action":
"play"|"add"}`. One `playlistcontrol` per action. 404 for an unknown kind,
action or id, 409 before the adapter has resolved the player, 502 when LMS
is unreachable, 503 unwired. **Note:** LMS drops the connection rather than
answering when asked to play an id that does not exist, so that case
surfaces as 502, not 404.

**Reads as built (step 3, 2026-09-17):** `GET /library/counts`, `/library/new`,
`/library/artists?offset&limit`, `/library/artists/{id}/albums`,
`/library/albums/{id}` (with its tracks), `/library/playlists` (with track
counts), `/library/playlists/{id}?offset&limit`. 404 for an unknown id, 400
for a non-numeric one, 502 when LMS is unreachable, 503 unwired. The root's
"stations" count is not reported: it still has no source.

### 6. Lists are cached in memory

List pages are cached in the core's memory (ADR-0020, "cached aggressively in
RAM"). How long an entry is kept is a setting (§9). **A full rescan renumbers
every album and artist id** (Finding 029), so a change in `serverstatus`
`lastscan` drops the cache, the radio handles and any remembered id. Whether
CometD also pushes a rescan is not checked.

### 7. Artwork and icons come straight from LMS

The panel loads artwork from LMS directly (ADR-0020):
`/music/<artwork_track_id>/cover_<W>x<H>_o.jpg`.

**Why `_o.jpg`, measured 2026-09-17 on one album:**

| URL | Type | Bytes |
|---|---|---|
| `cover` (original) | JPEG | 86,101 |
| `cover_300x300` | PNG | 173,269 |
| `cover_300x300.jpg` | PNG | 173,269 |
| `cover_300x300_o.jpg` | JPEG | 25,474 |

**Two sizes, each the size the panel draws** (2026-09-17): 500 px for a
cover (the album page, now playing's well — the design's 500×500) and 200 px
for a thumbnail (a New Music card is 176 px, a row's thumb smaller). Ten
500 px covers in 176 px cards were part of what made the strip scroll
unevenly on the panel, and now playing was blurring the *unsized* original —
up to 358 KB — behind the screen.

The bare resize returns a PNG twice the size of the original. **Repeated on
20 random albums (step 1):** the bare `cover_300x300` was a PNG for 5 of 20,
up to 245 KB; `cover_300x300_o.jpg` was a JPEG for all 20, median 22 KB,
largest 53 KB (500 px: median 52 KB). 4,521 of 4,554 albums have an
`artwork_track_id`.

SlimBrowse icons arrive as server paths (`plugins/…` and `/plugins/…`, both
forms seen) and are resolved against the LMS base. An image that fails to load
shows the design's pending glyph (data contract, empty states).

### 8. Radio: what is excluded, and how

- **Podcasts is excluded by its command, `["podcast","items"]`, not by an
  id.** ADR-0030 named the id `opmlpodcast`; the `radios menu:radio` reply on
  2026-09-17 carried no `id` on any of its eleven items. The command was
  present.
- **Radio Now Playing stays** (George, 2026-09-17). This closes ADR-0030's open
  item.
- Text-input items are dropped wherever they appear (ADR-0030, unchanged).
  Search TuneIn carries an `input` block today.
- **An item's action can be inherited, and the inherited action can be a
  play.** Measured in step 1: station lists carry no `actions` on their items;
  the list's `base.actions.go` applies, and there it is
  `["radionowplaying","playlist","play"]` or `["local","playlist","play"]`,
  with `nextWindow: nowPlaying`. The core decides open-or-play from the
  resolved command, not from the key name `go`. Found by starting playback
  unintentionally (Finding 029).

### 8a. A playing station on now playing (George, 2026-09-17)

Criterion 9. For an LMS item reported `remote`:

| Field | Source |
|---|---|
| **Title** | the song's title (`playlist_loop[0].title`, the same as `remoteMeta.title`); if there is none, the station name (`current_title`, trimmed) |
| **Artist** | the song's artist |
| **Album line** | the song's album if it has one (a Qobuz track through LMS is also `remote`); otherwise the station name, unless it is blank or already contains the song title |
| **Artwork** | the song's `artwork_url` (tag `K`), resolved against the LMS base when relative; otherwise **none** — the panel shows "artwork pending" |

George chose the song as the title (option A over the station as title) and
"artwork pending" over LMS's grey radio-tower placeholder. Three shapes are on
record and the rule has to survive all of them: the station name in
`current_title` and the song in the song fields (Finding 029); a blank
`current_title` with the station in the song fields (KissFM, Phase 6); and the
song as "Artist - Title" in `current_title` (2026-09-08,
`docs/HANDOFF-ARCHIVE.md`).

**Built and checked 2026-09-17** (Phase 7 step 2): on TuneIn "Paradiso
Berlin" the panel showed "CRAZY" / "SEAL" / "Paradiso Berlin" and the song's
cover. The station-without-a-song case is covered by tests, not yet seen on
hardware.

**Phase 8** (George asked, 2026-09-17): a station that sends no artwork is a
named case for the enrichment service, which has the artist and song title
but no album or duration, so its confidence rule matters more there.

### 9. Settings (George confirmed 2026-09-17; appended to ADR-0022's inventory)

| Setting | Mark |
|---|---|
| Albums in the New Music strip | [H] — 10, per the design |
| Podcasts excluded from Radio | [H] |
| Radio Now Playing shown | [H] — shown, George 2026-09-17 |
| How long cached library lists are kept | [N] |
| Artwork size requested from LMS | [H] |

The [H] rows are hardcoded as they are built in this phase.

## Rejected

- **Build all eleven of ADR-0030's lists.** Seven have no design, and George
  put them out of scope.
- **Pass SlimBrowse actions from the panel to LMS.** Simpler to build, but it
  would let any device on the network issue LMS commands through `gexis`
  (§5).
- **The core powers LMS on before a load.** Unnecessary, per ADR-0027, and it
  would add the one call that record removed on purpose.
- **Artwork proxied through the core.** ADR-0020 settled this: LMS already
  resizes and caches, and a direct URL degrades gracefully.

## Consequences

- `docs/DEVELOPMENT.md` Phase 7 criterion 1 lists the designed screens instead
  of eleven lists. The queue rail, and Home with the mini strip, are added as
  criteria.
- Criterion 3's "lists of thousands" still applies: 7,292 artists in the grid
  and the Browse artist pane. The 60,974 songs have no designed screen.
- Now playing's Home and Queue buttons are wired, clearing the last
  `phase-7` markers.
- Adding a streaming service still means our own work (ADR-0030); nothing here
  changes that.

## Measured in step 1 — [Finding 029](../findings/029-library-and-radio-against-lms.md)

Everything this record listed as unverified was measured on 2026-09-17 except
the two items at the end.

- **§4 holds.** `playlistcontrol cmd:load` works by album, album artist, track
  and playlist; `cmd:add` adds to the queue without interrupting. On a
  powered-off player LMS powers itself on and the core takes it as an
  ordinary acquisition, also over a playing Spotify session. **But** the
  core then restored a stale position onto the new content (Finding 029
  defect A), fixed as Phase 7 step 1a.
- **Queue origin:** `status` carries `playlist_name`, `playlist_id` and
  `playlist_modified` (0 as loaded, 1 once added to). Absent after an
  album, artist or track load.
- **Add to playlist:** one `playlists edit cmd:add url:<track url>` per
  track; an album or artist is added as its tracks. Library playlists are
  `file:` URLs.
- **Rescan:** a full rescan renumbers every album and artist id; the core
  drops its cache, handles and remembered ids when `serverstatus`
  `lastscan` changes (§6).
- **Radio (§5, §8):** station ids (`item_id`) change on every browse, so a
  handle stores how to re-reach an item, not the id alone; the reply's shape
  depends on the request parameters; station items rely on `base.actions`
  through `goAction`.
- **Criterion 9 has a second shape:** the station name in `current_title`,
  the song in `remoteMeta`, and the song's art in `remoteMeta.artwork_url`
  while the published artwork is LMS's placeholder.

Still open:

- **The root's "stations" count** has no obvious source in the radio tree.
- **Whether CometD pushes a rescan**; `lastscan` polling works regardless.
