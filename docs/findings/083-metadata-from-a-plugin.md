# Finding 083 — Metadata from a plugin, and the credential it arrives with

**Date:** 2026-09-25
**Question:** The half of the contract nothing outside this repository had ever
used. Contract v1 was frozen on the arbitration evidence
([Finding 082](082-a-renderer-from-another-repository.md)) with metadata named
as the remaining gap — George: *"Freeze now and do metadata. If we need to adapt
it's v2."* Does it work, and what does it cost?
**Scope:** `gexis`, `gcarstoiu/gexis-plexamp` running from `/opt/gexis-plexamp`,
Plexamp claimed against George's own Plex account, one track. Read from the
moOde-compatible metadata file, which is what the panel and anything else on the
device are told. **The panel itself was not watched.**

## It works, and it needed one change in the core

```
file=plexamp
artist=2 Unlimited
album=Get Ready
title=Get Ready for This (orchestral mix)
coverurl=http://192.168.178.191:32400/library/metadata/91794/thumb/…?X-Plex-Token=…
```

Title, artist, album and artwork, from a plugin in another repository, through a
frozen contract, to the panel.

**The core was dropping it.** `_plugin_event` handled `available`, `acquire` and
`release` and let everything else fall through to a debug line — so a plugin
could send perfect metadata and nothing would happen, which is precisely the
shape of gap that "never exercised from outside" describes. It now builds a
`TrackMetadata` from the fields the contract names and hands it to the same
`state_store.set_metadata` the three built-ins reach through
`on_metadata_change`.

**Generic, and defensive in one specific way:** a plugin is written by somebody
who cannot test against this device, so a value of the wrong type is dropped
with a log line rather than raised. A renderer that sends a string where a
number belongs should lose that field, not take the daemon down mid-track.
`source_type` is set by the core, not read from the plugin: it says who supplied
the metadata, and a plugin naming a different renderer would be lying about
attribution the panel draws.

**Two translations belong to the plugin, not the core**, and finding them is
what writing a real one is for:

- **`repeat` is a word, not a flag.** The contract says off / all / one, because
  a panel has to draw which. Plex counts 0 / 1 / 2, and **`1` is one track** —
  the opposite order to how most people would guess.
- **Title and artist are not on the player.** Plexamp's timeline carries
  position, duration, volume and keys; the names are on the Plex Media Server,
  fetched once per track and cached. A poll every second that also fetched
  metadata every second would be a request per second to somebody's NAS for an
  answer that changes when the song does.

## A `ProtectHome=yes` that reported the wrong fault

The plugin reads Plex's token from Plexamp's own settings rather than asking for
a second copy — the user already gave it when they claimed the player, and a
second copy is a second thing to go stale. Its unit had `ProtectHome=yes`, which
hides that directory, and the symptom was:

```
gexis_plexamp.server INFO no Plex token yet - the player has not been claimed
```

about a player that plainly had been. `ProtectHome=read-only` fixes it. **Worth
recording because the message was honest and still misleading**: the plugin
correctly reported what it could see, and what it could see was wrong.

## The cost, which is a decision and not a detail

**The artwork URL carries a Plex account token, and the core publishes it.**

- `/var/local/www/currentsong.txt` is mode `0666` on the device.
- The state goes over `:8090` to **anything on the LAN**, which is ADR-0028's
  stated model.

This is not a new *kind* of exposure — [ADR-0083](../decisions/0083-a-backup-leaves-the-device.md)
already records that `GET /settings` serves the Pixabay, fanart and ListenBrainz
keys in plaintext to the same LAN, and the Beszel token joined them. **It is a
new degree.** Those are per-service API keys; a Plex token is account-wide and
reaches every server that account can see.

**Nothing has been decided about it.** Three options, with what each costs:

| | cost |
|---|---|
| Accept it | nothing to build; consistent with ADR-0028 and with every other credential here |
| The plugin stops sending artwork | one line, `supports_artwork: false`; the panel falls back to enrichment's covers, which work |
| The core proxies artwork | a new route, a cache, and a **contract question** — `artwork` is a URL and the frozen v1 has no way to say "fetch this on my behalf". That is a v2 conversation |

**The first is what happens if nobody chooses**, which is why it is written here
rather than left implicit.

## What this does not show

- **Nothing about the panel.** The metadata file is the oracle; whether Now
  Playing draws the cover, the title and the progress correctly was not looked
  at.
- **One track.** Not a queue, not a gapless transition, not a track whose server
  answer is missing fields.
- **`queue` and `volume` are routed but unexercised.** A plugin sending a queue
  now reaches `set_queue`; Plexamp does not send one. **`volume` is still
  dropped**: a plugin renderer is not registered with the volume bridges, which
  is real work and not done.
- **No sample rate.** The timeline does not carry one, and the server describes
  the file rather than what the DAC was handed, so the plugin declares
  `supports_sample_rate: false` rather than guessing.
