# ADR-0106 — Plugins you install and update

**Status:** **Accepted** — George, 2026-09-29, the four decisions below (each
marked **Decided**), and the notice shown before an upload, in his words:
*"This plugin is not part of Gexis Player. It is installed and run at your own
risk and responsibility."*
**Date:** 2026-09-29
**Phase:** 13a ([DEVELOPMENT.md](../DEVELOPMENT.md), whose criteria this
answers). The first public release waits on it.
**Raised by:** George, 2026-09-28 - plugin updates and uploads are *"a phase set
before themes"*, after a plugin's author stopped publishing binaries: *what a
user builds and uploads is their choice, not ours*. Updates were decided the
same day (option B: *"we need to check them before allowing an update"*).
**Builds on:** the plugin contract ([ADR-0016](0016-plugins-as-separate-processes.md),
[ADR-0084](0084-plugins-speak-json-lines-over-a-unix-socket.md), [ADR-0086](0086-a-plugin-declares-itself-in-a-manifest.md),
[ADR-0088](0088-a-plugins-settings-reach-its-unit-as-environment.md)) and the
download mechanism ([ADR-0100](0100-software-we-may-not-redistribute-is-fetched-on-the-device.md)).
**Shares with:** [ADR-0105](0105-updates-over-the-network.md) the signed
repository.

## Two kinds of plugin, two paths

- **Ours** (Plexamp's adapter, Beszel, and any we add): built, tested and
  signed by us.
- **Uploaded**: built by the user or someone they trust, installed from a phone
  or computer, **not part of Gexis Player**, run at the user's own risk.

They share the contract, the Plugins screen, the switch, Remove and the
download row. They do not share trust.

## Proposed: our plugins update from versions we have tested

1. **An update is a new package in our repository** (ADR-0105). A plugin whose
   software we may not ship (Plexamp) moves by **its pin**: the package carries
   the maker's URL and a sha256 we have tested, and the device fetches that
   version on the next start (ADR-0100, unchanged). Nothing on the device ever
   fetches a version we did not name.
2. **Beszel and the adapters move to the download mechanism** (13a criterion
   5): the image carries pins, not binaries, as Plexamp does since ADR-0100.
3. **The plugin's row says an update is waiting**, installs it with the
   download row's progress and Retry, and keeps the previous version for one
   step back.
4. **When ours update: with the release** (ADR-0105) - one catalogue, one
   *Updates* screen. **Decided** (George: *"With the release. Might be less
   complicated than individual updates."*).

## Proposed: uploaded plugins

### The package

A `.tar.gz` holding, at its top level:
- `plugin.json` - the manifest the core already reads (ADR-0086: id, name,
  kind `renderer` or `service`, settings rows), plus **`version`** and
  **`run`** (the command to start, relative to the package), and **no `unit`**
  (the player writes the unit; see below);
- `mark.png` - its mark, as for ours;
- its files, **built for the Pi** (aarch64, Debian 13).

**Decided: the `.tar.gz`** (George: *"tar.gz"*). A `.deb` runs its maintainer
scripts as root before anything of ours can check it, which is exactly what the
sandbox exists to prevent.

### Installing

From **Settings → Plugins → Upload a plugin**, on a phone or computer only (the
panel has no file picker and does not offer it):
1. **A notice first** (George's words): *"This plugin is not part of Gexis
   Player. It is installed and run at your own risk and responsibility."*
2. **The core checks it before anything is written**: the manifest parses and
   passes the contract's validation; its id is not one of ours or another
   installed plugin's; no path escapes the package (no `..`, no absolute paths,
   no links pointing out); `run` exists and is an aarch64 executable or a
   script; a size limit.
3. It is unpacked into `/var/lib/gexis/plugins/<id>/<version>/` - **never under
   `/usr` or the image's own directories** - and `current` points at it. The
   previous version stays for one step back.
4. It appears in the Plugins list under its kind, **off**, with its mark and a
   tag saying *uploaded*.

**Uploading a newer version updates it**; the same `version` is refused;
**Remove** deletes the folder, its unit and its settings rows.

### The sandbox

**The player writes the unit, and never takes one supplied.** Every uploaded
plugin runs under the same template, `gexis-uploaded@<id>.service`:

- **its own unprivileged user, made for each run** (`DynamicUser=yes`; **Decided**,
  George: *"temporary"*; nothing is left behind by Remove),
  **never root**, `NoNewPrivileges`, no capabilities;
- **the system read-only** (`ProtectSystem=strict`, `ProtectHome=yes`,
  `PrivateTmp`), and **only its own data folder writable**
  (`/var/lib/gexis/plugins/<id>/data`, kept across versions);
- **the sound card only for a renderer** (`DevicePolicy=closed` with the ALSA
  devices allowed for `kind: renderer`; a service gets none);
- **the plugin socket** through its group (ADR-0084's `SupplementaryGroups`),
  which is how it talks to the core, and nothing else of ours;
- **memory and CPU limits** (`MemoryMax`, `CPUQuota`; values to be measured
  against Plexamp, the heaviest renderer we run);
- **the network: open** (**Decided**, George: *"open"*): a streaming renderer
  needs the internet, and the device is on a home network anyway.

**Arbitration takes the device from it as from any renderer** (ADR-0027): an
uploaded renderer gets no special standing.

### Backups

A backup keeps an uploaded plugin's **settings and data, not its package**
(George, 13a criterion 4: *"Agree with your suggestion"*). After a restore the
plugin is listed as *needs uploading again*, with its settings waiting.

## Not in this record

- **A store or catalogue of other people's plugins.** Uploading is the user's
  choice of what to run; we do not list or vouch for third-party plugins.
- **Signing uploaded plugins.** A signature would only say who built it; the
  sandbox is what limits what it can do.

## Unverified

- Whether `DynamicUser` works with the plugin socket's group ownership as
  ADR-0084 builds it (`SupplementaryGroups` on a dynamic user is documented to
  work; not tried here).
- Whether a renderer under `ProtectSystem=strict` can open the `output` PCM,
  whose configuration lives in `/etc/alsa` (read-only is enough in principle).
- The memory and CPU limits' values.
