# Finding 075 — What moOde learned about Plexamp

**Date:** 2026-09-25
**Question:** George's other project ran Plexamp and Plex on moOde and kept
notes. Phase 11 is about to make Plexamp this device's fourth renderer, and
Phase 10 is about to make it the plugin contract's proof. What does that
record say that bears on either?
**Sources:** two exports from George's moOde project, both 2026-09-25 — a
memory summary, and then the investigation behind its parking note
(`moode-plexamp.md` plus the 2026-08-28 chat). **The second changed this
finding's conclusion**; §1 is kept with the correction beside it rather than
rewritten, because the wrong reading is the one a summary line invites.
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

### Answered 2026-09-25 by a second export, and it changes the conclusion

George supplied the investigation behind the parking note
(`moode-plexamp-stop-vs-disconnect.md`, from `moode-plexamp.md` and the
2026-08-28 chat). **It is much better news than the summary line suggested**,
and it corrects this finding's own first section.

**1. The API stop releases the ALSA device.** Plexamp headless answers on
**:32500**:

```
curl -sS -m 5 'http://localhost:32500/player/playback/stop?commandID=1' \
  -H 'X-Plex-Client-Identifier: probe' \
  -H 'X-Plex-Target-Client-Identifier: local'
```

`200`, and `/proc/asound/.../hw_params` reads `closed` afterwards — **without
restarting the service**. The stop is clean and distinct: `state="stopped"`,
`time="0"`, queue attributes gone, where `paused` keeps `ratingKey`,
`playQueueID` and `time`. Plexamp's own UI has no Stop button, so this state is
otherwise unreachable.

> **Its own caveat, quoted:** *"The 'before' read printed nothing, so the device
> was probably already closed when the test started. Strictly, the test shows
> 'stopped and closed', not 'open, then stop, then closed'."* A rerun with
> playback confirmed running was suggested; **whether it happened is
> UNVERIFIED.**

**2. There *is* a positive disconnect signal — and it is not in the API.** The
count of TCP connections to `:32500` **drops to 0** when the phone app is
dismissed or explicitly disconnected, and recovers on reopen, with a latency of
seconds.

**So "no observable disconnect signal" was about the HTTP endpoints, not about
the renderer.** This finding's §1 repeated that phrase as though it closed the
question. It does not: the socket count is an observable signal, and it is the
one moOde's own unbuilt design was going to watch.

**3. What a Plexamp adapter would look like here**, mapped onto ADR-0010's
ladder, which it fits without bending:

| our contract | Plexamp |
|---|---|
| `Adapter.release()` — the polite stop | **the API stop above.** Frees the DAC and leaves Plexamp running and instantly reusable |
| `Adapter.signal_stop(force)` — escalation | kill the unit. moOde's `stopPlexamp()`, which needs a restart before next use — exactly why it is the *second* step and not the first |
| `on_release` in `Adapter.run()` | **TCP count to :32500 reaching 0**, seconds after the app goes away |

**4. What is still not known**, and the export is explicit about it: **what the
TCP count does after an API stop.** *"Neither the guide nor the chat excerpt
covers it."*

**Note the export's own summary overstates this.** It opens with *"It does NOT
close the network connection"* — a measured negative — while its *Not recorded
anywhere* section says nobody checked. This finding treats it as **unknown**,
because the document's own evidence section outranks its summary. It matters:
if our own `release()` drops the count to 0, the adapter would see its own
polite stop as a user disconnect. `Supervisor.relinquish` already ignores a
release from a renderer that is not active, which is the same echo problem LMS
and Spotify have and the same machinery absorbs it — but it needs knowing
rather than assuming.

**5. And pause is still not app-dismissed.** moOde's design *still* added a
paused-timeout *"because pause and app-dismissed are indistinguishable"*, on
top of watching the TCP count. Why a socket watcher did not settle it is not
explained in what was exported.

### George's recollection, and what the record says

**George, 2026-09-25: *"sending a Stop command to plexamp stopped the
connection."*** He was right about the substance and the record is narrower
than the wording: the stop **releases the audio device**; whether it closes the
*network* connection is the one thing nobody measured.

The original question and why it mattered is kept below, because the
distinction it draws is what makes the answer above readable.

### A commanded stop is a different question, and it is the one that matters

**George, 2026-09-25: *"I believe that the findings also should show that
sending a Stop command to plexamp stopped the connection."***

**Not in the first export** — searched for `stop`, `disconnect`, `power 0`,
`slpower` and `release`, which found only the Route A sentence and an open item
about the **Squeezelite** button whose note ends *"Results not received."*
**Answered by the second export**, above.

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
- **Whether the API stop frees a device that was actually open.** The one
  test recorded had an empty "before" read, so it shows *stopped and closed*
  rather than *open, then stop, then closed*. The rerun that would close the
  gap is written out in the export and is the first thing to run on `gexis`.
- **What the TCP count does after an API stop.** Nobody checked, on either
  machine. If our own `release()` drops it to 0, the adapter sees its own
  polite stop as a user disconnect.
- **Why a socket watcher did not separate pause from app-dismissed.** moOde's
  design added a paused-timeout anyway and the reason is not in what was
  exported.
- **Anything about Plexamp's behaviour on this device.** All of the above is
  moOde's, on a Pi 5, with Plexamp 4.13.2.
- **Whether a newer Plexamp behaves differently.** 4.13.2 is what was parked.
- **Whether the S32_LE problem is peppyalsa's, the plugin's, or the stream's.**
  The note says the mechanism was not investigated.
