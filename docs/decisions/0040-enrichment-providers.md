# ADR-0040 — Enrichment providers: LMS first where it can answer, a key-free set behind it

**Status:** Accepted — George read it and opened Phase 8, 2026-09-18
**Date:** 2026-09-18
**Raised by:** Phase 8 (enrichment and lyrics); decisions taken with George
2026-09-18
**Amends:** [0012](0012-enrichment-service.md) — its Sources section names
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
| Similar artists | ListenBrainz | 1 call/s |
| Lyrics, plain and synced | LRCLIB | None published; serial, honour `Retry-After` |

**Rejected:** Last.fm (per-user key, non-commercial only, written approval
for public pages), Discogs (may not cache longer than necessary — conflicts
with ADR-0012's persistent cache), Spotify (development mode needs Premium
from February 2026), Genius, Musixmatch, TheAudioDB, iTunes, AcoustID. Each
disqualifier is in Finding 030.

**fanart.tv is not used.** It was the only good key-free-ish source for
artist photos, and §1 removes the need: where LMS answers we use it, and
where it does not the artist page keeps its initials (George chose this over
a per-user key).

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
