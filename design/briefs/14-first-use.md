# Brief for Claude Design — First use in two parts (Phase 14)

Written 2026-10-15 for George to hand to Claude Design. Background, if you
want it: [ADR-0149](../../docs/decisions/0149-first-use-in-two-parts.md) (the
direction and a first set of questions, with George's words). You do not
need to read it: this brief carries what the design needs. **The questions
below are a starting point for the discussion, not a spec** (George: *"a
good starting point in the discussion with design Claude. Questions might
change there."*).

---

**gexis** is a music player for the Raspberry Pi 4. It usually has its own
touchscreen (the "panel": a 10.1" 1280 x 800, or a wide *bar*, 11.9" 1480 x
320 or 7.9" 1280 x 400), and every player has a phone page for settings,
control and typing. It plays music from a **Lyrion Music Server** (files,
and Lyrion's apps and radio), and is also a **Spotify Connect** speaker, a
**Plexamp** player and a **Bluetooth** speaker.

## What happens today (the starting point)

First use is **one walk on the phone** (`screens.md` §13,
`source/Setup.dc.html`): the player opens its own Wi-Fi, *gexis-setup*; the
panel shows a QR code to join it and then one to open the setup page
(`source/Panel Setup.dc.html`); the phone asks **Network, New player or
backup, Name, Time, Output, Music (Lyrion, Spotify, Bluetooth), Screen,
Visualiser, Plugins, Review**. Then the player joins the home network,
restarts if it must, and the panel shows **the downloads** (skins, plugins)
until it has settled, with *Use the player now* to leave early.

It works, but it asks everything at once, over the most fragile connection
the player has (the setup network: a phone far away, a busy channel or the
player's own screen can keep it out), and it asks a newcomer about things
they cannot yet judge. A further source, MPD (music files played on the
player itself, multichannel), comes next, and George does not want it to
become one more option a newcomer has to understand.

## What we want: two parts

**Part 1 — make it work.** On the phone, over the setup network or a network
cable, only what the player needs to run: **Network, New player or backup,
Name, Time** (time zone and clock), **Output** (where the sound goes),
**Screen** (which one, or none), **Review**. Same design language and step
rail as today, fewer steps.

**Part 2 — make it yours.** **On the phone** too (George: *"It's where the
user sets up the panel in the first place and we have more control over the
space. A bar might be tough to accommodate for certain things."*), once the
player is on the home network. Part 1's last page already tells the phone to
return to the home Wi-Fi and open the player's address; that page continues
into part 2. A few questions, in the user's words, not the settings'
words; each answer switches settings on or off behind the scenes. It ends
with **the downloads** its answers started.

**The panel, meanwhile**, shows a screen that says the player is ready and
points to the phone, with a **QR code** to part 2's page (*Make it yours on
your phone*), and then the **downloads**. On the 10.1" panel and both bars.

### Part 2's questions, as a starting point

1. **What should the player's screen show?** *My music library, to browse,
   and what is playing* · *Only what is playing: I choose music on my phone
   and in apps.* The second keeps the player a Lyrion player (its apps still
   play to it) but the screen has **no library to browse**: its home is the
   waiting screen with the sources.
2. **Lyrion Music Server**: the servers found on the network · enter an
   address · *install the Lyrion Server on this player* · *I don't use
   Lyrion*. Zero, one or several servers can be found. (MPD later joins
   here, and the question becomes *Where is your music?*)
3. **Which services?** Spotify Connect, Plexamp, Bluetooth, each on or off.
   With nothing on and no Lyrion, the player would have nothing to play: say
   so.
4. **On the screen**: the visualiser (VU meters and spectrum) yes or no; a
   clock and weather when nothing plays, yes or no, and the place for the
   weather.
5. **Anything else to install?** Optional plugins (today: Beszel monitoring).
6. **Downloads**: what was chosen arriving, with progress, on the phone and
   the panel.

Every question has a default and a **Later** that keeps the defaults; the
whole of part 2 can be opened again from **Settings → System →
Personalise**. A player without a screen skips 1 and 4. A restored player
(its backup already holds these answers) and a player updated from an
earlier release are not shown part 2.

**Challenge all of this.** Fewer questions, other groupings, a different
first question, pictures instead of words for question 1: whatever makes a
newcomer's first ten minutes clearer. George will decide with you.

## Keep

- **The design system as it is**: `design/tokens.css`, Nunito Sans and IBM
  Plex Mono, the blurred-weave backdrop, the source accents and marks.
- **Setup's patterns**: the step rail and its accents, one card per step on
  the phone, one step at a time on the panel, readable from two metres.
- **No on-screen keyboard** on the panel; anything typed is typed on the
  phone.
- **The panel takes no input during setup**, except what a QR screen or the
  downloads screen already offer (*Use the player now*).
- **Pi 4 budget**: transform and opacity only, no blur in motion
  (`screens.md`, *Motion*).
- **Nothing personal in mock-ups**: names like *Living Room*, addresses from
  192.0.2.x, the public-domain demo library.

## What we need from you

1. **Part 1 on the phone**, shortened: the step rail and each step's card,
   and the Review, for a new player and for a backup.
2. **Part 2 on the phone**: each question's card with its states (for
   question 2: none found, one found, several found, install chosen, *I don't
   use Lyrion*; for question 3: the nothing-to-play warning), *Later*, and
   the downloads with their end (done, or one that failed and can be tried
   again from Settings).
3. **The panel during part 2**: the *Make it yours on your phone* screen with
   its QR code, and the downloads, on the 10.1" panel and on the 11.9" and
   7.9" bars.
4. **The screen with no library** (question 1's second answer): the panel's
   home when the Lyrion client is running but the library is not shown, on
   the 10.1" panel and a bar.
5. **Settings → System → Personalise**: the row, and how part 2 looks when
   opened again on a player already in use.
6. **Your view on the questions**: what to cut, merge, reword or reorder.

George will share screenshots of today's setup on the phone, the panel's
setup and download screens, and the waiting screen with you separately.
