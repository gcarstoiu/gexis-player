# What the panel does that the designs do not draw

**For Claude Design, 2026-09-18.** George asked for a diff so the mockups can
be brought up to date before Phase 9's UI sweep.

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

**[U] Press feedback shrinks; it does not fill.**
The design's grey press fill read as a flash. Controls keep their resting
fill and scale to 0.95 (the mini strip to 0.995).

**[U] The volume glyph is the drawer's 30 px one everywhere**, including now
playing's button and the mini strip, not the design's 26 px and 24 px
variants, whose three arcs merge at full volume.

**[U] The volume drawer opens on a change from elsewhere.** A phone's volume
change raises it; it closes 3 s after the last change. The panel's own
changes and a takeover's restored level do not open it.

---

## Now playing

**[S] The tabs are Track, Lyrics, Artist, Release - all four now work.**
The design's Track panel has two forms and both are built: the tall block,
and a **compact one when the track has synced lyrics** - title, artist and
album on one line, a rule, then the words following the playhead. The compact
form is also held while the lookup runs, so the panel does not jump.

**[S] An attribution line under the biography and the lyrics.**
The designs have no element for it. Wikipedia's text is CC BY-SA and
MusicBrainz's tags are CC BY-NC-SA: the credit is a licence term, not
decoration (ADR-0040 §4). It reads *"From Wikipedia, CC BY-SA"* or *"From
LMS"*, in mono, under the text it credits. **This wants drawing properly.**

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

**[S] The artist page's About block is measured, not fixed.** It takes as
much height as is left while the first row of albums still shows a quarter of
itself (George, 2026-09-18), with More/Less for the rest. A fixed height was
wrong in both directions - it hid the text on a short biography and the
discography on a long one. Biographies arrive as plain text with paragraph
breaks and no markup; the panel renders paragraphs and shows the first
twelve, because LMS returns whole encyclopaedia articles for some artists
(56,573 characters for 2Pac).

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

**[S] 54 rows, 6 wired.** The design's seven groups are intact and the keys
match, with four deviations already recorded: `idle_grace` merged into
`idle_timeout`; `travel_curve` decided; `drawer_on_external` and
`drawer_autohide` added under Display › Panel; and two new keys the design
has no row for - **`listenbrainz_token`** and **`fanart_key`**, both per-user
API keys (ADR-0022). Those two want drawing.

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

**[U] `skin_corpus` is four words about what a skin shows**, not two about
which directory it lives in: VU meters / Spectrum / VU meters + spectrum /
**All**. Counted on the device, `templates/` is 71 meters and no spectrum at
all, so a directory-shaped option would have handed a spectrum to someone
who asked for a needle — and two of the four words would have offered
nothing (ADR-0019 as amended, ADR-0051). The fourth word was `Random` until
George renamed it: `skin_rotate` is the one that is random.

**[U] The `device_name` warning is a different sentence.** The drop says
saving *"restarts the services that carry the name. Anything playing
stops."* ADR-0048 writes all four services and applies none of them until
the next restart, so on this device nothing stops. The row reads *"Change
only takes place after a restart of the device."*

**Two type sizes are pinned rather than grown**, pending George: the drop
moves `--t-artist` 25 → 35 and `--t-lead` 22 → 25 for the Track header, and
the Artist tab's name and the Release tab's title used those tokens. The
drop changes neither panel, so both keep the size they had.
