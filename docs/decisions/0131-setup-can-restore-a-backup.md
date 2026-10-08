# ADR-0131 — Setup can restore a backup

**Status:** **Accepted** — George, 2026-10-08: *"We need to give the user the
option to also restore a backup."* On the proposal: *"keep wi-fi then and add
the rest. There should be also a review of the import just like we have it now
and then restart"*; backups *"from older releases yes - unless there is a
change in the sqlite schema that would break the import completely"*; plugins
on the getting-ready screen, *"Agree"*. Designed by Claude: *"Then you do it."*
**Builds on:** [ADR-0083](0083-a-backup-leaves-the-device.md) (what a backup
holds, restoring it), [ADR-0104](0104-how-the-device-knows-it-needs-setup.md)
and [ADR-0031](0031-first-boot-setup-access-point.md) (setup),
[ADR-0105](0105-updates-over-the-network.md) §5 (settings migrations),
[ADR-0128](0128-setup-installs-plugins-and-settles.md) (the settling screen),
[ADR-0109](0109-other-screens.md) (*Keep this screen?*).

## Context

A reflashed card asks every setup question again, and only afterwards can a
backup be restored, from *Settings → System → Restore*, out of the player's
Backups share. On a new card that share is empty: the owner first has to copy
the file back into it over the network. Setup is where someone with a backup
wants it.

## Decision

1. **A step after Network: *New player* or *Restore a backup*.** The Wi-Fi is
   always asked first: a backup does not carry it, and the player needs it to
   join. *New player* goes on as today.
2. **Restoring, the file comes from the phone.** It is uploaded over the setup
   network to the player, which checks it before anything else happens.
   - The step says where a backup is: in the old player's Backups share,
     copied off before the card was flashed.
   - The file is kept, readable only by root, until setup finishes or another
     file replaces it. Then it is deleted: it holds Bluetooth keys and
     sign-ins.
3. **The other questions are skipped; a review of the backup takes their
   place**, the same table as today's Review:
   - name, time zone, output, library, services, screen, visualiser and
     plugins, as the backup has them;
   - what else comes back: paired Bluetooth devices, the Spotify sign-in,
     Plexamp's claim, the Beszel identity, the Lyrion server's settings and
     playlists, and artist and album information;
   - what does not: network share passwords;
   - when the backup was made, and from which player.

   Network keeps its *Change*; the backup has *Choose another*. Finishing
   reads ***Restore and connect***.
4. **Which backups are accepted.** A backup is a tar archive of named files;
   the settings are one SQLite table of keys and values, unchanged since the
   first release.
   - **Older releases: accepted.** The migrations (ADR-0105 §5) run at the
     start that follows, as they do after a restore from Settings.
   - **Refused**, each with its own sentence on the phone:
     - not a gzip tar archive;
     - a path a backup never holds, or a link (ADR-0083's rule);
     - no settings in it;
     - settings the store cannot open: a database that does not open, or
       has no `settings` table. That is George's "change in the sqlite schema
       that would break the import".
   - **Newer releases: accepted, and said** in the review. *Made by a newer
     version of gexis; settings this version does not know wait for its
     update.* The store already leaves those keys alone (`migrate`). A
     decision Claude took; see *Open*.
5. **Finishing, in this order:**
   1. The Wi-Fi country, from the backup's time zone.
   2. The join. A failed join returns to Network with the reason, as today,
      and the backup stays.
   3. **The backup's main answers, applied as setup applies its own**: name,
      time zone, clock, output, Lyrion, Spotify, Bluetooth, Headless, screen
      and visualiser, through `Settings.set`. This is needed because some of
      them live outside the settings too:
      - the screen is `screen.json`, which the core makes the settings follow
        at start, so a restore alone would lose it on a new card;
      - the time zone is the system's;
      - the name is in four places.
   4. **The files put back.** The two SQLite databases are written beside
      themselves and renamed into place, so the store the core holds open is
      never overwritten underneath it.
   5. The settling screen (ADR-0128) is told what to wait for: the skin pack
      if the backup has the visualiser, and each plugin switched on in it that
      downloads its software.
   6. The panel says *Restoring the backup and restarting…*, and the player
      restarts. At start the plugins' units follow their switches
      (`_reconcile_sources`) and download. *Keep this screen?* is asked on
      the panel if the screen changed, and the phone says so before it is
      put down.
6. **Nothing new to set**: no ADR-0022 row.

## Amended (George, 2026-10-08, the same day)

*"In the review phase why not use the same review screen we have for the new
installation setup which would allow also a change? Use case would be
installing the player for another device but not wanting to start from
scratch ... This would be only for the entries in the current setup that can
be changed and not for api credentials."*

- **§3:** the review is the new player's Review table, with *Change* on every
  answer setup asks: name, time zone, output, library, services, screen,
  visualiser and plugins. Each step opens on the backup's answer. The backup
  and what else it brings are rows above and below it. Keys, pairings and
  sign-ins have no *Change*: setup does not ask for them.
- **§5:** a step continued from is setup's answer, and it wins over the
  backup's. The order changes so that it can:
  1. the join;
  2. the files put back;
  3. **the changed answers written into the restored settings file**
     (`backups.write_settings`), the one the next start reads;
  4. the main answers applied through `Settings.set`, as before;
  5. the backup's name re-applied everywhere only when the name was not
     changed.
- *Find my Lyrion server*, chosen in the review, searches after the join and
  writes what it finds into the restored settings.

**A consequence for a second player** (*Open* below): a backup used for
another player also brings the first player's identities.

## Open

- **Backups from a newer release are accepted.** A setup run from an older
  card then restores settings that version cannot read until it updates.
  Refusing instead would leave the owner unable to use their own backup until
  they found a newer image. George may want them refused.

- **Identities on a second player.** A backup restored onto a second player
  gives it the first one's Beszel fingerprint (the hub would see one system
  in two places), Plexamp's claim (one Plex player identity on two devices),
  the Spotify sign-in and the Bluetooth pairings. The pairings are bound to
  the first Pi's adapter and do nothing on another. Setup could offer to
  leave these behind when the name is changed. George's to decide.

## Not decided here

- Restoring a backup that is still on the old player, over the network.
- Wi-Fi networks in backups.
