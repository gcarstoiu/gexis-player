# ADR-0133 — The waiting screen, and the player's own wallpapers

**Status:** **Accepted** — George, 2026-10-10, on the design page's three
options for the panel's home with the LMS client off: *"I kind of like all
three. Can you mix all three into one design? A bit less text, but with the
clock and wallpaper."* On the four decisions put to him: the wallpapers are
**public-domain photographs** chosen by hand (*"B"*); they are **built into
the image**; holidays follow the **country**, taken from the time zone and
then from the location, with the proposed list (*"Completely agree with the
proposal"*); the waiting screen **follows the idle screen's Background**
(*"4a"*), and **Space pictures** become a Background of their own (*"add NASA
pictures as a standalone option for the idle screen as well"*). The settings
rows below are **in ADR-0022's inventory**, confirmed by George the same
day (*"Go ahead. Settings lines are fine"*).
**Date:** 2026-10-10
**Amends:** [ADR-0079](0079-with-lms-off-the-panel-is-two-screens.md) (the waiting
screen's look), [ADR-0047](0047-the-idle-screen-gains-backgrounds-and-weather.md)
(two more backgrounds)
**Relates to:** [ADR-0049](0049-the-pictures-folder-is-a-share.md) (the
Pictures share, which *Wallpapers on device* keeps reading),
[ADR-0022](0022-settings.md) (the inventory)

## Context

With the LMS client off there is no library, and the panel's home is the
waiting screen (ADR-0079): every renderer's mark, name and state, centred on a
flat ground, with Settings in the top right corner. It says nothing about
which player it is or how to start music, and the ground is an even
grey-blue.

The player has no pictures of its own. The idle screen's *Background* offers
artist pictures (from the library), Pixabay wallpapers (with the owner's key),
the Pictures share and black.

The three options and the mix were drawn on the panel and the bar on a
private design page, for George to review.

## Decision

### 1. The waiting screen

- **The wallpaper fills the screen** under the veil *Background brightness*
  sets.
- **The clock, the date and the player's name** sit in the top left, smaller
  than on the idle screen; they follow *Clock format*.
- **Each waiting source is a glass tile** along the foot: its mark, its name
  and its state, no instructions.
- **One line above the tiles**, *Start music from your phone*. It is the only
  other text.
- **Settings stays** the button in the top right corner.
- **On a bar:** the clock in a column on the left, the four tiles beside it,
  no hint line.
- **Against the idle screen:** the same background, so the move between them
  does not jump. The waiting screen is the one with the tiles; the idle
  screen keeps its large clock and the weather.

### 2. One background for both screens

The waiting screen follows the idle screen's *Background*. **Artist pictures
come from the library**, which is not there while the LMS client is off; then
the player's own wallpapers show instead.

### 3. Two new backgrounds

- **Gexis wallpapers:** the player's own set (section 4).
- **Space pictures:** images from NASA's missions and telescopes, on its own:
  NASA's public-domain ones, and ESA, ESA/Hubble and ESA/Webb releases under
  CC BY, each drawn with the credit line its release asks for (George,
  2026-10-10: *"for the standalone idle screen don't discard them. We can use
  the credit line."*). Named *Space pictures* rather than *NASA pictures* for
  that reason (George, the same day: *"Do that"*). The Gexis wallpapers stay
  public domain or CC0.

**Gexis wallpapers are built into the image**: no key, no network. **Space
pictures come from the network** (George, 2026-10-10: *"Yes. Record it that
way"*, on whether they are fetched as they are shown):

- **Downloaded and kept on the player**, as Pixabay's are (ADR-0047 §2a):
  new pictures arrive over time, and the screen still has pictures when the
  network is down.
- **Only from sources where every picture's licence is known:** NASA's own
  image library (`images-api.nasa.gov`, no key), filtered to items credited
  to NASA itself; and the ESA/Webb and ESA/Hubble pictures of the week, all
  CC BY, each drawn with its credit line.
- **Not NASA's Astronomy Picture of the Day:** it regularly carries amateur
  photographers' copyrighted pictures, so its licence cannot be taken on
  trust.
- **A small built-in set**, chosen by George from the contact sheet, shows on
  a first start and whenever nothing has been downloaded yet.
- With one background for both screens (§2), Space pictures bring these to
  the waiting screen too.

### 4. The player's own wallpapers

- **Public-domain photographs, chosen by hand**, each shown with its credit
  as Pixabay's are. George sees a contact sheet per set and picks before any
  of them ships.
- **Built into the image.** About 80 photographs at about 250 KB each add
  about 20 MB. **An estimate, not measured.**
- **Three styles**, about ten pictures each: **Calm**, **Colourful**,
  **Psychedelic**. Several can be chosen; each new picture comes from one of
  them at random, as the online topics do.
- **Time of day**, on by default: pictures for dawn, day, dusk and night take
  their turn by the clock.
- **Seasons**, by hemisphere, on by default: spring, summer, autumn, winter.
- **Holidays**, on by default, about five pictures each, on these days only:
  - **New Year**, everywhere: 31 December to 1 January.
  - **Christmas**, where it is a public holiday: 24 to 26 December.
  - **Easter**, Good Friday to Easter Monday, **Western or Orthodox by
    country** (Orthodox in Romania, Greece, Bulgaria, Serbia and similar).
    Both dates are computed, not tabled.
  - **Later, per country, when asked for:** Lunar New Year, Diwali, Eid. Their
    dates follow lunar calendars and need a table of years, and each needs its
    own pictures.
  - **Left out:** Valentine's Day and Halloween, customary in some countries
    only and more commercial than seasonal.
- **On a holiday's days its pictures replace the styles**, while *Holidays*
  is on (George, 2026-10-10: *"They replace them. For the time being if
  option is selected."*). "For the time being": open to revisiting.
- **The country** comes from the time zone at first (the mapping the setup's
  Wi-Fi country already uses), and from the weather location once one is set.

### 5. Settings rows (in ADR-0022's inventory, 2026-10-10)

| Setting | What it does | Default | Mark |
|---|---|---|---|
| *Background* (exists) | Gains **Gexis wallpapers** and **Space pictures**; one background for the idle and the waiting screen | Gexis wallpapers on a new player; an existing choice is kept | [N] new options on an existing row |
| **Wallpaper styles** | Calm, Colourful, Psychedelic; several allowed | Calm | [N] |
| **Follow the time of day** | Dawn, day, dusk and night pictures by the clock | On | [N] |
| **Seasons** | The season's pictures, by hemisphere | On | [N] |
| **Holidays** | New Year, Christmas and Easter for the player's country, on their days | On | [N] |
| **Clock on the waiting screen** | Time, date and name in the top left | On | [N] |
| **Hint on the waiting screen** | *Start music from your phone* above the tiles | On | [N] |

*Change the picture every* and *Background brightness* apply unchanged.

## Not decided here

- **Which pictures**, until George has seen the contact sheets.

## Consequences

- The image grows by about 20 MB (estimate), most of it the Gexis wallpapers;
  Space pictures add only their small built-in set.
- Space pictures add two network sources whose licences have to be checked
  as they come in: credited to NASA, or an ESA feed's CC BY.
- Each picture's credit has to be kept with it and drawn, as Pixabay's are.
- The holidays' dates for the later, lunar ones are a table that has to be
  kept up to date.

## Amended 2026-10-11: a Background section, and Pixabay searches

George, testing the waiting screen with Lyrion off: the rows behind its
picture were not under *Home screen*. They were under *Idle screen*, because
the two screens share one background (§5).

1. **A section of its own, *Background***, in Settings → Display between
   *Home screen* and *Idle screen*, since it serves both (George chose it
   over repeating the rows or a pointer line): *Background*, *Background
   brightness*, *Change the picture every*, the Pixabay key and topics, and
   the four wallpaper rows. *Background* no longer depends on the idle
   screen being the built-in one: with an external idle page the waiting
   screen still draws it. No key changes, so no migration.
2. **Pixabay topics gain Space, Calm and Season** (George, reversing
   2026-09-21's *"We start with categories"*). They are searches, not
   Pixabay categories: Space asks for *space*, Calm for *calm*, Season for
   the current season (*spring*, *summer*, *autumn*, *winter*) by the
   player's hemisphere, as the Gexis wallpapers' seasons are read. Measured
   on the bar player the same day: each search has Pixabay's ceiling of 500
   usable photos. **Searches ask for editors' choice only** (ours: a search
   matches captions as well as pictures, and Pixabay's picks are its
   reviewed ones); categories stay as they were.
3. **Holidays supersede the chosen topics** (George: *"holidays are a toggle
   that supersede the choice of wallpaper"*). The existing *Holidays* row
   now governs *Wallpapers online* too: on New Year, and on Christmas and
   Easter where they are holidays, Pixabay is asked for that holiday
   (*new year*, *christmas*, *easter*) instead of the topics. Same country
   rule as the Gexis wallpapers (§4).
4. **The registry learns "one of"** (`{"in": [...]}` in `onlyWhen`): the
   *Holidays* row shows for either wallpaper background.

**Revised the same day, after George saw it on sofapi:** Space left the
topics - the *Space pictures* background covers it - and so did Season:
the *Seasons* toggle now governs *Wallpapers online* as it does the Gexis
wallpapers, adding the season's search beside the chosen topics (George
chose the toggle over the topic). Calm stays a search. Space's searches had
been fine (the top results were the Milky Way, galaxies and Earth from
orbit); the topic was redundant, not broken.

## Amended 2026-10-11 (second): two backgrounds, and Display in seven sections

George, on sofapi: one shared *Background* section *"is not working for me
organisation wise"*. The home screen and the idle screen each get their own.

1. **Display's sections**, in order: *Panel*; **Touchpad** (the phone's
   touchpad, pointer speed and style); **Volume** (the drawer's two rows);
   **Photo service and location** (the Pixabay key, and the location the
   weather and the seasons and holidays read); **Home screen**; **Idle
   screen**; *Visualiser* and *Visualiser tweaks*. The shared *Background*
   section of the first amendment is gone.
2. **Two backgrounds.** *Home screen* keeps its rows (the strip with the
   Lyrion client on; clock and hint with it off) and gains a background of
   its own for the waiting screen, shown with the Lyrion client off:
   `waiting_background` and `waiting_background_brightness`,
   `waiting_background_interval`, `waiting_wallpaper_topics`,
   `waiting_wallpaper_styles`, `waiting_wallpaper_time_of_day`,
   `waiting_wallpaper_seasons`, `waiting_wallpaper_holidays`. **Fresh
   defaults** (George), not a copy of the idle screen's: Gexis wallpapers,
   Calm. *Artist pictures* is not offered there - the library it needs is
   off whenever the waiting screen shows. The idle screen keeps today's keys,
   so nothing changes for it on an update.
3. **One order in both** (George: *"background should be followed by Topics
   and then season toggle"*): Background, Topics or Styles, Follow the time
   of day, Seasons, Holidays, Background brightness, Change the picture
   every.
4. **The idle screen can be switched off**: an *Idle screen* toggle heads
   its section and hides every row under it when off. **Off by default on a
   new player** (George); a player already in use keeps it on (a migration
   for existing players only). Off, the panel never goes idle by itself and
   the phone's idle button is not offered.
5. **The picture route says which screen asks** (`/idle/wallpaper?for=home`);
   each screen keeps its own last picture, so the two do not show the same
   one by turns.
