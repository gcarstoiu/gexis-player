# ADR-0184 — Plex information through Plexamp's claim

**Status:** **Built** 2026-11-16 to 18, in 1.18.0 (Testing serial 74), its
four steps below; **amended** 2026-11-21 (George): timed lyrics first, items
7-10. **Accepted** 2026-11-16 (Phase 32's acceptance 1): George
answered its four decisions and then confirmed the consequence and the
settings row, the same day. **Builds on:**
[ADR-0016](0016-plugins-as-separate-processes.md) (plugins are separate
processes), [ADR-0040](0040-enrichment-providers.md) (the provider chain),
[ADR-0119](0119-plexamp-is-claimed-from-settings.md) (Plexamp's claim),
[ADR-0174](0174-plexamp-and-beszel-from-the-catalogue.md) (Plexamp from the
catalogue), [ADR-0022](0022-settings.md) (the inventory). **Relates to:**
[ADR-0083](0083-a-backup-leaves-the-device.md) and
[ADR-0125](0125-a-problem-report-users-can-download.md) (secrets in backups
and reports). **On:** [Finding 086](../findings/086-what-the-plex-server-could-answer.md).

## Context

Phase 32 puts a Plex provider in ADR-0040's chain, ahead of the internet
ones, for whatever plays: Lyrion, Spotify and Bluetooth included. It needs
a Plex token and a server, and today:

- **The player is signed in to Plex once already**: Plexamp's claim, a code
  from `plex.tv/claim` pasted in Plexamp's row (ADR-0119). Plexamp keeps the
  token in its own settings store; our plugin reads it there to fetch a
  track's title and artwork (`gexis-plexamp`, `server.py`), and Finding 086
  read the library with it. The plugin's own rule: a credential is not asked
  for twice, because a second place to keep it is a second place for it to
  go stale.
- **A claim code works once**: Plexamp spends it signing in, so the core
  cannot be given the same code.
- **The core may not read the plugin's files** (ADR-0016).
- **The token is the whole Plex account**, not one library. `GET /settings`
  serves `secret` rows to anyone on the LAN (ADR-0022, ADR-0083), so it
  cannot be a setting.
- **The plugin keeps the token on the local network** (George, 2026-09-25:
  the calls may carry it while they stay inside the local network;
  `server.is_local`): artwork through a server that is not on it is left
  out.
- **The server**: the plugin learns which one Plexamp plays from from
  Plexamp's timeline, and only while Plexamp plays.

## Options weighed

- **A. A sign-in of the core's own**, by a code at `plex.tv/link`: no
  Plexamp needed, a second device in the Plex account.
- **B. A second claim code**, exchanged by the core: the same gesture as
  Plexamp's row, a second time.
- **C. Plexamp's claim**, lent by the plugin: nothing more to do where
  Plexamp is claimed; nothing without it.
- **D. A token typed into Settings**: the account in a setting on the LAN.

## Decided (George, 2026-11-16)

1. **Plexamp's claim, not a second sign-in (C).** The plugin, which already
   reads Plexamp's token, lends it to the core through the plugin contract,
   with the server it is for. The core reads nothing of the plugin's.
2. **Backups as Plexamp's claim is today**: restored onto the same player,
   left behind on a second one, where Plexamp is claimed again (ADR-0131's
   identities). The core stores nothing of it, so there is nothing more to
   back up or leave out.
3. **The server is the one Plexamp is claimed to and plays from**, on the
   local network only, as the plugin's artwork already is.
4. **The row is in Sources, beside Plexamp.**

**The consequence**, confirmed by George: Plex answers only on a player
where Plexamp is installed and claimed. Without Plexamp (ADR-0174 made it
optional), and while it is claimed again or signed out by Plex, the internet
providers answer as they do today.

## How it is built

1. **A new event in the plugin contract**, contract version raised (not
   so: *As built*, 1),
   documented in `docs/PLUGIN-CONTRACT.md` and `docs/WRITING-A-PLUGIN.md`:
   `{"t": "library", "kind": "plex", "url": "http://<address>:32400",
   "token": "…"}`, or `null` for both when Plexamp is not claimed or its
   server is not on the local network. Sent at the plugin's start and when
   either changes. Any plugin may send it; the core takes the one from the
   plugin that serves Plexamp.
2. **The core holds it in memory only**: never in `settings.db`, never in a
   backup or a problem report (which says only whether a library was lent).
   A plugin that stops takes it with it, as its row's status does (ADR-0119
   item 4).
3. **The Plex provider** is first in ADR-0040's list, nothing else
   reordered (acceptance 2); asked only while a library is lent and the row
   is on.
4. **The plugin** (`gexis-plexamp`, a release of its own through the
   catalogue) sends the event from what Plexamp keeps (U1, below): the
   server Plexamp is set to, its local connection that is not a relay, and
   that server's own token.

## The row, in ADR-0022's inventory (confirmed by George)

- **[N] Information from Plex** - Sources, beside Plexamp: a switch, **on**
  by default, its note *Artist and album information from your Plex server,
  ahead of the internet's*. Greyed with *Claim Plexamp first* while Plexamp
  is not claimed. Appended to ADR-0022 the same day.

## U1 - where Plexamp keeps its server (read 2026-11-16)

Read from Plexamp 4.13.2's own code (`js/index.js` of the pinned headless
download, its checksum matching the plugin's pin), not from a player.
Plexamp's settings store - one file per key, as the plugin already reads
the token from - holds:

- **`server:identifier`** (the file `%40Plexamp%3Aserver%3Aidentifier`:
  Plexamp's settings wrapper puts `@Plexamp:` before the key and a type
  marker, `S`, before the value, as for the token): the server Plexamp is
  set to, by its `clientIdentifier`; set with `server:library` when a
  library is chosen, cleared on sign-out.
- **`@Plexamp:resources`** (written raw, no marker): the account's devices
  as JSON keyed by their ids, each with
  `clientIdentifier`, `owned`, `accessToken` (that server's own token),
  `httpsRequired` and `connections`, each connection `uri`, `local`,
  `relay` and `proxied`. Plexamp orders them loopback first, then local,
  relays last; for plain http it rewrites a `plex.direct` name to its
  address (`cloneAsHttp`).

So the plugin can name the server and its local connection while Plexamp
is not playing, and lend that server's own token rather than the
account's. **Seen on sofapi** (2026-11-17, Finding 149): both files on a claimed
player, read by the plugin, the library lent over HTTP. **Not yet seen**: a
server with `httpsRequired`, whose local address is a `plex.direct` name.

## As built (2026-11-16)

Phase 32's first step, covers first. Where the build departed from *How it is
built*, or settled what it left open:

1. **The contract stays at version 1.** The event is *added within version
   1*, as `output`, `software` and `artwork` were: the contract's own rule
   (`docs/PLUGIN-CONTRACT.md`, *Versioning*) refuses a plugin whose version
   the core does not serve, so raising it would have turned away every
   plugin that speaks 1. A core older than the event answers it with an
   error, which the plugin ignores.
2. **The event names the server too**: `{"t": "library", "kind": "plex",
   "server", "url", "token"}`, `server` being its `clientIdentifier`. The
   core remembers that id (not the token) beside the enrichment cache, and
   drops the cache's Plex answers when another server is lent: an album's
   number on one server is another album on the next.
3. **The core checks the address as well**: a host that is a global address,
   or a name that is not a `plex.direct` one for a local address, is refused.
   It logs only *a library is lent* or *no library is lent*; a problem report
   therefore says which, and nothing more.
4. **Covers are served through the core**, `/plex/cover/<key>/<stamp>`: a
   Plex picture's address needs the token, and the enrichment cache keeps
   what it finds on disk while the state goes to every phone. The route asks
   Plex's scaler (600 px unless asked otherwise), the stored picture if the
   scaler refuses, and serves only an album's picture by its two numbers.
5. **Matching, for now**: one index of the library's albums (a page of 500
   at a time, summaries left out), kept six hours or until the library is
   lent again; an album matches on `match_title` and the artist or lead
   artist, on either side. MusicBrainz ids (acceptance 3) come later, with
   the hit rate measured.
6. **A sleeping server costs one connection wait of 2 s**, then the
   enrichment service's backoff (15 minutes) - what acceptance 4 measures.
7. **The row is in the plugin's manifest** (`plexamp.plex_info`, gexis-plexamp
   0.6.0), so it shows and hides with Plexamp's other rows, and a plugin too
   old to lend has none. The core greys it with *Claim Plexamp first* until
   the plugin's *Claim token* row reports a claim.

**Measured on sofapi, 2026-11-17** ([Finding 149](../findings/149-plex-covers-as-built.md)):
the library lent over HTTP and taken; 3,539 of LMS's 4,823 albums matched by
name; a cover through the core in 54-81 ms; 2 s for a host that does not
answer; neither the token nor the server's address in the logs. The sweep
(*Update album covers*) did not ask Plex: George's answer is below.

## Second step: the artist, popular tracks and the sweep (2026-11-17)

**Decided (George, 2026-11-17):** the *Update album covers* sweep asks Plex
first, ahead of fanart.tv; the work goes on with artist pictures and
biographies; and he expected the server to hold an artist's popular tracks
as well. It does: Finding 086's 404 was `popularLeaves`, while Plexamp's own
DJ asks the library's tracks of the artist sorted by `ratingCount`. Measured
on sofapi the same night, counts only: 509 artists, 507 with a picture and
494 with a biography; of a sample of 80, similar artists for 80 (30 each,
the median) and ten popular tracks for 80; 13-17 ms a call.

**How it is built:**

1. **A second provider, `plex-artist`**, first in the chain beside
   `plex-release`, answering by artist: the biography (credited *Plex*), the
   picture, similar artists (Plex's *Similar*, up to 30) and popular tracks
   (the artist's tracks in the library, `sort=ratingCount:desc`,
   `group=guid`, ten). Warmed when a track starts, as the other local
   providers are. The artist is found in an index of the library's artists
   made beside the album index (one call), by folded name or lead artist.
2. **Pictures through the same route.** `/plex/cover/<key>/<stamp>` serves a
   picture of the server's by its two numbers, an artist's as well as an
   album's; a size outside 100-1200 is brought into it rather than replaced.
3. **The artist page asks Plex first for every field**, then LMS's own
   plugin and the others in the order they had (LMS's text still ahead of
   Wikipedia's, fanart's picture still ahead of LMS's). LMS's plugin, too,
   shows what it fetched from the internet; the server that holds the files
   comes first. *Popular* takes Plex's titles, matched to the library's own
   tracks as ListenBrainz's are, and ListenBrainz's where Plex has none.
4. **Both sweep buttons ask Plex first** (*Update album covers* by George's
   answer; *Update artist portraits* the same way). What Plex has is stored
   under its own names (`plex-artist`, `plex-album`) and read first while a
   library is lent and *Information from Plex* is on; fanart.tv and
   TheAudioDB are still asked and kept, so with Plex off, or Plexamp gone,
   the lists fall back to them without another run. *Found* counts either.
5. **Another server, and everything Plex said is forgotten**: both
   providers' cached answers and both of the sweep's Plex stores, since an
   item's number on one server is another item on the next.

**Measured on sofapi, 2026-11-17** ([Finding 150](../findings/150-plex-artists-and-sweep-as-built.md)):
for 40 artists the server holds, its picture on every page and its
biography on 39; *Popular* rows for 12 of 13 held by the same name, 3 of 27
held by the lead artist only (1,177 of the 1,719 LMS artists matched). One
sweep, 69 minutes: Plex's picture on 556 of 948 artists in the list and 169
of 270 sampled covers; no token or address in the logs.

**Confirmed (George, 2026-11-17):** Plex ahead of LMS's own plugin on the
artist page (3), and *Update artist portraits* asking Plex first as well (4).
**A collaboration's page stays the lead artist's (George, 2026-11-17).**
Taking the biography and similar artists from Plex only for the whole name
was agreed, then not built: the internet sources already answer for the
lead artist, since MusicBrainz resolves a collaboration to it (ADR-0059's
rule for the picture; Finding 150), so the page would show the lead's
biography from Wikipedia instead. Put back to him with the other choices
(the whole name for every source; a heading naming the lead), he kept it as
built: the lead's picture, biography and similar artists, Plex first.

## Third step: the artist's MusicBrainz id behind the name (2026-11-17)

Phase 32's acceptance 3 asked for MusicBrainz ids where both sides carry
them. [Finding 152](../findings/152-plex-matching-by-musicbrainz-ids.md):
**LMS's CLI gives none**, while Plex has an `mbid://` guid on nearly every
artist and album. The id the core already resolves for an artist by name
(`ArtistIdentity`, kept between restarts) stands in for LMS's: on sofapi it
adds 34 of 948 album artists and 125 of 4,823 albums to what the names
find, and contradicts no artist the names found.

**How it is built:**

1. **The index keeps Plex's artist ids and each artist's albums**: artists
   read with `includeGuids=1`, by `mbid://` id; albums also by their
   artist's key and reduced title.
2. **The name first, as built; the id only when the name finds nothing.**
   An artist by its id; an album by its artist's id and its title. Where
   the two disagree (5 albums of 3,477 on sofapi) the name's answer stands,
   so nothing found today changes.
3. **The id is the one the other providers use**, at the same confidence
   threshold (ADR-0059): `PlexRelease` and `PlexArtist` ask `ArtistIdentity`
   after a miss by name, and their answer carries its score; the sweep uses
   the id it resolves for fanart.tv. An artist not yet resolved costs one
   MusicBrainz search, which the providers behind Plex would make anyway.
4. **The Plex providers' misses kept from before are forgotten once**, at
   the first lend after the update: a "nothing" is otherwise believed for a
   week, and the id may now find it. Their finds stay.

## Fourth step: lyrics, behind LRCLIB's (2026-11-18)

Phase 32's acceptance 6. [Finding 153](../findings/153-plex-lyrics-are-rationed.md):
Plexamp's own request works, but the server serves **about five lyrics per
ten minutes, to whoever asks with its token** (a client identifier of our
own got none of its own; whether Plexamp's own lyrics draw on it was not
tested); and LRCLIB
already has more of them timed on this library. Offered LRCLIB alone, Plex
behind it, or Plex first, George chose (2026-11-18) **Plex behind LRCLIB:
asked only where LRCLIB has no lyrics, or none timed**.

**How it is built:**

1. **A provider of its own, `plex-lyrics`, after LRCLIB.** The track by its
   album - the name, then the artist's id, as the covers are found - and its
   title; its lyric streams from the track's own record (an album's track
   list does not carry them); the stream Plexamp would choose (the library's
   own file first, else a timed one, else the first), asked as Plexamp asks
   it (`?format=xml&includeInlineAttribution=1`). A timed answer becomes LRC
   lines; lines without a time (the licensor's credit, at the end) stay in
   the plain text only.
2. **Asked only after LRCLIB has answered, and only when that answer leaves
   something to add**: nothing found, plain words only, or LRCLIB could not
   be asked. Timed or instrumental from LRCLIB, and Plex is not asked. The
   enrichment service gains this as a rule of its own: a provider may stand
   behind another, and is started once that one has finished.
3. **The lyrics move as one set**: a later provider's replace an earlier
   one's only when theirs are timed and the earlier are not, so the credit
   under them is the source of the words shown (*From Plex · LyricFind* for
   a licensed lyric, *From Plex* for the library's own file).
4. **Asked only while the panel shows lyrics, and not for a track skipped
   past**, as Plexamp fetches them only while its lyrics are shown. The
   panel already tells the core whether its lyrics are on screen
   (ADR-0101). For a track playing under five seconds the answer is marked
   not final, and the panel's look-back asks again; when the lyrics come on
   screen, the panel asks again for the track playing. A player with no
   panel never asks.
5. **A refusal is "could not ask", for this provider alone.** A 404 on a
   stream the track lists is the allowance spent, not "no lyrics": it is not
   stored, and it backs off `plex-lyrics` (15 minutes), not the covers or
   the artist. A track that lists no lyric stream is a miss, believed for a
   week as the others' are.
6. **The switches that exist**: *Lyrics* (Enrichment) and *Information from
   Plex* (Sources) both stop it. No new row.

## Amended: timed lyrics first (George, 2026-11-21)

**Seen on sofapi**, George's check of Plex's lyrics: on a track LRCLIB has
only plain words for, the panel showed them first and swapped in Plex's
timed ones a few seconds later. The plain words come at once from LRCLIB.
Plex is not asked in a track's first `LYRICS_SETTLE_S` (5 s, item 4), then
it is asked behind the enrichment's 4 s wait, and the panel's look-back
(6 s) picks up its answer. **George: timed lyrics always come first.**
Offered three ways to handle the wait (wait with a limit, wait as long as
it takes, keep the swap), he chose **to wait, with a limit**.

7. **Plain words held back while Plex may still bring timed ones.** For a
   track whose LRCLIB answer is plain words only, while Plex is waiting to
   be asked or still answering for it, the route leaves the words out and
   says `lyrics_pending`. The panel then shows its looking state for lyrics
   on the Lyrics tab, the Track tab and the bar, and its look-back asks
   again.
8. **At most 10 s** (`LYRICS_WAIT_S`), counted from the first ask for the
   track with its lyrics on screen. After that the plain words show. A timed
   answer that comes later still replaces them (item 3): timed words come
   first in every case, and only the wait is bounded.
9. **No wait when Plex will not be asked**:
   - lyrics not on screen;
   - *Lyrics* or *Information from Plex* off, or no library lent;
   - `plex-lyrics` backed off, its allowance spent (item 5);
   - LRCLIB's answer timed, instrumental or empty.

   Both answers are stored, so the wait happens only the first time a
   track's lyrics are shown.
10. **The cost**: on those first showings, plain words appear up to 10 s
    later than before. Plex had timed words for 1 of the 92 tracks played
    on sofapi (Finding 153), so most such waits end in the plain words.

## Consequences

- No second sign-in and no second Plex device in the account.
- The plugin contract grows by one event; a plugin older than it lends
  nothing, and the provider stays silent.
- Plex information goes with Plexamp: a player without Plexamp gets the
  internet providers only.
