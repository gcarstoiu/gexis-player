# Finding 030 — Free enrichment providers for Phase 8: what each offers, and what its terms allow

**Date:** 2026-09-17
**Question:** George, 2026-09-17: *"Is MusicBrainz the only provider and the
best one? Give me options with pros and cons. Only look up free APIs."*
ADR-0012 names MusicBrainz and ListenBrainz Labs. Phase 8 criterion 1 is
written around MusicBrainz alone.
**Status:** research for Phase 8. **Nothing is decided here.** The provider
choice needs its own ADR when Phase 8 starts.

**Scope, stated up front:**

- **Desk research, not a build.** Each provider's own documentation and terms
  were read on 2026-09-17, plus a small number of single test calls. No
  lookup quality was measured against George's library. No provider was
  exercised at volume.
- **Not every page could be read on the provider's own site:**
  - Cloudflare blocked (HTTP 403) the Discogs developer docs and every
    fanart.tv page. Discogs' terms were read through a reader proxy; fanart.tv
    only through its GitHub wiki and a test call.
  - The Deezer API docs and the Musixmatch pricing page render in JavaScript
    and gave no text.
  - Where a claim rests on a search snippet, a third-party site, GitHub or a
    single test call, it says so. Those claims are **not verified**.
- **Terms change.** Wikimedia and Spotify both changed theirs in 2026. Recheck
  the chosen providers' terms when Phase 8 starts.
- **Criteria used:** free to use; compatible with ADR-0012's rules (additive
  only, persistent cache including negative results, rate-limited, confidence
  threshold); usable from artist/album/title strings, because Bluetooth
  supplies nothing else.
- **API keys are not a disqualifier.** George, 2026-09-17: a key becomes a
  setting each user enters, never shipped in the image or the repo (ADR-0022
  inventory, Phase 8 group). Where a provider needs a key, how a user gets one
  is recorded instead.
- **Method note.** One Discogs test call sent a personal contact address in
  its User-Agent before generic project strings were used. Phase 8's
  User-Agent must identify the project, not a person.

## Result

**MusicBrainz is not the only free provider, and no single provider covers
every field Phase 8 needs.** MusicBrainz with the Cover Art Archive covers
identity, label, release type, track count and artwork. Biographies,
similar artists, artist photos and lyrics each need a different source.

### Which fields each provider covers

Y = verified · (Y) = present but not verified, or only indirect ·
✗T = the data exists but the terms forbid this use · – = no

| Provider | bio | tags | similar | artist photo | album notes | label | release type | track count | artwork | plain lyrics | synced lyrics |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MusicBrainz + CAA | – (Wikidata link (Y)) | Y (NC-SA) | – | – | (Y) annotation | Y | Y | Y | Y (CAA) | – | – |
| Last.fm | Y | Y | Y | ✗T | (Y) | – | – | (Y) | ✗T | – | – |
| Discogs | Y (profile) | Y (genre/style) | – | Y (restricted) | Y (notes) | Y | (Y) formats | Y | Y (restricted) | – | – |
| TheAudioDB | Y | (Y) | – | Y | Y | Y | (Y) | – | Y | – | – |
| fanart.tv | – | – | – | (Y) | – | – | – | – | (Y) | – | – |
| Wikipedia / Wikidata | Y (CC BY-SA) | (Y) | – | (Y) mixed licences | Y | (Y) | (Y) | – | (Y) often fair use | – | – |
| LRCLIB | – | – | – | – | – | – | – | – | – | Y | Y |
| Deezer | – | Y (genres) | (Y) | (Y) | – | Y | Y | Y | Y (1000 px) | – | – |
| Genius | (Y) | – | – | (Y) | (Y) | – | – | – | – | ✗T | – |
| Musixmatch | – | Y (genres) | – | – | – | – | – | – | (Y) | Y (Basic) | Y (Grow, paid) |
| ListenBrainz | – | Y | Y (needs MBIDs) | – | – | – | – | – | – | – | – |
| AcoustID | – | – | – | – | – | – | – | – | – | – | – |
| Spotify | – | (Y) | ✗ removed | (Y) | – | ✗ removed | (Y) | (Y) | Y (temporary cache only) | – | – |
| iTunes Search | – | Y | – | – | – | – | – | Y | ✗T | – | – |

### Usable options, by field

| Field | Option | For | Against |
|---|---|---|---|
| **Identity, label, release type, track count** | **MusicBrainz** | No key. Core data CC0. Lucene search returns a 0–100 score, which suits the confidence threshold. Its IDs unlock CAA, ListenBrainz, fanart.tv and Wikidata | 1 request/s per IP; above that **every** request gets 503. Tags, genres and annotations are CC BY-NC-SA 3.0. No bio, photos or lyrics |
| **Artwork** | **Cover Art Archive** | No key; "no rate limiting rules in place"; 250, 500, 1200 px or original | Needs a MusicBrainz release or release-group ID first. Images stay copyrighted by their owners |
| | Deezer | No key for reads (test calls); covers to 1000 px; also label, `record_type`, `nb_tracks`, genres; name search works | Terms: personal, non-commercial, "strictly private use within a family scope"; access removable without notice; caching not addressed; quota exists but no number published (50 per 5 s from secondary sources only) |
| **Biography** | **Wikipedia** REST summary | No key. 200 requests/min with a compliant User-Agent (10/min without) | CC BY-SA 4.0: link the article, share-alike. Weak on ambiguous names unless reached through MusicBrainz → Wikidata. `api.wikimedia.org` is being retired (portal sunset June 2026, Core API deprecated July 2026 – June 2027); `en.wikipedia.org/api/rest_v1/page/summary` answered 200, no sunset date found |
| | Last.fm `artist.getInfo` | Bio, tags, similar artists in one call; `autocorrect` for messy names; `lang` parameter | Per-user key (Last.fm login required). Non-commercial only. "Powered by AudioScrobbler" and links back required. Clause 2.7: public pages need written approval. Stored data capped at 100 MB. No published rate limit. Bio text licence not verified |
| **Similar artists** | **ListenBrainz** Labs | Free; MusicBrainz IDs | 1 call/s; Labs endpoints carry no stability promise. Name → ID lookup (`/1/metadata/lookup`) needs a user token |
| | Last.fm | As above | As above |
| **Artist photos** | fanart.tv | Good imagery keyed by MusicBrainz ID; personal key free | fanart.tv prefers a developer project key, and asks developers not to make end users get their own. Images appear 7 days late on a project key, 2 on a personal one. Terms and rate limits not verified (site blocked) |
| | Wikipedia image | No key | Licence per image; some are fair use that does not transfer |
| **Lyrics, plain and synced** | **LRCLIB** — the only free synced source found | No key or registration. Plain and LRC-synced, plus an `instrumental` flag. Active: server commit 2026-08-06, docs 2026-07-22 | **No licence stated for the lyrics.** `/api/get` needs track, artist, album **and duration within ±2 s**, which Bluetooth often lacks; `/api/search` works without duration but returns at most 20, unpaged. No published rate limit; 429 with `Retry-After`, which must be honoured or the client is banned. User-Agent must name app, version and homepage |

### Ruled out, and why

| Provider | Disqualifier |
|---|---|
| Discogs | Terms (updated 27 May 2025): content may not be shown if more than 6 hours older than on Discogs, nor cached longer than necessary. Conflicts with ADR-0012's persistent cache. Images are restricted data |
| Spotify Web API | Development-mode apps need the owner to hold Premium (from February 2026): not free. Only temporary caching of metadata and cover art. Related Artists removed (November 2024), album `label` removed (February 2026) |
| Genius | The API returns no lyrics text, and the site terms forbid scraping |
| Musixmatch | Synced lyrics on a named paid plan; written approval before public pages (2.1.4); forbids karaoke use (2.2.13); whether any plan is free not verified |
| TheAudioDB | Free key `123` is for development projects; a personal key costs $8/month |
| Last.fm, for images | Terms exclude images and artwork. Its bios and tags remain usable |
| iTunes Search | Album art only "for promoting store content", beside iTunes badges |
| AcoustID | Needs an audio fingerprint; no lookup by artist, album or title |

## Consequences for Phase 8 (not decisions)

- **Phase 8 criterion 1 assumes one provider.** With several, "a single
  shared token bucket" becomes one bucket per provider, each shared across
  the service: MusicBrainz 1/s, ListenBrainz 1/s, Wikipedia 200/min, LRCLIB
  unpublished (serial, 200–500 ms apart, honour `Retry-After`).
- **ADR-0012's Sources section** names MusicBrainz and ListenBrainz only. The
  Phase 8 provider ADR supersedes or extends it.
- **Attribution has to be designed.** Wikipedia (CC BY-SA link), MusicBrainz
  tags (NC-SA), Last.fm (badge and links) and fanart.tv each ask for
  something on screen. The designs carry no attribution element today.
- **A key-free combination exists** for everything except artist photos:
  MusicBrainz + Cover Art Archive, Wikipedia via MusicBrainz → Wikidata,
  ListenBrainz, LRCLIB. Recommended to George on 2026-09-17 as the starting
  point; **not decided**.
- **Artist photos are the gap.** fanart.tv is the only good source, and its
  own guidance prefers a project key over per-user keys.
- **Lyrics without duration** (Bluetooth) fall back to LRCLIB search, which
  is weaker; it needs a confidence rule of its own.
- **Do not key the cache on LMS ids.** A full LMS rescan renumbers every
  album and artist id (Finding 029, 2026-09-17). ADR-0012 already keys on
  (artist, album, title, duration), which survives that.

## Sources read

- **MusicBrainz / CAA:** musicbrainz.org/doc/MusicBrainz_API, …/Rate_Limiting,
  …/Search, …/About/Data_License, …/MusicBrainz_Database,
  …/Cover_Art_Archive/API; coverartarchive.org
- **Last.fm:** last.fm/api, last.fm/api/tos, last.fm/api/show/artist.getInfo,
  last.fm/api/account/create
- **Discogs:** support.discogs.com API Terms of Use (via reader proxy);
  api.discogs.com test calls. discogs.com/developers blocked
- **TheAudioDB:** theaudiodb.com/free_music_api, theaudiodb.com/docs_terms_of_use.php
- **fanart.tv:** github.com/fanart-tv/fanartwiki (personal API key page),
  github.com/fanart-tv/fanart.tv-api README, webservice.fanart.tv test call
- **Wikimedia:** mediawiki.org/wiki/Wikimedia_APIs/Rate_limits,
  …/Access_policy, mediawiki.org/wiki/API:REST_API/Changelog,
  wikitech.wikimedia.org/wiki/API_Portal/Deprecation,
  wikidata.org/wiki/Wikidata:Licensing,
  en.wikipedia.org/wiki/Wikipedia:Reusing_Wikipedia_content, summary test call
- **LRCLIB:** docs source `src/docs/api.md` in tranxuanthang/lrclib-homepage;
  github.com/tranxuanthang/lrclib (ARCHITECTURE.md, commits)
- **Deezer:** developers.deezer.com/termsofuse, …/guidelines, Deezer FAQs For
  Developers, api.deezer.com test calls
- **Genius:** docs.genius.com, genius.com/static/terms
- **Musixmatch:** docs.musixmatch.com (getting-started, implementation
  guidelines, checklist, content restrictions, API reference pages),
  about.musixmatch.com/apiterms
- **ListenBrainz:** listenbrainz.readthedocs.io API pages (index, metadata,
  core, misc, recommendation), labs.api.listenbrainz.org,
  metabrainz.org/social-contract
- **AcoustID:** acoustid.org/webservice, acoustid.org/new-application
- **Spotify:** developer.spotify.com February 2026 migration guide, 2024-11-27
  Web API changes post, developer.spotify.com/terms, /policy
- **iTunes Search:** performance-partners.apple.com/search-api
