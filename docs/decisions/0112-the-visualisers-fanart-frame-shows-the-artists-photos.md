# ADR-0112 — The visualiser's fanart frame shows the artist's photos

**Status:** **Proposed** — George decided to do it (2026-10-02: *"Fanart -
yes, we do it"*); the choices under *For George* are open.
**Phase:** 13b ([DEVELOPMENT.md](../DEVELOPMENT.md)), with ADR-0111's packs.
**Builds on:**
- [ADR-0111](0111-skin-sets-follow-the-screen.md) (the packs that carry the
  fanart skins);
- [ADR-0040](0040-enrichment-providers.md) and [Finding 035](../findings/035-lms-artist-information-plugin.md)
  (LMS's Music & Artist Information plugin, which the player already asks
  for one photo per artist);
- [Finding 108](../findings/108-how-many-photos-an-artist-has-for-a-slideshow.md)
  (how many photos it has).

## Context

72 skins in the packs reserve a frame for the playing artist's photos: 20 at
1280×800 and 52 at 1920×1080 (upstream's *Fanart* skins). Upstream, the
Volumio plugin fills it with a slideshow, from the artist's folder,
fanart.tv and Volumio's metadata service. Each skin says only where the
frame is and how a photo sits in it:

| Key | Values in the packs | Meaning upstream |
|---|---|---|
| `fanart.pos`, `fanart.dimension` | the frame | |
| `fanart.scale` | `fit` (all 20 at 1280×800) | preserve the aspect, or `stretch` |
| `fanart.zorder` | `background` (19), `overlay` (1) | behind the meters, or over them |

Interval, order and transition are the plugin's global settings, not the
skin's. Our renderer draws none of this today: the frame shows whatever the
skin's background has there.

Finding 108, on George's library (60 random artists of 7,296): 31 have at
least one photo from the plugin's `artistphotos`, 22 have two or more, 12
have five or more; the photos come from Discogs and Last.fm, all real, Discogs
at most about 600 px wide; a list costs about 0.75 s uncached. 16 of the 29
with nothing are collaborations.

## Proposed (technical)

1. **The core fetches, the visualiser draws.** On a track change the core
   asks `musicartistinfo artistphotos` for the artist, downloads the photos
   into a bounded cache on the device, and writes their local paths into
   `nowplaying.json` (`fanart`). The visualiser never goes to the network for
   them - the same split as the album art's sizes.
2. **Ahead of time.** The next track's artist (LMS knows its queue) is
   fetched while the current one plays, so a photo is there when the track
   starts.
3. **The renderer draws the frame as the skin says:** its position and size,
   `fit` or `stretch`, behind the meters or over them, cycling the photos
   with a crossfade.
4. **Bounded:** at most 10 photos per artist, decoded no larger than the
   frame; the cache trimmed oldest first at a fixed size.

## For George

1. **Which music gets photos.**
   - **A:** LMS's own tracks only - the artist id is exact.
   - **B (recommended):** also Spotify, Bluetooth and plugins, when their
     artist's name matches an LMS artist exactly. A name that matches
     nothing gets no photos.
2. **A collaboration** ("Snoop Dogg feat. Mystikal", "X & Y"): the first
   named artist's photos (recommended), or none.
3. **An artist with no photos:** the frame shows the skin's own background,
   as it does today (recommended), or the album art fitted into it.
4. **How often the photo changes:** every 20 seconds with a crossfade,
   in the order the plugin gives them (recommended); fixed, no setting. If it
   should be a setting, it goes to ADR-0022's inventory first.

## Not settled here

- fanart.tv's background lists, which the library sweep reads one image of,
  are not used: Finding 108 measured the plugin only.
- Photos smaller than the frame are scaled up and look soft on 1920×1080;
  nothing here finds larger ones.
