# ADR-0115 — The Lyrion server as a plugin

**Status:** **Accepted** — George, 2026-10-02: Phase 13e (*"Lyrion server -
this way an user can have the client and server"*), its choices answered that
evening; two small points open below.
**Phase:** 13e ([DEVELOPMENT.md](../DEVELOPMENT.md)).
**Builds on:** [ADR-0114](0114-the-beszel-hub-as-a-plugin.md) (a server as a
`service` plugin, in the image and off), [ADR-0107](0107-our-parts-as-debian-packages.md).

## Context

The player is a Lyrion client (squeezelite); the server is usually another
machine. Upstream publishes **Lyrion Music Server 9.1.1** as
`lyrionmusicserver_9.1.1_arm.deb` (27 MB, about 100 MB installed,
`Architecture: all`), which runs on the system's Perl and depends on `perl`,
`libio-socket-ssl-perl`, `libcrypt-openssl-rsa-perl`, `ca-certificates`,
`procps`, `psmisc` and the C libraries. Licence: GPL-2.0 for the server, with
bundled CPAN modules under their own terms (to list in Legal and Credits).
Its ports, 9000 (web and JSON), 9090 (CLI) and 3483 (players), are free on
the player.

On George's player (0.7.0, measured 2026-10-02): every dependency is present
but `libcrypt-openssl-rsa-perl`, which joins the image; 3.8 GB of memory with
2.3 GB available (whether it was playing was not checked); 48 GB free on its 57 GB card.

Settled in Phase 13e already (George, 2026-10-02): **music comes first**, and
the effect of a scan on playback is measured; it **may need more than 13a's
1 GB**; its music can be on **a USB disk, the device's own storage, or a
network share**; and **it ships in our releases**.

## Proposed (technical)

1. **`gexis-lyrion-server`**: upstream's package at a pinned version and
   checksum, repackaged so its service ships disabled (upstream's starts on
   install), versioned by Lyrion's version, in the release's `ours` part.
   Its dependencies join the tested set the image is built from.
2. **A `service` plugin under Sources**, off until switched on; its switch
   reads "Open http://<name>.local:9000" (ADR-0114's `port`).
3. **Music first, by the unit, not by trust:** the server and its scanner run
   at the lowest CPU and I/O priority (`Nice=19`, `IOSchedulingClass=idle`,
   a low `CPUWeight`), so playback always wins the processor and the card.
   Phase 13e criterion 2 measures that it is enough: no gap or click in any
   renderer while a scan runs.
4. **Memory:** started at **2 GB**, then set from the measured peak of a
   scan of George's library.
5. **Its preferences in backups;** its database and artwork cache are not
   (rebuilt by a rescan), which keeps backups small.

## Decided (George, 2026-10-02)

1. ~~In the image, off until switched on, like the hub (*"Agree"*).~~
   **Replaced by decision 11** the same evening: Lyrion's own notice
   restricts redistributing parts of it.
2. **The player does not switch to its own server by itself** (*"User
   decides which server to use. No automatic switch is made when the
   lyrion server is turned on"*). Phase 13e criterion 3 changes with it: the
   player's own server is **offered** where a server is chosen, not chosen
   for the user.
3. **The music folders** (*"Agreed to those mentioned"*), each proposed for
   ADR-0022's inventory before it is built:
   - **a USB disk**, mounted read-only and offered to the server when plugged
     in, with no setting;
   - **a Music folder on the device**, shared on the network like the
     Pictures share;
   - **a network share** - which is how a NAS is reached (*"How about mounting
     network shares from a Nas?"*): its address, user and password, mounted
     read-only.
4. **Lyrion's own settings stay on its own web page**; ours hold only the
   music locations (*"Agree"*).
5. **Preinstalled Lyrion plugins** (*"Can we also have it pre installed with
   the material skin and the plugins we already recommend having?"*):
   **Material Skin**, and **Music & Artist Information**, which the player
   already relies on for artist photos, biographies and the fanart
   slideshow (ADR-0040, ADR-0112). Each at a pinned version, enabled, its
   licence in Legal and Credits.

### Settled the same evening (George)

6. **The preinstalled plugins are installed by Lyrion itself** from its own
   plugin list, the first time the server starts with the internet - as any
   Lyrion user installs them (*"A"*). Music & Artist Information states no
   licence anywhere (its repository, README and source, read 2026-10-02), so
   it is not redistributed; Material Skin (MIT) is installed the same way,
   one mechanism for both.
7. **A network share may be SMB or NFS** (*"Both"*): SMB with an address, a
   user and a password; NFS with an address.
8. **The share's rows are in a Lyrion subcategory, shown only while the
   Lyrion server is on** (*"These should be part of the lyrion subcategory
   and available only when the user turn on the lyrion server"*).
9. **More than one music location** (*"Can we support multiple paths in case
   the user has music folders spread?"*): the network shares are a list -
   each its own address (and user and password for SMB) - beside the USB
   disks and the Music folder, every one offered to the server as a music
   folder.

10. **Playlists are saved in a Playlists folder inside the device's Music
    folder** (*"A"*): writable by Lyrion, visible through the Music share,
    carried by backups. Everything else Lyrion writes - its database, artwork
    cache, preferences and logs - is in its own folders
    (`/var/lib/squeezeboxserver`, `/var/log/squeezeboxserver`), so the music
    folders and every network share stay read-only. Debian's build of
    Lyrion sets no playlist folder at all (its `dirsFor('playlists')` is
    empty), so this is set for it.

11. **Lyrion is downloaded by the player, not shipped by us** (*"A"*).
    Upstream's copyright notice (`/usr/share/doc/lyrionmusicserver/copyright`
    in 9.1.1) says Slim Devices' *"logos, graphics, animations, and
    documentation ... are not licensed for redistribution"*, and the CODE2000
    font it carries is shareware. So, as ADR-0100 does for Plexamp: the
    image carries our part - the manifest, the unit drop-in, the Music share,
    the first prefs and Lyrion's dependencies - and the first time the
    switch is turned on, the device fetches upstream's package from the
    Lyrion community's own server, checks it against its pinned checksum and
    installs it, with its progress in the plugin's row. Nothing of upstream's
    is in our image or our releases.
12. **Preinstalled add-ons: Material Skin, Music & Artist Information and
    Radio Now Playing**; not Squeeze Plex Hub (*"Radio now playing can be
    added. Not squeeze Plex hub"*).
13. **The network shares' settings are as proposed** (*"Network shares
    settings are fine"*), now in ADR-0022's inventory.

### Settled 2026-10-03 (George), after testing on his player

14. **Remove takes everything the Lyrion server made** (*"1. B"*, of three:
    A kept the network shares, C kept it as it was). ADR-0100's Remove
    deletes only the downloaded software and keeps the plugin's settings,
    which is right for Plexamp's sign-in. For the Lyrion server it left a
    reinstall that was not one - no setup wizard, Material already chosen,
    the old library - and NAS logins on the device for a server that was
    gone (George: *"How can I do a full check from scratch for the lyrion
    server if we store the settings even after a removal?"*). So Remove
    also deletes:
    - Lyrion's own folders: its preferences, and its cache - the library
      database, the artwork and the add-ons it installed
      (`/var/lib/squeezeboxserver/prefs` and `/cache`, named in the pin as
      `DATA`);
    - the network shares, unmounted, with their logins;
    - the record that the add-ons were installed, so they are installed again.

    **What stays:** the Music folder and its Playlists - they are the user's
    files, on the Music share. Switching on again downloads Lyrion, seeds
    its first preferences (the unit does it at start now, not the package
    at install) and scans the library afresh. The confirmation says so.
15. **A share's password is kept only where `mount` reads it** (*"2. B"*,
    of two: A kept it in the settings store). The store - and so
    `GET /settings` and every backup, whose share any guest on the network
    can open (ADR-0083) - holds the address and the user; the password is
    in a root-only file under `/etc/gexis/shares`, which backups do not
    carry. **The cost, accepted:** after a restore onto a new card, an SMB
    share says *Needs its password again* and is mounted once it is typed
    in; a guest share mounts by itself. Stores written before this keep no
    password past the next start: it moves to its file.

    Found on the way (2026-10-03): the Network shares row drew the stored
    list itself - `[{"address": ..., "user": ..., "password": ...}]` - so a
    password was on the page. The row now names its shares and the stored
    value is not sent (commit 19877a6), before this decision; this one
    takes the password out of the store as well.

### Settled 2026-10-03 (George), after scanning his library

Measured on George's player, 2026-10-03 (Finding 109): his NAS share, 61,362
files, took **2 h 7 min** to scan the first time and **26 min** to check with
nothing changed; the scanner's own memory grew by about 27 KB a file, to
**1,876 MB** for Lyrion as a whole - past the 2 GB this record set, once file
cache is counted.

16. **A saved share stays in Lyrion's list while it is not mounted** (*"clearly
    A"*, of two: B kept taking it out). Lyrion answers a folder taken out of
    `mediadirs` by wiping the whole library and scanning everything again
    (`Slim/Utils/Prefs.pm`), so a NAS that was off when the player started
    cost a two-hour rescan. Now only **Forget** takes a share out - and then
    Lyrion does rescan everything, which Forget is for. A full rescan started
    by hand while a NAS is off would still drop that share's songs until the
    next one.
17. *Open:* a USB disk unplugged is still taken out of the list, with the
    same wipe and full rescan.
18. **Lyrion's memory follows the player's** (*"A plus B - let's try"*). The
    limit is the player's memory less 1 GB for the player itself (measured:
    about 700 MB of Peppy, the screen's browser, Plexamp and the core): 3 GB
    on a 4 GB Pi, about 1 GB on 2 GB. A scan stopped for memory is said on the
    server's row, with about how many files fit, rather than leaving half a
    library unexplained; Lyrion does not retry it by itself (it rescans at
    start only when its library is empty). **B:** whether Lyrion's
    `dbhighmem` - on by itself above 900 MB - is what makes the scanner grow
    is being measured with a full scan with it off.

## Not settled here

- The memory and CPU measured during a scan of George's library, and the
  playback check; the 2 GB limit stands until then.
- The SD card's wear and space for the database and artwork cache.
