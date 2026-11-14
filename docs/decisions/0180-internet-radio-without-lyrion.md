# ADR-0180 — Internet radio without Lyrion

**Status:** **Accepted** 2026-11-13 (George: decisions 1-7 as recommended,
8 as (b) with the dashboard card); proposed 2026-11-12 by Claude, Phase 31
(`ph-radio`).
**Relates to:** [ADR-0030](0030-library-typed-radio-slimbrowse.md) and
[ADR-0038](0038-library-and-radio-on-the-panel.md) (Lyrion's radio on the
panel), [ADR-0079](0079-with-lms-off-the-panel-is-two-screens.md) (with
Lyrion off, two screens), [ADR-0040](0040-enrichment-providers.md) (covers
looked up for any source), [ADR-0151](0151-mpd-on-the-player.md) (MPD,
parked), [ADR-0162](0162-a-simple-equaliser.md) (the stage),
[ADR-0166](0166-multiroom-for-every-source.md) (groups).

## Context

**What the phase asks** (`docs/DEVELOPMENT.md`, Phase 31): a radio directory
for players that only stream, with no Lyrion server. The ADR settles which
directory, how a station plays and shows on Now Playing, favourites, and how
it sits beside Lyrion's Radio on a player that has both.

**Today** (read from the code at 1.16.1 plus the review's fixes):
- Radio is Lyrion's: the core walks Lyrion's `radios` tree (`radio.py`) and
  Lyrion plays the station. Lyrion's favourites show only under *Extended
  navigation* (ADR-0118); the player keeps none of its own.
- With Lyrion off there is no Radio at all: the panel is the waiting screen
  and Now Playing (ADR-0079). The phone page browses nothing.
- Nothing on the image plays an address by itself. The FFmpeg libraries are
  there (Squeezelite links them); no program uses them that way.
- The equaliser's stage does not run at 32 kHz and below (`equaliser.py`,
  `runs_at`): such a stream plays without the equaliser or room correction.
- A cover for a track that arrives without one is looked up for any source
  (ADR-0040, `artwork_lookup`), radio included.

**The directories** (desk research, 2026-11-12):
- **radio-browser.info** is the only one open to any software: no key, the
  data public domain ([its site](https://api.radio-browser.info/),
  [its dump](https://db.radio-browser.info/)), about 52,500 stations, each
  checked at least daily from several countries (`lastcheckok`), the stream
  address after playlists and redirects already resolved (`url_resolved`).
  Music Assistant, Home Assistant's Radio Browser, GNOME Shortwave and a
  2026 Lyrion plugin use it.
  - **Its weakness is one server**: on 2026-11-12 the server list named only
    `de1`; it was down on 2025-03-30 and answered 503 everywhere on
    2026-10-23. One maintainer; no published rate limit; a descriptive
    `User-Agent` asked for.
  - A play reported through `url/{uuid}` counts a *click*, once a day per
    address and station; the address is kept 24 hours for that.
- **TuneIn** needs a partner agreement for production use
  ([developer.tunein.com](https://developer.tunein.com/cfp_login)); the
  open-source projects that use it reuse partner ids they were not shown to
  hold. **SHOUTcast**'s licence bars open-source integrations (4.4c) and
  storing its data (4.5d). **radio.net** allows private use only. None is
  usable here.

**Playing a stream** asks for: `.pls` and `.m3u` playlists, HLS (about 13 %
of a sample, more among the most played), redirects and https, MP3 and AAC
mostly (Opus, Vorbis and FLAC rare), titles from ICY metadata
(`StreamTitle`) or HLS tags, and reconnecting after a drop with a watchdog of
its own (FFmpeg's reconnect options alone are reported not to recover live
streams reliably).

**What each engine adds to the image** (measured 2026-11-12 on sofapi:
`apt-get -s install --no-install-recommends`, installed sizes from
`apt-cache`, on its package set at the time): PyAV (`python3-av`) 25
packages, 61 MB; `mpv` 31 packages, 59 MB; GStreamer with its Python binding
83 packages, 163 MB. PyAV and mpv bring the same FFmpeg filter and device
libraries; the decoding libraries are already installed. No CPU figures for
radio on a Pi 4 were found published: to be measured.

## Decision

1. **The directory is radio-browser.info** (decision 1), read by the core:
   - the server found through `all.api.radio-browser.info` (or its SRV
     record), tried in turn, never one address written in;
   - `User-Agent: GexisPlayer/<version>`; only stations whose last check
     passed (`hidebroken`);
   - every answer kept on the device for a day, so browsing again costs
     nothing and a directory that is down still shows what was seen;
   - **favourites never need it** (item 5): they keep the station's address
     and name, and play with the directory down.
2. **What Radio offers**: *Favourites*; *Popular here* (the country set in setup
   for Wi-Fi, changeable); *By genre* (tags), *By country*, *By
   language*; and *Search* by name. Each station row shows its name, logo,
   country and codec with its bitrate. No curated list of our own: moOde's
   shows what keeping one costs.
3. **The engine is mpv**, run by the core as a renderer of its own,
   `gexis-radio.service`, controlled over mpv's JSON socket - the shape of
   the Spotify adapter (go-librespot over a local API):
   - mpv reads the playlists, follows redirects, plays HLS and reports
     ICY titles as a property; the adapter adds a watchdog (no audio for
     10 s: reconnect, three times, then stop with *The station is not
     answering*);
   - it plays to `output` at the stream's own rate; a stream at 32 kHz or
     below is resampled to 48 kHz so the equaliser and room correction
     still apply (it is lossy already);
   - the unit runs only while radio plays, and is stopped when the source
     is switched off (ADR-0077).
   - *Not PyAV*: it would need our own playlist reading, ICY parsing,
     buffering and reconnecting - what mpv already does - for the same
     size. *Not GStreamer*: 163 MB, HLS only through `playbin3`. *Not MPD*:
     parked (ADR-0151), and it would bring a second library model.
   - **Measured before it is built on** (item 11, step 2): CPU on a Pi 4 for
     MP3, AAC, HE-AAC and HLS; the rate reaching the card and the stage;
     titles from ICY and from HLS; a drop and its recovery. If mpv fails
     there, PyAV is the fallback, and the choice comes back to George.
   - **Measured 2026-11-13**
     ([Finding 146](../findings/146-mpv-as-the-radio-engine-on-a-pi-4.md)):
     mpv confirmed - eleven stations, `.pls` and HLS included, at 3-6 % of
     a core and 65-87 MB. What it adds to the renderer: FFmpeg's reconnect
     on and a 5 s network timeout (a cut and a freeze then go unheard on a
     station buffering more than 5 s); any end of a live stream taken as a
     drop (mpv reports a cut and a station gone as an ordinary end of
     file); the watchdog counting from the playback stopping; stereo asked
     for (a mono station decodes as one channel). The rate at the card,
     the stage and a stream at 32 kHz or below are measured in the build,
     on a player not in a group.
4. **How a station plays and shows**:
   - Tapping a station plays it: the radio renderer acquires the output as
     the others do (arbitration, ADR-0027); another source takes over and
     stops it (a live stream is stopped, not paused: `release_action`
     disconnect). Play after a stop starts the same station afresh.
   - **Now Playing**: the title and artist from `StreamTitle`, split at its
     first " - " (artist, then title) when both halves are there, the whole
     line as the title otherwise; read as UTF-8, else Latin-1. The album
     line is the station's name, as ADR-0038 §8a does for Lyrion's radio.
   - **Artwork**: the track's cover when the lookup finds one (ADR-0040),
     else the station's logo, else the radio mark. A third of the
     directory's logos are missing and some are `.ico`: those count as none.
   - The quality line shows the codec and bitrate (*AAC · 128 kb/s*); no
     position or seek; Next and Previous as decision 6.
   - Groups as the other sources not Lyrion's (ADR-0166).
5. **Favourites** (decision 4): the player's own list, kept in its settings
   (so a backup carries it), in the order the owner sets; a heart on Now
   Playing and on each station row; reordered and removed on the phone and
   the panel. Each keeps the directory's id, name, logo and address; the
   address is asked for again from the directory at play time when it
   answers (stations move hosts), the kept one used when it does not.
6. **Settings (ADR-0022)**, confirmed by George 2026-11-13 and appended:
   - **[N]** Internet radio on or off, as each source (decision 7);
   - **[N]** the country for *Popular here* (setup's Wi-Fi country by
     default);
   - **[H]** the watchdog's 10 s and three tries; **[H]** a day's cache;
     **[H]** streams at 32 kHz and below resampled to 48 kHz;
   - **[H]** FFmpeg's reconnect on and a 5 s network timeout, confirmed by
     George 2026-11-14 after Finding 146 and appended;
   - counting a play has no setting (decision 5).
7. **What leaves the player**: the directory sees the player's address and
   what is browsed and searched; each station's server sees the address
   that plays it. No account, nothing else. Said in the FAQ.
8. **The screens are designed first** (Claude Design, as Phases 29 and 30):
   the panel's Radio with and without Lyrion, the bar's layout, the phone's
   Radio, Now Playing for a station, the favourites, the directory
   unreachable. Built as drawn once George has picked.
9. **The public documents**: the manual's Radio and Sources, the FAQ (what
   the directory is, what leaves the player, why a station may not play),
   the technical guide (the renderer and its unit), README's sources.
   The plugin manual is untouched: this is not a plugin.
10. **Home Assistant, in this phase** (decision 8): the favourites as the
    player entity's sources; the directory browsed and searched in Home
    Assistant's media browser; a Radio view with the favourites on the
    dashboard card (in the design). Released after the player's, as for
    multiroom. **Not in this phase**: recording, a station's schedule,
    alarms, podcasts.
11. **Steps, each checked before the next**:
    1. This ADR decided; the settings confirmed and appended to ADR-0022.
    2. **The engine measured on sofapi** (checked not in use first), with
       public stations named in the finding, never a listener's: a finding
       (146) - CPU, rates, titles, drops; the engine confirmed.
    3. The design brief, then George's picks.
    4. The core: directory client, favourites, the renderer and its unit,
       routes; tests that fail first, the real directory asked once
       (Lesson 40) and a fake that fails as it does (Lesson 83).
    5. The screens: panel, bar, phone; layouts checked with made-up
       stations.
    6. The documents; a preview on sofapi; George's regression pass; the
       release with notes George approves.
    7. The integration (item 10), released after the player's.

### Acceptance (also in `docs/DEVELOPMENT.md`)

1. With Lyrion off, a station found by country, genre or name plays from the
   panel and from the phone; Now Playing shows the station, and the title
   and artist when the stream sends them.
2. Favourites survive a restart and a backup restored, and play with the
   directory unreachable.
3. Another source takes the output and gives it back, and Radio plays in a
   group, as the other sources do.
4. The equaliser and room correction apply to every stream, one at 32 kHz
   included.
5. A stream cut mid-play recovers; one that stays down stops with a
   message.
6. With Lyrion on, Lyrion's radio opens from Radio and works as before.
7. The CPU it takes on a Pi 4, measured at Finding 146's figures (3-6 % of
   a core) or better.
8. In Home Assistant, a favourite plays from the player's sources and from
   the card, and the directory is browsed and searched from the media
   browser.

## The core, built 2026-11-14 (step 4)

On `ph-radio`, the screens not yet (the design had not reached the
repository). What the build settled that the decision above leaves open:

- **Routes under `/stations`**: Lyrion's `/radio` stays as it is. The
  overview (favourites, the country, whether the directory answered),
  *Popular here*, a list by genre, country or language, search, play (a
  station a list gave, or a favourite by id), the favourites (add, order,
  remove) and a station added by its address. The renderer is `radio`; the
  published state gains `radio` (the station; connecting, playing,
  reconnecting with its try, stopped, not answering; a favourites revision).
- **The volume** (`VolumeMechanism.OUTPUT`): mpv plays at its own 100 % and
  the panel's slider is the output's level. Nothing is kept per station.
- **Favourites** are kept with the settings as `_radio_favourites`, a value
  no Settings row shows; the whole store is what a backup carries.
- ***Popular here*'s country** is chosen from tzdata's `iso3166.tab`; until
  it is set, the time zone's country, as setup's Wi-Fi country is found.
- **The artwork**: the cover is looked up as for any renderer that sends
  none (the recording, as for Lyrion's radio; the album-based lookup is
  skipped, the album line being the station's name); the station's logo
  stands in until one is found, and when none is.
- **A station added by its address** must sound within 20 s to be kept; it
  plays at the address given and is not counted with the directory.
- **A takeover while a station is still being looked up** stops that play;
  a reload the watchdog has begun always finishes. Stop stops the unit.
- **A rewritten chain** (an output, a group, the visualiser's tuning): the
  radio's unit is stopped with the other renderers and the station loaded
  again after; the switch stops what plays and never enables the unit.
- **Checked against a real mpv** (0.41, on the development machine, a silent
  output, the unit's own options): the options are accepted; a 22.05 kHz
  mono stream left mpv at 48 kHz in stereo; a stream that ended was loaded
  again after the watchdog and played; an address that answered nothing
  stopped as not answering after three tries; titles arrived as `icy-title`.
  **Not yet**: a player (mpv 0.40), the format at the card, the stage, a
  group, the CPU, an hour's memory.
- **Placeholders until the design**: the source's accent (the warning
  token's colour today) and its mark (none).

## Decided 2026-11-13 (George)

Decisions 1-7 as recommended: radio-browser.info; one Radio screen with
*Lyrion's radio* inside it; with Lyrion off, the waiting screen gains Radio;
the player's own favourites, a station added by its address from the phone;
each play counted, said in the FAQ; Next and Previous step through the
favourites; on by default and offered in first use. Decision 8 as (b): the
phone and Home Assistant in this phase, Home Assistant with its sources, the
media browser and a Radio view on the dashboard card. The settings in item 6
confirmed.

## Decisions for George (as proposed)

- **Decision 1, the directory.** (a) **radio-browser.info**, *recommended*:
  the only one open to us; its one server is the risk, met by the day's
  cache and favourites that play without it. (b) Also TuneIn: no agreement
  to use it under.
- **Decision 2, beside Lyrion's Radio, with Lyrion on.** (a) **One Radio
  screen**, *recommended*: the player's directory, with *Lyrion's radio* as
  one more entry in it that opens Lyrion's tree as today. (b) Two tiles,
  *Radio* and *Lyrion radio*. (c) Lyrion's Radio only while Lyrion is on;
  the player's only without it.
- **Decision 3, with Lyrion off.** (a) **The waiting screen gains Radio**,
  *recommended*: ADR-0079's two screens become three (waiting, Radio, Now
  Playing), and Now Playing gains a way back to Radio; where, the design
  shows.
  (b) Radio becomes the home in place of the waiting screen.
- **Decision 4, favourites.** (a) **The player's own, separate from
  Lyrion's**, *recommended*, with **a station added by its address** (from
  the phone) for one the directory lacks. (b) The same, without adding by
  address. (c) Lyrion's favourites shown beside them when Lyrion is on.
- **Decision 5, counting plays.** (a) **Count each play with the
  directory**, *recommended*: it is how *Popular* is ranked, Music
  Assistant and Home Assistant do it, and the directory keeps the address
  24 hours; said in the FAQ, no setting. (b) Never count. (c) A setting,
  on by default.
- **Decision 6, Next and Previous.** (a) **Step through the favourites
  while a favourite plays**, *recommended*, like a radio's presets;
  greyed for any other station. (b) Always greyed.
- **Decision 7, on by default.** (a) **On**, *recommended*, and offered in
  first use's *How will you listen?*; it costs nothing until a station is
  played (the unit starts then). (b) Off until switched on.
- **Decision 8, the phone and Home Assistant.** (a) **The phone's Radio in
  this phase, Home Assistant after**, *recommended*: the phone is where
  searching by name is easiest; the integration (favourites as its
  sources) follows the player's release, as for multiroom. (b) Both in
  this phase. (c) The panel only.
