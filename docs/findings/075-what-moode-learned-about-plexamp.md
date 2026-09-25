# Finding 075 — What moOde learned about Plexamp

**Date:** 2026-09-25
**Question:** George's other project ran Plexamp and Plex on moOde and kept
notes. Phase 11 is about to make Plexamp this device's fourth renderer, and
Phase 10 is about to make it the plugin contract's proof. What does that
record say that bears on either?
**Scope:** **Evidence from another system, not a measurement on `gexis`.**
moOde 10.3.2, Raspberry Pi 5, Debian Trixie, HiFiBerry DAC on card 2, Plexamp
headless **4.13.2**, LMS 9000, Squeeze Plex Hub 3000. Supplied 2026-09-25 as a
memory export whose own header says the entries are **summaries** and that the
authoritative record is a separate guide — and which lists three places where
it already disagrees with that guide. Nothing below was re-measured here.
**Two items were checked against this repository**, and that is said where it
happened.

## 1. Plexamp headless has no observable disconnect signal

The load-bearing item, quoted:

> **Route A — Plexamp headless: BUILT, PARKED (not decommissioned).** Parked
> because Plexamp headless has no observable disconnect signal: **pause and
> app-dismissed are byte-identical at all observable endpoints.**

**This is not about the audio device.** ADR-0008's reversal condition, which
Phase 11 criterion 1 exists to test, asks whether Plexamp *releases* the ALSA
device. This is the other half of ADR-0010: whether an adapter can tell that
the renderer **gave the device up**. `Adapter.run`'s contract requires an
`on_release` edge, and every built-in has one — LMS on the player being
deactivated, Spotify on go-librespot's `inactive`, Bluetooth on `MediaPlayer1`
disappearing. If pause and gone-away are indistinguishable, a Plexamp adapter
has nothing to raise that edge with.

### A commanded stop is a different question, and it is the one that matters

**George, 2026-09-25: *"I believe that the findings also should show that
sending a Stop command to plexamp stopped the connection."***

**Not found in the supplied export.** Searched for `stop`, `disconnect`,
`power 0`, `slpower` and `release`: the only disconnect items are the Route A
sentence above and an open one about the **Squeezelite** disconnect button
(LMS `power 0` → `slpower.sh` → `slactive=0`), whose own note ends *"Results
not received."* Nothing about a Stop to Plexamp. The `moode-customisations`
clone is not on this machine and Plexamp is not installed on `gexis`, so it
could not be checked any further here.

**It is not contradicted either, and the two statements are compatible.** The
export says pause and app-dismissed cannot be *told apart*; a Stop that drops
the connection is a *command that works*. Both can be true at once, and the
distinction is the whole of whether Plexamp can be a renderer here:

| what arbitration needs | where it lives | Plexamp |
|---|---|---|
| **Release it on a takeover** — the polite stop through the renderer's own control channel | `Adapter.release()`, ADR-0010's first ladder step | **This is what George's Stop would be.** If it drops the connection, the critical path works |
| **Notice it released by itself** — the user paused and walked away | `on_release` in `Adapter.run()`, ADR-0027 | This is what the export says is impossible |

**The first is load-bearing and the second is not.** A renderer that can be
released on demand fits ADR-0010; without the second it only fails to report
*"nobody holds the device"*, which leaves it showing as active until something
takes over. That is a known shape — it is exactly the defect ADR-0077 created
and [LESSONS](../LESSONS.md) 39 records, where a renderer switched off stayed
active for ever because nothing was left to raise the edge.

So **the parking note alone does not disqualify Plexamp**, and this finding
should not be read as saying it does. What it does is put one question ahead
of the others in Phase 10's pulled-forward hardware check: **does a Stop
command drop the connection?** George believes it does. It is not written down
anywhere this device can reach, and it is cheap to answer once Plexamp headless
is on `gexis` — which that check installs anyway.

**And this device has seen the same shape independently.** The handoff's own
issues list, from the Phase 6 hardware rounds on `gexis`:

> Over Bluetooth, the Plexamp app reports pauses late or not at all — about
> 6 s from its own button, 4.5 s or never for a panel command. The Spotify app
> on the same phone reports in 0.2 s.

Two observations, two transports, two machines, same complaint: **Plexamp is
poor at saying what it is doing.** Neither was a controlled test of the other,
and this finding does not merge them into one conclusion.

## 2. peppyalsa gives an all-zero meter FIFO for S32_LE

> `peppyalsa` produces an all-zero meter FIFO for S32_LE streams but works for
> S24_LE. Confirmed by comparison; mechanism not investigated. *(Relevant to
> Plexamp: this is why `/home/moode/.asoundrc` pins S24_LE.)*

**Checked here: our `output.conf` pins no format at all.**

```
pcm.output {
    type meter
    slave.pcm "hw:sndrpihifiberry"
    scopes.0 peppyalsa
}
```

The format is whatever the renderer negotiates. Today's three renderers feed
the meters correctly — the whole of Phase 9's visualiser work depended on it —
so whatever they open, peppyalsa handles. **A renderer that opens S32_LE would
have flat meters and nothing on screen to say why**, and moOde had to pin the
format *because of Plexamp specifically*.

Not fixed here: pinning a format on the shared output affects every renderer
and is an ADR, not an edit. Recorded so Phase 11 does not rediscover it at the
point where the meters look broken.

## 3. Plex already reaches LMS without a fourth renderer

> **Route B — Plex via Squeeze Plex Hub: ACTIVE, fully working.** Plex audio
> arrives via LMS and plays through Squeezelite.

On that machine Plex plays **through the renderer this device already has**.
If the goal is Plex on `gexis`, Squeeze Plex Hub is a route that needs no
plugin contract, no fourth renderer and no ADR-0008 reversal — it is an LMS
plugin, and LMS is already our renderer.

That is a **product question for George**, not a conclusion: Route B gives Plex
*playback*, and a Plexamp renderer would give Plexamp *the app* as a source, as
Spotify Connect does. They are not the same thing.

## 4. The uppercase K — already right here

> LMS tag string must contain UPPERCASE `K` to get `artwork_url` on remote
> (hub-streamed) tracks. Lowercase `k` does nothing.

**Checked: ours is `METADATA_TAGS = "aldcTKsey"`** — the `K` is there. No
change. Recorded because the trap is invisible until a *remote* track plays,
which on this device means radio, and because the memory file says this
corrects an earlier guide that had it the other way round.

## What this does not tell us

- **Anything measured on `gexis`.** Different machine, different OS release,
  different DAC, Plexamp 4.13.2. Items 2 and 4 were checked against this
  repository's files; 1 and 3 were not tested here at all.
- **Whether Plexamp releases the ALSA device.** That is Phase 11 criterion 1
  and is still unanswered. §1 is about a *different* signal, and a renderer
  could fail either independently.
- **Whether a Stop command drops the connection.** George says it does; the
  supplied export does not mention it and nothing here could test it. **Four
  separate questions now hang on the same install**: does it free the device,
  does a commanded stop work, can a spontaneous release be observed, and what
  sample format does it open.
- **Whether a newer Plexamp behaves differently.** 4.13.2 is what was parked.
- **Whether the S32_LE problem is peppyalsa's, the plugin's, or the stream's.**
  The note says the mechanism was not investigated.
