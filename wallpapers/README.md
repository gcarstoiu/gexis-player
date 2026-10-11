# The player's own wallpapers

The pictures behind the idle screen and the waiting screen when *Background*
is **Gexis wallpapers**
([ADR-0133](../docs/decisions/0133-the-waiting-screen-and-the-players-own-wallpapers.md)).
Chosen by hand from candidates on 2026-10-10.

## Folders

| Folder | Used for |
|---|---|
| `calm`, `colourful`, `psychedelic` | The three *Wallpaper styles* |
| `dawn`, `day`, `dusk`, `night` | *Follow the time of day* |
| `spring`, `summer`, `autumn`, `winter` | *Seasons*, by hemisphere |
| `newyear`, `christmas`, `easter` | *Holidays*, by country |

Each picture is the original scaled to 1920 px wide at most and saved as
WebP (quality 80), with its metadata removed.

## Licences

`credits.json` lists every picture: its title, author, licence, the page it
came from, the original's address and the original's SHA-256.

- **Every picture is public domain or CC0** (68 CC0, 21 public domain). Each
  licence was read from the file's own page: Wikimedia Commons' `extmetadata`, or NASA's
  image library for pictures credited to NASA alone.
- **Fifteen came to Commons from Unsplash**, whose photos were CC0 only until
  June 2017. For fourteen, `unsplash_published` records the date Unsplash
  itself gives, all earlier than that; for one photo Unsplash has since
  removed, the date comes from the Internet Archive's copy of its page. The
  fifteenth carries Commons' own licence review (`licence_review`).
- The twelve space pictures, five of them ESA's under CC BY 4.0, left with
  the *Space pictures* background on 2026-10-11 (ADR-0133 amended).
