# Finding 086 — What the Plex server could answer that the internet answers today

**Date:** 2026-09-25
**Question:** George, after Phase 11: *"what does plexamp or Plex expose via
their API… Anything that can reduce the dependency on internet providers is a
good thing. They can be kept as fallbacks, not removed."* So: what is actually
there, how much of **this** library does it cover, and is it better than what we
fetch now?
**Scope:** George's own Plex Media Server at `192.168.178.191:32400`, read with
Plexamp's token, and the daemon's own `enrichment.db` (3,734 rows) as the record
of what has really been asked. **Nothing was built.** Counts are that server's
answers today; coverage is measured against the artists this device has looked
up, not against the whole LMS library, which was switched off.

## What is there

**Plexamp's player API (`:32500`) has none of this.** It reports *what is
happening* — state, position, volume, shuffle, repeat, and which server the
music is on. Everything below is the **server**.

| | |
|---|---|
| Artist | `summary` (a full biography), `thumb`, `art`, **Genre**, **Style**, **Mood**, **Country**, **Similar** (up to 30 artists), **UltraBlurColors** (four corner colours) |
| Album | cover, `art`, review `summary`, year, and Plex's own grouping: *Singles & EPs, Live Albums, Soundtracks, Compilations, Demos, Remixes* |
| Track | `/nearest` — **sonic similarity with a distance**, and `musicAnalysisVersion` to say the analysis has run |
| File | `bitDepth`, `samplingRate`, `codec`, and **ReplayGain**: `gain`, `peak`, `albumGain`, `albumPeak`, `loudness` |
| Library | 21 genres, 444 styles, 294 moods, 32 countries, 80 years; five smart playlists; `/hubs/search` |

**Not there:** `popularLeaves` answers **404** on this server, and
`includePopularLeaves=1` adds nothing — so popular tracks look like a
plex.tv/Discover feature rather than a local one. A **lyrics** stream exists on
the track's Part (`streamType=4`, provider `com.plexapp.agents.lyricfind`) and
fetching `/library/streams/<id>` returned 1,782 bytes of **plain, untimed**
text; **a second attempt the same evening returned 404 and that is unexplained.**

## How much of this library it covers

```
  plex artists: 507
  distinct artists the daemon has looked up: 855
  of those, Plex has: 442  (51.7%)
```

**About half**, and that is a floor: the match is one folding rule (case,
accents, a leading article, punctuation), so some of the 413 misses are names
Plex spells differently rather than does not have.

## Where it is better, and it is better by a lot

For the artists and albums it *does* know, Plex is more complete than every
internet provider we ask — measured on the same library, from the same
database:

| what | the internet, today | Plex |
|---|---|---|
| Album cover | **50 %** (Cover Art Archive), 47 % (recording art) | **100 %** — 3,908 of 3,908 |
| Artist picture | **61 %** (fanart.tv, needs a key) | **100 %** — 507 of 509 |
| Artist background | **61 %** (fanart.tv) | **87 %** |
| Biography | **73 %** (Wikipedia) | **97 %** |
| Similar artists | **80 %** (ListenBrainz) | 59 of the first 60 artists carry them |
| Album review | nothing asks for one | 74 % |

**Cover art is the headline.** Half of album-cover lookups fail today, for
albums George owns the files of — and the server that holds those files has a
cover for **every single one**.

## What is *not* an argument, and was assumed to be

**Speed.** Five runs each, from the device:

```
  Plex artist by name        87-143 ms
  Plex similar artists      169-305 ms
  Plex sonic nearest        120-249 ms
  musicbrainz artist search     113 ms
  wikipedia summary             110 ms
  lrclib search                 112 ms
```

**The internet providers are as fast.** Finding 036's 5.3 s MusicBrainz lookup
was not typical of this evening. Anyone planning this work on the assumption
that local means faster is planning against a number that is not there.

What *is* real about cost: `providers.py` rate-limits MusicBrainz to **1.1
requests a second** by its own constant, and fanart.tv and ListenBrainz need a
per-user key that ADR-0022 inventories and George had to obtain. A Plex server
has neither limit.

## Things nothing in this project supplies today

- **Sonic similarity with a distance** — `/nearest` on a track or artist.
  Plexamp's own "sonic" features use it; nothing here has an equivalent.
- **Moods and styles** — 294 and 444 of them across the library.
- **ReplayGain per track and per album**, already computed.
- **UltraBlurColors** — four corner colours per artist, which is what the
  panel's Now Playing wash approximates by hand.

## What this does not establish

- **Nothing about availability.** The server is another machine on the LAN. If
  it sleeps, so does this. Nothing here measured how often it is up.
- **Nothing about a second token.** The core would need Plex credentials of its
  own; today the only one on this device belongs to the Plexamp plugin, and the
  core reading a plugin's private files would be the coupling ADR-0016 exists to
  avoid.
- **The 51.7 % is one folding rule**, not a matching strategy. A real one would
  use MusicBrainz ids where both sides have them.
- **The LMS library was off**, so the comparison is against what the daemon has
  looked up (855 artists), not against the 917 the panel reports.
