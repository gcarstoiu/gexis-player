# ADR-0149 — First use in two parts: set up, then make it yours

**Status:** **Proposed** — 2026-10-15. The direction is George's (2026-10-15,
*"Let's do it"*); the questions, answers and defaults below are for his review.
On acceptance it amends ADR-0031 (the setup network), ADR-0104 (what setup
needs), ADR-0128 (plugins and settling in setup) and ADR-0131 (restore in
setup). Phase 14, `ph-first-use`.

## Context

Setup today is one walk on the phone, over the setup network or the cable:
Network, Start (new or restore), Name, Time, Output, Music, Screen,
Visualiser, Plugins, Review. Then the player joins the home network and the
panel shows the downloads until it has settled (ADR-0128).

George (2026-10-15): *"have 2 parts. One like now on first boot, but only
with the device specific things to make it work like WiFi, display, audio,
device name and clock, and then another part shown once the player boots
that covers customisations that will make the player personalised to the
user and be driven by questions ... At the end of this small wizard we would
have the download part."* And before MPD, *"because mpd will add another
option of playing and indexing music ... for a person who is just starting
it might get too much."*

Three facts make the split worth more than tidiness:

- **The setup network is the fragile part** (Finding 126: a screen can jam
  its channel; a phone far away or among busy channels may not get in). The
  less is asked over it, the shorter that window.
- **Several questions work better on the home network**: finding a Lyrion
  server searches the LAN, which the setup network cannot see (today it
  searches once, after the join); a service's sign-in and every download need
  the internet.
- **What is downloaded follows from the choices** (skins, plugins), so the
  downloads belong at the end of the choosing, not of the device setup.

## Decision

### Part 1 — make it work (as today, shorter)

On the phone, over the setup network or the cable, unchanged in how it is
reached (ADR-0031, ADR-0104). Only what the player needs to run:

1. **Network** — Wi-Fi, or the cable.
2. **New player or a backup** (ADR-0131). A backup answers part 2 as well:
   after a restore part 2 is not offered.
3. **Name.**
4. **Time** — time zone and clock. The time zone also sets the Wi-Fi country,
   which is why it stays here.
5. **Output** — where the sound goes.
6. **Screen** — which screen, or none (Headless).
7. **Review**, then the player joins the home network and restarts if it must.

Gone from part 1: Music, Visualiser and Plugins.

### Part 2 — make it yours (new)

Once the player is on the home network, **the panel offers it, and the phone
page as well**; a player without a screen offers it on the phone page only.
Every question has a default, a **Later** that keeps the defaults and leaves,
and the whole of part 2 can be run again from **Settings → System →
Personalise**. Typing, where any is needed, comes from the phone (the
touchpad, ADR-0121).

| # | Question | Answers | Default | What it does |
|---|---|---|---|---|
| 1 | **How will you use this player?** | *Play my music library* · *Only stream* · *Both* | none: an answer is needed (or Later = *Both*) | Decides which of the questions below are asked |
| 2 | **Where is your music?** (asked for *library* and *both*) | a Lyrion server found on the network (each listed) · *Enter an address* · *Install the Lyrion Server on this player* | the one server found, if exactly one | `lms_server`; *Install* turns on the Lyrion Server plugin (`gexis-lyrion-server`) |
| 3 | **Which services?** | Spotify Connect · Plexamp · Bluetooth, each a switch | Spotify Connect and Bluetooth on, Plexamp off (as today) | `spotify_enabled`, `bt_enabled`, Plexamp's plugin switch |
| 4 | **On the screen** (not asked when Headless) | the visualiser yes/no · a clock and weather when nothing plays yes/no | visualiser: needs an answer as today; idle screen off (ADR-0133) | `visualiser_skins` (its pack downloads), `idle_enabled` |
| 5 | **Anything else to install?** | Beszel monitoring, and future plugins | off | the plugin switches |
| 6 | **Downloads** (today's settling screen, ADR-0128) | — | — | waits for what 2-5 started; *Use the player now* as today |

*Only stream* turns the Lyrion client off (`lms_enabled`): the panel then
has no library, and its home is the waiting screen with every source's state
(ADR-0079, ADR-0133).

**When Phase 15 (MPD) lands**, question 2 gains *Music on this player or a
share* (MPD), and question 1 is unchanged. Until then that answer does not
appear.

### Who sees it

- **A new player** — part 2 opens on the panel once it is on the home network.
- **A restored player** — not offered; Settings has Personalise.
- **A player already set up** (an update) — not offered; Settings has
  Personalise.
- **After a factory reset** — both parts, as a new player.

## Settings (ADR-0022)

Proposed, not appended until George confirms: whether part 2 has been
finished or put off is state, not a setting ([N] none needed). *Personalise*
is an action row in System, like *Reset to factory settings*.

## Open (George)

1. The questions and wording above, and question 1's three answers.
2. Whether *Only stream* should hide the library entirely, or only start on
   Now Playing.
3. Whether part 2 is offered on the phone page at the same time as on the
   panel, or only when the panel's is put off.
4. Claude Design draws part 2 (panel 10.1", bars, phone) and the shorter
   part 1 once 1-3 are settled.

## Not decided here

The look (Claude Design), the bar's layout for questions with several
switches, and how part 2 is told apart from Settings for someone who opens
Personalise again.
