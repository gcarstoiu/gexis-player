# ADR-0167 — AirPlay 2 as a plugin

**Status:** **Accepted** 2026-10-28 (George: decisions 1-8, Open 1 off, the
settings row and the Legal and credits wording; decision 9). Phase 23
(`ph-airplay`), started the same day (George: as a plugin, offered in first
use). The experience is George's: on 2026-10-28 he took Claude's
recommendation on each of eight questions (*Decided*), and answered Open 1;
Open 2 waits for an Apple device. The technical decisions
are Claude's, proposed, and confirmed or changed by the phase's first
measurement. Builds on [ADR-0016](0016-plugins-as-separate-processes.md)
and [ADR-0086](0086-a-plugin-declares-itself-in-a-manifest.md) (plugins),
[ADR-0089](0089-arbitration-carries-a-plugin-renderer.md) and
[ADR-0091](0091-a-plugin-renderer-is-taken-off-the-device.md) (a plugin
renderer in arbitration), [ADR-0090](0090-plexamp-ships-the-way-beszel-does.md)
(Plexamp's shape), [ADR-0107](0107-our-parts-as-debian-packages.md) (packages),
[ADR-0145](0145-multichannel-folded-down-to-stereo.md) (built from pinned
source), [ADR-0149](0149-first-use-in-two-parts.md) (first use),
[ADR-0137](0137-plugins-are-told-when-output-is-fixed.md) (Fixed) and
[ADR-0166](0166-multiroom-for-every-source.md) (multiroom).

## Context

- **Shairport Sync is the receiver.** It is the maintained open-source
  AirPlay 2 audio receiver with multiroom, and needs NQPTP, a timing daemon
  of its own (one per host, UDP 319 and 320). The others: UxPlay mirrors a
  screen, and its README sends multiroom audio to Shairport Sync;
  openairplay's receiver and goplay2 have had no commit since 2023;
  openairplay2 is at 0.1.0, one stream, without PTP.
- **Debian has no AirPlay 2 receiver for trixie.** Its `shairport-sync`
  4.3.7-1 is classic AirPlay only (`debian/rules` has no `--with-airplay-2`);
  NQPTP is not in trixie (forky and sid carry 1.2.6). Upstream: Shairport
  Sync 5.6.2 (2026-10-25) and NQPTP 1.2.9 (2026-10-14); 5.6 needs NQPTP's
  shared-memory interface 11, which 1.2.9 has.
- **Senders**: iPhone, iPad, and Macs from macOS 10.15 (upstream's
  `AIRPLAY2.md`). The audio is 44.1 kHz (realtime ALAC, buffered AAC) or
  48 kHz (buffered AAC, lossless ALAC at 24 bits); no hi-res, no Atmos.
- **What it tells a player** (5.6 and 5.6.1's release notes): title, artist,
  album, cover and progress under AirPlay 2, through the metadata pipe and
  D-Bus. Remote control - play, pause, skip, the sender's volume - works
  under AirPlay 2 since 5.6, called a work in progress: its `Available`
  properties still say false.
- **It announces itself through avahi**, which AirPlay 2 requires, and its
  TXT records change while it runs (a session starting or ending), so the
  player's `announce` for plugins (ADR-0142) cannot stand in for it.
- **Licences**: Shairport Sync is permissive (MIT-style, with BSD-3, MIT and
  ISC parts; `COPYING` refers to each file); NQPTP is GPL-2.0-only. AirPlay
  is Apple's trademark: Apple's guidelines for third parties allow naming it
  to say what works with it, never Apple's logos.
- **On sofapi (1.8.0)** most of its libraries are already installed -
  libplist, libsodium, libgcrypt, FFmpeg's, soxr, popt; libconfig is not.

## Decided (George, 2026-10-28)

1. **A plugin, offered in first use.** In *Make it yours*, AirPlay is a
   switch, on in every preset as Spotify and Bluetooth are, with a page of
   its own shaped like Spotify's and a row on the review page. It is in the
   image: nothing downloads.
2. **No transport controls on the player at first.** Now Playing shows what
   plays; play, pause and skip are offered once a test with an Apple device
   shows upstream's remote control works. Until then they are the Apple
   device's.
3. **The Apple device's volume moves the player's**, as Spotify's does, and
   is held at full on Fixed (ADR-0137). Whether the player's own slider can
   move the Apple device's is measured with the controls (2).
4. **No password**, for now.
5. **Groups as for every source** (ADR-0166): AirPlay to a grouped player
   plays on the whole group, that player leading; every player stays in the
   AirPlay list. AirPlay's own multiroom - several players picked on the
   Apple device - is for players not grouped in Gexis, and the manual says
   to pick one player of a group.
6. **Our own neutral mark**, the name *AirPlay* in text, and Apple's
   trademark line in *Legal and credits* and in the manual. No Claude Design
   round: the first-use page copies Spotify's.
7. **The adapter in its own public repository**, `gcarstoiu/gexis-airplay`
   (GPL-3.0), as Plexamp's is (ADR-0090).
8. **Apple's Home app** is neither offered nor documented, for now.

9. **Released before it is tried, marked *Limited testing*** (George,
   2026-10-28: no Apple device to test with yet): a tag beside its name - on
   its switch in Settings (the manifest's `tag`) and in *Make it yours* -
   until it has been played to from an Apple device, and whatever that
   shows is fixed then. The manual and the FAQ say what the tag means.

## Open (George)

1. ~~**A player that updates**~~ - **off** (George, 2026-10-28): a release
   does not start announcing a new service on a network nobody chose it
   for; the release notes say where to switch it on (*Settings → Plugins*).
2. **The Apple device for the tests**: none available yet (George,
   2026-10-28) - decision 9 stands until one is.

## Proposed (Claude)

- **T1. Built by us from pinned source**, as Squeezelite is (ADR-0145):
  `gexis-nqptp` 1.2.9 and `gexis-shairport-sync` 5.6.2 (`--with-airplay-2
  --with-alsa --with-avahi --with-ssl=openssl --with-soxr --with-metadata
  --with-metadata-pipe --with-dbus-interface`), in the arm64 trixie builder,
  each commit and its source checksum checked. Debian's `shairport-sync` is
  not installed. Its build libraries are installed by its own build, not in
  the builder image, whose one layer would be rebuilt whole (about 1.4 GB
  on the build machine's `/`, which had 1.9 GB free).
- **T2. Three packages, Plexamp's shape** (ADR-0090, ADR-0107): those two,
  and `gexis-airplay` - the adapter from its repository's tagged release,
  the manifest, the units and the configuration. All three in the player
  meta-package, so in the image.
- **T3. The units.** NQPTP as upstream ships it (a dynamic user,
  `CAP_NET_BIND_SERVICE` for 319 and 320). Shairport Sync as `pi`, in
  `audio`, as every renderer runs (the output chain's meter pipes are
  `pi`'s; a user of its own was the first draft), its name taken from
  `/etc/gexis/device-name.env` (ADR-0048), so a rename restarts it. The
  manifest's `unit` is Shairport Sync's, which opens the device; the
  adapter's unit is `PartOf` it, and the one switch starts and stops the
  three.
- **T4. It plays through `pcm.output`**, as every renderer does, so in a
  group it reaches the group (ADR-0166). The rate is the source's own
  (`output_rate` auto); the format order is set against what each chain
  accepts, the equaliser's loopback included (LESSONS 82). Shairport Sync
  does not set the level (`ignore_volume_control`): the adapter reports the
  sender's, and the core applies it (decision 3).
- **T5. It takes the device before opening it.**
  `run_this_before_entering_active_state`, waited for, asks the adapter to
  `acquire` and returns on `device_freed`, or after a bound, logged. The
  core's polite `release` is D-Bus `DropSession`, then ADR-0091's ladder.
  The adapter sends `release` when the sender's session ends.
- **T6. Now Playing from the metadata pipe**: title, artist, album, cover,
  progress and whether it plays. The adapter logs nothing of what plays.
- **T7. The name and the announcement are Shairport Sync's own**, through
  avahi, as AirPlay 2 needs. It is the player's own plugin, not an uploaded
  one, so ADR-0142's port 5353 rule does not apply: avahi answers, not the
  plugin.
- **T8. Legal and credits** (ADR-0099): both licences; NQPTP's source with
  each release, as GPL-2.0 asks; Apple's trademark line. The wording, with
  the entries OpenCV, NumPy and the two models had been missing since
  ADR-0120, approved by George on 2026-10-28.
- **T9. Covers as bytes: the contract's `artwork` event**, added within
  version 1 (found building, 2026-10-28). A cover reaches the screens as an
  address, and AirPlay's arrive as pictures. The plugin sends each one
  (JPEG or PNG, 800 px at most, under the line's 1 MiB); the core keeps the
  last two per plugin in memory and serves them at
  `/plugins/<id>/artwork/<key>` (the picture's sha256, 16 digits), which the
  plugin names as its metadata's `artwork`. Generic: any plugin whose covers
  come as bytes can use it.

## Settings (ADR-0022)

Appended 2026-10-28 on George's confirmation:

- **[N] AirPlay** - `airplay.enabled`, the plugin's own switch (ADR-0086),
  under Sources and on the Plugins page; on from first use's presets
  (decision 1), and on an update as Open 1 decides.
- Nothing else: the name is the device's, and there is no password
  (decision 4).

## Measured before it is called done

- An Apple device plays to each test player, listed under the player's
  name; Now Playing shows title, artist, album, cover and progress.
- The device taken both ways - AirPlay from Lyrion, Spotify, Bluetooth and
  Plexamp, and each of them from AirPlay - within the release ladder, the
  gap heard.
- The Apple device's volume moves the player's; Fixed holds full level.
- With the equaliser on, and in a group as leader and as member, a join
  while AirPlay plays included: a renderer restarted for a new chain drops
  its session (LESSONS 81, 84).
- AirPlay's own multiroom to two players not grouped.
- The remote control (decision 2), and the player's slider on the Apple
  device (decision 3).
- What it costs a Pi 4, playing and idle; an hour without a dropout on
  Wi-Fi.

## Not decided here

The adapter's code; the first-use page's words, which follow Spotify's; the
release.
