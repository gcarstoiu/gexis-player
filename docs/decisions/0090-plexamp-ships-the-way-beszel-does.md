# ADR-0090 — Plexamp ships the way Beszel does

**Status:** **Accepted and built**, 2026-09-25 — the stage is
`image/stage-gexis/08-plexamp` and `verify-image.sh` has a section for it;
**nothing built from it has been booted.** George, 2026-09-25: *"Present in the image just like
beszel. I thought in general we did beszel to learn how to do it. Let's rely on
the learnings and do it similarly."* The two things this record asked him for —
the repository's name and the settings row — were confirmed the same day: *"I am
fine with your proposal."* So the plugin lives at **`gcarstoiu/gexis-plexamp`**,
public, publishing tagged releases the stage pins by checksum, and
`plexamp.claim_token` is in ADR-0022's Plugins group.
**Date:** 2026-09-25
**Raised by:** Phase 11, and Phase 10's criterion 2 which it carries — *a fourth
renderer built against the contract, in a separate repository, with no changes
to the core.*
**Relates to:** [0087](0087-the-beszel-agent-is-the-first-service-plugin.md)
(the pattern this copies), [0089](0089-arbitration-carries-a-plugin-renderer.md)
(what makes a plugin renderer possible at all),
[0086](0086-a-plugin-declares-itself-in-a-manifest.md) (the manifest),
[0088](0088-a-plugins-settings-reach-its-unit-as-environment.md) (how its
settings reach it), [0085](0085-the-alsa-default-is-our-output.md) (why its
audio lands in our meter path), [0048](0048-how-the-device-name-reaches-four-services.md)
(the device name, which becomes a fifth service), [0042](0042-a-local-cache-for-vendored-downloads.md)
(pinned, checksummed downloads)

## Context

Beszel was built to find out whether the contract could carry a plugin, and it
found two holes before it worked. What it also produced is a **shape**: a stage
that pins a download by checksum, a unit, a manifest, a synthesised switch, and
settings that reach the process as environment. George's instruction is to reuse
it rather than invent a second way.

**Plexamp differs from Beszel in one structural way**, and it is the only thing
here that needed thinking about: Beszel is one process that is entirely
third-party. Plexamp is **two** — the third-party player, and *our* plugin that
speaks ADR-0084 on one side and Plexamp's `:32500` API on the other. The second
is the one criterion 2 requires to live in its own repository.

## Decision

### 1. One stage, `08-plexamp`, installing three things

Exactly `07-beszel`'s shape:

- **Plexamp headless**, pinned by version and sha256, verified independently
  rather than copied from an API once.
- **Our plugin**, from its own repository, pinned the same way.
- **The manifest, the units, and a state directory** — with the unit
  **disabled**, so an unclaimed device runs nothing and the switch in the
  Plugins category reads off by asking `systemctl is-enabled`.

### 2. The manifest's `unit` is Plexamp's, and one switch still controls both

`unit` means *the process that opens the ALSA device* — the release ladder
attributes a still-busy device to it (`alsa.device_held_by`, and Finding 077
already measured `alsa.device_held_by("plexamp.service") -> True`). So the
manifest names `plexamp.service`, not ours.

**Our plugin is a second unit bound to it**: `PartOf=plexamp.service` so
stopping the player stops the plugin, and pulled in by the player's own
`Wants=`, so the one switch starts and stops the pair.

**This deliberately does not change the contract.** A `plugin_unit` field
beside `unit` was the obvious alternative and is rejected: Phase 10's plugin
amended the contract twice, both times because something could not be expressed
at all, and this can be. systemd already has the vocabulary for "these two go
together"; the contract does not need its own.

### 3. What it costs, because George decided the image before this was measured

| | installed size |
|---|---|
| `nodejs` + `libnode115` | **~51 MB** — and **not in the image today**; it was hand-installed on 2026-09-25 at 14:42, after the flash |
| Plexamp headless | **41 MB** on disk, from a 14.6 MB tarball |
| our plugin | **built**: the release tarball is 12 KB, and `/opt/gexis-plexamp` is source only |
| *(for comparison: the Beszel agent)* | 9.5 MB |

**About 92 MB**, an order of magnitude more than the precedent. Stated rather
than buried: it is still the right call for the same reason Beszel's was — an
installer is a phase of its own — but the number is not the one that decision
was taken against.

### 4. One settings row, not three

**Claiming needs a token and a player name in one session** (Finding 077: *"answering
only the first consumes the token and persists nothing"*).

- **The token is a row** — `plexamp.claim_token`, `secret`, hidden behind the
  switch like Beszel's credentials. Consumed once; the note says so.
- **The player name is not.** ADR-0048 already writes one device name to four
  services, and this makes a fifth. A second place to type the same name is a
  second place for it to disagree.
- **Nothing else.** Plexamp finds its servers from the account the token claims.

### 5. Our plugin is the one that acts on it

Unlike Beszel, this plugin is ours and speaks the contract, so it receives
`setting` over the socket and can do the claim itself rather than needing the
value at exec. It still gets the environment file for free; whether it uses it
is the plugin's business and not this record's.

## Consequences

- **Criterion 2 becomes closable**: a renderer in its own repository, against
  the contract, with no core changes. The core changes in Phase 11 were
  ADR-0089's, which are the contract's own machinery rather than anything that
  names Plexamp.
- **`verify-image.sh` gains a section**, as `07-beszel` did, so the stage is
  checked on every build rather than once.
- **Node arrives in the image**, and with it a runtime nothing else here uses.
- **Two more things become measurable that Finding 077 could not reach**:
  everything with a Plex controller attached, and whether a connected phone
  changes the 14 s hold. Both were listed there as untouched.

## Settled with it

- **The repository is `gcarstoiu/gexis-plexamp`**, public, publishing tagged
  releases that the stage pins by checksum — the same relationship the image
  already has with go-librespot, peppyalsa and beszel-agent. **Public matters
  here beyond preference**: criterion 2 is about a renderer somebody else could
  have written, and a private repository would make that claim untestable by
  anyone but us.
- **`plexamp.claim_token` is in ADR-0022's inventory**, Plugins group, `[N]`.
