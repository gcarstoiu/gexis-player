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
- **Whether a newer Plexamp behaves differently.** 4.13.2 is what was parked.
- **Whether the S32_LE problem is peppyalsa's, the plugin's, or the stream's.**
  The note says the mechanism was not investigated.
