# Brief for Claude Design — Lyrion's own menus on the panel (Phase 13f)

Written 2026-10-06 for George to hand to Claude Design. Background, if you
want it: [ADR-0118](../../docs/decisions/0118-lyrion-s-own-menus.md) (every
decision below, with George's words),
[Finding 110](../../docs/findings/110-what-lyrion-s-own-menus-hold.md) and
[Finding 111](../../docs/findings/111-lyrion-menus-measured-for-13f.md) (what
the tree holds, measured). You do not need to read them: this brief carries
what the design needs.

---

**gexis** is a music player for the Raspberry Pi 4 with its own touchscreen
(the "panel"). Its music comes, among other sources, from a **Lyrion Music
Server** (formerly Logitech Media Server). The panel's library screens so far
are **our own**: Home, Browse (three columns), the Artists grid, the artist
page, the album page, Playlists and Radio — each a query we chose and drew
(`design/screens.md` §3–§8).

Lyrion has far more than those: its own library views (Genres, Years, Random
Albums, Popular Artists, Top Tracks…), the user's Favourites, and **apps** —
Qobuz, Spotify (through the *Spotty* plugin), YouTube, Radio Paradise, TIDAL…
— each with its own menus, searches, playlists and albums. Phase 13f puts
**all of it on the panel**, behind a setting (*Extended navigation*, off by
default). It is built and working; **its look is a first pass by Claude
Code, and George wants you to design it properly.**

## What is built today (the starting point, not the target)

- Home's card row gains tiles and scrolls sideways.
- A **generic screen** walks Lyrion's tree one level at a time — the same
  screen for every list, whatever app it comes from.
- Lists are drawn three ways: **grouped tinted cards** (My Music), **the
  design's Radio cards** (three across, a tinted circular disc with a CSS
  glyph — `screens.md` §8) for categories, a **cover grid** for albums and
  playlists, **long rows** for tracks.
- A **list / tiles switch** at the top right of each list, remembered per list.
- Icons and colours were chosen from the Radio palette as a stopgap.

George will share screenshots of the current pass with you separately.

## Keep

- **The design system as it is**: `design/tokens.css`, Nunito Sans and IBM
  Plex Mono, the blurred-weave backdrop, the source accents.
- **The library's navigation** (`screens.md`, *Navigation*): Back always in
  the header; Home beside it below the first level; the mini strip at the
  bottom back to Now Playing.
- **The row-actions rule** (`screens.md`, *Row actions*): no long press
  anywhere; a **leaf row** (a track, a station) reveals Play / Add on its
  first tap and plays on its second; **branch rows** (genres, years,
  categories, folders) have no actions — a tap navigates, and queueing
  happens inside. *(The current pass shows a track's actions all the time —
  that is a mistake of the build, not a proposal.)*
- **Radio's principle** (`screens.md` §8): *"the grid is read by colour and
  silhouette before it is read by word. Two grey shapes for nine categories
  is not a simplification of this, it is a different screen."* George's
  first review of this phase said exactly that about the current pass.
- **No on-screen keyboard.** Typing comes from the user's phone, which acts
  as the panel's touchpad and keyboard (ADR-0121): the panel shows a text
  field, the phone types into it.
- **Pi 4 budget** (`screens.md`, *Motion*): transform and opacity only, one
  region at a time, no cross-fades between screens.

## Where it lives (decided)

**Home's card row**, in this order (George, ADR-0118 A):

**My Music** · Browse · Artists · Playlists · **Favourites** · Radio ·
*(any top category an app adds)* · **Apps** · Settings

- The bold three are new. Browse, Artists, Playlists, Radio and Settings are
  today's and stay as they are.
- A top-level category an app adds to Lyrion in future gets a tile of its
  own **just before Apps**; it needs a generic look.
- **The row scrolls sideways** (George): cards keep today's size, five in
  view and the next peeking at the edge; New Music keeps its height.
- Off (*Extended navigation* not set), Home is exactly as today.

## The tree, as the panel walks it

Measured on George's server 2026-10-06. *Count* is what a typical library
holds — the design must work from a handful to tens of thousands. *First
open* is how long the first page takes; later pages and repeat visits are
fast (10–50 ms).

### My Music — every library view Lyrion offers (21)

Grouped by us into five (a first pass — **regroup or rename freely**):

| Group | Entry | Opens | Count (George's) | Pictures | First open |
|---|---|---|---|---|---|
| **Artists** | All Artists | artists | 8,393 | **none** | 48 ms |
| | Composers | artists | 3,617 | none | 19 ms |
| | Popular Artists | artists, by play count | 121 | almost none | 35 ms |
| | New Artists | artists, newest first | 948 | none | 118 ms |
| | Recently Played Artists | artists | 57 | almost none | 16 ms |
| **Albums** | Albums | albums | 4,780 | covers | 18 ms |
| | Random Albums | albums, shuffled each time | 50 | covers | 33 ms |
| | Compilations | albums | 122 | covers | 11 ms |
| | Works | classical works | 78 | covers | 20 ms |
| | New Music | albums, newest first | 100 | covers | 11 ms |
| | Recently Updated Albums | albums | 100 | covers | 44 ms |
| | Popular Albums | albums, by play count | 100 | covers | 14 ms |
| **Tracks** | Top Tracks | tracks, play count in the title — *"Sogno (189)"* | 536 | covers | 145 ms |
| | Flop Tracks | tracks least played | **65,287** | covers | 335 ms |
| **By category** | Genres | genres | 326 (11 with **no name**) | none | 11 ms |
| | Years | years | 78 | none | 10 ms |
| | Music Folder | folders, then files | 1 at the top | none | 22 ms |
| | Disks and folders | the server's own disks | 6 | none | 11 ms |
| **More** | Search | five searches: Artists, Albums, Works, Songs, Playlists | 5 | none | 8 ms |
| | Library Views | the server's library views | 1 | none | 9 ms |
| | Remote Music Libraries | other servers' libraries | 0 | none | 16 ms |

Inside: an **artist** opens to their albums; an **album** to its tracks; a
**genre** or a **year** to its albums (or artists); a **folder** to folders
and tracks. Each of those can also be played whole.

**Left out by decision** (ADR-0118 C): Album Artists and Playlists (our own
Artists and Playlists screens are those), Playlists Folder (the same
playlists again), and Lyrion's player settings, alarms, sync and power,
which live in the same tree.

### Favourites

The user's Lyrion favourites: any mix of stations, albums, playlists,
tracks, and folders of them. George's is empty today (Lyrion answers with
one text line, *Empty*) — the design needs that state, and a full one.

### Apps

Whatever apps the server has installed — each with its own logo (a square
PNG, colourful). George's six, and what their first level holds:

| App | First level | Below |
|---|---|---|
| **Qobuz** | Search · My Purchases · My Favourites · My Playlists · Qobuz Playlists · Bestsellers · New Releases · In the Press · Qobuz Selection · Genres | lists of up to 200 albums or playlists, **with covers**; first page **0.2–0.7 s** (from the service) |
| **Spotty** (Spotify) | Home · Search · What's New · Top Tracks · Genres and Moods · Popular Playlists · Albums · Artists · Playlists · Podcasts | playlists and albums by the hundred, **with covers**; first page **up to 1 s** (Albums: **8.6 s** once) |
| **YouTube** | 11 different searches (Video, Music, Channel, Playlist, URL…) and three lists | almost everything starts from a search |
| **Radio Paradise** | six mixes and two streams | each mix: its stream in four qualities (FLAC first) |
| **Sounds & Effects** | Alarm Sounds · Musical Sounds · Natural Sounds · Sound Effects | 16–27 short sounds each |
| **TIDAL** | nothing without an account (one unnamed item) | — |

**Left out by decision**: Spotty's *Transfer Playback* (moves playback to
another device), preset buttons, and entries that write to the account —
Qobuz's *Add Release to Qobuz favourites* (J; they come with context menus in
a later iteration).

### An album or playlist page from an app

Lyrion gives **no header**: a Qobuz album page is its tracks, then lines of
text — *Artist: …* (a link), *Credits* (a link), *Genre: Metal*, *Release
Type: Album*, *Duration: 0:46:05*, *Tracks count: 10*, *Released at:
10/02/2026*, *Music Label: …* (a link), *Copyright* (a link). How those
become a page is yours to design (our own album page, `screens.md` §7, is
the obvious reference).

## What each item carries (the data you can design with)

| Field | What it is |
|---|---|
| `label` | the first line — can be **empty** (show as *No name*), can be long |
| `subtitle` | a second line where Lyrion gives one — *artist* under an album, *artist – album* under a track |
| `image` | **a cover** (albums, playlists, tracks), **an app's logo** (apps), or **none**. Lyrion's own stock icons exist but are grey or white silhouettes; the current pass replaces them with our glyphs |
| `kind` | **folder** (opens) · **container** (an album or playlist: opens, or plays whole) · **play** (a track or station) · **search** (asks for text) · **text** (a line, inert) |
| actions | for *container* and *play*: **Play · Play next · Add to queue**, as Lyrion offers them |
| `hint` | what an entry is, when Lyrion says: **genre · year · folder · artist · album · work · app** — enough to give each kind its shape |
| paging | lists arrive 100 at a time as the user scrolls; the total is known from the first page |

## Please design

For the **Standard family** (1280 × 800 logical; `design/source/13b/`'s
rules for 711–853 tall) and the **Bar family** (1280 × 400 and 1480 × 320):

1. **The three new Home tiles** — My Music, Favourites, Apps — and the
   generic tile for a category an app adds: icon and colour each, beside the
   existing five, in the scrolling row.
2. **My Music**: its groups (or another structure you prefer) and its 21
   entries, each with its own shape and colour.
3. **Category lists without pictures** — genres, years, folders — from 6
   entries to 326; and the **unnamed** entry.
4. **Artist lists, with no pictures**, from 57 to 8,393 — do they need the
   Artists grid's letter rail (`screens.md` §5)?
5. **Album and playlist lists with covers**, from 2 to 4,780 — grid, list,
   or both.
6. **Track lists** — Top Tracks, an album's tracks, 65,287 Flop Tracks —
   following the row-actions rule (Play · Play next · Add).
7. **An app's album or playlist page**, with its text lines.
8. **An app's first level** — Qobuz's ten mixed entries, YouTube's eleven
   searches, Radio Paradise's mixes and streams.
9. **Search**: where the field sits when a search entry is tapped, the
   results, and *no results*. Text is typed on the phone.
10. **The list / tiles switch** — whether it stays, its icon, its place.
11. **States**: loading (a service's first page can take a second), empty
    (*Empty*), *nothing here*, the service unreachable.

**Out of scope**: our own screens (Browse, Artists, Playlists, the album and
artist pages, Radio) — unchanged; Settings; context menus (a later
iteration).

## Return

As before: `.dc.html` files under `design/source/13f/`, with every value in
`tokens.css` terms, and a short note of anything that changes a decision
above, for George.
