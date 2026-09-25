# Finding 085 — Plexamp's takeover gaps, and every control pressed

**Date:** 2026-09-25
**Question:** Phase 11's criteria **2** (*acquisition and release fit the
arbitration model; takeover gaps measured against the other renderers*) and
**5** (*transport commands measured and declared*).
**Scope:** `gexis`, `gcarstoiu/gexis-plexamp` from `/opt/gexis-plexamp`, LMS on
George's own server. **Playback was started by API calls, never by a phone**,
and the Plex play queue held **one track** — which is why one result below is
weaker than it looks. Numbers are the core's own ladder timings from six
takeovers across forty minutes.

## The gaps

| takeover | how the outgoing renderer let go | measured |
|---|---|---|
| **LMS → Plexamp** | LMS's polite stop | **0.2 s**, five times, no variance |
| **Plexamp → LMS** | Plexamp's own idle timer after a commanded stop | **12.6, 14.1, 14.2, 14.2, 12.6 s** |

**The asymmetry is the whole story of this renderer.** Taking the device from
LMS costs a fifth of a second. Giving it back costs **twelve to fourteen**,
because a commanded stop confirms at once and Plexamp's native layer holds the
ALSA device until its own timer expires — compiled in, not a setting, and seven
settings changed by hand did not move it
([Finding 077](077-plexamp-on-gexis.md)).

**Every one of those six was inside the polite grace** the plugin declares for
itself (16 s), so the ladder never escalated: no SIGTERM, no SIGKILL, in any
run. That is ADR-0010's model working exactly as designed for a renderer the
core knows nothing about — **the renderer declared its own timing and the core
believed it.**

**The spread is 12.6–14.2 s, not a constant 14.** Finding 077 called it "a
fixed hold, not a fade or a race" from three runs that all read 14 s at
one-second sampling. At the ladder's own resolution it varies by 1.6 s. Nothing
here explains that, and it does not matter while the grace is 16 — but the
earlier record's word *deterministic* is stronger than these numbers support.

## Spotify and Bluetooth cannot be measured this way, and that is correct

```
  --- spotify takes it from plexamp
    activate -> 409
  --- bluetooth takes it from plexamp
    activate -> 409
```

**Not a failure of the test.** Neither declares `activate`, because neither can
be made to take the device on request: Spotify needs a phone to pick the device
and Bluetooth needs one to connect. The 409 is the core refusing to pretend
otherwise.

So the gaps against those two are **unmeasured, and need a phone**. What is
already known is that nothing about them is Plexamp-specific: the outgoing side
is Plexamp's 12–14 s whoever is taking over, and the incoming side is their own
acquisition, measured in Phase 2.

## Every declared control, pressed through the core

The first attempt returned **502 for all four** of play, pause, next and
previous:

```
  command: plexamp declares next but implements none
```

**A real defect, and exactly what this criterion is for.** `__main__.transport`
dispatches by `getattr(adapter, command)` — the three built-ins each define
`play`, `pause`, `next` and the rest, and `PluginAdapter` defined none. A
renderer that declared controls the panel offers, and answered 502 when they
were pressed. It was found by pressing them.

After giving the adapter a method per command:

```
  pause     HTTP 200   state playing -> paused   track 91795 -> 91795
  play      HTTP 200   state paused  -> playing  track 91795 -> 91795
  next      HTTP 200   state playing -> playing  track 91795 -> 91795
  previous  HTTP 200   state playing -> playing  track 91795 -> 91795
  shuffle   {"on":true}     HTTP 200   shuffle=1
  shuffle   {"on":false}    HTTP 200   shuffle=0
  repeat    {"mode":"all"}  HTTP 200   repeat=2
  repeat    {"mode":"one"}  HTTP 200   repeat=1
  repeat    {"mode":"off"}  HTTP 200   repeat=0
```

**`repeat` is the one worth looking at twice.** The contract says
off / all / one; Plex counts 0 / 1 / 2 and **`1` is one track**, which is the
opposite order to how most people would guess. Mapping it backwards would set
repeat-one when the panel asked for repeat-all — and the panel would then draw
what Plexamp reported, so it would *look* correct and be wrong. `all → 2` and
`one → 1` above are the check that it is not.

**`next` and `previous` are the weak result.** Both answered 200 and the track
did not change, because the queue this test built holds **one track**. So what
is established is that the command reaches Plexamp and is accepted, **not that
it moves between tracks.** A queue of several would settle it and was not built.

## What this does not show

- **Nothing with a phone attached**, which is the normal way to use either this
  renderer or the two that could not be measured.
- **Nothing about cross-rate.** Phase 11's criterion 2 also asks for takeover
  gaps across sample rates, and that half has been blocked since Phase 9 for a
  reason that has not changed: a 60,974-track scan of George's library found
  **zero** non-44.1 kHz files, so testing it means sourcing content first.
- **Nothing about what the panel showed** during these takeovers beyond the
  handoff screen already photographed.
