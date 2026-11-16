# ADR-0184 — Plex information through Plexamp's claim

**Status:** **Accepted** 2026-11-16 (Phase 32's acceptance 1): George
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
account's. **Not yet seen on a player**: both files on a claimed player
(read by the plugin's code in a preview, its result as yes or no, no
names or addresses printed), and a server with `httpsRequired`, whose
local address is a `plex.direct` name.

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

## Consequences

- No second sign-in and no second Plex device in the account.
- The plugin contract grows by one event; a plugin older than it lends
  nothing, and the provider stays silent.
- Plex information goes with Plexamp: a player without Plexamp gets the
  internet providers only.
