# Architecture

**Status:** settled at high level. Layer boundaries and the arbitration model are
decided. Implementation detail below the layer boundaries is not.

**Last updated:** 2026-09-04

---

## 1. What this is

A high-fidelity music player distribution for the Raspberry Pi 4, built from
scratch. Conceptually adjacent to moOde, Volumio and piCorePlayer, derived from
none of them. moOde is read as a reference implementation (see
`docs/findings/001`), not forked.

Delivered as a **flashable image**. We own the whole system, which is what makes
the bit-perfect claim provable rather than conditional on what the user did to
their OS.

---

## 2. Requirements

### Must

**Hardware**

- Raspberry Pi 4, 4 GB. No other boards in scope.
- HiFiBerry DAC2 HD. PCM179x codec, 192 kHz / 24-bit ceiling, no DSD.
- Attached touchscreen at 1280x800.

**Audio**

- Bit-perfect playback, provable by inspection of the ALSA chain.
- One active renderer at a time. No dmix.
- Hardware volume by default; software volume only as fallback for HATs without
  a mixer.
- Base-image renderers: squeezelite (LMS), go-librespot (Spotify Connect),
  Bluetooth A2DP sink.
- Multiroom via LMS only.

**Interface**

- One web UI codebase serving the touchscreen and remote browsers.
- Four screen types: library navigation, now playing, Peppy screen, idle.
- Now playing, artist info and track info available for every renderer.
- Lyrics on now playing: synced, unsynced, or none.
- Peppy screen renders unmodified PeppyMeter/Volumio-extended skins at 1280x800,
  meters and spectrum animated, track metadata drawn into the skin's positions.
- Switching to the Peppy screen with no visible render-in delay.
- Snappy: low latency on track change, navigation and renderer handoff.
- Metadata file for external displays, moOde-compatible format.
- Headless mode disables the local screen. The web UI remains served.

### Should

1. Qobuz Connect (via an open-source client — see §9)
2. Plexamp
3. Spotify account navigation and control
4. Theme engine
5. Plugin extensibility: renderers, idle screens, meters, themes

### Could

- Visual equaliser
- Room correction using a phone as measurement input
- Hardware polarity inversion — free, exposed as `DAC Invert Output Switch`
- PCM179x rolloff filter selection — free, exposed as `DAC Rolloff Filter Switch`

### Out of scope

- MPD and local library
- Native mobile apps
- Tidal, Deezer and other services at this stage

---

## 3. On "bit-perfect", and the two output modes

Precise wording matters here, and the loose version is what gets quoted back.

The PCM179x has an **internal digital attenuator**. Hardware volume is applied
inside the DAC chip, after the I²S data path. So there are two genuinely
different modes, not a marketing gradation:

| Mode | Volume controlled by | Claim |
|---|---|---|
| **Fixed output** | external amplifier | Nothing in the signal path is touched — not on the Pi, not in the DAC |
| **Variable output** | DAC hardware attenuator | The samples we send to the DAC are unmodified; attenuation happens inside the chip |

Fixed output sets `DAC Playback Volume` to 240 (0 dB) and locks it. It is the
stronger claim and it is available on this hardware.

Variable output is the convenience mode. Note what it is **not**: it is not "no
digital processing anywhere". Attenuation happens, it is digital, and it happens
downstream of everything we control.

Mixing and bit-perfect are mutually exclusive by arithmetic. These are not
quality levels, they are provability modes — which is why there is one audio
path and no mixer.

### Consequences of fixed output

- **Volume controls disappear, not grey out.** A slider that does nothing is
  worse than no slider. Same rule as inapplicable transport buttons.
- **Phone apps will still show a slider.** Spotify and Bluetooth send volume
  commands regardless; we accept and ignore them. The phone's slider moves and
  nothing happens. Unavoidable, and it needs a line in the user documentation.
- **Full-scale output is loud.** Switching from variable to fixed while playing
  must not jump to 0 dB unannounced. Confirmation on the switch, and the change
  should take effect on the next track or after a stop rather than immediately.

Software volume remains as a third path, used only on hardware without a mixer.
Not applicable to the DAC2 HD.

---

## 4. Layers

```
┌─ Presentation ─ web UI, one codebase ───────────────────────┐
│   library nav  │  now playing  │  peppy screen  │  idle     │
│                   capability-      skin renderer            │
│                   driven UI        (circular/linear/spec)   │
│   local: Chromium kiosk under labwc  ·  remote: any browser │
└────────────── WebSocket (state + levels) ───────────────────┘
┌─ Control plane ─ Python ────────────────────────────────────┐
│  Core state daemon                                          │
│    · normalised playback model                              │
│    · capability declaration per adapter                     │
│    · arbitration supervisor                                 │
│    · library proxy (normalised, source-agnostic)            │
│    · volume bridge → ALSA hardware mixer                    │
│    · metadata file writer → external displays               │
│  Visualisation service   levels + FFT                       │
│    · transports: WebSocket │ PeppyMeter HTTP │ peppyalsa FIFO│
│  Enrichment service   artist/album/track → bio, artwork     │
│  Lyrics service                                             │
│  Config store — SQLite                                      │
└──────────────── IPC contract (plugins) ─────────────────────┘
┌─ Renderers ─ separate processes, systemd units ─────────────┐
│  squeezelite      go-librespot      bluealsa-aplay          │
│           all write to logical device "output"              │
└─────────────────────────────────────────────────────────────┘
┌─ Audio ─────────────────────────────────────────────────────┐
│  output  →  type meter + peppyalsa scope  →  hw: DAC2 HD    │
│  hardware mixer for volume                                  │
└─────────────────────────────────────────────────────────────┘
┌─ Base ──────────────────────────────────────────────────────┐
│  image + kernel + hifiberry-dacplushd (EEPROM-detected)     │
│  BlueZ + bluez-alsa · avahi                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Audio layer

**Direct ALSA. No sound server.** PipeWire was the earlier decision and was
reversed when Plexamp moved from Must to Should — see ADR-0008. The reversal
condition is recorded: a non-cooperative renderer entering Must.

### The `output` indirection

Every renderer targets a logical ALSA device named `output`. Nothing references
`hw:` directly and nothing references a card index.

```
pcm.output {
    type meter
    slave.pcm "hw:sndrpihifiberry"
    scopes.0 peppyalsa
}
```

This is the hinge of the whole design. Adopting PipeWire later becomes one
config file rather than a renderer migration. moOde validates the pattern with
its `_audioout` device (Finding 001).

**Card index is never used.** It is 3 on our rig and 2 on moOde, because
`dtparam=audio=on` adds an onboard device at index 0. Always
`hw:sndrpihifiberry`.

### Format constraints

The card advertises S16_LE, S24_LE, S32_LE at 44.1–192 kHz, stereo only.
`S24_3LE` is not offered — 24-bit content travels in a 4-byte container.
All 18 combinations verified working through the meter chain (Finding 002).

### Volume

Hardware, via `DAC Playback Volume`: 240 steps of 0.5 dB, 0 = mute, 240 = 0 dB.
Simple-mixer name is `DAC`, which is what `squeezelite -V` needs.

One global control shared by all renderers. Spotify, LMS and Bluetooth each
expect to own device volume; all three are bridged onto this one mixer.

### Known defect

`type meter` loses the final 768 frames of a stream at S32_LE/192000. Interior
samples are bit-identical at both extremes of the grid. Characterised in
Finding 003, unresolved, logged. Does not block the design; does block the
bit-perfect claim being written into marketing copy until closed.

---

## 6. Arbitration

**Base slot + active slot.** Not a stack. No history.

- **Base slot** is permanently LMS. Squeezelite's connection to the server is
  structural, not a user session.
- **Active slot** holds at most one other renderer.
- Release empties the active slot. The base becomes current. Nothing is
  restored, because nothing was stored.

Stack ordering was considered and rejected: stack order is invisible state, so
the user cannot predict it. A Spotify session connected an hour ago and
forgotten should not win the device back because Bluetooth dropped.

### Acquisition — on connection

Connection is a deliberate user act, so the user owns the consequence. It is
also mechanically cleaner: connect events are D-Bus signals and API state
changes, where stream-start detection means hooking AVDTP START or PCM open.

Each adapter **declares its acquisition events**, because the renderers have
different shapes:

| Renderer | Acquisition |
|---|---|
| LMS | explicit play or resume (no connect event exists — always connected) |
| Spotify Connect | device selected in the app |
| Bluetooth | A2DP profile connect |
| Qobuz Connect | device selected in the app |

### Release — disconnect, uniformly

**Takeover disconnects the outgoing renderer. The only exception is LMS, which
pauses, because its connection is structural rather than a user session.**

| Renderer | On losing the device |
|---|---|
| LMS | pause, stay connected (base slot) |
| Bluetooth | disconnect |
| Spotify Connect | disconnect |
| Qobuz Connect | disconnect |

Disconnect is self-explaining: the phone shows the device gone rather than
showing "playing" into a silent room. No invisible state anywhere.

#### Why Bluetooth is not an exception — the rejected alternative

Pausing Bluetooth via AVRCP while keeping it connected was designed and then
rejected. It fails because **no signal available to us distinguishes deliberate
playback from incidental audio.**

If a paused-but-connected phone can reacquire by starting a stream, then a
notification chirp, an autoplaying video in a feed, or a navigation prompt all
count as acquisition — and music stops because someone scrolled past a video.
That is a defect users will hit routinely, not an edge case.

The alternatives were examined and none works:

- **Duration threshold** — delays every legitimate start, and does not help with
  a long autoplaying video.
- **Signal level** — notification sounds are often loud. No separation.
- **App identity** — A2DP does not carry it. AVRCP session state does not
  reliably reflect where audio is going: a phone that has handed Spotify
  playback to our Connect renderer may still report "playing", because Spotify
  *is* playing, just elsewhere. Treating that as acquisition ping-pongs the
  device between renderers.

The cost of disconnect is that reacquisition requires reconnecting from the
phone. That is mitigated in the UI rather than the audio layer — see below.

Weighed against this, the argument for pausing was that A2DP disconnect can
bounce audio to the phone's own speaker. Pausing before disconnecting largely
addresses that, so it does not outweigh the notification problem.

### Mitigating Bluetooth reconnection

Reconnecting should not require a trip into phone settings. The idle and
now-playing screens list recently-connected Bluetooth devices; tapping one
initiates the connection from our side. BlueZ can initiate connections to
trusted devices, so this is available to us.

**Unverified:** how reliably a phone that has moved on accepts an
inbound connection.

### LMS power state

Power on/off in the LMS interface plays **no role in arbitration**. It is a soft
state inside LMS — a powered-off player is one that will not play. It does not
acquire the device and does not release it.

If a player is powered off in LMS and someone presses play on it, LMS powers it
on and starts. That is still play, so it is still acquisition. No special case.

**Our UI shows nothing special for a player powered off in LMS.** It is not a
state a person standing in front of the device can act on.

Power state matters for multiroom, because a powered-off player will not join a
sync group. That is LMS's concern, not ours.

### Implementation note

Squeezelite holds the ALSA device open by default. `-C <seconds>` makes it close
after idle, which is what actually frees the device. That flag is part of how
release is implemented, not a tuning option.

### Rules

- **No auto-resume.** Release never starts playback. The user chooses what plays
  next. Release of the active slot leaves LMS current but not playing, which
  means the idle screen.
- **Takeover acts on the outgoing renderer through its control channel.**
  Blocking the audio path is not sufficient: the source would still show
  "playing" into a silent room. An adapter must be able to disconnect or pause
  its renderer on demand and report success or failure.
- **The UI must never show "playing" while silent.** Handoff is a displayed
  state.

### Open

- Sync group behaviour: squeezelite stays in its LMS group while another
  renderer holds the device, so a group play command becomes an acquisition that
  interrupts. Consistent with the rule, possibly surprising.
- Empty base slot, if run headless with no LMS. Valid state, undefined
  behaviour.

---

## 7. Display

Four screens. Two are driven by different things, and conflating them was an
error corrected during design.

```
   Idle  ──playback starts──▶  Now playing  ◀──▶  Library navigation
     ▲                            │   ▲
     │                          button │ touch
  nothing                         ▼   │
  playing                     Peppy screen
                                  ▲
                       idle timeout while playing
```

### Library navigation is the whole LMS browse tree

Not a music-library browser. The full navigation the LMS server exposes:

- **My Music** — artists, albums, genres, years, new music, random mix,
  playlists, favourites, and whatever else the server offers
- **Radio**
- **My Apps** (Could tier)
- Anything LMS plugins have added to the menu

**The browse tree is data, not screens.** LMS returns menus as structured items
carrying their own types and actions — it describes its own navigation. So the
UI renders one **generic browser** driven by whatever the server returns, rather
than having a screen per category.

This is what makes the Qobuz navigation Should tractable: it maps onto the same
generic browser, and LMS plugin menus we have never heard of work without us
knowing they exist.

App menus will eventually need text input and search, which the generic browser
must support.

**Now playing is capability-driven.** LMS gives full transport plus queue.
Spotify Connect gives transport, queue lives in the phone app. Bluetooth gives
AVRCP with per-device command support. Controls that will not work are hidden or
greyed — a next button that silently does nothing is worse than no next button.

**The Peppy screen is capability-blind.** Metadata plus levels, nothing else.
Identical regardless of what is playing. Display-only.

### The skin format is the metadata contract

The 71 Gelo5 skins inspected all carry `config.extend = True` and position:

```
title · artist · album · artwork · sample rate · remaining time · source type
```

Album is optional (44 of 71). That set is the minimum every renderer adapter
must supply. Where a field is absent, the skin renderer **blanks that region,
never the screen**.

### Skin rendering

In-browser, consuming the PeppyMeter/Volumio extended format unmodified. The
value is in the community skins, so consuming them is the point.

Layer stack, explicit in the skin data, mapping to stacked DOM layers where only
one changes per frame:

```
screen.bgr          full-screen JPG          static
bgr.filename        meter background PNG     static
indicator.filename  needle / bar sprite      30 fps
fgr.filename        glass overlay (54/71)    static
albumart + text     from playback state      per track
```

A circular needle is a CSS `transform: rotate()` on an `<img>` —
GPU-composited, no repaint of the static layers. PeppyMeter blits on the CPU.

Surface enumerated from the skin corpus: `meter.type` is `circular` (53) or
`linear` (18), nothing else. All stereo. Rare variants: `direction =
bottom-top` (5), `indicator.type = single` (2), per-channel angles (2).
Spectrum is one shape across 13 sections.

`steps.per.degree` (values 2 and 4) exists because PeppyMeter pre-renders
rotated needle sprites. A browser rendering continuously would be *smoother
than the original*. Some skins are period reproductions where stepping may be
intentional — quantisation is a deliberate choice, not a default.

---

## 8. Control plane

Python. One core daemon plus three services.

### Core state daemon

- **Normalised playback model** — the seven fields above, plus position and
  duration.
- **Capability declaration per adapter** — drives now-playing control rendering.
- **Arbitration supervisor** — §6.
- **Library proxy** — see below.
- **Volume bridge** — ALSA mixer, subscribed to ctl events rather than polled,
  so external changes keep the UI slider in sync.
- **Metadata file writer** — moOde-compatible format, so existing external
  display projects work unchanged.

### Library data path

**Core proxies the browse tree and metadata; artwork URLs point directly at LMS.**

Rationale is the Qobuz navigation Should. If the browser learns LMS's API,
adding Qobuz means teaching it a second one, and the two screens will diverge in
behaviour no matter how carefully they are designed. A normalised browse API
means "navigate a source" is one thing the UI knows how to do, regardless of
source.

The core normalises LMS menu items into a source-agnostic node shape — title,
subtitle, artwork reference, node type, available actions, whether it has
children. The UI never learns LMS's vocabulary.

Artwork bypasses the core because it is the heavy part and LMS already has a
caching image resizer. It degrades gracefully if unreachable.

Cache list data aggressively in RAM. 4 GB is ample and responsiveness is the
point.

### Adapters

| Renderer | Transport |
|---|---|
| LMS | CometD subscribe for push; JSON-RPC on :9000 for calls |
| Spotify | go-librespot HTTP + WebSocket API |
| Bluetooth | BlueZ `org.bluez.MediaPlayer1`, D-Bus PropertiesChanged |

LMS polling is not acceptable — CometD or track changes will visibly lag.

### Visualisation service

Reads the peppyalsa FIFOs, publishes on three transports: WebSocket (primary,
for the browser renderer), PeppyMeter HTTP (so unmodified PeppyMeter can be
dropped in as a plugin), peppyalsa FIFO (compatibility).

Publishing on all three keeps the renderer choice reversible.

peppyalsa does not block when the FIFOs have no reader (Finding 002), so this
service can attach and detach freely without stalling audio.

**Logged alternative:** computing RMS and FFT ourselves rather than reading
peppyalsa would free us from its `decay_ms`, smoothing and 0–100 scale, and
would remove the meter plugin from the audio path entirely — sidestepping the
Finding 003 defect. It requires our own tap, whose shape is unknown. Not
adopted; recorded so the option is not lost.

### Enrichment service

Renderer-agnostic, keyed on (artist, album, title, duration). Bluetooth is the
thinnest input, which is why it forces the design honest — but LMS and Spotify
need artist bios too.

- **Never block the now-playing render on network.** Text appears immediately;
  art and bio arrive later. Reserve artwork space so late arrival does not
  reflow.
- **Additive only.** Never overwrite renderer-supplied text. A fuzzy match on
  messy AVRCP strings will sometimes be wrong, and the screen must not lie about
  what is playing.
- **Confidence threshold.** Below it, show nothing. A confidently wrong artist
  biography is worse than a blank panel.
- **One global rate limiter.** MusicBrainz permits about one request per second
  per IP and 503s everything above that; a meaningful User-Agent is required and
  polling is explicitly discouraged. Single shared token bucket, persistent
  cache, negative results cached too.

### Config store

SQLite. The UI writes settings while the core reads them; concurrent access is
the deciding factor over plain files.

---

## 9. Plugins

**Separate processes with an IPC contract.** Not in-process modules.

Two reasons:

1. A crashing plugin cannot take down playback or the UI.
2. Plugins can be written in any language, and a plugin can live in a different
   repository. The Qobuz Connect plugin is planned for a **private** repo, which
   makes the contract real rather than a convention inside one codebase.

### Contract fields

Minimum, derived from the three defaults:

- audio connection method (always `output`)
- acquisition events (one or more)
- release behaviour (disconnect | pause)
- pause capability, with success/failure reporting
- metadata capability declaration
- control surface

**The three default renderers are implemented against the public contract**, not
special-cased. If the built-ins are privileged, the contract will be incomplete
and the first external plugin will discover it.

### Qobuz Connect

Qobuz Connect launched May 2025, developed with StreamUnlimited. The official
route is partnership, a proprietary SDK and a certification self-test. That is
incompatible with a public repository. moOde reached the same conclusion in May
2025 and found no FOSS-licensed code to integrate; Volumio has it via
partnership.

The unofficial route is reverse-engineered clients — `ahcm/qconnect` exists, and
roderickvd (librespot, pleezer maintainer) has been working on an
implementation since May 2025.

Therefore Qobuz Connect is a **Should, delivered as an optional plugin the user
installs**, not something the base image ships. It is also the first external
test of the plugin contract.

It does not replace Plexamp as the ADR-0008 reversal test: `qconnect` is open
source and writes to ALSA, so it is cooperative and will not stress the PipeWire
question at all.

---

## 10. Non-negotiable principles

**Spend the hardware on responsiveness.** Footprint and flash wear are not
selection criteria. Everything stays resident — Chromium never restarts,
renderers stay loaded even when inactive, arbitration controls who holds the
device rather than who is running. Cold start is the enemy.

**Protect the audio path with priority, not by doing less.** If UI load ever
causes audio underruns, the answer is scheduling priority and CPU affinity, not
a reduced interface.

**Never reference an ALSA card by index.**

**Findings state their scope.** What was tested, under what conditions, what was
not. A single negative result is not decisive.

---

## 11. Open questions

**Deferred to their ADRs:**

- Peppy screen exit gesture. Touch-to-exit costs three actions to skip a track;
  a transient transport overlay on first touch costs a hidden gesture.
- Volume semantics in variable-output mode. Does the phone's Spotify slider move
  the amp?
- `steps.per.degree` quantisation — match PeppyMeter or render smooth.
- Degraded metadata display rule beyond "blank the region".
- Empty base slot behaviour.
- Bluetooth reconnection UX and whether inbound connection is reliable.

**Needing measurement:**

- Takeover gap under direct ALSA, same-rate and cross-rate.
- Finding 003 grid fill and mechanism.
- Per-frame cost of the layered browser renderer at 1280x800 on a Pi 4.
- LMS CometD latency in practice.
- Pi 4 Wi-Fi/Bluetooth coexistence under simultaneous A2DP and network
  streaming.

**Needing investigation:**

- Base OS: Raspberry Pi OS Lite vs DietPi. Still open (ADR-0001). Blocked on
  whether DietPi supports a reproducible, CI-drivable image build comparable to
  Volumio's `build.sh` or moOde's pi-gen wrapper. Note that DietPi on a Pi is a
  conversion applied on top of Raspberry Pi OS Lite and uses the same apt repos
  and kernel, so Phase 1 measurements transfer either way.
- PeppyMeter skin asset conventions: needle sprite pivot, the meaning of
  `distance`, the font faces the skins assume, the `playinfo.type` icon set.
- Spotify Web API scope availability for the account-navigation Should.
- Synced lyrics sources for non-LMS renderers.
- BlueZ AVRCP cover art in the controller role.

**No reference implementation exists for our display stack.** moOde and Volumio
run Chromium on X; piCorePlayer runs Jivelite on the framebuffer. Chromium on
Wayland under labwc is none of those.
