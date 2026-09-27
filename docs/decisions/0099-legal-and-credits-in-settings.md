# ADR-0099 — Settings carries a legal notice and credits

**Status:** **Accepted** — George, 2026-09-27: *"create two more entries in
settings: 1. Legal disclaimer -> that covers not only this, but in general the
entire player, the license scheme, what we took from other repository based on
their licenses etc. 2. Credits -> whatever contributed to the player needs to
be credited and acknowledged for their work."* **Built; wording and six findings with George.**
**Date:** 2026-09-27

## Decision

1. **Two rows in Settings → System: *Legal* and *Credits*.** Each opens a page
   to read. Neither has a setting.
2. **Legal** covers the whole player:
   - The player's own licence, GPL-3.0-or-later
     ([ADR-0025](0025-project-licence-gplv3.md)), and where its source is.
   - That it comes with no warranty.
   - Every third-party component, with its licence: shipped, fetched at build
     time, installed by the user, or reimplemented from.
   - The proprietary pieces that are downloaded, not shipped (Plexamp), and
     under whose terms.
   - Unofficial clients: the Qobuz receiver (ADR-0098) and any like it.
   - Trademarks, which are used only to name what they belong to.
   - The external services contacted, and what is sent to them.
3. **Credits** acknowledges every person and project whose work is in the
   player, by name, with a link. It includes the skin authors and the upstream
   code the renderer was reimplemented from.
4. **One source of truth, in the repository, checked at build time.** Both pages
   come from a data file listing each component with its name, role, author,
   licence, link and how it arrives. They are not hand-written prose that drifts.
   The build fails when something the image installs has no entry. The same
   file gives the repository a `THIRD-PARTY.md`.
5. **The wording is George's to approve, and it is not legal advice.** Claude
   drafts it; George reviews it before it ships.

## How (as built, 2026-09-27)

- **`core/src/gexis_core/notices.json`** holds 45 components, each with a name,
  role, author, licence, link, how it arrives, and a group. It also holds both
  pages' prose, which is **drafted and awaiting George's approval**.
  `notices.py` builds each page from it and serves it at `/notices/legal` and
  `/notices/credits`. `python -m gexis_core.notices` writes `THIRD-PARTY.md`.
- **A `document` row type** opens a full-screen reader on the panel, built like
  the skin picker. It has been checked through the API and the build; **nobody
  has seen it on the panel yet.**
- **`core/tests/test_notices.py` fails the build** when a stage fetches a URL,
  installs a Debian package, or bundles a UI or Python dependency that has no
  entry, or when `THIRD-PARTY.md` is stale. To prove it can fail, go-librespot
  and Samba were removed from a copy; both were caught.
- Licences nobody read, mostly Debian packages, say *"see
  /usr/share/doc/<package>/copyright"* rather than a name.

## Found while building it: open, and George's to decide

A research pass over everything the image contains (2026-09-27) found:

1. ~~**Plexamp is included in the image, and our right to redistribute it is not
   established.**~~ **Resolved by ADR-0100 (George: "1A"):** it is fetched from
   Plex on the device when switched on. The stage copies Plex's proprietary tarball, BASS libraries
   and all, into `/home/pi/plexamp`. No licence or EULA comes with it, and no
   record here has Plex's terms. The Legal page says truthfully that it is
   included. The alternatives are Plex's permission, or installing it on the
   device when the user asks, as ADR-0098 does for Qobuz.
2. **go-librespot** is an unofficial Spotify client shipped in the image. That
   is the ground on which ADR-0098 kept Qobuz's receiver out.
3. ~~**The image's GPL obligations have no written offer of source.**~~
   **Resolved 2026-09-27 (George: "Fine"):** the Legal page and
   `/usr/share/doc/gexis-player/SOURCE.md` carry a three-year written offer,
   handled through the repository's issues. `packages.txt` records every
   package and its source version. peppyalsa's modification is named there.
   Originally: That covers
   the kernel, squeezelite, Samba, go-librespot, and our modified peppyalsa
   (which also needs its GPL §5a "modified" notice, now on the Legal page).
4. ~~**Some licence texts do not reach the device.**~~ **Resolved 2026-09-27
   (George: "Agree"):**
   - The UI's bundled licences go to `/opt/gexis-ui/licenses/`.
   - The screensaver, templates and Beszel MIT notices go to
     `/usr/share/doc/gexis-player/licenses/`, and so do go-librespot's and
     peppyalsa's GPL notes.
   - The player's `COPYING` ships beside them.
   - yarl's and propcache's NOTICE files were already in the venv; checked on
     gexis.
   - `verify-image.sh` checks all of it.

   Originally:
   - OFL for Nunito Sans and IBM Plex Mono
   - MIT for Svelte, Beszel, and foonerd's screensaver and templates
   - Apache NOTICE files for yarl and propcache
   - go-librespot ships with no licence text.

   Shipping the texts under `/usr/share/doc/gexis-player/` would cure these.
5. **The Spotify, Bluetooth and Lyrion marks** came from Claude Design with no
   recorded source.
6. **`design/assets/album-art.webp` and `artist-photo.webp`** are photographs
   of real people with no recorded source. They are committed to the public
   repository, though not shipped.
