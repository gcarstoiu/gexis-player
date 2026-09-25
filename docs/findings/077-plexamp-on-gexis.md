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

### It is a fixed idle timer, not something the stop does

George, 2026-09-25: *"I remember for sure how the stop basically disconnected
the phone that was connected to moOde and then the investigation showed that
the card was released."* He is right that the card is released, and the
measurement below says why both records can be true at once.

| played for | then | device released after |
|---|---|---|
| 3 s | **stop** | **14 s** |
| 30 s | **stop** | **14 s** |
| 10 s | **pause** | **15 s** |

**Independent of how long it played, and the same for pause as for stop.**
That is an idle timeout, not a teardown: nothing about the *command* frees the
device, and nothing about the session's length changes it. moOde's guide saw
`closed` because it looked afterwards — which is exactly what its own caveat
warned the test could not distinguish.

**And it means pause and stop are identical at the audio layer**, which is the
same shape as that record's *"pause and app-dismissed are byte-identical"*,
one level down.

### Re-run with the card explicitly selected — same answer

George, 2026-09-25: *"Can you check audio card is selected now and perform
again the disconnect test."*

**It was not selected correctly.** `audioDeviceUuid` read **`sysdefault`**,
which on this device resolves to **card 0, `vc4hdmi0` — HDMI**, not the
HiFiBerry. Set explicitly to `hw:5,0` and re-run:

```
open, playing: format: S32_LE          <- card5, the DAC
STOP -> HTTP 200, state="stopped"
  +1s still open   +3s still open   +6s still open
released 14s after the stop
plexamp still: active
```

**Unchanged.** Which is what the idle-timer reading predicts: the hold is in
the audio layer, so which card is open does not alter it.

**No controller was connected for this run either** — the count was 0
throughout, and the one connection seen beforehand was a `FIN-WAIT-2` already
closing. So the phone half is still untested.

### Is the hold configurable? Not that this found

**Checked:** all **138** settings in Plexamp's own store, filtered for
`audio`, `device`, `idle`, `hold`, `release`, `buffer`, `exclusive`, `sink`,
`output`; the audio settings the web UI exposes; and the bundle for
`freeDevice`, `deviceTimeout`, `BASS_Free` and 14–15 s constants.

The only `idleTimeout` in the JavaScript is **15 s on an EventSource**
(`connect`, `onMessage`, `eventSource.close`) — the same number against a
different thing, and **not** claimed here as the cause.

**Not checked, and where the answer probably is:** `treble/linux-arm64/` holds
the native BASS libraries (`libbass*.so`). The device is opened and freed
there, not in the JavaScript, so a setting for it would be BASS's rather than
Plexamp's. `PLEXAMP_JACK` is the only Plexamp environment variable in the
bundle.

### Does "no source selected" in the web UI invalidate any of this? No

George opened `:32500` and saw no source selected. **That page is a Plexamp
*browser client*** — `js/index-browser.js`, 9.6 MB, served by the headless
player at `/` — and its source selection is the browser's own, not the
player's.

The player's own state is set and was used:

- `/resources` reports **`<Player title="Gexis" product="Plexamp" deviceClass="speaker">`** — the headless player, identifying itself.
- Its settings carry `server:identifier` (Plexy), `server:library`
  (`/library/sections/4`, Music) and populated `discovery:hubs`.
- **And playback provably resolved against them**: a queue created on that
  server, `state="playing"`, `key="/library/metadata/91795"`, the DAC open.

A player with no source could not have done that. The numbers stand.

## The four questions

**1. Does a commanded stop work?** **Yes.** `GET
/player/playback/stop?commandID=N` on `:32500` answers 200, the timeline goes
to `state="stopped"` at once, and audio stops. **But the device is not free
for 14 s**, and that is a fixed idle timer rather than anything the stop does
— see above. So `Adapter.release()` exists and works; ADR-0010's polite grace
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

## The audio path had two problems. George's question removed both

**George, 2026-09-25: *"Why aren't we setting the default for the device to
our hat and let plexamp use it?"*** — which is the answer, and it is
[ADR-0085](../decisions/0085-the-alsa-default-is-our-output.md).

With `pcm.!default "output"` in place and Plexamp set to **Default**:

```
open: /proc/asound/card5/pcm0p/sub0/hw_params     <- the DAC, via pcm.output
   format: S32_LE     rate: 44100 (44100/1)
meter fifo:  25 23 25 24 26 25 26 25 16 17 25 26 26 25 27 25 …
```

**So the card is right, by name, and peppyalsa is in the path.** No index
anywhere, and it follows ADR-0055's output picker for free.

### And the S32_LE meter problem does not reproduce here

The risk carried from moOde was that peppyalsa gives an **all-zero** meter
FIFO for S32_LE. **On `gexis` it does not.** Measured with a control:

| | meter FIFO |
|---|---|
| Plexamp playing, S32_LE, through `pcm.output` | `25 23 25 24 26 25 26 25 …` |
| nothing playing, card closed | **no writer, nothing to read** |
| playing again | `27 24 26 21 23 21 19 17 …` |

The spectrum FIFO carries bands the same way (`38 35 40 46 43 …`). Why moOde
saw zeros is not explained by this — different build, and this image patches
peppyalsa to write each frame in one call (Finding 052) — and that is not
investigated here. **What is established is that the symptom does not appear
on this device.**

## What the problems were, before that



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
- **Whether 14 s is tunable.** Looked for and not found; what was searched and
  what was not is listed above. The native BASS layer is the unexamined part.
- **Whether a connected phone changes any of it.** This is George's own
  recollection and the one thing none of this touches: every measurement here
  was taken with no Plex controller attached.
- **Whether `output` can be made visible to Plexamp**, by an ALSA hint or
  otherwise. `aplay -L` already lists it, so its enumeration filters on
  something else, and what that is was not investigated.
- **Whether pinning S24_LE fixes the meter**, here or at all. moOde measured
  the symptom and explicitly did not investigate the mechanism.
- **Anything about gapless, artwork, metadata or volume**, none of which was
  touched.
