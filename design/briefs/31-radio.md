# Brief for Claude Design — Internet radio (Phase 31)

Written 2026-11-13 for George to hand to Claude Design. Background, if you
want it: [ADR-0180](../../docs/decisions/0180-internet-radio-without-lyrion.md)
(George's decisions of 2026-11-13). What is built and differs from the
earlier designs is in [`IMPLEMENTED-DIFFERENTLY.md`](../IMPLEMENTED-DIFFERENTLY.md).
Start from what is built: Lyrion's Radio in the library
([`screens.md`](../screens.md) §8), the waiting screen with Lyrion off
([ADR-0079](../../docs/decisions/0079-with-lms-off-the-panel-is-two-screens.md)),
the phone remote (`source/21`), the Home Assistant card (`source/19`) and
the group's mark (`source/22`).

---

**Gexis Player** is a music player for the Raspberry Pi 4. It usually has its
own touchscreen (the "panel": 7" to 13.3", most often a 10.1" 1280 x 800, or a
wide *bar*, 11.9" 1480 x 320 or 7.9" 1280 x 400, laid out at 1850 x 400 CSS
px and drawn at 0.8), and every player has a phone remote (your *Phone
Remote v3*, built as drawn). It plays from a **Lyrion Music Server**, which
an owner may switch off, and is also a Spotify Connect speaker, a Plexamp
player, a Bluetooth speaker, an AirPlay receiver, and whatever plugins add.
In Home Assistant each player is a media player, with a Gexis card.

Please use the existing design, in the default theme and the five others,
and export as before: artboard HTML/CSS, a PNG per state, new tokens as CSS
custom properties, component boundaries.

## What internet radio is

- **The player's own radio**, with or without a Lyrion server: about 50,000
  stations from a public directory, found through *Popular here* (the
  country set at setup), *By genre*, *By country*, *By language*, and
  *Search* by name.
- **A station** has a name, a logo (a third have none, and some are tiny),
  a country, and its codec and bitrate (*MP3 · 128 kb/s*).
- **Favourites** are the player's own list, apart from Lyrion's, in the
  order the owner sets: a heart on each station row and on Now Playing,
  reordered and removed on the panel and the phone. From the phone, a
  station missing from the directory can be added by its address (a stream
  link) and a name.
- **Playing**: a tap on a station plays it. A station is live, so it stops
  rather than pauses, and Play after a stop starts it afresh. No seek and no
  position. **Next and Previous step through the favourites** while a
  favourite plays, like a radio's presets; for any other station they are
  greyed.
- **When a station drops**, the player reconnects by itself, up to three
  times, then stops with *The station is not answering*.
- **When the directory cannot be reached**, favourites still play, and
  browsing shows what was seen in the last day, or says so.
- **Groups and takeovers** work as for the other sources.
- **On by default**, and offered in first use.

## 1. Radio on the panel, Lyrion on

Today the library's *Radio* card opens Lyrion's radio: nine categories in a
three-up card grid, each with its own glyph and tint, then dense lists. It
becomes **one Radio screen**: *Favourites*, *Popular here*, *By genre*, *By
country*, *By language*, *Search*, and **Lyrion's radio** as one more entry,
which opens Lyrion's tree as today. The station lists, the station row and
search are yours to propose; the category cards are a starting point.
Search on the panel takes typing as the panel's other fields do.

## 2. Radio on the panel, Lyrion off

Without Lyrion the panel is two screens: the waiting screen (the services'
marks scaled up, a settings icon top right) and Now Playing (with settings
in place of Home). **The waiting screen gains Radio**: a way into the same
Radio screen as above, without Lyrion's entry, and **Now Playing gains a way
back to Radio**. Where both go is yours to propose; the waiting screen
should stay calm.

## 3. The bars

On the bars, Lyrion's Radio is two rows that scroll sideways. The same Radio
screen, station lists, favourites and search in the bar's layout, and with
Lyrion off how the bar's waiting screen leads to Radio.

## 4. Now Playing for a station

On the panel, the bars and the phone:
- **the lines**: title and artist when the station sends them (often
  *Artist - Title*), the whole line as the title when it cannot be split, or
  nothing at all; the station's name on the album line;
- **the artwork**: the track's cover when one is found, else the station's
  logo, else the radio mark;
- **the quality line**: codec and bitrate;
- **the controls**: the heart; Next and Previous live only for a favourite;
  no seek bar (or Bluetooth's inert rule); stopped, with Play;
- **reconnecting**, and **not answering**.

## 5. The phone

The phone remote browses nothing today; for a player without a screen it is
the only way in. It needs **Radio**: where it opens from (a quick action,
the menu: yours to propose), the same Radio screen, search with the phone's
keyboard, favourites with reorder and remove, and **adding a station by its
address**: the address and a name, checked by playing it before it is
added. Phones 360 to 430 px wide.

## 6. The Home Assistant card

The Gexis card follows Home Assistant's theme. It gains **a Radio view with
the favourites**: a tap plays one, the one playing is marked. Browsing and
search in Home Assistant happen in its own media browser, not designed
here. The card's sizes as before: a phone, one dashboard column, a wall
tablet; compact and full.

## 7. First use and Settings

- First use's *How will you listen?* gains **Internet radio**, on by
  default, on the panel and the phone.
- **Settings → Sources** gains Internet radio's switch, and the country for
  *Popular here*, as the other sources' rows.

## States

- **The Radio screen**: with Lyrion's radio and without; the directory
  unreachable, with the last day's lists and with none.
- **Favourites**: none yet (how to add one), a few, twenty with long names;
  reordering; removing.
- **Station lists**: with logos, without, tiny ones; long names; MP3, AAC
  and FLAC; loading; a long list's end.
- **Search**: typing, results, nothing found.
- **Now Playing**: title and artist; a show's name only; nothing sent; a
  favourite and another station; reconnecting; not answering; stopped; in a
  group.
- **The phone**: a station added by address: the form, being checked, did
  not play.
- **The card**: favourites with one playing; none yet.
- **The bars**: each of the above that applies. **Every theme.**

## Not in this design

- Recording, a station's schedule, alarms, podcasts.
- Home Assistant's media browser (its own).
- A list of stations chosen by us: the directory's lists only.
