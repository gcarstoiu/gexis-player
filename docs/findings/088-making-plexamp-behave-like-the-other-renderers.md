# Finding 088 — Making Plexamp behave like the other renderers

**Date:** 2026-09-26
**Question:** George: *"There are two issues that are making the plexamp plugin
less attractive now… the 14 seconds takeover time as well as the fact that I
cannot just disconnect from my phone with the panel following the disconnect.
Even when taking over via lms for example in the phone i still see the panel as
connected… When plexamp takes over the panel is still showing that it's waiting
for renderers until I start playing something."* Then: *"look at all options,
hacks, outside the box ideas… Really thorough sweep on what is possible."*
**Scope:** `gexis`, Plexamp headless **4.13.2**, Squeeze Plex Hub **1.43.0** at
`192.168.178.53:3000`, LMS **9.1.1**, George's own PMS and library. The DAC's
card resolved by name every time. Measurements are single runs unless a count is
given; each is stated with what it was. **Nothing was booted from the image.**
Read-only against PMS and plex.tv apart from starting and stopping playback;
`audioDeviceUuid` was changed and restored, and one orphaned timeline subscriber
this session created was removed (LESSONS 42).

## 1. The fourteen seconds is not Plexamp being slow to stop

The stop is immediate. Plexamp's own log, on a commanded
`/player/playback/stop`:

```
BASS: Stop.
BASS: Removed stream 102570 in 0 ms.
BASS: Stopped in 0 ms.
...
+3.0s  BASS: Pausing audio output (after delay: 1)
+3.0s  BASS: Suspending player.
```

What costs the time is what happens to the ALSA device afterwards. Sampling
`pcm0p/sub0/status` every 500 ms across a stop:

| after the stop | state |
|---|---|
| 0–2 s | `RUNNING` — the fade-out |
| 3–13 s | **`SETUP`** — the device is still open, suspended |
| 14 s | `closed` |

**So Plexamp suspends output at +3 s and holds the open PCM for a further
~11 s.** This confirms [Finding 077](077-plexamp-on-gexis.md)'s 12.6–14.2 s from
a different instrument and adds the mechanism. `SETUP` is consistent with
`sampleRateMatching: 1` — *"sample rates are adjusted when playback is idle"* —
which requires keeping the device.

**The exact parallel is already in this repository.**
`image/stage-gexis/02-renderers/files/squeezelite.service` carries `-C 1`, and
its own comment records why: *"a commanded pause releases the ALSA device in
~700ms at -C 1 versus ~8500ms at -C 10."* Squeezelite holds an idle device too;
we configure it not to. **Plexamp is squeezelite with `-C 13` and no way to set
`-C`.**

### A runtime settings channel exists, and does not contain the knob

Plexamp's HTTP server has `GET /settings`, `GET /settings/values?name=`, and
**`PUT /settings?name=<x>&value=<v>`**, which assigns a live mobx observable
gated by `isHeadlessSetting(name)`. The gate's list, read from the bundle, is 32
names — `audioDeviceUuid`, `sampleRateMatching`, `playerName`, the equalizer and
quality settings, and so on.

| lever | result |
|---|---|
| `PUT audioDeviceUuid=bluealsa` while `RUNNING` | `PREPARED` at +0.03 s, back to **`RUNNING` at +0.13 s**; the device was **never released** within 25 s. BASS re-initialised and carried on playing |
| `setSinksForSource` | needs `rootStore.mesh`; **404** without it, and it routes between players, not to a null sink |
| `remoteControl=false` (would stop Companion, de-register at plex.tv, close the GDM socket) | **not in `isHeadlessSetting`** → `PUT` returns **400**. Settable only in the settings file, which needs a restart |
| any idle or device-close timeout | **no such setting exists** in the gated set |

**There is no runtime lever inside Plexamp for the fourteen seconds.**

## 2. Our own ladder is why the phone still shows it connected

`_release_with_ladder` sends `release()`, then polls the device for the whole of
`polite_grace` and returns `POLITE` the moment it frees. The plugin declares
`polite_grace: 16.0`, and the device frees at ~14 s — **so the polite rung wins
the race on every takeover, the ladder never escalates, and the player is left
running, registered and claimed.** That is the stale "connected", and it is ours,
not Plexamp's.

### Where a phone learns about the player, and how fast it unlearns

A GDM broadcast to `udp/32412` from this device — which is what a controller
does — is answered by:

```
192.168.178.131:32412   Name: Gexis      Product: Plexamp            Port: 32500
192.168.178.53:32412    Name: gexis      Product: Squeeze Plex Hub   Port: 3000
192.168.178.53:32412    Name: ShelvesPi  Product: Squeeze Plex Hub   Port: 3000
```

The same player also appears in the PMS client table and in plex.tv's resources,
where `Gexis` was the only device with `presence: True`. **The Hub appears in
plex.tv's resources not at all** — it advertises over GDM only.

Withdrawal, measured across `systemctl stop plexamp.service` with samples every
10 s for 3 minutes:

| where | when it lets go |
|---|---|
| plex.tv `presence` | **True → False within ≤10.5 s** (True at t+1.9, False at t+12.4) |
| PMS `/clients` | **still listed at t+149.7, gone by t+181.3** — roughly three minutes |

Recovery, across one `systemctl restart plexamp.service`: `/resources` answering
again at **3.13 s**, plex.tv `presence` back to True at **9.1 s**, device left
`closed`.

## 3. What a signal does, which decides how it comes back

Each signal sent with `systemctl kill -s`, from a healthy unit, watched for 25 s:

| signal | outcome |
|---|---|
| **SIGTERM** | `ActiveState=inactive`, `ExecMainStatus=15`, `Result=success`, `NRestarts=0` — **systemd does not bring it back.** The plugin unit stayed `active` |
| **SIGKILL** | back by itself at **t+0.6 s**, `NRestarts=1`; the plugin unit restarted too |

**`pcm` was `closed` throughout both, and after a full restart.** Plexamp does
not open the ALSA device at startup — it opens it when it plays.

That last sentence is the one that matters, because
[Finding 013 §1](013-phase2c-attack-test-and-spotify-reliability-defects.md)'s restart
storm needed the opposite: squeezelite opens the device as soon as it is back,
failed busy on systemd's own `RestartSec` clock, and burned through
`StartLimitBurst` until the unit stayed failed. Two fixes that stopped and
explicitly restarted the unit were shipped and reverted within a day each.
**The storm's precondition is absent here, measured.**

## 4. Two corrections to Finding 087

[Finding 087](087-what-a-disconnected-phone-does-to-plexamp.md) concluded *"the
phone never connects to Plexamp at all"* and reasoned that a controller talks to
the server, which relays. **Both are wrong.** Plexamp's own HTTP log, grouped by
source address across the full retained log (2026-09-25 16:35 → 2026-09-26
13:54), records the phone talking straight to the player:

```
196  192.168.178.61  /player/playback/setParameters
104  192.168.178.61  /resources
 10  192.168.178.61  /player/playback/skipNext
  9  192.168.178.61  /player/playback/stop
  7  192.168.178.61  /player/playback/createPlayQueue
  6  192.168.178.61  /player/playback/pause
  2  192.168.178.61  /settings/values
```

**The `ss` observation was still real**, and both can be true: these are
short-lived request connections, opened and closed per command. An instantaneous
count of established connections misses them almost always — **so the count
fails because the phone does not hold a connection open, not because it never
connects.** Finding 087's conclusion about the count stands; its stated reason
does not.

**What is still unmeasured, and is the one live lead left for a presence
signal:** `/player/timeline/poll` appears in the log **zero** times, for any
address, including our own plugin which polls it once a second. That route is not
logged, so the log shows commands and not polls, and it cannot say whether the
phone polls the timeline while it is attached. If it does, a sustained absence of
polls is a real signal. Answering it needs a packet capture on `:32500` while
George's phone is attached — twenty seconds of `tcpdump` with the phone absent
found nothing, which proves only that the phone was absent.

### The subscriber list is not the signal either

Plexamp keeps a timeline subscriber map. `addSubscriber` keys it by the
`x-plex-client-identifier` **header**; `removeSubscriber` reads
`e["X-Plex-Client-Identifier"]` from the **query string**. Across the whole
retained log there is exactly **one** `Adding subscriber` line and it is this
session's own probe. The Hub's `timelinePublisher.ts` says why:

> *"This is not required for Plexamp clients as they do not subscribe nor send
> wait=1 when calling poll.get… This is probably LEGACY functionality for Plex
> web player and other clients."*

An independent implementation of the player side, by someone who reverse-
engineered the same controller, agrees with the measurement. **No implementation
of the player can know when Plexamp selects or deselects it.**

## 5. The Squeeze Plex Hub route, measured

`onmomo/squeeze-plex-hub`, MIT, Nuxt/Nitro, a GDM announcer plus a per-player
Plex façade in front of LMS selected by `X-Plex-Target-Client-Identifier`. It
**already advertises this device's own squeezelite** as a Plex target, and
`/api/players` shows it discovering both `gexis` (`88:a2:9e:79:e1:32`) and
`ShelvesPi` from `Lyrion Music Server (Docker)`.

Same 24-bit/192 kHz FLAC, same DAC, both paths:

| | Plexamp direct | Hub → LMS → squeezelite |
|---|---|---|
| `hw_params` | `S32_LE 192000Hz 2ch` | **`S32_LE 192000Hz 2ch`** |
| transcode | none | none — LMS is handed `http://<pms>:32400/library/parts/…/file.flac` |
| device released after stop | ~14 s | **1.00 s** |
| the core's own release log | — | `release[lms]: polite stop freed the device (0.4s)` |

Metadata through LMS is complete: album, artist, track number, duration,
`samplesize: 24`, `3594kbps CBR`, and artwork proxied from the PMS thumb. The
core sees it as LMS (`lms: player powered on (acquisition)`), which is what the
panel would show.

**`playMedia` needs `protocol=http`.** With `protocol=https` the Hub answers
**503** — the PMS certificate is issued for a `plex.direct` name, not the bare
address. The phone's own `playMedia`, in Plexamp's log, uses `protocol=http`.

**A discriminator exists** if a Plex-sourced LMS stream ever needs presenting as
its own renderer: LMS reports these tracks `remote: 1` with the stream URL
pointing at the PMS.

## What this does not establish

- **One device, one phone, one library.** The withdrawal and recovery timings are
  one run each, not distributions.
- **The Hub leg was driven by this session as the controller**, not by George's
  phone. What his phone shows when casting through the Hub is unmeasured.
- **Whether the phone polls the timeline while attached** — §4. The single most
  useful thing a future session could measure here.
- **Nothing about the Hub under load, over time, or across a reboot**, and
  nothing about running it on this device rather than `ShelvesPi`.
- **Nothing about sound quality by ear.** `hw_params` says the format reaching
  the DAC is identical; it says nothing about what LMS's or BASS's paths do to
  the samples before that.
- **No claim that killing the player makes the phone's display follow.** What was
  measured is when plex.tv and the PMS let go; what the phone's UI does with that
  is George's to observe.
