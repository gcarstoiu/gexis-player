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

**Create playlist is not in Phase 7** (George, 2026-09-17). It needs a name
typed on the panel, which ADR-0029 allows only with a USB keyboard, in a text
sheet the design describes but does not draw. Add to playlist picks an
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

**To verify in step 1**, not assumed: that `playlistcontrol cmd:load` takes the
same auto-power-on path as `play` does.

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

### 6. Lists are cached in memory

List pages are cached in the core's memory (ADR-0020, "cached aggressively in
RAM"). How long an entry is kept is a setting (§8). A library rescan
invalidates the cache when LMS reports one. Whether the existing CometD
subscription delivers that is measured in step 1.

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

The bare resize returns a PNG twice the size of the original. One album, one
size. The strip's thumbnails will ask for more, so step 1 repeats this across
albums.

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

## Unverified — measured in step 1 (Finding 029) before building on it

- `playlistcontrol cmd:load` by album, artist, track and playlist; `cmd:add`
  for the queue; auto-power-on from a `load` while Spotify plays (§4).
- **Add to playlist:** which command adds an album, artist or track to a saved
  playlist.
- **Which artists the grid and Browse list.** All Artists (7,292) or Album
  Artists (916). The design says "Artists". Brought to George with the
  measurement.
- **Folded filing:** whether LMS's `textkey` already files "The Beatles" under
  B and "Ándra" under A. `ignoredarticles` is "The El La Los Las Le Les".
- **Release types** for the discography, and track durations for the album
  page, and what each costs in round trips.
- **Page costs:** a page of albums and a page deep into 7,292 artists.
- **The root's counts:** albums, artists and playlists are typed counts. The
  design's "stations" count has no obvious source in the radio tree.
- **The radio tree below its first level:** item shapes, `nextWindow`, play
  actions, four levels deep.
- **The queue's "came from" playlist**, and whether a rescan arrives over
  CometD.
