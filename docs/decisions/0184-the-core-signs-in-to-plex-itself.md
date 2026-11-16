# ADR-0184 — The core signs in to Plex itself

**Status:** **Proposed** 2026-11-16 (Phase 32's acceptance 1; George opened
the phase the same day). **Builds on:**
[ADR-0016](0016-plugins-as-separate-processes.md) (plugins are separate
processes), [ADR-0040](0040-enrichment-providers.md) (the provider chain),
[ADR-0022](0022-settings.md) (the inventory),
[ADR-0119](0119-plexamp-is-claimed-from-settings.md) (Plexamp's claim; links
in notes), [ADR-0174](0174-plexamp-and-beszel-from-the-catalogue.md)
(Plexamp out of the release). **Relates to:**
[ADR-0083](0083-a-backup-leaves-the-device.md) and
[ADR-0125](0125-a-problem-report-users-can-download.md) (secrets in backups
and reports). **On:** [Finding 086](../findings/086-what-the-plex-server-could-answer.md).

## Context

Phase 32 puts a Plex provider in ADR-0040's chain, ahead of the internet
ones, for whatever plays: Lyrion, Spotify and Bluetooth included. It needs a
Plex token, and today:

- **The only one on a player is Plexamp's**, `user:token` in Plexamp's
  settings store, which our plugin reads. Finding 086 was read with it. The
  core reading it is the coupling ADR-0016 exists to prevent.
- **A player may have no Plexamp** since 1.13.0 (ADR-0174: installed from the
  catalogue, or not at all), and so no token, while its music is still on a
  Plex server worth asking.
- **A Plex account token is the whole account**: every server, the shares,
  the account's own settings, not one library. `GET /settings` serves
  `secret` rows in plain text to anyone on the LAN (ADR-0022, ADR-0083), and a
  backup carries `settings.db`. A Plex token kept as the fanart.tv key is
  kept would put the account on the LAN and in every backup.

## Options

- **A. The core signs in with a code.** Plex's own sign-in for devices: the
  core asks plex.tv for a short code, the player shows it with
  `plex.tv/link`, the user enters it there, signed in to Plex, and the core
  collects a token of its own once plex.tv has it. The player becomes a
  device of its own in the account's *Authorized Devices*, named after the
  player. *For:* nothing typed on the player; nothing shared with Plexamp;
  works without Plexamp; removed from the account on its own. *Against:* a
  second entry in the account beside Plexamp's; plex.tv reachable at
  sign-in.
- **B. A claim token, exchanged by the core**, as Plexamp's row does: a token
  from `plex.tv/claim` pasted, the core exchanging it for its own. *For:* the
  same gesture as Plexamp's row. *Against:* a long string pasted within the
  token's four minutes; the exchange for a client that is neither a server
  nor Plexamp is undocumented and unmeasured.
- **C. Plexamp's token, handed over by the plugin**, through a new contract
  message. *For:* no second sign-in where Plexamp is claimed. *Against:*
  nothing without Plexamp (ADR-0174); *Claim again*, or Plex signing Plexamp
  out (ADR-0119's amendment), takes the provider with it; an account token
  passed between processes; a contract change for one plugin.
- **D. A token typed into Settings**, `X-Plex-Token` read from a browser.
  *Against:* finding it means reading a page's XML; it is the account; it
  would be a `secret` row, served on the LAN.

## Proposal

1. **A: the core's own sign-in.** In Settings → Enrichment, a *Plex* row:
   *Sign in* shows a four-character code and `plex.tv/link` (a link, by
   ADR-0119 C: on the phone it opens a new tab); while signed in it reads
   the server's name, with *Sign out*. An expired code goes back to *Sign
   in*.
2. **The token is not a setting.** The core keeps it in a file of its own,
   `/var/lib/gexis-core/plex.json`, root's, mode 0600: never in
   `GET /settings`, never in a backup (a restore asks for a sign-in again),
   never in a problem report, which says only whether the player is signed
   in. *Sign out* deletes it; the device stays in the Plex account until it
   is removed there, and the row's note says so.
3. **The server**, from the account's list of servers (plex.tv's
   *resources*): those with a music library and an address on the local
   network. One is used without asking; with more than one, the row offers
   the choice. Asked on its local address only, never through plex.tv's
   relay: the phase is about depending less on the internet, and a server
   not reachable locally counts as not there, so the internet providers
   answer (acceptance 4).
4. **A server's own token instead of the account's**, if U3 finds one that
   opens that server and nothing else: the core keeps it and drops the
   account token after listing the servers.
5. **ADR-0022's inventory** gains the row as [N] once George confirms it.

## Decisions for George

1. **The sign-in:** A (recommended), B, C or D.
2. **Backups:** the token kept out, a restore asking for a sign-in again
   (recommended), or carried as the keys are.
3. **Which servers:** the local network only, with a choice when there is
   more than one (recommended); or every server the account reaches,
   through plex.tv's relay when not local.
4. **Where the row goes:** Settings → Enrichment, beside the providers
   (recommended), or Sources, beside Plexamp.

## Claude's choices

- A client identifier per player, made once and kept with the token; the
  product named *Gexis Player*, the device by ADR-0048's device name.
- A code is asked for only when *Sign in* is pressed; plex.tv is polled
  every 2 s while the code is shown, and stops when it expires or the row
  closes.
- The provider is one more entry in `providers.py`, first in the list;
  nothing else is reordered (acceptance 2).

## Unmeasured, measured before building

- **U1.** Plex's code sign-in from a player: the code, the link, the token
  collected, the code's lifetime.
- **U2.** What the device is called in the account's *Authorized Devices*.
- **U3.** Whether the *resources* list gives a server's own token that answers
  the library calls Finding 086 made, and whether it opens anything beyond
  that server.
- **U4.** The local address from the player: plain http on 32400, or https
  with the server's own certificate.

## Consequences

- A user with Plexamp signs in twice, and sees two devices in the account.
- plex.tv is needed at sign-in and to list the servers; the library calls
  after that stay on the local network.
- Nothing changes for a player without Plex: no row is signed in, and the
  chain is as today.
