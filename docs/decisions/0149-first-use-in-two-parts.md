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

### Part 2 — make it yours (new), on the phone

**On the phone** (George, 2026-10-15: *"It's where the user sets up the panel
in the first place and we have more control over the space. A bar might be
tough to accommodate for certain things."*). Part 1's last page already tells
the phone to go back to the home Wi-Fi and open the player's address; that
page now continues with part 2. **The panel**, meanwhile, shows a QR code to
the same page (*Make it yours on your phone*), and at the end the downloads.
Every question has a default and a **Later** that keeps the defaults and
leaves; the whole of part 2 can be run again from **Settings → System →
Personalise**.

| # | Question | Answers | Default | What it does |
|---|---|---|---|---|
| 1 | **What should the player's screen show?** (not asked without a screen) | *My music library, to browse, and what is playing* · *Only what is playing: I choose music on my phone and in apps* | none: an answer is needed (Later = the first) | The second turns **library navigation off on the screen** (below); the Lyrion client keeps running |
| 2 | **Lyrion Music Server**: plays your music files, and its apps can play to this player | a server found on the network (each listed) · *Enter an address* · *Install the Lyrion Server on this player* · *I don't use Lyrion* (not offered with the first answer to 1) | the one server found, if exactly one | `lms_server`; *Install* turns on the Lyrion Server plugin; *I don't use Lyrion* turns the Lyrion client off (`lms_enabled`), as today |
| 3 | **Which services?** | Spotify Connect · Plexamp · Bluetooth, each a switch | Spotify Connect and Bluetooth on, Plexamp off (as today) | `spotify_enabled`, `bt_enabled`, Plexamp's plugin switch. With nothing on and no Lyrion, the page says the player would have nothing to play |
| 4 | **On the screen** (not asked without a screen) | the visualiser yes/no · a clock and weather when nothing plays yes/no, and its place for the weather | visualiser: needs an answer as today; idle screen off (ADR-0133) | `visualiser_skins` (its pack downloads), `idle_enabled`, the weather's location |
| 5 | **Anything else to install?** | Beszel monitoring, and future plugins | off | the plugin switches |
| 6 | **Downloads** (ADR-0128's settling) | — | — | on the panel as today, and on the phone at the end of part 2 |

**Library navigation off, the Lyrion client on** (George, 2026-10-15: *"the
lyrion client is up and running but there is no library navigation on the
screen. This would be a modification of the current no lyrion client
enabled."*): the player is still a Lyrion player - Lyrion's apps, other
controllers and its radio play to it, and Now Playing shows what they play -
but the screen has no library, browse or Lyrion menus. Its home is the
waiting screen, as with the client off (ADR-0079, ADR-0133), with Lyrion
among the sources. Today's *client off* stays, for *I don't use Lyrion*.

**When Phase 15 (MPD) lands**, question 2 becomes *Where is your music?* and
gains *Music on this player or a share* (MPD); until then it is Lyrion's.

### Who sees it

- **A new player** - part 2 follows part 1 on the phone; the panel shows its
  QR code until it is done or put off.
- **Without a screen** - questions 1 and 4 are not asked.
- **A restored player** - not offered; Settings has Personalise.
- **A player already set up** (an update) - not offered; Settings has
  Personalise.
- **After a factory reset** - both parts, as a new player.

## Settings (ADR-0022)

Proposed, not appended until George confirms:

- **[N] Library on the screen** - on / off; on by default, off from question
  1's second answer. Display (or Sources), beside the Lyrion client row,
  which it needs.
- *Personalise* is an action row in System, like *Reset to factory settings*;
  whether part 2 was finished or put off is state, not a setting.

## Open (George)

1. The questions and wording above.
2. **Library on the screen** as a setting ([N] above), and where it sits.
3. Settled 2026-10-15: *Only stream* keeps the Lyrion client and hides the
   library on the screen; part 2 runs on the phone, the panel showing a QR
   code to it and then the downloads.
4. Claude Design draws part 2 on the phone, the panel's QR and download
   screens (10.1", bars), and the shorter part 1, once 1-2 are settled.

## Not decided here

The look (Claude Design), and how part 2 is told apart from Settings for
someone who opens Personalise again.
