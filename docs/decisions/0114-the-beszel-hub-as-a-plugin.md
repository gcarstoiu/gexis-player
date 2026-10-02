# ADR-0114 — The Beszel hub as a plugin

**Status:** **Proposed** — George, 2026-10-02: Phase 13e (*"Beszel Hub -
same reasoning"*), started early (*"While we wait can we already start with
the beszel hub?"*). The choices under *For George* are open.
**Phase:** 13e ([DEVELOPMENT.md](../DEVELOPMENT.md)).
**Builds on:**
- [ADR-0087](0087-the-beszel-agent-is-the-first-service-plugin.md) (the agent, the first plugin that is
  not a renderer);
- [ADR-0107](0107-our-parts-as-debian-packages.md) (one package per
  third-party component, versioned by its own version).

## Context

The player already ships Beszel's **agent**, which reports the device's
load to a **hub** somewhere else on the network. The hub is the web page
that shows the history; most owners have no other machine to run it on.
Upstream publishes both from one release:
`henrygd/beszel` v0.20.0 (2026-09-19, the latest; the agent's pin), with
`beszel_linux_arm64.tar.gz` (12 MB) for the hub, MIT-licensed like the
agent.

**The hub's default port is 8090, which is the player's own**
(`state_port`); 8091 is the meters'.

## Proposed (technical)

1. **A package, `gexis-beszel-hub`,** built like `gexis-beszel-agent`: the
   upstream binary at the agent's pin, checked against its SHA256, versioned
   by Beszel's version, in the release's `ours` part.
2. **A `service` plugin** like the agent (ADR-0086): its own unit, its own
   manifest, the Plugins screen's row with status, off until switched on.
3. **Its data under the plugin's own directory**, so 13a's backups carry it
   and Remove can keep or delete it.
4. **The memory cap is 13a's 1 GB** unless measuring shows otherwise; the hub
   is a single Go process with an embedded database.

## For George

1. **Its port:** **8095** (recommended; free on the player - measured 2026-10-02 it listens on 22, 139, 445, 3678, 8090, 8091, 32500 and one ephemeral port), or another.
2. **How it arrives:**
   - **A (recommended):** in the image, off until switched on, like the
     agent - 12 MB, no download, no consent question.
   - **B:** downloaded from the release when switched on, like the skin packs.
3. **The first account:** made on the hub's own page at the first visit,
   as upstream does (recommended), or set in Settings beforehand.
4. **This device's own agent:** when both are on, the agent is connected to
   the local hub automatically, so the player's own history appears with no
   copying of keys (recommended), or left to the user as today.
5. **Settings** (for ADR-0022's inventory, appended only after you confirm):
   the hub has its own login and settings page, so the plugin itself needs
   none beyond its switch; the Plugins row shows its address
   (`http://<name>.local:8095`).

## Not settled here

- Its measured memory and CPU with history building; the 1 GB cap stands
  until then.
