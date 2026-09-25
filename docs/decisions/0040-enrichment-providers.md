# ADR-0040 — Enrichment providers: LMS first where it can answer, a key-free set behind it

**Status:** Accepted — George read it and opened Phase 8, 2026-09-18
**Date:** 2026-09-18
**Raised by:** Phase 8 (enrichment and lyrics); decisions taken with George
2026-09-18
**Amends:** [0012](0012-enrichment-additive-only.md) — its Sources section names
MusicBrainz and ListenBrainz only. This replaces that list and leaves its
rate-limiting, caching and confidence rules standing.
**Builds on:** [0020](0020-library-browse-tree.md) (artwork comes straight
from LMS), [0022](0022-settings.md) (a key, if one is ever needed, is a
per-user setting), [0038](0038-library-and-radio-on-the-panel.md) §7 (ask for
the size drawn, as JPEG)
**Evidence:** [Finding 030](../findings/030-free-enrichment-providers.md)
(free providers, field by field, with their terms),
[Finding 035](../findings/035-lms-artist-information-plugin.md) (what
George's LMS already answers)

## Context

Phase 8 fills the Artist, Release and Lyrics tabs on now playing and gives
radio stations artwork. ADR-0012 assumed one provider; Finding 030 found
that no free provider covers the fields the design draws, and that a
**key-free combination** covers all of them except artist photos.

Then George asked whether LMS already had the photos. It does — not core
LMS, but the **Music & Artist Information** plugin on his server, which
answers both artist photos and biographies (Finding 035). That changes the
shape of the phase: for LMS, the work is often to *render* rather than to
fetch.

## Decision

### 1. LMS first where it can answer, our own providers behind it

George, 2026-09-18. When the active renderer is LMS and the
`musicartistinfo` plugin answers, that answer is used. Otherwise — and
always for Spotify and Bluetooth, which have no LMS ids — the providers in
§2 answer.

**Why.** It is the same data by a shorter route: no rate limit to respect,
no User-Agent policy, no key, and the licence arrangement is the server
owner's rather than this project's. It also closes the artist-photo gap
that had no good key-free answer.

**The plugin is a bonus, never a requirement** (George, 2026-09-18). It is
detected at runtime by asking it; a server without it is not an error and
not a warning. Phase 7's initials remain the fallback for a missing photo.

**Two things measured that this depends on** (Finding 035):

- `/music/artist_<id>/cover` is **not** artist artwork. It answers `200` with
  LMS's generic placeholder, byte-identical for every artist including one
  that does not exist. Only the plugin's `artistphoto` URL is real.
- Ask the plugin for `.jpg`: at 200×200 the PNG is 93,939 bytes and the JPEG
  17,999, for the same picture. ADR-0038 §7's ladder applies here too.

### 2. The key-free set

George, 2026-09-18, from Finding 030's comparison. Nothing here needs
registration, a key, or a per-user setting.

| Field | Provider | Limit to respect |
|---|---|---|
| Identity, label, release type, track count | MusicBrainz | **1 request/s per IP**; above it *every* request gets 503 |
| Album and track artwork | Cover Art Archive | No published limit; needs an MBID first |
| Biography | Wikipedia REST summary, reached through MusicBrainz → Wikidata | 200/min with a compliant User-Agent |
| Similar artists | ListenBrainz Labs `similar-artists` | 1 call/s |
| What an artist is played for | ListenBrainz `popularity/top-recordings-for-artist` | 1 call/s, **and a token since 2026-09-18** |
| Lyrics, plain and synced | LRCLIB | None published; serial, honour `Retry-After` |

**Rejected:** Last.fm (per-user key, non-commercial only, written approval
for public pages), Discogs (may not cache longer than necessary — conflicts
with ADR-0012's persistent cache), Spotify (development mode needs Premium
from February 2026), Genius, Musixmatch, TheAudioDB, iTunes, AcoustID. Each
disqualifier is in Finding 030.

**fanart.tv is used after all, for pictures only** (George, 2026-09-18,
reversing his earlier choice once LMS's plugin was in and he could see what
it looked like). A per-user key, `fanart_key` in ADR-0022's inventory; with
none the provider is not *ready* and nothing changes.

**Pictures before LMS, text after it.** The speed was measured first, at
George's instruction, and it qualifies the approach rather than simply
endorsing it:

| artist | fanart | LMS's plugin (warm) | fanart's image |
|---|---|---|---|
| Rod Stewart | 614 ms | 18 ms | 705 KB |
| 2 Unlimited | 169 ms | 9 ms | 247 KB |
| Gary Moore | 1,065 ms | 12 ms | 353 KB |
| Red Hot Chili Peppers | 721 ms | 13 ms | 246 KB |
| Andreas Bourani | 751 ms | 14 ms | 826 KB |

Fanart had a picture for all five, which is the case for using it. It is
also **13-80× slower** and serves the **original**, which is the case for
two limits on where it is used:

- **Its pictures go through LMS's image proxy**, the same route the
  plugin's own remote pictures take: 705 KB became 32.8 KB at 300px on
  hardware. Phase 7a step 1 existed to stop exactly the first number.
- **The artist grid still asks LMS by id.** 917 artists at 9-18 ms each and
  no MusicBrainz involved; through fanart each one would need an MBID
  resolved first, against the endpoint that answers 503 most often. Fanart
  is for the screens with one artist on them.

**Measured against real tracks afterwards**
([Finding 036](../findings/036-key-free-providers-against-real-tracks.md),
Phase 8 step 1), three things that change how these are used:

- **A 503 is not "nothing found".** MusicBrainz's *search* answered
  `{"error": "The MusicBrainz web server is currently busy…"}` for 4 of 9
  searches, retries included, while lookups by MBID answered 4 of 4. ADR-0012
  caches negative results; a busy server's 503 landing in that cache would
  deny an album its enrichment permanently. **"Not found" and "could not
  ask" are different states, and only the first is cached.**
- **ListenBrainz's name → MBID lookup needs a token** (401), so MBIDs come
  from MusicBrainz. Its Labs `similar-artists` endpoint works without one,
  but `algorithm` is an enum that has already changed: the value in
  ListenBrainz's own older examples is rejected today. **No similar artists
  is a missing section, never an error on screen.**
- **LRCLIB's search fallback needs the confidence rule to be real.** Of 16-20
  hits per track, the synced ones were 0, 8, 16 and 19 - the top hit is not
  automatically right.

**Amended 2026-09-18: one key after all.** ListenBrainz's popularity
endpoint - the artist page's *Popular* list - answered `200` with 878
recordings in the morning and `401 "Due to bad actors and AI scrapers
causing undue traffic on our sites, you need to provide an Auth token for
this endpoint"` in the afternoon. George chose a **per-user token**
(ADR-0022's inventory, `listenbrainz_token`) over dropping the section or
redefining it as local play counts, which LMS cannot supply without a
statistics plugin. **Nothing else here needs a key**, and with no token the
section simply does not draw: a missing token is `UNAVAILABLE`, never
"this artist has no popular tracks".

### 3. Lyrics: synced, from LRCLIB, with the licence question stated

George, 2026-09-18: ship synced lyrics. **LRCLIB states no licence for the
lyrics themselves.** What is being accepted is that a personal device
displays them to the person sitting in front of it and redistributes
nothing. This is recorded here rather than buried, because it is the one
provider whose terms we cannot point at.

Their rules we do keep: a User-Agent naming the application, its version and
its homepage; serial requests; and `Retry-After` honoured, since ignoring it
is what gets a client banned.

**Without a duration** — Bluetooth often has none — `/api/get` cannot be
used (it wants track, artist, album and duration within ±2 s). The fallback
is `/api/search`, which returns at most 20 unpaged results and needs a
confidence rule of its own (ADR-0012's threshold: below it, show nothing).

### 4. Attribution is a line on the panel, beside what it credits

George, 2026-09-18. Wikipedia text is CC BY-SA and MusicBrainz tags are
CC BY-NC-SA: both require visible credit. A quiet source line sits under the
biography and under the lyrics — *"From Wikipedia, CC BY-SA"* — naming the
provider and linking where a link is required.

Not a credits screen in Settings: CC BY-SA expects attribution **with** the
content, and a separate screen is a weaker reading of it. The designs carry
no attribution element today, so this one is designed here rather than taken
from `design/`.

### 5. One limiter per provider, not one shared bucket

ADR-0012 criterion 1 says "a single shared token bucket", which assumed a
single provider. With five, it becomes **one bucket per provider**, each
shared across the service, at the rates in §2. Everything else in ADR-0012
stands: persistent cache including negative results, never overwrite what
the renderer said, a confidence threshold, and now playing renders before
enrichment returns.

**The cache is not keyed on LMS ids.** A full rescan renumbers every album
and artist id (Finding 029). ADR-0012 already keys on (artist, album, title,
duration), which survives one.

## Consequences

- **Two paths to keep honest.** The panel must look the same whether LMS's
  plugin or our own providers answered, and the attribution line must name
  whichever actually did.
- **A returned URL is evidence of a photo** — measured after George
  restarted LMS (Finding 035): for an id that does not exist, both commands
  answer `{"error": "I'm sorry, didn't find any relevant information."}`
  rather than a placeholder URL. Six random artists all answered with real,
  distinct images, 10–19 KB as JPEG at 200 px, 32–76 ms. The
  `/music/artist_<id>/cover` placeholder remains the trap; the plugin's own
  commands do not have it.
- **Biographies are the slow half**, 386–1005 ms against 9–23 ms for a photo
  URL, and every artist tried may already have been cached on that server. A
  first lookup is unmeasured, so Phase 8 treats all of these as slow: fetch
  off the screen's path, never block a render.
- **Spotify and Bluetooth get the longer route**, so their enrichment is
  slower and subject to the rate limits. Now playing renders first
  regardless (ADR-0012).
- **Phase 8 adds work to a panel that already drops frames** while music
  plays (Finding 034). Enrichment must not make the running panel busier:
  fetch off the panel, publish once, and let Phase 9 judge the result
  against 034's baseline.

## Alternatives considered

- **Our providers first, LMS as fallback** — one source of truth across all
  three renderers, so a track reads the same on Spotify as on LMS. Rejected
  by George: more external calls and more rate-limit exposure for a
  consistency the listener rarely sees.
- **LMS only in Phase 8** — much smaller, but Spotify and Bluetooth would
  keep bare now playing and the tabs would stay empty for them.
- **Last.fm** — one call for bio, tags and similar artists, with autocorrect
  for messy names. Rejected: a per-user key for a device whose whole setup
  story is "no keys", plus badge and link obligations.
