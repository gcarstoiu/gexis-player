# ADR-0179 — The music services under accounts of their own

**Status:** **Accepted** 2026-11-11 (Claude; nothing seen changes, so no
decision was George's). **Changes:**
[ADR-0167](0167-airplay-2-as-a-plugin.md) T3 (Shairport Sync as `pi`),
[ADR-0107](0107-our-parts-as-debian-packages.md) (go-librespot as
`pi`), [ADR-0166](0166-multiroom-for-every-source.md) (the Snapcast units as `pi`).
**Follows:** [ADR-0170](0170-plugins-that-ask-for-more.md) (the panel's token)
and the review of 1.16.1.

## Context

The review of 1.16.1 took the panel's token off Chromium's command line, out
of reach of other accounts (Lyrion's, Roon Bridge's). It found it still in
reach of every service that runs as `pi`, the screen's own user:
Squeezelite, go-librespot, Shairport Sync and its plugin, and the two
Snapcast units. Each of them takes data from the network - a Lyrion
server, Spotify, an Apple device, another player. One broken into as `pi`
could read the token from the kiosk's runtime folder, and more: connect to
the compositor's socket there, which shows what is on the screen and types
into it, and read Chromium's memory and profile. The token is only the
smallest part of it; the line that matters is the account.

`pi` was theirs because the output chain's meter pipes and software volume
were `pi`'s (ADR-0167 T3). Neither holds any more: the core makes the meter
pipes in `/run/gexis` open to every writer, and the software volume is a
card control reached through `audio`. No ALSA device is shared between
processes through shared memory (no `dmix` or `dsnoop`), so processes of
different users can play through the chain as they do now.

## Decision

1. **Four system accounts**, made by `systemd-sysusers` from each package's
   own file, as Roon Bridge's is ([ADR-0172](0172-roon.md)): `gexis-squeezelite`,
   `gexis-spotify` (go-librespot), `gexis-airplay` (Shairport Sync and the
   AirPlay plugin, which share a runtime folder, the metadata pipe and the
   hook's socket) and `gexis-snap` (the Snapcast server and client). No
   login, no home. The ones that open a sound device are in `audio` through
   their units (`SupplementaryGroups=`); the AirPlay plugin is in
   `gexis-plugins`, for the core's plugin socket. The plugin's unit comes
   from its own repository's release, so its account is set by a drop-in.
2. **`pi` stays the screen's**: the kiosk and the visualiser (its session),
   and the two local services that take nothing from the network - the
   level meter and CamillaDSP, which ADR-0170's review sandboxed.
3. **go-librespot's folder is given to its account at every start**
   (`ExecStartPre=+chown -R`). systemd re-owns a `StateDirectory=` only when
   the folder itself has another owner, and a restore puts the Spotify
   sign-in back under the owner its archive names. Archives keep naming
   `pi` and `audio` for that file, as every backup before this did, so an
   older release restores it to the account its own go-librespot runs as.
4. **Shairport Sync's D-Bus name** is owned by `gexis-airplay`, and called
   by it and root only.

## Unverified

When written: everything on a device - each source playing (Lyrion through
Squeezelite, Spotify, AirPlay, a group), an update from 1.16.1 bringing the
accounts in, and a backup from before it restored with the Spotify sign-in.
