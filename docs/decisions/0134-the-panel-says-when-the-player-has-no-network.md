# ADR-0134 — The panel says when the player has no network

**Status:** **Proposed** — 2026-10-10, for George's three decisions below.
**Builds on:** [ADR-0104](0104-how-the-device-knows-it-needs-setup.md) (the
setup network, and how the core already decides it is on a network).

## Context

On the bar player, the address the router gave was already taken by another
device: NetworkManager's duplicate-address check refused it, and the player
had no IPv4 address. Nothing on the panel said so. Lyrion, the phone page,
updates and enrichment all failed, each in its own way, with no one reason
shown (the to-do list's c06; recorded in `docs/HANDOFF-ARCHIVE.md`).

What exists today: at boot the core waits up to 90 s for a network
(`setup_network.online()`: an Ethernet or Wi-Fi device NetworkManager calls
*connected* - its word for an address and a route) and opens the setup
network if none comes. Once online, nothing watches again; a network lost
later is silent. ADR-0104 keeps the setup network to boot only (George).

## Proposal

1. **The core keeps watching**, for the life of the player: NetworkManager's
   device states every 15 s, with the same test as at boot. No new package.
2. **After 60 s without a network** - outside setup, with the setup network
   closed - `/state` carries `network: {online: false, since, reason}`, and
   the log says it once. `reason` is read from the same states: Wi-Fi joined
   but still getting its address (the bar's case) is *no address*; Wi-Fi not
   joined, or no cable, is *not connected*.
3. **The panel shows a strip** along the top of every screen, over nothing
   that plays: *No network address* or *Not connected to a network*, with one
   line - *Music from the network and the phone page wait until it is back.
   Settings → Network.* The *no address* case adds *Restarting the router
   usually fixes it.* It goes by itself when the network is back.
4. **The setup network is not reopened** after boot (ADR-0104 unchanged).
5. **No setting** (nothing for ADR-0022's inventory).

## For George to decide

- **A. Where it shows:** a strip on every screen (proposed), or only on the
  idle and waiting screens.
- **B. How long before it shows:** 60 s (proposed: a Wi-Fi roam or a router
  restart passes in less), or another delay.
- **C. Setup's network after a long loss:** stays boot-only (proposed), or
  reopens after, say, 10 minutes without a network.

## Consequences

- A phone cannot show this: with no address it cannot reach the player.
  The panel is the only surface that can.
- A headless player has nothing to show it on; it is in the log only.
