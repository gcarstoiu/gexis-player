# ADR-0136 — Switching between players on the phone

**Status:** **Accepted** — George, 2026-10-11: *"The switcher on the phone we
can do now. Simple switch with status and renderer connected."*

## Context

Each player serves its own phone page at its own address
(`name.local:8090`). A browser keeps each address apart, so with two players
on one network the owner keeps two tabs open. Players already resolve by name
over mDNS (avahi), and avahi already advertises each player's share
(ADR-0049 §4).

## Decision

1. **Each player announces itself**: `_gexis._tcp` on port 8090, an avahi
   service file in `gexis-system`, beside the share's.
2. **Each core finds the others** with `avahi-browse` (installed with avahi),
   every 30 s at most, and asks each for `GET /player/status`: its name,
   address, whether it plays, and the renderer connected. The phone reads
   `GET /players` from the player it is on; the core asks the others, so the
   browser never reaches across addresses.
3. **On the phone, the line under *Settings*** (name, address) becomes a
   button when another player is found. It opens a list of every player,
   this one marked, each with its status - *Playing · Spotify*, *Paused ·
   Lyrion*, *Idle* - and choosing another opens that player's page **in the
   same tab**.
4. **The panel has no switcher**: a panel belongs to its own player.

## Consequences

- A home-screen bookmark still opens the player it was made on; the switcher
  moves on from there.
- A player that is off, or on another network, is simply not listed.
- Players older than this release announce nothing and are not listed until
  updated.

## Built (2026-10-11, on `phase-13d`)

As decided. Tried on sofapi and the bar player, both on the preview: each
lists the other with its status (*Stopped · Lyrion*), and the phone's list
opens from the header line.
