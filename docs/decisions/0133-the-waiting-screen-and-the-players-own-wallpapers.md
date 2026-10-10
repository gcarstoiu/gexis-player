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

Both are in the image, so neither needs a key or a network.

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

- The image grows by about 20 MB (estimate).
- Each picture's credit has to be kept with it and drawn, as Pixabay's are.
- The holidays' dates for the later, lunar ones are a table that has to be
  kept up to date.
