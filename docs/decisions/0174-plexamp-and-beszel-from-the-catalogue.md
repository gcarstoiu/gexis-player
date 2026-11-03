# ADR-0174 — Plexamp and Beszel from the catalogue

**Status:** **Accepted** 2026-11-03 (George: decisions 1-3), Phase 28
(`ph-catalogue-plugins`). George decided the move on 2026-11-03: Plexamp, and
Beszel's agent and hub, out of the player, as standalone plugins. How is
Claude's proposal; three decisions are his.
**Changes:** [ADR-0168](0168-a-plugin-catalogue.md) decision 11 (ours stay
with the release) for these three; [ADR-0169](0169-one-store-for-every-plugin.md)
decision 11 (they become catalogue rows); [ADR-0087](0087-the-beszel-agent-is-the-first-service-plugin.md),
[ADR-0090](0090-plexamp-ships-the-way-beszel-does.md) and [ADR-0114](0114-the-beszel-hub-as-a-plugin.md) (shipped in
the image); [ADR-0129](0129-a-service-says-whether-it-is-connected.md) (connected
status, ours only).

## Context

**Today they are plugins shipped with the player** (ADR-0168 decision 11:
*"Ours stay with the release"*): in the image, pinned exactly by
`gexis-player`, updated only by a player release. Plexamp's adapter has had
13 releases (`gcarstoiu/gexis-plexamp` v0.1.0-v0.4.7), each reaching players
only through one.

**How they run** (read 2026-11-03):
- **Beszel**: two plugins, `beszel` (the agent, a service with rows for the
  hub's address, token and key) and `beszel-hub` (a service with a page on
  port 8095). Both are statically linked Go programs (MIT): no Debian
  dependency, 9.9 and 32 MB. Each runs as the `beszel` user made by its
  package, with `/var/lib/beszel-agent` (the agent's fingerprint) and
  `/var/lib/beszel-hub` (PocketBase, the history). Both ship off.
- **Plexamp**: our adapter (Python, standard library) and Plex's Plexamp
  (Node, fetched on the player from a pin, ADR-0100: it may not be shipped),
  as two units under `pi`: `plexamp.service` (`plexamp-run`: settles the
  claim, then `node`; `ExecStartPre` starts idle, `ExecStopPost` reads the
  exit; a restart burst of 20 in 60 s, ADR-0091) and `gexis-plexamp.service`.
  Plexamp's sign-in is in `/home/pi/.local/share/Plexamp`, its software in
  `/home/pi/plexamp`, fetched by the root helper `gexis-fetch@plexamp`, whose
  progress setup and Settings show.

**What a catalogue plugin gets** (`uploads.py`, the
`gexis-uploaded-{renderer,service}@` templates, ADR-0106, ADR-0170): its own
archive in `/var/lib/gexis/plugins/<id>`, run by our template with no unit of
its own and no arguments; a temporary user per run with its state in
`/var/lib/private/gexis-uploaded/<id>` (kept across updates, backed up);
the system read-only, `/proc` and `/sys` readable, the network open, the
sound card only for a renderer; 1 GB of memory, 128 tasks; settings as
environment, as ours have. It cannot install Debian packages, use
`gexis-fetch`, or keep an id the player ships a manifest for.

**What stands in the way:**
1. **The ids are taken**: the player calls an id its own while a manifest for
   it is installed, and refuses a catalogue or uploaded plugin of that id; the
   catalogue's tools reserve `plexamp`, `beszel` and `beszel-hub` too.
2. **An update removes nothing**: a package dropped from a release stays
   installed (the updater never autoremoves), manifest and all.
3. **Their data is where the sandbox cannot reach**: pi's home, and
   directories owned by `beszel`.
4. **Plexamp needs what its units give it**: the restart burst, the start
   and stop scripts, `HOME`, the device's name, and a download of Plex's
   software with progress shown in setup.
5. **The core knows ours only**: the connected status (ADR-0129), the link
   to a plugin's page, and setup's plugin step all skip uploaded plugins.

## Proposed (Claude)

1. **Three catalogue plugins, the same ids.** `plexamp` from
   `gcarstoiu/gexis-plexamp` (its adapter's repository, now the whole
   plugin); `beszel` and `beszel-hub` from a new `gcarstoiu/gexis-beszel`,
   each archive upstream's binary with its licence, pinned by sha256, and a
   small `run` script. The same ids keep every setting row (`beszel.hub`,
   `plexamp.claim_token`, …) as it is. Listed as TV remote was: George merges
   each first listing on Claude's review note.
2. **Out of the release.** `gexis-plexamp`, `gexis-beszel-agent` and
   `gexis-beszel-hub` leave the image and `gexis-player`'s dependencies;
   `gexis-player` *conflicts* with them, so the update that brings it removes
   them (their data is not package files and stays for the carry-over). Node
   stays in the image: `gexis-player` already lists `nodejs` among the OS
   packages a release carries. The catalogue's reserved ids lose the three,
   and a test ties that list to the manifests the player ships.
3. **What the sandbox gives every catalogue plugin**, not only these:
   - `HOME` set to its state directory;
   - the device's name in its environment;
   - a renderer's restart allowance as Plexamp's unit has it (back after 1 s,
     20 starts in 60 s; ADR-0091 kills a renderer on takeover);
   - the connected status for a plugin run as a temporary user (its uid read
     from the running process);
   - the link to a plugin's page (`port` in the manifest) shown for catalogue
     plugins too;
   - setup's plugin step listing catalogue plugins that setup offers.
4. **Beszel in the sandbox.** The agent's `run` sets its data directory to
   the state directory and keeps it listening nowhere (`--listen -1`, its
   check moved into the script); the hub's serves on 8095 with its data in
   the state directory. Nothing beyond the sandbox is asked for: what the
   agent reads (`/proc`, `/sys`, D-Bus) is readable there. Lost: SMART and
   Docker figures, which the player never had.
5. **Plexamp in the sandbox.** One `run`, the adapter, which starts Plexamp
   as its child and settles the claim from Plexamp's exit (what
   `ExecStopPost` did), starting idle with no saved queue (what
   `ExecStartPre` did). Plexamp's software is downloaded as decision 1 says.
   Node and the adapter share the 1 GB and 128 tasks: measured on a test
   player before the release.
6. **The carry-over** (decision 2): at the new release's first start, for
   each of the three that was switched on, the core installs the listed
   version from the catalogue as *Add* would, moves its data into its state
   directory (Plexamp's sign-in and claim; the agent's fingerprint; the
   hub's database, stopped first), switches it on, and then deletes what is
   left of the old (pi's copy of Plexamp's software, the empty directories,
   the `beszel` user). Without the network it tries again at the next
   catalogue read; the row says so. Backups, factory reset and the identity
   check follow the data to its new place.
7. **One release** carries the move. Beszel goes first on the branch: the
   simpler of the two proves the carry-over before Plexamp's.
8. **Found while reading, fixed here:**
   - Remove with *Keep its settings and sign-in* off leaves Plexamp's
     sign-in (it is in pi's home, which Remove never touched; ADR-0169
     decision 8 says it goes). In the state directory, Remove deletes it.
   - Setup's second part switches plugins on without adding them to the
     Plugins page's list (`_plugins_added`), from reading only.
   - `WRITING-A-PLUGIN.md` says Remove deletes data and settings; since
     ADR-0169 it keeps them when asked.

### Decisions for George

- **Decision 1, Plexamp's own software.** Plex's Plexamp may not be shipped
  (ADR-0100), so the player downloads it.
  - **(a) The plugin downloads it, *recommended*:** its archive carries the
    pin (address and sha256), read when the listing is reviewed; it fetches
    into its own folder and shows its progress on its row. A new Plexamp is
    a new plugin version, with no player release.
  - (b) The core's download helper fetches it from a pin in the listing:
    the same review, but root writing into a sandbox's folder, and the
    catalogue's format grows.
  - (c) The pin stays in the image: a new Plexamp needs a player release
    again, which is what the move is for.
- **Decision 2, players using them.** *Recommended:* carried over at the
  update without a question (6), sign-in and history kept. The alternative:
  the update removes them and the Plugins page offers them again, to be
  added and signed in afresh, the hub's history lost.
- **Decision 3, first use.** *Recommended:* setup offers what it offers today
  (Plexamp in its second part), installed from the catalogue when chosen;
  setup's second part has the network. The alternative: setup stops
  offering Plexamp, and it is found under *Add plugins*.

## Decided (George)

- **Decision 1, Plexamp's own software** (2026-11-03), as (a) proposes: the
  plugin downloads it, from a pin in its archive read when the listing is
  reviewed, into its own folder, its progress on its row; over the core's
  helper fetching from a pin in the listing, and over the pin staying in the
  image.
- **Decision 2, players using them** (2026-11-03), as proposed: carried
  over at the first start after the update, without a question - installed
  from the catalogue, their data moved, switched on again; retried without
  the network, the row saying so. Over removing them and offering them again.
- **Decision 3, first use** (2026-11-03), as proposed: setup offers what it
  offers today; Plexamp, chosen in its second part, is installed from the
  catalogue there, then asks for the Plex claim as now. Over setup no longer
  offering it.

## While building (2026-11-03)

- **No test ties the catalogue's reserved ids to the player's manifests**
  (proposed in 2): both sides already refuse on their own - the player any
  id it ships a manifest for, at upload and at a catalogue install - so a
  list out of step hides or refuses a listing, never installs over ours. The
  catalogue's list loses `beszel` and `beszel-hub` (gexis-plugins #13).
- **Beszel is listed for 1.12.1 and later**, not the release that drops its
  packages: a 1.12.1 player still ships Beszel, so the id is its own and the
  listing is neither shown nor installable there, while a preview of the
  next release (1.12.1 plus the branch) can be offered it to try the
  carry-over before that release (gexis-plugins #14).
- **Older backups** hold Beszel's data in its old places: restored there
  (`backups.RESTORED_ONLY`), then moved by the carry-over like an update's.
  The same for Plexamp's store in pi's home.
- **Plexamp's carry-over moves pi's copy of its software, with its stamp**,
  instead of deleting it (6): it is the plugin's installed copy at the same
  pin, so a carried player does not download Plexamp again. Pi's home keeps
  none of it either way. Both old units are stopped first
  (`plexamp.service`, `gexis-plexamp.service`).
- **Plexamp is listed for 1.12.1 and later**, as Beszel is, after the
  catalogue's list loses `plexamp` (gexis-plugins #15, #16).
- **Setup (decision 3)** offers Plexamp from the catalogue while it is not
  installed: *Download* posts `POST /personalise/install`, which installs it
  as *Add plugins* does and records it as the carry-over records one -
  switched on once in, installed at the next start if it did not get in. A
  catalogue not read yet (a new player reads it a minute after its start) is
  read first. Only a listing that asks for nothing beyond the sandbox is
  offered there, since setup has no page to agree on.
- **The plugin's own folder runs what it downloads** (found on sofapi): systemd
  mounts a DynamicUser state directory `noexec`, and Plexamp's native module
  failed to load from it, the plugin restarting every few seconds. Both
  sandbox units give the folder exec back (`ExecPaths=`). Nothing was kept
  out by it: the units' own `/tmp` and `/var/tmp` were never `noexec`.
- **One unit for the adapter and Plexamp**: a takeover's kill (ADR-0091) now
  ends the adapter too, which comes back with Plexamp a second later. To be
  measured with the takeovers before the release.

## Not in this phase

- Roon, AirPlay 2 and the Lyrion server: each needs a permission the
  sandbox does not have (a loopback card, privileged ports, the music
  storage).
- Spotify, Bluetooth and the Lyrion player: core sources (ADR-0169).

## Settings (ADR-0022)

None new. The three keep their rows; `beszel-hub` keeps none.

## Measured before it is called done

- Each of the three installed from the catalogue on a test player and
  working: the agent reporting to the hub, the hub's page and history,
  Plexamp signed in and playing, taken over and back.
- Plexamp's memory and tasks under the sandbox's limits while playing.
- A player with all three switched on updated to the release: each carried
  over with its sign-in and history, the old packages gone, the `beszel`
  user and pi's Plexamp copy removed.
- A player with none of them updated: nothing installed; *Add plugins* lists
  them from the catalogue.
- First use on a fresh card offering Plexamp from the catalogue (with
  decision 3).
