# Finding 019 — Criterion 7 attack test against ADR-0027's arbitration

**Date:** 2026-09-12
**System:** `gexis`, flashed image `v0.2.1-51-g89dca15-dirty` (the first image containing ADR-0027, Finding 016's polling fix and blocker 4's volume fix — all three were hot-patches until this build).
**Question:** criterion 7 — "no renderer can be made to play while another holds the device" — re-tested against the arbitration model ADR-0027 replaced the base slot with.

## The existing test had stopped testing anything

`tools/phase-2c/attack_test.py` drives LMS with `cli.play()`. That was the
acquisition trigger under the base-slot model. Under ADR-0027 **powering
the player on is**, and `play` against an already-powered-on player is not
an acquisition at all.

Run unmodified against this build it reported **0 violations** — but its
own trace showed whole rounds with no PCM holder transitions: the renderers
never contended, so there was nothing for a violation to occur during.
That number would have been a false pass, and the exact shape
`docs/LESSONS.md` tracks.

Replaced for this criterion by `tools/phase-2c/attack_test_adr0027.py`,
which differs in two ways that matter:

1. **LMS is driven by power**, covering both routes back — activating the
   player, and pressing play (where LMS's own auto-power-on takes the
   device).
2. **Every round asserts it actually contended.** A round that produces no
   handover is counted `INCONCLUSIVE`, never as a pass. The run prints
   "NO ROUND CONTENDED - this run proves nothing about criterion 7" when
   nothing happened, which is precisely what it printed on the first
   attempt (see Scope).

The violation check itself is unchanged and mechanism-independent: poll the
real PCM holders (`sudo fuser`, never arbitration's own log lines) at 20ms
and flag any moment two renderers hold the device at once.

## Result

| scenario | rounds | contended | violations |
|---|---|---|---|
| Spotify holds → LMS races in by **activation** | 8 | 8 | 0 |
| Spotify holds → LMS races in by **pressing play** | 8 | 8 | 0 |
| **Deactivate/activate churn** while Spotify plays (6 cycles/round, 350ms apart) | 8 | 8 | 0 |
| **total** | **24** | **24** | **0** |

**Criterion 7 held across 24 genuinely contended rounds.** System state
through the same window:

- **Zero ladder escalations** — no SIGTERM, no SIGKILL, no "STILL holds"
- **Zero warnings or errors** from `gexis-core`
- **Zero** go-librespot `resource busy` failures — the signature blocker 2
  left on every LMS→Spotify handoff before ADR-0027
- `NRestarts=0` on squeezelite and `gexis-core`; no restart storm under the
  churn pattern, which is the load that broke both reverted fixes
  (Finding 013 §1, Finding 014)

**8 squeezelite failed ALSA opens occurred during the run, and that is the
criterion passing rather than failing.** They are the LMS-incoming race:
squeezelite attempts its open ~58ms after power-on while Spotify still
holds the device for another ~100ms. The device refuses the second opener
and squeezelite backs off and retries — which is exactly "no renderer can
be made to play while another holds the device". A violation would have
been the opposite: both processes holding the PCM at once, which never
occurred.

## Scope

- **LMS↔Spotify only.** Bluetooth-involving pairs are deferred by George's
  decision, 2026-09-12 — `bluetoothctl` reconnects the A2DP profile but not
  reliably the audio stream, so contested rounds need a human tapping a
  phone for every one. Criterion 7 is therefore **unproven for any pair
  involving Bluetooth**, and Bluetooth's own release (2.5-2.9s, untouched
  by ADR-0027) remains an open ADR-0010 item.
- 24 rounds in one session on one build. Not a distribution, and not a
  soak: an attack test answers "can this be provoked", not "how often".
- **The first attempt produced nothing and said so.** Spotify's Web API
  returned `404 Device not found` because the reflash regenerated
  go-librespot's identity and `gexis` was absent from Spotify's device
  list until George selected it on his phone once. All 12 rounds were
  correctly reported `INCONCLUSIVE`. Worth carrying forward: **a
  long-running criterion 8 collection depends on `gexis` staying in that
  list**, and go-librespot re-authenticated 15 times in the ~3.5h since
  boot, so it can lapse mid-run. The inconclusive guard is what keeps that
  from silently becoming a result.
- The card index was 5 on this boot (`/dev/snd/pcmC5D0p`), having been 3 on
  the previous one — Finding 005's varying index, again, and harmless only
  because nothing references the device by index.
