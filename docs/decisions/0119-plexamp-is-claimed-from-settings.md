# ADR-0119 — Plexamp is claimed from Settings, and says when it is

**Status:** **Draft** — 2026-10-05. George asked for the screen on the
Settings copy review and said yes to building it; the questions below are
his before anything is built.
**Builds on:** [ADR-0090](0090-plexamp-ships-the-way-beszel-does.md) §4-5 (one
row, the token; our plugin acts on it), [ADR-0048](0048-how-the-device-name-reaches-four-services.md)
(one device name), [ADR-0088](0088-a-plugins-settings-reach-its-unit-as-environment.md) (a row's `env`),
[ADR-0022](0022-settings.md) (`plexamp.claim_token`, [N]). On
[Finding 077](../findings/077-plexamp-on-gexis.md).

## Context

George, on the Settings copy review, 2026-10-05, about the *Claim token* row:

> Text should only be: Claim token from plex.tv/claim. The link is tapable and
> it opens a new tab. Once claim is done, this tile changes to something like
> Claimed, with a green checkmark. A button is offered saying Re-claim, that
> shows the text entry again.

Then, to "a small *Claim again* link under *Claimed ✓*": **yes**.

### What is there today - found while answering

- **The claim was never built.** The plugin accepts the row and only logs it
  (`gexis-plexamp`, `main.py` `_setting`: *"claiming is not implemented here
  yet"*). gexis was claimed through Plexamp's own interactive setup (Finding
  082). A token typed into Settings reaches nothing.
- **It could not have reached Plexamp anyway.** The row exports
  `PLEX_CLAIM_TOKEN`; Plexamp reads **`PLEXAMP_CLAIM_TOKEN`** and
  **`PLEXAMP_PLAYER_NAME`** (Finding 077 §6, from its strings). And
  `plexamp.service` loads no environment file - only `gexis-plexamp.service`
  does.
- **The plugin already knows whether the player is claimed:** Plexamp's own
  token is a file in its settings store (`server.token()`), which the plugin
  reads to fetch metadata.
- **The contract has no way to say it.** A plugin sends `acquire`, `release`,
  `available`, `metadata`, `queue`, `volume`; nothing reaches a settings row.

## Proposal

1. **The claim, by environment.** `plexamp.service` loads
   `/run/gexis/plugins/plexamp.env`; the row's `env` becomes
   `PLEXAMP_CLAIM_TOKEN`; the player's name is exported beside it as
   `PLEXAMP_PLAYER_NAME`, from the device name (ADR-0048 - a fifth service,
   still one name). Saving the token restarts Plexamp, which claims on start.
   **Unmeasured:** that Plexamp headless claims from the two variables without
   its prompt. Finding 077 found the names, not the behaviour.
2. **A plugin may report a row's state** - a new event, contract version
   raised, in [PLUGIN-CONTRACT.md](../PLUGIN-CONTRACT.md):
   `{"t": "row", "key": "claim_token", "state": "done", "text": "Claimed"}`.
   The core holds it in memory and publishes it with the row; it is not a
   setting and is never stored.
3. **The row, as George drew it:**
   - not claimed: the note is *Claim token from plex.tv/claim*, the address a
     link that opens a new tab; the field as today;
   - claimed: *Claimed* with a green tick, and a small *Claim again* link that
     opens the field.
4. **Links in notes.** A note may hold one `https://` address, drawn as a link -
   for every row, not only this one.

## Questions owed (George)

- **A. Claim again**, and the player already claimed: Plexamp keeps its old
  claim until the new one succeeds - or the old one is cleared first, so a
  failed claim leaves it unclaimed. Proposed: kept until the new one succeeds.
- **B. A claim that fails** (an expired token - plex.tv's last four minutes):
  the row says *The claim did not work. Get a new token and try again.*
- **C. Settings rows as links** (4) is new for every row; ADR-0022 notes
  stay plain text otherwise.

## To measure before it is accepted

- **Plexamp claims from the environment, unattended** - on gexis, against a
  second, throw-away Plexamp home so George's player stays claimed. Needs a
  fresh token from George (plex.tv/claim, valid four minutes), and leaves a
  second player in his Plex account to remove afterwards.
- **What a failed claim looks like** to the plugin: an expired token.
