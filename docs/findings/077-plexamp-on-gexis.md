# Finding 077 — Plexamp headless on gexis

**Date:** 2026-09-25
**Question:** Phase 10 step 0, pulled forward from Phase 11 criterion 1. Four
questions, one install: does a commanded stop work, does it free the ALSA
device ([ADR-0008](../decisions/0008-direct-alsa-over-pipewire.md)'s reversal
condition), can a spontaneous release be observed, and what sample format does
it open?
**Scope:** `gexis`, Plexamp headless **4.13.2** — the same build moOde parked —
on Node 20.19.2 from Debian trixie, claimed against George's account and named
`Gexis`. **Playback was driven by this session's own Plex API calls, not by a
phone**, so the questions that need a Plex *controller* attached are not
answered here and say so. One track, one library, three repeats where a number
is given.

## The headline: moOde's guide is wrong about the stop, and its own caveat said so

[Finding 075](075-what-moode-learned-about-plexamp.md) carried this from
`moode-plexamp.md`:

> The stop releases the ALSA device (`hw_params` reads `closed`) without
> restarting the service.

with the caveat that the "before" read printed nothing, so the test showed
*stopped and closed* rather than *open, then stop, then closed*.

**Run with playback confirmed open, the device is still held.**

```
=== BEFORE ===
  format:    format: S32_LE          <- open
  state:     state="playing"
=== API STOP ===  HTTP 200
  +1s  state="stopped"  hw_params: S32_LE, 44100, 2ch   <- still open
  +3s  state="stopped"  hw_params: S32_LE, 44100, 2ch   <- still open
  +6s  state="stopped"  hw_params: S32_LE, 44100, 2ch   <- still open
```

**It does release — after fourteen seconds, every time.**

| run | device released |
|---|---|
| 1 | **14 s** after the stop |
| 2 | **14 s** |
| 3 | **14 s** |

No variance across three runs: a fixed hold, not a fade or a race. The service
stays `active` throughout and is instantly reusable, which is the half of the
guide that does hold.

## The four questions

**1. Does a commanded stop work?** **Yes.** `GET
/player/playback/stop?commandID=N` on `:32500` answers 200, the timeline goes
to `state="stopped"` at once, and audio stops. **But the device is not free
for 14 s.** So `Adapter.release()` exists and works; ADR-0010's polite grace
for this renderer has to be **longer than 14 s**, or the ladder escalates to
`signal_stop` — which kills the service and costs a restart before next use.
That is exactly why the ladder is per-renderer: LMS already overrides it for
squeezelite's own idle tick.

**2. Can a spontaneous release be observed?** **Not answered.** The TCP count
on `:32500` was **0 throughout — including while playing** — because no Plex
controller was attached; this session drove playback through the API itself.
**The count reflects a controller being connected, not audio being played**,
which is a different thing from what Finding 075 assumed and needs a phone to
test. It also raises a question that record did not: a phone that locks or
backgrounds drops the connection while the audio keeps going, which would read
as a release that did not happen.

**3. Does it free the ALSA device (ADR-0008's reversal condition)?** **Yes, in
14 s, with the service still running.** ADR-0008's reversal is about a renderer
that will *not* cooperate. This one cooperates slowly. **The condition is not
triggered.**

**4. What sample format?** **`S32_LE`**, 44100, 2 channels, MMAP_INTERLEAVED —
and this is the one that costs something.

## The audio path is the real problem, and it is two problems

**a. Plexamp opens `hw:5,0` directly, so `pcm.output` is not in the path.**
Every other renderer here goes through `pcm.output`, which is a `type meter`
PCM with peppyalsa as its scope — that is how the visualiser gets levels. A
renderer on the raw card feeds it nothing.

**b. And the format is the one moOde measured as fatal to the meter.** Its
record: *"peppyalsa produces an all-zero meter FIFO for S32_LE streams but
works for S24_LE… this is why `/home/moode/.asoundrc` pins S24_LE."* Plexamp
opens exactly S32_LE here. So even routed through `pcm.output`, the meters
would read zero unless the format is pinned.

**`output` cannot simply be selected.** It *is* an ALSA PCM and `aplay -L`
lists it, but **Plexamp's own enumeration does not**:

```
default · hw:4,0 (headphones) · bluealsa · sysdefault
hw:5,0 (HiFiBerry DAC+ HD) · hw:0,0 (HDMI) · hw:1,0 (HDMI)
```

Setting `audioDeviceUuid` to `output` is **silently ignored** — `findDevice`
misses, it falls back to "Follows System Output", and playback went to
**card 0, HDMI**. Confirmed by `hw_params` on the wrong card while the DAC read
`closed`.

**And it addresses the DAC by card index.** `hw:5,0`. This project's standing
rule is never to do that — Finding 005 measured the same DAC at index 3, 2 and
1 on three machines, and it is 5 on this card today. A Plexamp plugin inherits
that exposure and cannot fix it from our side without making `output`
enumerable to Plexamp, which is untried.

## Smaller things worth having

- **Its timeline declares a control surface**, which is what ADR-0037 and
  `Capabilities.controls` want:
  `controllable="volume,repeat,skipPrevious,seekTo,stepBack,stepForward,stop,playPause"`.
- **Playback needs a play queue first.** `playMedia` with a bare `key` logs
  `PlayQueue: Processed play media with success false` and does nothing; it
  works once a queue is created on the PMS and passed as `containerKey`.
- **Setup needs two answers in one session** — a claim token *and* a player
  name. Answering only the first consumes the token and persists nothing.
- **`plex.direct` hostnames carry a dashed IP** (`https://192-168-178-191.<hash>.plex.direct:32400`),
  the same shape moOde's Route B had to unwrap.
- Plexamp's settings live in `~/.local/share/Plexamp/Settings/` as one file per
  key, URL-encoded names, each value prefixed with a **type marker byte**
  (`S` for string).

## What this does not tell us

- **Anything with a phone attached**, which is questions 2's whole subject and
  the normal way a person uses this.
- **Whether 14 s is tunable.** No setting was looked for.
- **Whether `output` can be made visible to Plexamp**, by an ALSA hint or
  otherwise. `aplay -L` already lists it, so its enumeration filters on
  something else, and what that is was not investigated.
- **Whether pinning S24_LE fixes the meter**, here or at all. moOde measured
  the symptom and explicitly did not investigate the mechanism.
- **Anything about gapless, artwork, metadata or volume**, none of which was
  touched.
