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

1. **In the image, off until switched on,** like the hub (*"Agree"*).
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

## Open

- **Which of George's server's add-ons come preinstalled** beyond the two
  above. His server runs, besides Lyrion's own: Radio Now Playing 0.0.56 and
  Squeeze Plex Hub 1.0.1 (read from its plugin page, 2026-10-02).
- **The settings rows** for the network shares, as a list, for ADR-0022's
  inventory - appended after George confirms their final shape.

## Not settled here

- The memory and CPU measured during a scan of George's library, and the
  playback check; the 2 GB limit stands until then.
- The SD card's wear and space for the database and artwork cache.
