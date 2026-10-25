# ADR-0159 — Raspberry Pi Imager

**Status:** **Accepted in part** — 2026-10-24 (George): D1 yes, D2 and D3
not now, D4 open. A task alongside Phase 17's close, not a phase. Settles
ADR-0021's deferred *Image distribution channel* for now.

## Context

Today: each release carries `gexis-player.img.xz`; `docs/INSTALL.md` has the
user choose it in Imager with *Use custom*. The image runs its own
`firstrun.sh` (`image/stage-gexis/01-firstboot`, `ENABLE_CLOUD_INIT=0`), and
the player is set up from a phone over its setup network (ADR-0031, 0104).

Imager as of 2.0.12 (2026-10-08), from its source, docs and issues:

- **Use custom** offers no customisation: a local file is treated as
  `init_format: none` and the settings steps are skipped (rpi-imager #1302,
  #1507, closed as not planned). `docs/INSTALL.md` step 5 describes Imager 1.x.
- **A list of our own** (Repository JSON v4, `doc/json-schema/os-list-schema.json`):
  required per entry `name, description, icon, url, extract_size,
  extract_sha256, image_download_size, release_date, devices`. Imager opens
  it from `--repo`, *App Options → Content Repository*, an
  `rpi-imager://open?repo=<https URL ending .json>` link (2.0.3, with a
  confirmation) or a double-clicked `.rpi-imager-manifest` file. It then
  shows the OS by name, downloads it and checks `extract_sha256`.
- **`init_format`** decides what Imager writes to the boot partition:
  `none` nothing; `systemd` its own `firstrun.sh` and a `systemd.run` entry
  in `cmdline.txt` (would replace ours and add a second entry; its user step
  passes its own user name - read from source, untested); `cloudinit` /
  `cloudinit-rpi` NoCloud files (needs cloud-init, which the image leaves
  out); `rpi-preseed` (2.0.11; its package is not in Raspberry Pi's archive).
- **Imager's own list**: a Google Form, *Request an addition to the
  Raspberry Pi Imager OS List*. It asks for one or two named individuals as
  contacts, device annotations, a 40 x 40 icon and a minimal sub-list, and
  asks whether the OS ships a default password and an unattended update
  mechanism. No review time is published. Media player OSes listed: moOde,
  Volumio (`systemd`), piCorePlayer, LibreELEC, OSMC (`none`).

## Decisions

**D1 — The image file with *Use custom* stays,** and `docs/INSTALL.md` says
what Imager 2 does: nothing to skip. **Done 2026-10-24.**

**D2 — Our own Imager list, published with each Stable release:** one entry,
`init_format: none`, as a `.json` release asset reached through the release's
`latest` download URL; the image URL inside names that release's own asset.
`docs/INSTALL.md` offers an *Open in Raspberry Pi Imager* link and the
manifest file beside the image. Setup stays on the phone. **Not now:**
GitHub renders an `rpi-imager://` link as plain text (checked with its
Markdown API, 2026-10-24), so only the downloaded file would be left, which
saves little over *Use custom*.

**D3 — Imager's own settings (Wi-Fi, name): not now.** They would need the
image to take Imager's `firstrun.sh` or cloud-init in place of its own first
boot.

**D4 — Imager's own list: open.** It needs a list file like D2's and
George's name as a contact, and an answer for the setup network's fixed
password (`gexis-setup`, used until a screen is kept, and always without
one).

## To measure

- The link and the manifest file in Imager 2.0.12 on Windows, macOS and
  Linux (open: #1609 local manifest on Windows, #1776).
- That Imager follows GitHub's redirect from a release's `latest` URL.
- The written card starts and raises the setup network as one written with
  *Use custom* does.
