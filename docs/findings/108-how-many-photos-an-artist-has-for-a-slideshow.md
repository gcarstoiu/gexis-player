# Finding 108 — How many photos an artist has, for the visualiser's fanart slideshow

**Date:** 2026-10-02
**Question:** 72 skins reserve a frame for a slideshow of the artist's photos
(`fanart.*`; 20 at 1280×800, 52 at 1920×1080). George: *"Fanart - yes, we do
it. Do we have pictures for a slideshow"*. How many photos can the player get
per artist, from what it already talks to?

**Scope:**
- **One library:** George's LMS (7,296 artists, `192.168.178.188:9000`), with
  the Music & Artist Information plugin.
- **60 artists drawn at random** (seed 20261002) from LMS's full artist list,
  which includes collaborations ("X feat. Y", "X & Y") and track-numbered
  names. The artists actually played were not weighted, so this describes the
  library, not the listening. Raw results:
  [data/108-artist-photos-sample.json](data/108-artist-photos-sample.json).
- **One command:** `musicartistinfo artistphotos artist_id:<id>`, asked one at
  a time from R2D2. The player today asks `artistphoto` (one photo).
- **Not measured:** fanart.tv's background lists (the sweep keeps one
  per artist; Finding 054's coverage figures stand), and whether a Spotify or
  Bluetooth track's artist can be matched to an LMS artist id.

## Result

| Photos for the artist | Artists (of 60) |
|---|---|
| none | 29 |
| 1 | 9 |
| 2-4 | 10 |
| 5 or more | 12 (up to 23) |

- **31 of 60 have at least one photo; 22 have two or more** - enough to
  change pictures.
- **Sources:** Discogs 184 photos, Last.fm 144, the music folder 6. All 144
  Last.fm photos are distinct files, so none is Last.fm's well-known
  placeholder star.
- **Sizes:** 95 of 334 are 500 px wide or more; 150 come with no size.
  Discogs serves at most about 600 px - smaller than a 1920×1080 frame needs.
- **Cost:** a median 747 ms per artist, uncached (the plugin goes to the
  network), in line with Finding 035's 500-900 ms.
- **Every artist with nothing** in the sample was a collaboration, a
  numbered track name or an obscure name ("Purple Disco Machine, Dabeull",
  "Laura Pausini & Andrea Bocelli", "Heydeon").

## What it bears on

The fanart ADR: a slideshow is possible for about a third of this library's
artists and a single photo for half; the rest need the frame to show
something of its own. Photos must be fetched ahead of the track, once, and
may need upscaling for the largest frames.
