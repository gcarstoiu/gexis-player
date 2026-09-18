# Finding 035 — What LMS's Music & Artist Information plugin already answers

**Date:** 2026-09-18
**Question:** George, when the Phase 8 provider decisions were put to him:
*"doesn't LMS already have artist photos? couldn't we cover some of it from
there directly?"*
**System:** George's LMS 9.1.1 at `192.168.178.188:9000`, probed read-only
from `gexis`. The server reports `Plugins have been updated - Restart
Required (Music and Artist Information)`.

**Scope:** one server, one plugin, four artists plus one id that does not
exist. Read-only HTTP and JSON-RPC; nothing was installed, changed or
restarted. This records **what that server answers**, not what every LMS
answers — the plugin is optional and a server without it answers none of
this.

## Result

**Yes, and it is more than photos.** The answers do not come from core LMS
but from the **Music & Artist Information** plugin (`musicartistinfo`),
which is installed there.

### Artist photos

```
["musicartistinfo","artistphoto",0,1,"artist_id:7452"]
  -> {"artist_id":"7452","url":"imageproxy/mai/artist/7452/image.png"}
```

Fetched, and **different per artist**, with a distinct image for an id that
does not exist:

| artist_id | `image_200x200_o.png` |
|---|---|
| 7452 (2 Unlimited) | 93,939 b |
| 12316 (Rod Stewart) | 62,997 b |
| 999999 (no such artist) | 6,944 b — the plugin's own placeholder |

### Biographies

```
["musicartistinfo","biography",0,1,"artist_id:7452"]
  -> {"artist_id":"7452","biography":"2 Unlimited are a Belgian-Dutch dance
      music act, founded by Belgian producers/songwriters ..."}
```

### Ask for JPEG, not PNG

Same image, same size on screen:

| URL | Type | Bytes |
|---|---|---|
| `image_200x200_o.png` | PNG | 93,939 |
| `image_200x200_o.jpg` | JPEG | 17,999 |
| `image_500x500_o.jpg` | JPEG | 83,101 |

The same lesson as the album artwork ladder (ADR-0038 §7, Phase 7a step 1):
the bare or PNG form is several times the JPEG's size for no visible gain.

## The trap, checked first

**`/music/artist_<id>/cover_200x200_o.jpg` looks like it works and does
not.** It answers `200` with a 10,697-byte PNG — **byte-identical for every
artist tried, including `artist_999999`**:

| artist_id | md5 (first 12) | bytes |
|---|---|---|
| 7452, 12316, 12272, 7453, **999999** | `e62718c29078` | 10,697 |

It is LMS's generic placeholder. This is the shape that produced the grey
radio tower George saw in Phase 7 (ADR-0038 §8a): a placeholder served with
`200` reads as success, and an image that is "there" for an artist that does
not exist is the only tell.

## What this does not say

- **Nothing about servers without the plugin.** It is optional; a device
  pointed at one that lacks it gets none of the above. Phase 8 therefore
  detects it at runtime and falls back (ADR-0040, George's call: a bonus
  when present, never a requirement).
- **Nothing about where the plugin's own data comes from**, what it caches,
  or under what licence. It fetches from third parties itself; that is the
  server owner's arrangement rather than this project's.
- **Nothing about Spotify or Bluetooth.** These are LMS ids; the other two
  renderers have none, so their enrichment comes from Phase 8's own
  providers.
- **Not measured:** how long a first (uncached) photo or biography takes,
  what the plugin answers for an artist it has never looked up, or whether
  `artistphoto` can say "no photo" distinctly rather than returning a
  placeholder URL. All three matter for the confidence rule and are Phase 8
  work.
