# ADR-0119 — Plexamp is claimed from Settings, and says when it is

**Status:** **Accepted** — George, 2026-10-05: asked for the screen on the
Settings copy review, said yes to building it, answered its three questions
the same day, and confirmed from his Plex account that the claim names the
player as `PLEXAMP_PLAYER_NAME` says (*"I see the gexis-claimtest there"*).
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

## Decided (George, 2026-10-05)

- **A. Claim again keeps the old claim until the new one succeeds.** A failed
  attempt leaves the player claimed as it was.
- **B. A failed claim** says *The claim did not work. Get a new token and try
  again.*
- **C. Links in notes**, for every row: a note may hold one `https://`
  address, drawn as a link that opens a new tab.

## Measured so far (2026-10-05, gexis, Plexamp 4.13.2)

A throw-away Plexamp - its own `HOME` under `/tmp`, an invented token, no
input - beside George's claimed one, which was not touched:

- **It reads the variables and does not prompt.** It printed `Starting
  Plexamp 4.13.2`, then `Error exchanging claim token.`, and **exited 255**,
  writing nothing to its settings store. That is the failure the plugin
  sees for B: a non-zero exit with that line.
- **From its code** (`js/index.js`): the variables are read **only when no
  `user:token` is stored**. A claimed Plexamp ignores them, so a spent token
  left in the environment is harmless - and **Claim again cannot work by the
  variable alone**. For A, the plugin sets the old claim aside (a copy of
  Plexamp's settings store), restarts Plexamp with the new token, and puts
  the copy back if the claim fails: the player is unclaimed for the seconds
  the attempt takes, and claimed as before if it fails.

- **A successful claim from the environment, unattended** (George's token,
  the same day, a throw-away home): `Starting Plexamp 4.13.2`, then *"Plexamp
  is now signed in and ready!"*, and it **stayed running** - the claim and the
  start are one process, so the plugin learns of success from the token
  file appearing, and of failure from the exit. 25 files in its store,
  `user:token` among them (the file the plugin already reads).
- **Two names are stored:** `player:name` = `gexis`, Plexamp's own device
  name (the hostname), and `settings:playerName` = `gexis-claimtest`, from
  `PLEXAMP_PLAYER_NAME`. Which one Plex shows is read off George's account.
- Harmless on the way: `Error loading cloud players from plex.tv HTTP status
  403`, and a failed probe of a phone's player on the LAN.

- **The name Plex shows is `PLEXAMP_PLAYER_NAME`'s**: George's Authorized
  Devices listed the test player as `gexis-claimtest` (left for him to remove).

## How it is built

1. **`plexamp.service`** reads `/etc/gexis/device-name.env` (ADR-0048's
   `GEXIS_DEVICE_NAME`, squeezelite's already) and
   `/run/gexis/plugins/plexamp.env`, and starts Plexamp through
   **`plexamp-run`**, which hands it `PLEXAMP_PLAYER_NAME` from the device
   name and `PLEXAMP_CLAIM_TOKEN` **only when there is a claim to make**.
2. **`plexamp-run` keeps the claim's bookkeeping**, in
   `~/.local/share/gexis-plexamp/claim.json` (the token's hash, never the
   token, and `trying` / `claimed` / `failed`), at every start:
   - a **new** token on a claimed player sets Plexamp's store aside
     (`Settings.previous`) and starts it unclaimed with the token: A;
   - the same token again, `trying`, and Plexamp's `user:token` there: the
     claim worked - `claimed`, the old store deleted;
   - the same token again, `trying`, and no `user:token`: Plexamp exited on
     the claim - the old store is put back, `failed`, and the token is not
     handed over again, so a dead token cannot loop the unit.
   **Claim again makes a new Plex player**, a fresh identity, as the first
   claim did; the old entry stays in the account until removed there.
3. **The core restarts `plexamp.service` when the token changes** - it does
   already for any `env` row (ADR-0088). The manifest's row exports
   `PLEXAMP_CLAIM_TOKEN`, no longer the `PLEX_CLAIM_TOKEN` nothing read.
4. **The plugin reports the row**, by the new event, from Plexamp's
   `user:token` and `claim.json`: `done` *Claimed*; `failed` with B's
   sentence (and still *Claimed* when the old claim was put back); nothing
   while unclaimed. The core keeps the last report per plugin in memory and
   publishes it on the row as `status`; a plugin that leaves takes it with
   it.
5. **The panel and the phone** draw a row with `status.state` `done` as its
   text with a green tick and *Claim again*, which opens the field; a failure
   as its sentence under the row. A note's `https://` address is a link that
   opens a new tab, shown without the scheme.

## Claim again, on George's own player (2026-10-05)

With a fresh token of George's, saved through `PUT /settings/plexamp.claim_token`
as the phone saves it, nothing playing: the core restarted Plexamp,
`plexamp-run` set the claimed store aside and handed the token over, and
Plexamp answered *"Plexamp is now signed in and ready!"*. The row read
*Claimed* throughout. At the next start `claim.json` went `trying` ->
`claimed` and `Settings.previous` was deleted; Plexamp answered on 32500,
named `gexis`.

**What a new claim costs**, by construction: Plexamp's own settings start
again - its volume, and anything set in its own settings screens (none is
set by this project). Its audio device is unset, which is "Follows System
Output": [ADR-0085](0085-the-alsa-default-is-our-output.md)'s default, the
chosen output, through the meter. **Playback after the new claim: George, the same day -** *"it plays and
the meters work"* - the DAC, through the meter.


**Amended 2026-10-08 - three faults a failing claim showed on guestpi.** Plex
issued a sign-in for each of three fresh tokens and refused it moments
later; Plexamp wrote half an account and exited 255, or signed in and then
dropped the sign-in. Plexamp claimed normally again later the same day.
- **Any store is set aside before a claim**, claimed or not, and comes back
  when the claim fails. Before, only a claimed store was, and a failed claim
  on an unclaimed player left half an account behind.
- **A failed claim is told by Plexamp's exit** (`ExecStopPost=plexamp-run
  --stopped`, reading systemd's `EXIT_CODE`/`EXIT_STATUS`), not by its
  files. The next start had taken a sign-in file, written before the
  exit, for a claim.
- **The row says a claim that was lost or never came** (gexis-plexamp
  0.4.2): *Plex signed this player out* when a recorded claim has no
  sign-in, and *The claim did not work* when one has been tried for more
  than 90 s without one. It went blank before.
