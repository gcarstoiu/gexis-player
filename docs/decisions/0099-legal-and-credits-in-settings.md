# ADR-0099 — Settings carries a legal notice and credits

**Status:** **Accepted** — George, 2026-09-27: *"create two more entries in
settings: 1. Legal disclaimer -> that covers not only this, but in general the
entire player, the license scheme, what we took from other repository based on
their licenses etc. 2. Credits -> whatever contributed to the player needs to
be credited and acknowledged for their work."* **Building.**
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

## How (as built - filled in when it is)

Not yet built.
