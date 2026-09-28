# Finding 097 — Pibuz publishes source only; our pin points at nothing

**Date:** 2026-09-28
**Question:** Testing Remove on gexis (ADR-0100, amended 2026-09-28): switching
Qobuz Connect back on failed with `The requested URL returned error: 404`,
three attempts. Why?

**Scope:** GitHub's API and the release pages of `PhilipVinc/pibuz`, read on
2026-09-28 around 11:55, and gexis's own state. Nothing was downloaded from
anywhere else.

## Result

- **The v2.5.1 release has no assets any more.** Its text now reads:
  *"Source release: no prebuilt binaries are published. Build with `cargo
  build --release -p pibuz` (see the README), or
  `./scripts/build-aarch64-pibuz.sh` for a Raspberry Pi."* The URL we pin
  (`…/v2.5.1/pibuz-2.5.1-linux-aarch64.tar.gz`) answers 404.
- **It was deliberate:** the commit of 2026-09-27 23:08 is titled *"Releases
  publish source only: disable the binary build"*. No reason is given. The
  author's build script says Pibuz builds natively on a 4 GB Pi, or by cross
  compilation with Docker.
- **The same night, both our issues were answered:** *"External volume mode
  (#3); fail a busy-device play honestly (#2)"*, 23:32, in a version 2.6.0
  that exists as source only.
- **The consequences for Gexis:**
  - **No new install of Qobuz Connect can succeed**, from any image.
  - The row said so: `failed`, with the 404, after three attempts. ADR-0100's
    feedback did its job.
  - **gexis lost its working copy to the Remove test**, which deleted exactly
    what it was asked to. The test should have checked that the download still
    existed first. Nothing else held 2.5.1: the only other copy anywhere is
    the 2.5.0 spike in `/tmp/pibuz-spike` on gexis.

## What follows

A decision for George, on how Pibuz reaches a player:
- **A.** We build it from the author's tagged source and publish the binary.
- **B.** Each player builds it for itself when Qobuz Connect is switched on.
- **C.** Ask the author why binaries stopped, then choose between A and B.
  Claude recommends C.

Whichever he picks, the Legal page's Qobuz paragraph ("from its author's own
release") changes with it. **For development only** (George: *"You can build
2.5.1 for dev purposes"*), 2.5.1 is built from its tag and installed on
gexis by hand, and nothing is published.
