# What the panel does that the designs do not draw

**For Claude Design, 2026-09-18.** George asked for a diff so the mockups can
be brought up to date before Phase 9's UI sweep.

**Brought up to date 2026-10-25**, for Phase 19's brief
([`briefs/19-ha-card-and-dpad-focus.md`](briefs/19-ha-card-and-dpad-focus.md)).
Everything since 2026-09-29 is in the last section, *Changed since
2026-09-29*; an entry above that is no longer true carries a dated note
under it. The pictures in `implemented/` are still those of 2026-09-28.

`design/source/` is locked and built from, never edited, so the shipped panel
has drifted from it in ways that are recorded per decision but never
collected. This is that collection. Everything here is deliberate and has a
record; nothing here is a bug waiting to be fixed back.

**Three kinds of entry:**

- **[H]** a hardware constraint - the design asked for something this device
  cannot afford, and the measurement is cited
- **[U]** a UX call George made on the panel, usually after seeing it
- **[S]** scope - a screen or control the design draws that is not built, or
  is built differently because of what the data turned out to be

---

## The whole panel

**[H] No blurred backdrops behind sheets. Ever.**
The designs put `backdrop-filter: blur()` behind the queue rail, its source
sheet, Settings and the volume drawer. On this GPU that costs two thirds of
the panel's frames - 24.5 ms a frame in draw-and-submit against a 16.7 ms
budget, with the CPU idle, because the compositor must read the live screen
back every frame (ADR-0041, Finding 037). **Scrims now dim and do not blur.**

*What the design can still have:* the impression of depth from a **static**
blurred image. The artwork bleed behind every screen is one, and it costs
nothing measurable; blurring *that* harder when a sheet opens is available.
The rule is: **depth is affordable, live readback is not.**

**[H] One screen is mounted at a time, and a screen change is not animated.**
The design layers the library over now playing and cross-fades in 260 ms.
Transparent screens cannot overlap without showing both, and over a shared
backdrop every fade showed the bare backdrop as a blink (George: *"Now it
really blinks... remove the entire animation from both directions"*). The
backdrop stays put and the swap is the whole effect. The library and Settings
are also **mounted only while open** - left in the page at opacity 0, the
closed library covered now playing in black.
*2026-10-25:* the library now stays mounted, hidden, under Now Playing and
Settings, so Minimise returns to it as it was (ADR-0122, 2026-10-06).

**[U] Press feedback shrinks; it does not fill.**
The design's grey press fill read as a flash. Controls keep their resting
fill and scale to 0.95 (the mini strip to 0.995).
*2026-10-25:* except the library's and Lyrion's rows, where a tap shows only
the teal selection, with no press effect (George, 2026-10-21); Home's cards
keep it.

**[U] The volume glyph is the drawer's 30 px one everywhere**, including now
playing's button and the mini strip, not the design's 26 px and 24 px
variants, whose three arcs merge at full volume.

**[U] The volume drawer opens on a change from elsewhere.** A phone's volume
change raises it; it closes 3 s after the last change. The panel's own
changes and a takeover's restored level do not open it.
*2026-10-25:* only a drawer opened by a change from elsewhere hides itself,
after *Drawer auto-hide* (1-30 s, Display › Volume). One the user opened
stays until it is closed, the visualiser takes over or Home opens; a change
from elsewhere leaves it alone (George, 2026-10-24; ADR-0022). On a bar the
same holds for its tray.

---

## Now playing

**[S] The tabs are Track, Lyrics, Artist, Release - all four now work.**
*2026-10-25:* on the standard screens; a bar's Now Playing has no tabs
(13b).
The design's Track panel has two forms and both are built: the tall block,
and a **compact one when the track has synced lyrics** - title, artist and
album on one line, a rule, then the words following the playhead. The compact
form is also held while the lookup runs, so the panel does not jump.

**[S] An attribution line under the biography and the lyrics.**
The designs have no element for it. *2026-10-25:* wrong - the 2026-09-22 drop draws
it (mono 12 px, 0.1em, sentence case); the build draws it at 11 px, upper
case, 0.12em, and the build's stays (George). Wikipedia's text is CC BY-SA and
MusicBrainz's tags are CC BY-NC-SA: the credit is a licence term, not
decoration (ADR-0040 §4). It reads *"From Wikipedia, CC BY-SA"* or *"From
LMS"*, in mono, under the text it credits. **Draw it as built.**

**[S] The Release tab omits what is not known.** The design draws a label
chip; LMS does not hold one, so for an LMS track the row simply has fewer
chips. For Spotify and Bluetooth the label comes from MusicBrainz.

**[U] The artist line is a link** to that artist's page, as the design's
`onNpArtist` intended.

---

## The library

**[S] Artists have photographs again.** ADR-0038 §2 said "LMS has no artist
photos" and drew initials. That was wrong: LMS's Music & Artist Information
plugin has them, and fanart.tv has better ones. The grid shows the plugin's
photo, the artist page prefers fanart's, and **the initial is the fallback**,
not the rule (ADR-0040 §1).
*2026-10-25:* the grid now shows fanart's portrait too, after *Update artist
portraits*, then Lyrion's photo, then the initial; one lookup serves the
grid, the artist page and the renderers, and a picture that failed is tried
again (ADR-0059, ADR-0075; Finding 125).

**[S] The artist page's About block is measured, not fixed.** It takes as
much height as is left while the first row of albums still shows a quarter of
itself (George, 2026-09-18), with More/Less for the rest. A fixed height was
wrong in both directions - it hid the text on a short biography and the
discography on a long one. Biographies arrive as plain text with paragraph
breaks and no markup; the panel renders paragraphs and shows the first
twelve, because LMS returns whole encyclopaedia articles for some artists
(56,573 characters for one artist).

**[S] "Popular" is absent without a ListenBrainz token.** The endpoint began
demanding one mid-phase. With a token it lists only tracks **on this device**,
which is the design's own note.

**[S] No playlist creation anywhere.** Adding to an existing playlist is
offered; creating one is not (George, ADR-0038 §3).

**[U] Play means in order.** LMS's shuffle is turned off before a load, and
**Shuffle all is its own button** beside Play all on a playlist and an artist
page.

**[U] Album rows carry the year beside the title**, and discographies are
newest first.

**[U] The jump rail's letters are folded** - `Ç` into C, `Í` into I, every
digit into `#` - so the rail is the design's `#` then A-Z, whatever LMS files
them under.

**[S] Radio is a walk of one subtree**, and two kinds of item never appear:
podcasts, and anything asking for typed text (Search TuneIn today). A station
list is reached in at most four taps.

---

## The queue rail

Built as drawn, with three notes:

**[S] It lists the queue from the track playing now.** What is already played
is not drawn - the rail answers "what is next".

**[S] The source row is also the chooser.** It names the playlist a queue
came from while LMS still reports one, and reads *"Play from / Choose a
playlist"* when there is nothing to name.

**[H] Its scrim does not blur** - see the top of this document.

---

## Settings

**[S] 54 rows, 6 wired.** *2026-10-25:* 8 categories, 129 rows, 18 of them never
shown; every shown row that takes a value works. The structure since is in
the last section. The design's seven groups are intact and the keys
match, with four deviations already recorded: `idle_grace` merged into
`idle_timeout`; `travel_curve` decided; `drawer_on_external` and
`drawer_autohide` added under Display › Panel; and two new keys the design
has no row for - **`listenbrainz_token`** and **`fanart_key`**, both per-user
API keys (ADR-0022). Those two want drawing.
*2026-10-25:* built as the drop draws them (a secret field with a
placeholder); four keys now - ListenBrainz, fanart.tv and TheAudioDB under
Enrichment, Pixabay under Display › Photo service and location.

---

## Small things

- **New Music artist names at 0.60 alpha**, not the design's 0.55, which is
  under its own 4.5:1 contrast floor for 15 px text.
- **Card counts are singular where they should be**: "1 playlist", not
  "1 playlists".
- **Artwork is requested at the size it is drawn**, on a ladder of four
  (500 / 300 / 200 / 100). Not visible, but it is why covers arrive quickly.

---

## What the sweep has not decided yet

These are open, and Phase 9's sweep is where George settles them:

*2026-10-25:* blur is ruled out for good (Finding 042 §6.16); the attribution
line and the API-key rows are drawn (above), the line in the build's style
(George). The scrim and the volume
questions have no recorded decision: the build keeps a 0.62 scrim and the
drawer.

- Whether a sheet without its blur reads as enough separation, or wants a
  darker scrim (free, measured).
- Whether the volume control should stay a modal at all, or live in the mini
  strip - George raised it; the numbers do not require it now that the blur
  is gone.
- How the attribution line should look.
- How the two API-key rows should present.

---

## Changed against the 2026-09-22 drop

**The drop is built, and four things in it are deliberately not as drawn.**
The panel is the point of truth where the two differ (George, 2026-09-22:
*"unless directly told so, do not change the designs from the panel with
whatever comes from the design output zip file"*), so these are what the
next drawing should carry rather than defects to fix back.

**[S] `weather_key` is not a row.** The drop gates four weather rows on a
provider key. Open-Meteo needs none (ADR-0047 §2a, Finding 043), so the row
would store nothing and gate on nothing; the rows hang off `idle_weather`.

**[U] `idle_minmax` is gone.** George, 2026-09-22: *"the min and max option
in settings you can remove as it is not needed."* Both forecast layouts draw
the day's high and low unconditionally now.

**[U] `skin_corpus` is six words about what a skin shows**, not two about
which directory it lives in: VU meters / Spectrum / VU meters + spectrum /
**Turntables** / **Tapes** / **All** (the two that move since 2026-09-27,
ADR-0096 as amended). Counted on the device, `templates/` is 71 meters and no spectrum at
all, so a directory-shaped option would have handed a spectrum to someone
who asked for a needle — and two of the four words would have offered
nothing (ADR-0019 as amended, ADR-0051). The fourth word was `Random` until
George renamed it: `skin_rotate` is the one that is random.
*2026-10-25:* seven words now, with *Fanart* (ADR-0112), and the row is
labelled *Skin type*.

**[U] The `device_name` warning is a different sentence.** The drop says
saving *"restarts the services that carry the name. Anything playing
stops."* ADR-0048 writes all four services and applies none of them until
the next restart, so on this device nothing stops. The row reads *"Change
only takes place after a restart of the device."*
*2026-10-25:* saving the name from Settings now restarts the device, and the
row says so (ADR-0048 amended 2026-10-05).

**Two type sizes are pinned rather than grown**, pending George: the drop
moves `--t-artist` 25 → 35 and `--t-lead` 22 → 25 for the Track header, and
the Artist tab's name and the Release tab's title used those tokens. The
drop changes neither panel, so both keep the size they had.
*2026-10-25:* George chose to grow both (2026-09-22): the Artist tab's name
is 35 px and the Release tab's title 25 px.

## Changed on 2026-09-26

**[U] No transition screen threshold; every takeover is shown.** George:
*"remove the Transition screen threshold setting. Basically the handoff
visualisation is to be shown at all times even when the takeover is nearly
instantaneous. The length of the visualisation is to be dictated by the
Transition screen length setting."* The `handoff_threshold` row is gone, and
**Transition screen length** defaults to **1.5 s** (ADR-0094). The pairs that
used to be exempt for being fast (LMS ↔ Spotify) are shown too.

**[U] The transition screen appears at once and only fades out.** The design
fades it in over 260 ms; the incoming renderer's artwork changed underneath
while it was still mostly transparent, which George saw as a blink: it should
*"start showing before the artwork is changed"*. The core now announces the
takeover before the new renderer, and the screen is opaque from its first
frame. Its contents still rise in as drawn.

## Changed since 2026-09-26

**For Claude Design, 2026-09-28.** Pictures are in [`implemented/`](implemented/),
photographed from the device (panel at 1280×800; phone at 412×915, 2×). The
setup pictures come from scripted trials at half size; **the setup password
and the join QR code are hidden in them**, and personal values (a location, a
network address) are blanked in two Settings pictures. The phone's setup page
has one picture, from George's phone (2026-09-29).
First-time setup is on branch `phase-13` (PR #37) until it merges.
*2026-10-25:* merged 2026-09-29. Since 2026-10-18 first use is in two parts
(ADR-0149, the `14-first-use` design): Music, Visualiser and Plugins moved
to the second.

### Settings

**[S] New rows.** Each is in `core/src/gexis_core/settings_registry.json`:
- **Audio → Starting volume** (`start_max`): the loudest Spotify starts at when
  it takes over (ADR-0054 §5). *settings-audio-starting-volume.png*
  *2026-10-25:* now beside Spotify's switch, under Sources › Spotify Connect.
- **Display → Clock format** (`clock_format`), 24 h / 12 h, under Clock
  (George, 2026-09-28). In 12 h the idle clock drops the leading zero and puts
  am/pm after the seconds, at their size. *settings-display-clock-format.png*
- **Display → the animated skins' rows**: `skin_motion`, `record_speed`
  (ADR-0096) and `rotation_mode`, Stepped / Smooth (ADR-0097), in
  **Visualisation tweaks**, which was *Meters and spectrum tweaks*.
  *2026-10-25:* now *Visualiser tweaks*.
- **System → Debug logs** (`debug_logs`), a switch, off by default (ADR-0103).
  *2026-10-25:* Device merged into System on 2026-10-10: Debug logs is in
  System › Help, Legal and Credits in System › About.
- **System → Legal** and **System → Credits** (ADR-0099): document rows that
  open a full-screen reader, generated from one inventory
  (`core/src/gexis_core/notices.json`). *settings-system-debug-legal-credits.png,
  settings-legal.png, settings-credits.png*

**[U] Plugins sit under their area** (George: *"beszel is system, plexamp in
sources"*): the Plugins page is headed **Sources** and **System**, by the
plugin's kind. *settings-plugins.png* *2026-10-25:* four headings now - Visualiser,
Library, Sources, System (ADR-0111, ADR-0150).

**[U] A plugin's download lives inside its own row** (George: *"The status
and the download need to be part of the pill itself otherwise it floats"*).
Under the switch: a status line (preparing, downloading, retrying with the
reason, verifying, installing, installed with the version, failed with the
reason), a progress bar with megabytes while downloading, and **Retry** after a
failure (ADR-0100 as amended). The picture shows the settled state,
*"Installed · Plexamp 4.13.2"*.

**[U] Remove, separate from off** (George, 2026-09-28, option C): switching a
plugin off stops it; **Remove** appears inside its row only while it is off
and installed, asks first, and says what goes (the download) and what stays
(settings and sign-in).

**[U] Bluetooth has gexis's own mark** (George: B1): a phone sending sound, in
the Bluetooth accent, in place of a redraw of the Bluetooth figure mark, which
is licensed only to the SIG's members. On the panel, the transition screen and
the visualiser's badge. It is square.

### The phone

**[S] A mini player pinned under the phone's Settings** (ADR-0101, George:
*"Option C - mini player. Only for phone."*): the source mark and title (tap
for a larger sheet), the panel's volume slider with its percentage, and two
toggles that act on the panel and show what it shows: the visualiser and the
idle screen. *phone-settings-mini-player.png, phone-system.png*
*2026-10-25:* the two toggles became a dock - see *The phone* in the last
section.

**[S] Settings as a bookmark with the gexis mark** (ADR-0102): a web manifest
and the gexis sound mark as the icon; Android offers a bookmark, not an
installed app, and George kept it.

### First-time setup (ADR-0031 as amended, ADR-0104) - as of 2026-09-29

Rewritten after the first full test on a blank card and George's review of it.
It supersedes the version of this subsection from 2026-09-28. The code is on
branch `phase-13` (PR #37) until it merges.

**[S] The panel has setup screens the design does not draw.** Setup is the
phone's (George: *"It is meant only for phone as the setting up device"*); the
panel shows the way in and follows along, and takes no input.

**[U] One step at a time, readable from 1-2 m** (George, 2026-09-29: *"2 QR
codes on the same screen is a bit much … center each on the screen with larger
text"*; *"what we display on the panel should be visible at 1 or 2 meters. Not
scratch your retina with the size, but decent enough to be visible while still
stylish"*). Everything centred; titles 60-72 px, lines 32 px, the network name
and password in mono at 48 px, QR codes at 340 px, **nothing that has to be read
under 30 px**; generous gaps between parts (*"everything is a bit compressed"*
was the first verdict). The header keeps the gexis mark and a mono crumb. The
steps follow what the device sees:

1. **Join** - nobody on the setup network yet: title (*"Set up gexis"* on a new
   device, *"gexis can't reach its Wi-Fi"* on one that lost its network), *"Scan
   with your phone to join the player's Wi-Fi"*, the join QR code beside the
   network name and password, and an amber **"Turn off mobile data on your phone
   while you set up"** box. *panel-setup-1-join.png*
2. **Phone connected** - a 220 px circle with a check and *"Phone connected"* at
   72 px, for 2.5 s, **once the phone has an address from the setup network**
   (not on association, which came before the phone itself showed it was
   connected).
3. **Open the page** - *"Now open the setup page"*, *"Scan with the same
   phone"*, the page QR code beside `10.42.0.1:8090` and *"Your phone may say
   'No internet'. Stay connected."*, and the mobile-data box again.
   *panel-setup-2-open-the-page.png*
4. **Carry on on your phone** - a phone icon in the circle, once the phone has
   loaded the page. *panel-setup-3-carry-on-on-your-phone.png*
5. **Joining <network>** - a pulsing Wi-Fi icon in the circle, 72 px title,
   *"Put your phone back on <network> too."*; it stays up while the player looks
   for a Lyrion server. *panel-setup-4-joining.png*
6. **Done** - a check in the circle, *"<name> is on <network>"*, *"Restarting to
   take its new name…"* when renaming, and **below it, apart, a card with the
   Lyrion mark**: *Found your Lyrion server* with the server's name and address,
   or the address given, *N Lyrion servers found - choose one in Settings*,
   *Lyrion is off*, or *No Lyrion server found*. 10 s, then the panel's own
   screens - or straight to the restart, with nothing in between (George: the
   home screen must not blink first). *panel-setup-5-done-with-lyrion.png*

- **Could not join** - the join step headed by a 64 px warning triangle and
  *"Could not join <network>"* with the reason and *"Everything else you
  entered is kept."* *panel-setup-could-not-join.png* (taken before the spacing
  was loosened).
- **The setup network did not start** - the triangle in the circle, the reason
  in mono, and *"Trying again in a moment."*
- **Starting setup…** - the gexis mark pulsing in the circle.
- **A new device on Ethernet** - one step: the page's QR code and its address on
  the home network.
- **QR codes are dark on light**, the one light element on the panel: an
  inverted code is one some phone cameras do not read.
- **No idle screen during setup**, and setup ending counts as a touch (the idle
  clock had appeared at the end, *"completely out of place"*).

**[S] The phone's steps, against `Setup.dc.html`:**
- **Backdrop as designed**: the blurred diagonal weave under the radial scrim.
  Drawn unblurred it read as *"this hash of colours"*.
- **Welcome** adds an amber card, *"Keep mobile data off - until setup
  finishes…"* (George could not reach the page until he turned it off).
- **Network saves the choice and does not test it** (one radio: the join can
  only happen after the page is gone). A wrong password brings setup back
  within about 15 s; the page opens on Network with *"Could not join <network>.
  The password was not accepted. Type the password again."*, every other answer
  kept, and **Continue goes straight to Review**.
- **Time**: the zone read from the phone, region then city by hand, and **Clock
  format (24 h / 12 h)**, now a real setting.
- **Music: Lyrion only on the user's say-so** (George: a server found and shown
  without being asked for *"looks as though we went behind the user's back"*).
  Three choices, **Continue disabled until one is picked** on a new device:
  *Find my Lyrion server* (searched once the player is on the home network; one
  found is used, several are left to Settings), *Enter an address* (the field
  appears), *I don't use Lyrion* (switches LMS off). No discovery list over the
  setup network. Then the Spotify Connect and Bluetooth switches.
  *phone-setup-music.png* (George's phone; the green slider on the right is
  Android's volume panel, and the lighter band at the bottom was a backdrop
  bug, fixed since).
- **Display**: *Panel attached* / *Headless* side by side and short at every
  width.
- **Review → Change → Continue returns to Review** for every step.
- **Finish** shows *"<name> is joining your network"*, the address
  `http://<name>.local:8090`, and what happens if the password is wrong.

## The waiting screen's sources: the library's pulsing marks (2026-10-18)

The design draws each waiting source as a wide tile, the mark on the left
and the name and status line beside it, sharing the screen's width. With
five sources on the 10.1" the names and status lines were cut ("Blue…",
"Starts …"). George: *"let's just reuse what we have on the waiting screen
with the simple or extended navigation, but without the back bar. Just the
icons pulsating directly on the wallpaper background"* - the library's
waiting footer (`WaitingServices`), its marks, rings, names and states,
without its plate.

## First use's *Where is your music?*: nothing ticked, and USB folders (2026-10-18)

The design (`14-first-use`) draws the three locations as switches with the
Music folder ticked. George: *"every the user selects we do in lyrion.
Nothing should be preselected"*, so all three start off, and with none on
the line under them says Lyrion starts with no music (ADR-0115 decisions
20-22). With *USB drive* on, the drives plugged in are listed under the
switches and each opens to its folders, *Add the whole drive* or *Add
<folder>* first, *Back up* inside a folder (decision 23; George: *"What we
need to add though is a folder selection from USB"*) - not in the design.
The same browsing is in Settings → Library → Lyrion Server → *USB folders*.

## First use's *Upload a backup*: the file's name, then what it restores (2026-10-18)

The design's tile names the backup's player and date, with what it brings
as one line under it. George: *"Each item should be on its own line with a
checkmark grouped by the section the setting is in. Just the filename stays
in the tile."* The tile holds the file's name and *Ready*; below it, one
block per Settings section in the design's own ticked list - the left
column of its *Split* block, drawn without the right column when that is
empty (ADR-0131 amended 2026-10-18).

## Changed since 2026-09-29

**For Claude Design, 2026-10-25.** Collected from the records for Phase 19's
brief. No new pictures yet: `implemented/` is still 2026-09-28's. Sizes on a
bar are CSS pixels of its 1850 x 400 page (drawn at 0.8 on the 11.9" bar).

### The whole panel

**[U] Text size, 90-130 %** (Display; ADR-0148). Every font scales. Above
100 % Home's tiles grow (200 to 260 px at 130 %); layouts, icons and buttons
keep their size, so titles cut off sooner.

**[S] The phone's pointer on the panel.** The Dot and Arrow pointers come from
Claude Design's *Cursors* handoff (2026-10-05, not in `source/`), built
without its jump to a control's centre, its glide or its busy states. It
hides after 5 s; its outline follows anything pressable and is cut where
covered; under it a tab shows its own underline instead of a ring (ADR-0121
amended 2026-10-06 and 2026-10-14).

**[U] The Home Assistant dashboard** (ADR-0156). Full screen, with nothing
over it but a 44 x 104 tab at the right edge, an X that dismisses it (George
chose the edge tab). A page that cannot be shown says so, with Close. Its
buttons: on Now Playing after the visualiser's (a house outline, only once an
address is set), in a bar's tray, and *Room* in the phone's dock. In its
scheduled hours it stands where the idle screen would; the visualiser takes
over from it.

**[U] Display standby** (ADR-0135): a black cover; a touch, music or the
phone wakes it.

### Now Playing, on the standard screens

**[U] Minimise** (ADR-0122): a 52 px round button with a down chevron at the
artwork's top-left corner. It goes back to the library exactly as it was left
(path and scroll), with the mini strip. Home stays bottom left and opens the
root. There is none with Lyrion off.

**[U] Names and titles open their pages** (2026-10-14): the Artist tab's name,
the release title on Track and Release, a similar artist's chip when the
library has that artist. They keep their own size and colour.

**[U] The Lyrics tab** shows five lines with a 7 % fade at the edges (the
design masks 30 % / 70 %), and no heading (2026-10-07).

**[U] Now Playing opens only on a track** (2026-10-19): a source with no title
leaves Home showing.

### Home and the library

**[U] Home's Artists tile reads *Album Artists*** in every mode (George,
2026-10-06).

**[U] Navigation is one choice: Simple, Extended or Off.** Extended adds
Lyrion's own menus (13f) - My Music, Favourites, the app categories and Apps -
as one sideways row of 200 px cards (13f draws 219) with no scroll-snap. Off
shows the waiting screen as Home while Lyrion still plays (ADR-0118; ADR-0149
decision 14). Lyrion's menus are otherwise built as drawn; George's own look
at them is still to come (Phase 30, `ph-lyrion-menus`).

**[U] A tap on a row shows only the teal selection**, and a second tap puts
its actions away again, so only Play plays; 13f and `Now Playing.dc.html` play
on the second tap (George, 2026-10-15 to 2026-10-21).

**[U] Album and playlist pages show a track's own artist** under its title
when it differs from the album's; an app's playlist has *Play playlist*
(2026-10-14, 2026-10-21).

**[S] An album an app cannot stream** opens with its tracks marked *Not
available* and inert, a line saying so in place of Play, and its cover dimmed
to 0.45 in grids (2026-10-06).

**[S] An app's Search folder opens straight to its field**; past searches are
not listed (ADR-0118).

**[S] Letter headers follow Lyrion's own sort**, and the jump rail is drawn
inert while its index loads, so nothing moves when it lands.

**[S] The artist page's genre pills stop at two rows**; a pill too long for one
line is left out (2026-10-04).

**[S] Not built:** on an app's album page the artist is plain coral text, not
the link 13f draws.

### The waiting screen, backgrounds, the idle screen

**[U] The waiting screen** (ADR-0133): its own wallpaper under a veil; the
clock, date and player name top left; Settings top right; the pulsing marks
at the foot; the picture's credit. `Now Playing.dc.html`'s plain weave with
180 px rings and 14's *Start music from your phone* line are gone.

**[U] While a new player first reads its library**, a centred plate on the
waiting screen: *Lyrion · Step n of 5*, the step as a 40 px title, a bar with
a percentage, Lyrion's detail and one line. Lyrion's mark leaves the sources
until then (ADR-0149 decision 43).

**[U] With no artwork, the blurred background is a built-in *Calm* sunset**,
not the bare weave; the waiting and idle screens show it until their first
picture loads (2026-10-18).

**[U] Gexis wallpapers are built in and the default**: Calm, Colourful,
Psychedelic, following the time of day, the seasons and holidays; Home and the
idle screen each have their own background rows (ADR-0133).

**[U] Pictures are placed by their subject** - faces, then a person or animal,
then whatever stands out. When the subject does not fit, the picture shrinks
to at least 75 % of the width over its own blur, or is skipped. The design
centres every picture (ADR-0120).

**[U] Seven weather icon sets** (Modern, Futuristic, Photographic and
Atmospheric added). Between sunset and sunrise the current weather's sun is
the moon in its real phase; *Static* stops every animation (ADR-0153,
ADR-0154).

**[U] The idle screen is off on a new player**, and the forecast's *None* is
called *Today only* (ADR-0133).

**[S] On the takeover screen** a plugin with no mark shows its initial in the
ring (2026-10-01).

### The bar (13b)

*Now Playing*
- **[U]** The artwork runs edge to edge, 400 px tall, flush left, square
  corners (the design: 336 px, radius 20, in 32/40 padding); artist 36, album
  32, the year 28 after the album (the design: 28/24/21). George, 2026-10-04.
- **[U]** The lyrics switch sits bottom right by the queue, and the source mark
  takes its place top right. Lyrics have no title header; the lines are
  centred, synced at 34 px and plain at 30 px (the design: 26/22).
- **[U]** The lyrics switch is always there, with *Instrumental*, *No lyrics*
  and *Retry* states (the design hides it without lyrics). With no position
  the progress bar is a faded line and the times hide (round-2 review,
  decisions 5 and 6).
- **[U]** A control the source lacks is removed; one that cannot work just now
  is dimmed to 0.4 (round 2 removed both; George, 2026-10-21).
- **[U]** Minimise, which the design does not draw: 60 px at 24/24 over the
  art, the chevron pointing right.
- **[U]** The pull handle is centred on the space right of the art. A tap on
  the 44 px band opens the tray too; a control under the finger wins.

*The tray*
- **[S]** A *Dashboard* button after the visualiser's, once a Home Assistant
  address is set (ADR-0156).
- **[H]** Home, Visualiser, Dashboard and Mute act when the finger lifts.
  Chromium sent no click for a tap within about a second of the pull: 9 of 9
  recorded taps, 0.52-0.97 s after it. A mouse still acts on its click
  (2026-10-24).
- **[U]** It stays open as the volume drawer does (above); one opened by a
  change from elsewhere takes no touch for its first 400 ms.
- **[U]** A swipe up closes it from anywhere on it, or from the dimmed screen
  below; on the slider the first 8 px decide between closing and sliding (the
  design has only the bottom 44 px band). George, 2026-10-04.
- **[U]** The slider's fill is Lyrion teal for every source (round 2: the
  source's accent).

*The library*
- **[U]** With nothing playing, the rail shows the waiting sources as pulsing
  marks without text, sized to how many there are (64 / 59 / 47 px); round 2
  has an empty slot and an inert play button (George, 2026-10-04).
- **[U]** Rows keep the standard screens' reveal - Play now, Add to queue, Add
  to playlist, 44 px. A tap no longer plays; a revealed row is teal, with no
  press effect (ADR-0109 amended 2026-10-01).
- **[U]** Playlist columns are 420 px wide, not 300. Radio is two rows that
  scroll sideways with a third of the next column showing, in the standard
  screens' category shapes and tints.
- **[S]** The artist page has no Top tracks and no tags, though round 2 draws
  both.
- **[U]** With Extended navigation, My Music, Favourites and Apps join a
  sideways row of 196 x 300 tiles that widens with Text size, over Now
  Playing's lighter veil (ADR-0118, ADR-0148).
- **[S]** The jump strip is `#` and 13 letter pairs; Lyrion's lettered lists
  use the same strip.

*Settings on a bar*
- **[U]** Settings stays on the bar, opened from its card on Home in the
  content area; ADR-0109 had put it on the phone only (2026-10-03) and is
  amended (George, 2026-10-25).
- **[U]** Sheets are 376 px tall and min(760, width - 48) wide; a confirmation
  takes its content's size, centred (2026-10-08). The value sits beside its
  slider (a 170 px + 1fr editor), an empty list is compact with a 40 px ring,
  and a long note scrolls (2026-10-24, after George found a slider's buttons
  cut off).
- **[U]** *Attached screen* is chosen in two steps, maker then model, as in
  `Settings.dc.html`, not side by side as *Bar States* draws them (George,
  2026-10-25).

*Moments*
- **[U]** Wallpapers fill the bar by cropping up to 70 % (25 % elsewhere),
  each placed by its subject; a topic mixes its wide pictures (2.4:1 and
  wider) with the usual ones, each once a round (ADR-0120 amended 2026-10-23).
- **[U]** The idle row is measured: today's type steps down to 0.8, then
  forecast days drop.
- **[U]** On the takeover screen the notes travel the line (George,
  2026-10-04).
- **[U]** The waiting screen: a clock column on the left and the pulsing marks
  beside it (the design's *wait* board uses rings and discs; ADR-0133).
- **[U]** *Keep this screen?* counts 2 minutes, not 30 s, from when the
  question is drawn, and is asked only when the picture changes; a change of
  rotation alone asks *Keep this rotation?* (ADR-0109 as amended).

### Settings

- **Eight categories**, in this order: Library (only with a library plugin
  installed), Sources, Handoff, Audio, Display, Enrichment, Plugins, System
  (ADR-0150). Device merged into System under headings - This player,
  Network, Updates, Backup and reset, Help, About, Power - and LMS is called
  Lyrion everywhere (2026-10-10).
- **Display has ten sections**: Panel, Display standby, Home Assistant
  dashboard, Touchpad, Volume, Photo service and location, Home screen, Idle
  screen (with its own switch), Visualiser, Visualiser tweaks; *Personalise*
  at the top (ADR-0149 decision 31).
- **One Volume row**: Hardware, Software or Fixed (ADR-0127). **Navigation**:
  Simple, Extended or Off.
- **Text size** 90-130 % (ADR-0148); **Screen brightness** 10-100 %, on DSI
  screens only (ADR-0158).
- **Attached screen** and **Screen port** are tiles with *Change* (ADR-0147).
- **Display standby has its own section**, and no *Turn the screen off* row:
  the phone's *Screen off* pill does it (George, 2026-10-11). Its interval
  grid is drawn only in 14-first-use's standby step.
- **A Cable row** while a cable is in (ADR-0123): its sheet shows the facts
  and Automatic / Manual with fields; the connected Wi-Fi network's sheet
  shows signal, speed, band and channel, with the same form; a banner on every
  page asks to keep a new address within 60 s.
- **Enrichment's two sweep rows are one tile**; a TheAudioDB key (ADR-0120).
- **Option sheets explain each option beside it.**
- **Plexamp's row** reads *Claimed* with *Claim again* (ADR-0119).
- **API explorer**: a switch, off by default; the API's page at `/api` on the
  player (ADR-0152).

### Screens and sheets no design draws

**[U] Updates** (ADR-0110): built from the existing design system on purpose,
never sent to Claude Design (George). A read-only *Release* row (number ·
channel); a *Software update* tile (the last check, notes waiting, one
button: *Check for updates*, *Update…*, *Updating…*); one modal on the phone
and in the panel's Settings: checking, available with its notes, the
playback warning, six steps ticked with bars, *Updated* or *Did not update*,
Done. On the panel a full-screen lock takes no input until Done, and lets go
after 10 min.

**[U] Release notes** are sections (*New*, *Fixed*, *Good to know*) with
bullets; an update waiting shows one block per release skipped; *Change logs*
opens the reader with the last 10 releases (ADR-0116).

**[S] Problem report and Hardware feedback**, on a phone or computer; on the
panel the sheet says to open Settings on a phone. The report: what happened
with how-often chips, then a ticking checklist, then Send. Feedback: Screen,
Sound, Anything else, Send. One shared Send step - GitHub, or download and
e-mail with Copy; kept feedback turns its row into a tile with *Send again* /
*Start over* (ADR-0125, ADR-0126, ADR-0138).

**[S] The test pattern** on the panel, asked for from the phone: a coloured
line on each edge, then a circle at a corner for each of four taps; the phone
shows how far off each tap landed (ADR-0126).

**[U] Factory reset**: the confirm button is held for 3 s while a bar fills, a
check that needs no keyboard (George). Then a reset screen covers the panel
and every phone, with no way out; the phone's says how to reach setup
(ADR-0132).

**[S] A different screen attached**: a sheet at start, on the panel and the
phone - *Use it*, *Choose*, *Not now* (ADR-0109 amended 2026-10-03).

**[S] Keep this screen, beyond 13b's drawing**: the phone gets a *Keep* / *Go
back* banner; a screen with no touch shows no buttons and says to answer on
the phone; DSI panels answer on the panel (ADR-0147, ADR-0158).

**[U] The settling card**, on the panel and over the phone's Settings: one bar
per download, *Installing…* while a package goes in, *Use the player now* from
the start, a failure named with *Settings → Plugins* and OK. Only the phone's
*Getting ready* is drawn, in 14-first-use (ADR-0128).

**[U] A network lost after boot** shows no strip; after two minutes, the setup
*Join* screen (ADR-0134).

### The phone

**[S] The mini player is a dock**: Home, Playing, Lyrics, Meters, Room and Idle
under a *Panel* heading, with the *Screen off* pill; opening its sheet adds the
touchpad (George's mockup D2, 2026-10-21; ADR-0101 amended).

**[S] The player switcher** (ADR-0136): a button at the right end of the title
line opens *Players*, each with its state (*Playing · Spotify*, *Paused ·
Lyrion*, *Idle*), this one marked; another opens in the same tab. Phone only.

**[S] The touchpad** takes half the phone's height, with two-finger scrolling
and a 1-3x pinch; over the dashboard its taps and typing become real input
(ADR-0121, ADR-0157).

### Phase 19: the focus and the card (2026-10-25)

Built from `source/19/` the same day; checked with mocked data against its
pictures (ADR-0161, ADR-0163).

*The focus ring*
- **[U]** Which form a control gets is a rule, not drawn per control: inside
  on rows and wherever a neighbour is under 12 px or the ring would leave
  the screen, outside otherwise. Now Playing's tabs have square corners, so
  their ring (radius 10) sits closer than `F07`'s.
- **[U]** The bar tray's slider is ringed round its rail and knob, not its
  taller touch area (which ran off the screen); the drawer's slider is
  ringed whole, as `F13`.
- **[S]** On a bar the library's rail (ADR-0109's 124 px column) is one
  control, Now Playing, and its play control a second below it; `B01` and
  `B04` draw a bottom strip. The tray comes down from the top, as built
  and in the manual, where `B02` and `B05` draw it at the foot.
- **[S]** Lyrion's own menu tiles (`F02`) were not seen with data: the
  check had no Lyrion server. They are buttons like Home's, so the same
  rules hold.

*The card*
- **[S]** The album line has no year: Home Assistant carries none.
- **[U]** The fixed output's note fits on one line where `Le` wraps it; a
  clamped title ends with an ellipsis, as the README asks.
- **[U]** The transport follows the player's rule, not the design's
  "removed, never greyed" (George, 2026-10-25, after trying the card): what
  the source has is shown, and a control it cannot use now (Next on the last
  track) is greyed at 0.38, as the quick-action tiles are. What the source
  lacks is still left out (`Lf`, `Lg`).
- **[U]** The quick actions are the phone's Panel views (George, 2026-10-25:
  Idle and Meters were missing): Home, Now playing, Lyrics, then Meters, Room
  and Idle, each left out where the phone leaves it out - three to a row in
  the full form, wrapping in the compact one, where the D-pad's button can
  fall to a second row. A view that is up has the accent's outline.


## The equaliser (Phase 20, 2026-10-26)

Built from `source/20` (look 3a, Ridge; ADR-0162, its *Built* section for the
decisions). Not yet seen by George on a device.

- **[U]** The headroom figure is the core's, not the drawing's: the worse of
  44.1 and 48 kHz, rounded strictly up to 0.5 dB, where `eq-data.js` allows
  0.05 dB the other way - so the sample *Evening* reads 3 dB, not 2.5.
- **[U]** The phone's curve spans its gradient over its own box (200 high),
  so the step from coral to blue falls on 0 dB; the drawing spans it over
  the panel's 240 and puts it below 0 dB.
- **[U]** Edit in the quick change opens the editor as a screen of its own,
  where it was opened; Back returns there. Settings → Audio opens the same
  editor inside Settings.
- **[U]** On the D-pad a band is an upright slider: Up and Down move it,
  Left and Right go to its neighbours, and the ring goes round the knob.
- **[S]** *Yours · 0 of 10* shows with nothing saved, so the list says where
  a saved setting will go.
- **[S]** A refused name (taken, too long) is said in the sheet, in amber,
  under the field; the drawing has no such state.
- **[U]** The headroom note says the volume gives the lowering back (George,
  2026-10-26, ADR-0162 D3 as amended): *Lowered by 5 dB so the boost cannot
  clip; the volume gives it back up to 65%* in the editor, where the drawing
  ends at *clip*; in the quick change *As loud as Flat up to 65% of the
  volume; above it, up to 5 dB quieter*, where the drawing had the editor's
  line. The badge stays the lowering; Fixed keeps the drawing's words. The
  wording is Claude's (C17), confirmed by George the same day.

## The phone remote (Phase 21, 2026-10-27)

Built from `source/21`'s second design, `Phone Remote v3` (ADR-0164, its
decisions; ADR-0165 for mute with Fixed volume).

- **[S]** Picking another player in the menu opens that player's own page
  in the same tab (C1); the drawing switches in place.
- **[S]** The seek bar seeks where the renderer can (Lyrion, Spotify; C2);
  elsewhere it is the drawing's inert rule, with no knob, as Bluetooth's.
- **[S]** With Fixed volume on an output with no volume control of its own,
  the locked row has no mute: nothing can silence that output (ADR-0165,
  C3).
- **[S]** The cover is the panel's: the renderer's, else the one the library
  enrichment found, else *artwork pending* - for any source, Bluetooth
  included (C4).
- **[U]** The EQ sheet's note is Phase 20's, with the volume giving the
  lowering back (C6); Custom leads the chips, with its dot, while it is the
  setting in use. The bar names *DSD* while DSD stands the equaliser aside.
- **[S]** The idle screen, Room and Meters are offered only where the player
  has them; Playing and Lyrics are dimmed with nothing playing (C7).
- **[S]** A player stopped with a source reads *Idle*, the drawing's third
  state.
- **[U]** On a phone shorter than the drawing's 780 px the touch area gives
  way first, to 312 px, and the cover without a screen to 140 px; only then
  does the Remote page scroll (D10, C10).
- **[U]** The scroll strips' 24 px steps scroll what is under the pointer by
  those 24 px, the content following the finger (D3).
- **[S]** A volume or mute that failed, and a character the player could not
  type, are said in a short note over the page (C13); the drawing has none.
- **[U]** The panel's fixed rows (the volume drawer, the bar's tray) have the
  mute button, and the volume button shows the crossed speaker while muted
  (ADR-0165 §4); `Now Playing.dc.html` is locked and does not draw them.

