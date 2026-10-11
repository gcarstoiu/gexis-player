# ADR-0134 — A network lost after boot opens the setup network

**Status:** **Accepted** — George, 2026-10-11. Proposed the day before as a
strip on the panel; George: *"we should have this already. When no network
is detected then we show a WiFi selection screen"*. At boot that was already
so (ADR-0104); after boot it was not, and his answer was to make it so:
*"Yes, after 2 minutes"*.
**Amends:** [ADR-0104](0104-how-the-device-knows-it-needs-setup.md) §3,
which opened the setup network at boot only.

## Context

On the bar player, the address the router gave was already taken by another
device: NetworkManager's duplicate-address check refused it and the player
had no IPv4 address. Nothing on the panel said so.

At boot a configured player waits 90 s for a network - NetworkManager's
*connected*, which needs an address, so a refused address counts as none -
then opens its setup network, and the panel shows the setup screen to join
one; it looks for saved networks every five minutes and rejoins one in
range. **After boot nothing watched**: a network lost later was silent.

## Decision

1. **The core keeps watching after boot** (`SetupNetwork.watch()`, every
   15 s, with boot's own test).
2. **Two minutes without a network opens the setup network**, with the same
   screen as at boot, and the same five-minute rejoin of a saved network in
   range. A Wi-Fi roam or a router restart passes in less.
3. **It stands aside** while setup's own join is under way, while setup
   itself is unfinished, and while the setup network is already open: those
   stay `run()`'s. A join from Settings goes through `wifi.join`, which gives
   up after 45 s (`JOIN_TIMEOUT_S`) - inside the two minutes, so it is not
   flagged.
4. **No strip, no new state, no setting.** The proposal's strip and its
   three questions are withdrawn.

## Consequences

- With one radio, the open setup network takes the Wi-Fi off the home
  network; the five-minute retry is what gives it back, as at boot.
- A headless player opens it too, with the fixed password, as at boot.
