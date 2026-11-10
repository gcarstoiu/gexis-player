# ADR-0178 — Fixes from the review of 1.16.1 that change what is seen

**Status:** **Accepted** 2026-11-10 (George: decisions 1-3 option A, decision
4 yes, all as recommended). **Changes:**
[ADR-0028](0028-ui-serving-and-command-channel.md) (decision 1),
[ADR-0104](0104-how-the-device-knows-it-needs-setup.md) and
[ADR-0134](0134-the-panel-says-when-the-player-has-no-network.md)
(decision 2; for a player already set up, the 2026-10-18 amendment's one
password), [ADR-0156](0156-home-assistant-dashboard-on-the-screen.md)
(decision 3), [ADR-0106](0106-plugins-you-install-and-update.md)
(decision 4).

## Context

A review of everything since 0.10.2, at v1.16.1, found 55 defects. George
asked for all of them to be fixed, critical first, and for any fix that
changes what a user sees or does to be put to him first. Four did.

## Decisions

1. **A browser drives the player only from the player's own pages.** A
   request that changes something, and a `/state` or `/touchpad` socket, is
   refused when it carries an `Origin` other than the player's own, or
   `Sec-Fetch-Site: cross-site`. A request from a browser must name the
   player by an address, a name without dots, `localhost` or a name under
   `.local`; any other `Host` is refused, which stops a public name being
   pointed at the player to read it. Home Assistant, curl and plugins send
   no browser headers and are not affected; Home Assistant's covers are
   fetched by Home Assistant. *Who notices:* someone opening the player in a
   browser under another name (a router's or a VPN's).
2. **A player already set up is only given a network over its setup
   network.** While it is open on a player already set up (ADR-0104's
   `needed` false), requests arriving on the setup network's address reach
   the setup page, its status and networks, its answers and Finish, and
   nothing else; restoring a backup is not offered there (it still is on a
   new player). Such a player with a screen in use (not headless, one
   connected) opens its setup network with a password of its own, shown on
   the panel; a headless one, and every new player, keeps `gexis-setup`.
   Once its home network is back, the player returns to it within 10
   minutes, whether or not the setup page is still open.
3. **A link in the Home Assistant dashboard that opens a new window does
   nothing on the panel** (the frame no longer allows pop-ups); links within
   the dashboard work as before.
4. **An uploaded or catalogue plugin whose settings rows the registry
   refuses is refused at upload**, with the registry's reason in the upload's
   existing refusal (`plugin.json: ...`).

## Consequences

- Decision 2 brings back, for a set-up player with a screen, the panel's
  password that the 2026-10-18 amendment removed for every player.
- A player opened by another name in a browser answers with a short sentence
  naming the ways that work.
- No setting is added.
