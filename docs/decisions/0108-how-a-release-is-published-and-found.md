# ADR-0108 — How a release is published and found

**Status:** Accepted — 2026-09-30. Technical, inside George's decisions in
[ADR-0105](0105-updates-over-the-network.md) (GitHub Releases, testing and
stable, the key on R2D2); George left such choices to Claude
(*"technical choice so you can decide what is best"*).
**Phase:** 13c step 2.
**Builds on:** ADR-0105, [ADR-0107](0107-our-parts-as-debian-packages.md),
[Finding 104](../findings/104-what-a-tested-set-weighs-and-where-it-can-live.md).

## Context

ADR-0105 decided *where* (GitHub Releases), *who signs* (the key on R2D2) and
*that* there are two channels. Left open: what one release consists of, how it
fits GitHub's 1,000 files per release, and how a device learns which release
its channel is on. Shown on 2026-09-30 with a one-package test release
(`repo-test-1`): apt installs from a GitHub release through GitHub's redirect
to its storage, verifying a flat repository's `InRelease` against our key alone,
and refuses one whose index was altered after signing.

## Decision

### One release is two flat repositories, split by origin

A release named after `gexis-player`'s version (the tag spells `+` as `-`,
because a `+` in a download URL is read as a space by some clients):

| GitHub release | Holds | Files (first release) |
|---|---|---|
| `r<version>` | our packages and the Raspberry Pi archive's part of the tested set | 10 + 140 |
| `r<version>-debian` | the Debian part of the tested set | 887 |

Each is a **flat apt repository**: the `.deb` files, `Packages`,
`Packages.gz`, `Release`, and `InRelease` signed with the release subkey. A
device uses both as two sources. Split **by origin** rather than by count, so
each half stays under 1,000 files for as long as either archive's share does,
and one half can be checked against its archive on its own.

**The tested set is what the image was built with**: the name, version and
architecture of every OS package installed in the image that release was
tested as (read from the image's dpkg status), fetched from its archive by
exact version and checked by apt against that archive's own signature before
it is re-signed by ours. Nothing newer, nothing chosen by hand.

### A channel is one small signed file

A permanent GitHub release, **`channels`**, holds two files, `testing` and
`stable`, each clearsigned by the release subkey:

```
Channel: testing
Serial: 3
Date: 2026-10-02T09:14:00Z
Release: 0.2.1+git860.a1b2c3d
Repositories: r0.2.1-git860.a1b2c3d r0.2.1-git860.a1b2c3d-debian
Notes: https://github.com/gcarstoiu/gexis-player/releases/tag/r0.2.1-git860.a1b2c3d
```

- **A device reads its channel's file** from the fixed URL
  `…/releases/download/channels/<channel>`, verifies the signature against the
  key in the image, and compares `Release` with the installed `gexis-player`.
- **`Serial` only increases.** A device keeps the highest serial it has
  accepted and refuses a lower one, so an old, genuinely signed file cannot be
  replayed to hold a device back or send it backwards.
- **Promoting to stable** writes `stable` with the release testing already
  names, and a new serial. Nothing is rebuilt or uploaded again.
- **What changed** is the release's notes on GitHub, linked from the file.

### Publishing is a separate, deliberate step

`make release` builds the two repositories locally from `packaging/out` and a
built image, signs them, and checks them (every package present, every
checksum, both signatures). `packaging/publish.sh` uploads a built release and,
when asked, moves a channel. Only publishing reaches GitHub; it is run on
George's say-so, as every outward step is.

## Consequences

- A device needs only `github.com` and our key; every past release stays
  installable, so going back is always possible.
- A release uploads the whole tested set (about 0.9 GB) even when little
  changed; a device downloads only what differs from what it has.
- The channel file is the one thing a device trusts to say *which* release;
  its signature and serial carry that trust, not GitHub.

## Not in this record

- The device side (checking, downloading, installing, going back): 13c
  step 3.
- The GPL source offer for the OS packages we publish (ADR-0105, to confirm
  before the first public release).

## Open

- **Each release uploads its whole Debian half again**, 876 files, even when
  not one changed (identical in 852 and 856). The second release in an hour
  hit GitHub's secondary rate limit; `publish.sh` is now resumable and paced,
  which makes it work, not cheap. Better: a release whose Debian half is the
  same as an earlier one's names that earlier half in its channel file. The
  updater then has to learn each release's repositories from where it was
  told them, not from the `<tag>-debian` convention - including the release
  it goes back to - so it is its own change.

## Unverified

- A full-size release: 1,037 files in two releases, and apt fetching a few
  hundred of them through the redirect.
- Fetching every package of the tested set by exact version from both
  archives (0 of 1,027 were missing on 2026-09-30; not yet fetched).
