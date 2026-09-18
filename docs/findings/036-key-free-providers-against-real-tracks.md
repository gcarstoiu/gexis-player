# Finding 036 — The key-free providers, asked for real tracks

**Date:** 2026-09-18
**Question:** Phase 8 step 1. [ADR-0040](../decisions/0040-enrichment-providers.md)
chose these providers from their documentation and terms
([Finding 030](030-free-enrichment-providers.md)); nothing had yet asked any
of them for a track from George's library.
**System:** run from `gexis` (the device's own IP, which is what the daemon
will use), against albums and tracks drawn at random from George's LMS.
User-Agent `gexis-player/0.2 ( https://github.com/gcarstoiu/gexis-player )`
throughout, per MusicBrainz's and LRCLIB's rules.

**Scope:** 5 albums and 4 tracks, one session, about 30 requests in total —
enough to see whether each provider answers at all and roughly how fast, and
**not** enough to characterise reliability or rate limits under sustained
load. Read-only: nothing was written anywhere.

## Result

**All four answer, and one of them is unreliable.**

### MusicBrainz: lookups are solid, *search* is not

| call | result |
|---|---|
| `/ws/2/release-group/?query=…` (album search) | 3 of 5 answered 200 with `score: 100` for the right release group; **2 answered 503** |
| `/ws/2/recording/?query=…` (track search) | 2 of 4 answered 200 with `score: 100`; **2 answered 503**, and a retry 2 s later also 503 |
| `/ws/2/artist/<mbid>` (lookup by id) | **4 of 4 answered 200**, spaced 2 s apart: 213 ms, 5,282 ms, 28 ms, 31 ms |

The 503 body is **not** the rate-limit message:

```
{"error": "The MusicBrainz web server is currently busy. Please try again later."}
```

Requests were spaced at least 1.1 s apart per host, above the documented
1 request/s, and the failures were on the Lucene search endpoint rather than
on lookups.

**What this means for the implementation, and it is the most important line
in this finding: a 503 must never be cached as "nothing found".** ADR-0012
caches negative results so a miss is not retried forever; if a busy server's
503 lands in that cache, an album gets no enrichment permanently because the
server was busy once. "Not found" and "could not ask" have to be different
states.

The one 5.3 s lookup also says the timeout must be generous and the fetch
must never be on a screen's path.

### Cover Art Archive: works, and is slow

`/release-group/<mbid>` answered 200 with one image each time, in **949 ms,
1,521 ms and 1,850 ms**. No key, no rate limit hit.

### Wikipedia, reached through Wikidata: works

MusicBrainz's artist lookup carries a `wikidata` relation for every artist
tried (3 of 3). Then:

- `wikidata.org/w/api.php … sitefilter=enwiki` → `enwiki: "AC/DC"`, 297 ms
- `en.wikipedia.org/api/rest_v1/page/summary/AC%2FDC` → 200 in 116 ms, a
  441-character extract

No `api.wikimedia.org` involvement, so the sunset Finding 030 flagged does
not apply to this path.

### ListenBrainz: similar artists work without a token, with a catch

- `/1/metadata/lookup` → **401, "You need to provide an Authorization
  header."** As Finding 030 predicted. So name → MBID resolution has to come
  from MusicBrainz, not from here.
- `labs.api.listenbrainz.org/similar-artists/json` → **200 in 255 ms, 100
  artists with scores** for AC/DC (Queen 8322, Led Zeppelin 8000, Guns N'
  Roses 7652, …). No token.

**The catch:** `algorithm` is a required enum, and the value in
ListenBrainz's own older examples — the one tried first — is **rejected**:

```
value is not a valid enumeration member; permitted:
 'session_based_days_1825_…_skip_30', 'session_based_days_7500_…_skip_30', …
```

The error helpfully lists the permitted values, so a client can recover by
reading them, but this is a Labs endpoint with no stability promise and the
enum has already changed once. It needs to fail softly: no similar artists
is a missing section, not an error on screen.

Similar artists also need the **artist MBID**, which comes from MusicBrainz —
so this feature inherits the search flakiness above.

### LRCLIB: the most reliable of the four

Four real tracks, `/api/get` with artist, track, album and duration:

| track | synced | plain |
|---|---|---|
| Morcheeba — Almost Done | yes | yes |
| 2Pac — All Out | yes | yes |
| Jimi Hendrix — 51st Anniversary | yes | yes |
| John Williams — A New Home (soundtrack) | no | no |

55–350 ms. The search fallback (`/api/search`, no duration) returned 16–20
hits each time, of which the synced ones were 0, 8, 16 and 19 — so **the
fallback's top hit is not automatically the right one**, and the confidence
rule ADR-0040 §3 asks for is genuinely needed rather than a formality.

## What this does not say

- **Nothing about reliability.** About 30 requests in one session. The 503s
  may be a bad hour for MusicBrainz or may be routine from this IP; that
  needs days, not minutes.
- **Nothing about sustained rate limits.** Every call here was spaced by the
  probe. Whether the daemon's limiters hold under a real listening session
  is Phase 8 step 2's to test.
- **Nothing about Spotify or Bluetooth**, whose metadata is often messier
  than LMS's tags — no album, no duration, and stream text that is not
  always a song.
- **No cost measured for a first, uncached lookup** on LMS's own plugin
  (Finding 035 leaves the same gap).
