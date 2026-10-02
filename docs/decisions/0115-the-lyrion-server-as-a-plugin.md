# ADR-0115 — The Lyrion server as a plugin

**Status:** **Proposed** — George, 2026-10-02: Phase 13e (*"Lyrion server -
this way an user can have the client and server"*), started that evening.
The choices under *For George* are open.
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

## For George

1. **How it arrives:**
   - **A (recommended):** in the image, off until switched on, like the
     hub. The image grows by about 100 MB installed.
   - **B:** downloaded from the release when switched on.
2. **The player and its own server:** when the plugin is switched on, the
   player's Lyrion address becomes this device **automatically**
   (recommended; Phase 13e criterion 3), and switching it off puts back the
   address it had. Or left to the user.
3. **The music folders, as settings** (each for ADR-0022's inventory, after
   you confirm):
   - **USB disk:** any USB disk plugged in is mounted read-only and offered
     to the server (recommended: automatic, no setting).
   - **The device's own storage:** a folder **Music**, shared on the network
     like the Pictures share (ADR-0049), so music is copied onto it from a
     computer (recommended).
   - **A network share:** settings for its address (`//server/music`), user
     and password; mounted read-only.
4. **Where the server's own settings live:** in Lyrion's own web page, as
   upstream (recommended), with only the music locations in our Settings.

## Not settled here

- The memory and CPU measured during a scan of George's library, and the
  playback check; the 2 GB limit stands until then.
- The SD card's wear and space for the database and artwork cache.
