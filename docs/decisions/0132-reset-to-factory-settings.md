# ADR-0132 — Reset to factory settings

**Status:** **Accepted** — George, 2026-10-09: *"add a reset to factory
settings which was deferred in the past but which is necessary now ...
once the user resets, all settings are reset, skins are removed, plugins
removed... everything goes to a clean installation with the next restart
showing the setup."* On the four choices put to him: backups on the player
**deleted**; music files and playlists on the player **deleted** - reversed
the same day, see the amendment below; started
from the **panel and the phone**; the row **added** to ADR-0022's inventory.
**Builds on:** [ADR-0021](0021-deployment-flashable-image.md) (where it was
deferred), [ADR-0104](0104-how-the-device-knows-it-needs-setup.md) (what makes
setup come back), [ADR-0083](0083-a-backup-leaves-the-device.md) (backups),
[ADR-0131](0131-setup-can-restore-a-backup.md) (the read-only store a live
replacement of the settings file meets).

## Context

Testing setup meant re-flashing a card. A player also has no way back to a
clean state for a new owner. ADR-0021 deferred a factory reset as "implied by
configuration persistence, specified nowhere".

## Decision

1. **Settings → System → *Reset to factory settings*.** An action, after
   *Restore*, on the panel and the phone like every other row. Its sheet says
   what goes - including the backups kept on the player - says
   to download a backup first under *Restore*, and confirms with ***Hold to
   reset and restart*** (decision 6).
2. **The wipe runs at the start of the next boot, not while the player
   runs.** Confirming writes a request (`/var/lib/gexis/factory-reset`) and
   restarts. `gexis-factory-reset.service` runs early - before NetworkManager,
   Bluetooth, the renderers and the core - so nothing holds a file it deletes
   (ADR-0131's read-only store), and the same boot ends in setup.
3. **What goes - back to a freshly flashed card:**
   - all settings (`settings.db`) and artist and album information
     (`enrichment.db`), and the caches built from them;
   - the device name: `device-name.env` removed, hostname `raspberrypi`
     (`/etc/hostname`, `/etc/hosts`), no pretty name, Spotify's name back to
     *gexis*; the time zone back to Europe/London, the image's;
   - the network: every saved NetworkManager profile (Wi-Fi networks, a
     cable's fixed address), the Wi-Fi country in `cmdline.txt`, the setup
     marker and answers, so setup comes back (ADR-0104);
   - the screen: `screen.json`, `screen-seen.json`, `screen.env` and the
     `video=` in `cmdline.txt`; the sound card board's block in `config.txt`;
   - identities: Bluetooth pairings, the Spotify sign-in, Beszel's agent and
     hub data, Plexamp's claim;
   - downloads: every skin pack (purged), the Plexamp app, uploaded plugins
     and their data, the components' state, the settling record;
   - the Lyrion Server's settings and library database;
   - **the backups kept on the player** (George's choice);
   - network share passwords; kept debug logs.
4. **What stays:** the installed release (no downgrade) and the image's own
   files; SSH access, when the card was provisioned with a key; **the music
   folder** (`/var/lib/gexis-music`, with the playlists Lyrion saves there)
   and **the Pictures share** (`/var/lib/gexis-core/pictures`). The Lyrion
   Server's library database goes, so it scans the kept music again.
5. **Plugins' units follow their switches at the next start**, as after a
   restore (`_reconcile_sources`): with the settings gone, each is back to
   its default.
6. **A challenge that needs no keyboard** (George, 2026-10-09: *"add a
   challenge of sorts when triggering a reset. Should be something that could
   work without a keyboard."*). The confirm button is **held for 3 seconds**,
   a bar filling across it; letting go, sliding off it or a cancelled touch
   before then starts over. It works the same by finger on the panel, on a
   phone, with a mouse, and with Space or Enter held down. A tap, or a stray
   brush of the panel, cannot reset a player. Typing a word was set aside:
   the panel has no keyboard. A puzzle was set aside too: it reads as a game
   on an action that deletes everything.
   Registry rows mark it with `"hold": true`.

## Amendment, 2026-10-09: the owner's files stay

George, the same day: *"music from music folder shouldn't be deleted, nor the
photos from the photos folder. Only the backups go."* The music folder and
the Pictures share are no longer emptied (decision 4); of what the owner put
on the player, only the backups go. The first answer above is kept as it was
given.

## Amendment, 2026-10-09: the reset is shown

George, after the first reset on the bar player: *"kept finger on the button
until the end on the phone, but then there was nothing: no message, no
overlay screen saying that the device is being reset. Something needs to be
shown to the user so he knows that the device is being reset."* A toast had
been the only sign. Now a **reset screen** covers the panel and every phone:
the core puts `resetting` on `/state` and restarts 3 seconds later; the phone
that confirmed shows it at once. A phone keeps it after the player goes,
with how to reach setup - *gexis-setup* and `10.42.0.1:8090`, or
`raspberrypi.local:8090` over a cable. It has no way out: the player is
going.

## Amendment, 2026-10-10: the boot after a reset is logged - temporarily

After a reset and a restore in setup, the bar player did not restart, and
the boot it happened in had kept its log in memory only, so nothing showed
why. George: *"Add the retaining of the log after reset but we need to
remove it before first release as normally nothing should make it through a
reset. So we add it today for debugging purposes only."*

**Temporary, removed before the first public release.** The wipe writes
`61-gexis-after-reset.conf` (journald `Storage=persistent`) and restarts
journald before the log moves onto the card. While it is there the core's
startup check of *Debug logs* leaves the logs alone. At the first start
after setup the core removes it and skips that check once, so the logs of
the reset and of setup survive setup's restart; from the next start
*Debug logs* decides again. Code marked `TEMPORARY` in `journal.py`,
`factory_reset.py` and `__main__.py`.

## Settings inventory (ADR-0022)

*Reset to factory settings* [R], System, after Restore; an action, no stored
value. Appended on George's confirmation, 2026-10-09.
