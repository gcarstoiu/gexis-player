# Architecture

**Status:** settled at high level. Layer boundaries and the arbitration model are
decided. Implementation detail below the layer boundaries is not.

**Last updated:** 2026-10-07 - brought into line with the code and the ADRs
up to ADR-0127 (the hardware, screens, volume, the ALSA chain, the screens
list, arbitration's plugin renderers, the visualiser, enrichment, plugins).
Where history explains a choice, the old text stays under a dated note.

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

- Raspberry Pi 4 only; 4 GB tested, 2 GB the untested minimum
  (`docs/HARDWARE.md`). No other boards in scope.
- A DAC HAT from the player's list, or a class-compliant USB DAC, each
  *Tested*, *Reported*, *Known* or *Detected*
  ([ADR-0117](decisions/0117-dacs-beyond-the-two-on-the-bench.md),
  [ADR-0126](decisions/0126-hardware-reports-from-users.md)). The bench
  reference is the HiFiBerry DAC2 HD (PCM179x, 192 kHz / 24-bit, no DSD); the
  IQaudIO Pi-DAC PRO is Tested too. *(Was: the DAC2 HD only.)*
- An attached HDMI screen of the Standard or Bar family, or none (headless)
  ([ADR-0109](decisions/0109-other-screens.md)); 1280x800 is the reference
  panel. *(Was: a 1280x800 touchscreen only.)*

**Audio**

- Bit-perfect playback, provable by inspection of the ALSA chain.
- One active renderer at a time. No dmix.
- Volume is **Hardware** (the card's own control; default), **Software** (the
  player scales the samples, on any output; it takes Hardware's place on an
  output with no control, such as HDMI) or **Fixed**
  ([ADR-0124](decisions/0124-software-volume.md),
  [ADR-0127](decisions/0127-one-volume-row.md)). *(Was: software volume only as
  a fallback for HATs without a mixer.)*
- Base-image renderers: squeezelite (LMS), go-librespot (Spotify Connect),
  Bluetooth A2DP sink.
- Multiroom via LMS only.

**Interface**

- One web UI codebase serving the touchscreen and remote browsers. **Refined
  2026-09-15 by [ADR-0032](decisions/0032-one-page-two-surfaces.md):** still
  one codebase and one served page, but not parity — the panel renders
  everything, a remote browser renders only the settings surface. Only the
  settings screen is responsive; every other screen is a fixed 1280x800
  artboard, because no other screen is ever served to a phone.
  **Amended 2026-10-07:** the panel lays every screen out by its family,
  Standard or Bar (ADR-0109); a phone gets Settings, the mini player
  ([ADR-0101](decisions/0101-a-mini-player-on-the-phone.md)) and the touchpad
  ([ADR-0121](decisions/0121-the-phone-as-the-panel-s-touchpad-and-keyboard.md)).
- The panel's screens: Home, the library (ADR-0030), now playing, the Peppy
  screen, idle, the takeover screen (ADR-0094), the waiting screens with LMS
  off (ADR-0079), Settings, setup, the update screen, the pairing
  confirmation. *(Was: four screen types.)*
- Now playing, artist info and track info available for every renderer.
- Lyrics on now playing: synced, unsynced, or none.
- Peppy screen renders PeppyMeter/Volumio-extended skins with the native
  engine (ADR-0026), drawn for the attached screen's size - or the largest
  set that fits, centred (ADR-0111) - meters and spectrum animated, track
  metadata drawn into the skin's positions.
- Switching to the Peppy screen with no visible render-in delay.
- Snappy: low latency on track change, navigation and renderer handoff.
- Metadata file for external displays, moOde-compatible format.
- Headless mode disables the local screen. The web UI remains served.

### Should

1. Plexamp - **delivered as a plugin**, fetched on the device when switched
   on (ADR-0090, ADR-0100).
2. Spotify account navigation and control
3. Theme engine
4. Plugin extensibility: renderers, idle screens, meters, themes - **renderers
   and services delivered** (ADR-0084, ADR-0086, ADR-0089, ADR-0106);
   themes, idle screens and meters not yet.

### Could

- Visual equaliser
- Room correction using a phone as measurement input
- Hardware polarity inversion — free, exposed as `DAC Invert Output Switch`
- PCM179x rolloff filter selection — free, exposed as `DAC Rolloff Filter Switch`

### Out of scope

- MPD, and a library managed by the player itself. A local library is served
  only through the optional Lyrion Server plugin
  ([ADR-0115](decisions/0115-the-lyrion-server-as-a-plugin.md)).
- Native mobile apps
- Tidal, Deezer and other services at this stage

---

## 3. On "bit-perfect", and the volume modes

Precise wording matters here, and the loose version is what gets quoted back.

The PCM179x has an **internal digital attenuator**. Hardware volume is applied
inside the DAC chip, after the I²S data path. So there are two genuinely
different modes, not a marketing gradation:

| Mode | Volume controlled by | Claim |
|---|---|---|
| **Fixed output** | external amplifier | Nothing in the signal path is touched — not on the Pi, not in the DAC |
| **Hardware** (was *Variable output*) | DAC hardware attenuator | The samples we send to the DAC are unmodified; attenuation happens inside the chip |
| **Software** (ADR-0124, ADR-0127) | the player scales the samples, after the meter tap | Bit-perfect at 100 % only (Finding 115); not below |

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

Software volume is the third mode, on any output (ADR-0124, ADR-0127): the
owner's choice where the card has its own control, and what takes Hardware's
place where it has none (HDMI). *(Was: a third path only on hardware without
a mixer.)*

---

## 4. Layers

```
┌─ Presentation ─ web UI, one codebase ───────────────────────┐
│   home · library · now playing · idle · settings · …        │
│                   capability-driven UI                      │
│   local: Chromium kiosk under labwc                         │
│   remote: Settings, the phone's mini player and touchpad    │
└──── WebSocket /state (publish-only) + REST, core on :8090 ──┘
┌─ Peppy screen ─ native process (ADR-0026) ──────────────────┐
│   PeppyMeter/PeppySpectrum, skins rendered natively         │
│   raised and hidden by labwc, not by the browser            │
└─────────────────────────────────────────────────────────────┘
┌─ Control plane ─ Python ────────────────────────────────────┐
│  Core state daemon                                          │
│    · normalised playback model                              │
│    · capability declaration per adapter                     │
│    · arbitration supervisor                                 │
│    · library proxy (normalised, source-agnostic)            │
│    · volume bridge → the active renderer's own volume,      │
│      mirrored onto the card's control or the software stage │
│    · metadata file writer → external displays               │
│    · enrichment and lyrics (in the core process, ADR-0040)  │
│  Visualisation service (gexis-meter) levels + FFT           │
│    · FIFOs to PeppyMeter │ WebSocket /meter │ PeppyMeter HTTP│
│  Config store — SQLite                                      │
└──────────────── IPC contract (plugins) ─────────────────────┘
┌─ Renderers ─ separate processes, systemd units ─────────────┐
│  squeezelite   go-librespot   bluealsa-aplay   plugins      │
│  (Plexamp, …)  all reach the logical device "output"        │
└─────────────────────────────────────────────────────────────┘
┌─ Audio ─────────────────────────────────────────────────────┐
│  output → meter (peppyalsa) → [softvol] → [plug] → card     │
│  softvol with Software volume; plug on HDMI; HDMI on Fixed: │
│  plug only, no meter                                        │
└─────────────────────────────────────────────────────────────┘
┌─ Base ──────────────────────────────────────────────────────┐
│  image + kernel + DAC overlay (by EEPROM, or from the list) │
│  BlueZ + bluez-alsa · avahi                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Audio layer

**Direct ALSA. No sound server.** PipeWire was the earlier decision and was
reversed when Plexamp moved from Must to Should — see ADR-0008. The reversal
condition is recorded: a non-cooperative renderer entering Must.

### The `output` indirection

Every renderer's audio reaches a logical ALSA device named `output` -
squeezelite through `output_wait`, its twin whose open waits for a busy card
(ADR-0095), and Plexamp through the ALSA default, an alias of `output`
(ADR-0085). No renderer references `hw:` for audio, and nothing references a
card index.

The default, for the DAC2 HD on Hardware volume (`image/stage-gexis/00-alsa/
files/output.conf`, with `output_wait`, `ctl.output` and the peppyalsa scope
beside it); the core rewrites it for the chosen output and volume mode
(`outputs.render()`):

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

The card's own playback control, its scale read from ALSA rather than assumed
(ADR-0117) - on the DAC2 HD `DAC`, 240 steps of 0.5 dB, 240 = 0 dB - or, with
Software volume, the software stage's `Gexis` control (-90..0 dB in 0.25 dB
steps, ADR-0124). squeezelite drives a private dummy mixer
(`hw:gexislmsvol`, `Master`) that the core follows.

One control shared by all renderers. Spotify, LMS and Bluetooth each expect to
own device volume; each reaches this one control through its own channel, and
the panel changes the active renderer's level rather than the card's
(ADR-0053, ADR-0054).

### No known defect in the meter

Finding 003 reported that `type meter` lost the final 768 frames of a stream.
**Withdrawn:** Finding 004 shows the same artefact with the meter removed - it
is `snd-aloop`'s, the capture device the test used.

---

## 6. Arbitration

> **Changed by [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md)
> (2026-09-12).** There is no permanent base slot. LMS is deactivated on every
> takeover and stays deactivated until the user activates it, so **"no renderer
> holds the device" is a normal state**, not an undefined one. The *not a stack,
> no history* rule below is unchanged. Evidence: Finding 018.

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

> **LMS's row changed by [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md):**
> powering the player **on** is the acquisition. Play is a separate intention
> afterwards, which makes LMS consistent with the other renderers.

| Renderer | Acquisition |
|---|---|
| LMS | the player powered on (ADR-0027; was: explicit play or resume) |
| Spotify Connect | device selected in the app |
| Bluetooth | A2DP profile connect; also the phone playing again (`MediaPlayer1` Status) |
| Plugin renderer | as its manifest declares, plus a play queue it has not seen (ADR-0089, ADR-0092) |

### Release — disconnect, uniformly

**Takeover disconnects the outgoing renderer. The only exception is LMS, which
pauses, because its connection is structural rather than a user session.**

> **LMS's row changed by [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md):**
> record the transport state, `pause`, then `power 0` — measured to free the
> ALSA device in 0.06-0.11s against 1.44s for a commanded pause alone, which is
> what lets the incoming renderer win its first open.

| Renderer | On losing the device |
|---|---|
| LMS | pause, then power 0 (ADR-0027; was: pause, stay connected) |
| Bluetooth | disconnect |
| Spotify Connect | disconnect |
| Plugin renderer | its unit taken off the device (ADR-0091) |

Every release escalates when the renderer does not let go: the polite stop,
then SIGTERM, then SIGKILL (`arbitration.py`).

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

**Planned, not built (2026-10-07):** reconnecting should not require a trip
into phone settings. The idle and now-playing screens would list
recently-connected Bluetooth devices; tapping one would initiate the
connection from our side. BlueZ can initiate connections to trusted devices,
so this is available to us. Today Settings lists and forgets paired devices
only (ADR-0044, ADR-0045).

**Unverified:** how reliably a phone that has moved on accepts an
inbound connection.

### LMS power state

> **REVERSED by [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md)
> (2026-09-12).** Power is now exactly the arbitration mechanism. Kept below
> because the reasoning was sound on what was known then; what changed is
> measured evidence, not logic.

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
  next. With no renderer holding the device the panel shows Home; the idle
  screen follows after five minutes without activity (ADR-0033). *(Was: LMS
  current but not playing, the idle screen.)*
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
- ~~Empty base slot, if run headless with no LMS.~~ **Answered by
  [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md):** no
  renderer holding the device is a routine state, not an edge case — the UI
  must represent it.

---

## 7. Display

> **Amended 2026-10-07.** The four-screen picture below predates Home
> (ADR-0033), the takeover screen (ADR-0094) and the waiting screens
> (ADR-0079). Now: with nothing connected the panel shows **Home**; **idle**
> comes after five minutes without activity, from any screen (ADR-0033); the
> **Peppy screen** is entered by its button or after five minutes of
> unattended playback - not the same timer (ADR-0036 §1); every takeover shows
> the takeover screen. The original picture is kept for the reasoning it
> records.

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

> **Superseded 2026-09-14 by
> [ADR-0030](decisions/0030-library-typed-radio-slimbrowse.md).** The premise
> below — one generic browser over the whole server menu — was challenged by
> George and did not survive. **The local library is now our own screens over
> typed queries** (`albums`, `artists`, `genres`, `titles`, …), and the generic
> browser survives only for **radio**, entered directly at
> `["radios","menu:radio"]`. My Apps, LMS's settings node and search are not
> filtered out — they are unreachable by construction. The "text input and
> search" paragraph below is moot: no text input is rendered anywhere
> ([ADR-0029](decisions/0029-text-entry-on-every-surface.md)).
>
> **The Qobuz argument below is the part that was wrong.** It claimed the
> generic browser made Qobuz tractable. Measured: plugin content is OPML
> (`hasitems`/`isaudio`) with no typed equivalent, so the generic browser buys
> less than assumed — and ADR-0030 accepts the opposite cost deliberately,
> that adding a streaming service later is our work rather than automatic.

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

This is what makes a streaming service's menus in LMS (its Qobuz app, say)
tractable: they map onto the same
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
must supply - **except the sample rate**, which is shown nowhere but the
visualiser, and there only for LMS or a plugin that declares it is the source's
(ADR-0036 §2 as amended). Where a field is absent, the skin renderer **blanks that region,
never the screen**.

### Skin rendering

> **Superseded by [ADR-0026](decisions/0026-peppymeter-native-process-integration.md).**
> The skins are drawn by the vendored PeppyMeter/PeppySpectrum engines, a
> native process kept rendering while hidden and raised by labwc (§4). The
> in-browser design below was not built; it is kept for the skin-corpus survey
> it records.

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

Python. One core daemon - state, arbitration, library, volume, enrichment and
lyrics (ADR-0040), settings, setup, the plugin socket - and a separate
visualisation service (`gexis-meter`). *(Was: one core daemon plus three
services.)* The other units on the image include `gexis-peppy`,
`gexis-kiosk`, `gexis-park`, `gexis-smb`, `gexis-screen-check`,
`gexis-fetch@`, the uploaded-plugin units and the updater's.

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

> **Partly superseded 2026-09-14 by
> [ADR-0030](decisions/0030-library-typed-radio-slimbrowse.md).** Core still
> proxies, and artwork still points directly at LMS —
> `artwork_track_id` → `/music/<id>/cover` is the same URL either way. What
> changed is *what* is proxied: typed queries for the local library, SlimBrowse
> only for radio. The rationale below assumed one normalised browse API would
> make Qobuz cheap; it would not, and Qobuz is no longer rendered.

Rationale is browsing a streaming service's own catalogue. If the browser learns
LMS's API, adding such a service means teaching it a second one, and the two screens will diverge in
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
| Bluetooth | BlueZ `org.bluez.MediaPlayer1` and `MediaTransport1`, D-Bus PropertiesChanged; volume from `org.bluealsa.PCM1` (ADR-0054) |
| Plugin renderer | JSON lines over `/run/gexis/plugins.sock` (ADR-0084, ADR-0089; `docs/PLUGIN-CONTRACT.md`) |

LMS polling is not acceptable — CometD or track changes will visibly lag.

### Visualisation service

Reads the peppyalsa FIFOs and republishes them, the levels scaled to follow
the volume (ADR-0057): to the native PeppyMeter through passthrough FIFOs (the
primary consumer, ADR-0026), on WebSocket `/meter` (:8091), and optionally to a
PeppyMeter HTTP server (off by default). *(Was: WebSocket primary, for a
browser renderer that was not built.)*

Publishing on all three keeps the renderer choice reversible.

peppyalsa does not block when the FIFOs have no reader (Finding 002), so this
service can attach and detach freely without stalling audio.

**Logged alternative:** computing RMS and FFT ourselves rather than reading
peppyalsa would free us from its `decay_ms`, smoothing and 0–100 scale, and
would remove the meter plugin from the audio path entirely. (The Finding 003
defect it would have sidestepped was withdrawn by Finding 004.) It requires our own tap, whose shape is unknown. Not
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
- **One rate limiter per provider** (ADR-0040 §5; was: one global bucket).
  MusicBrainz permits about one request per second per IP and 503s everything
  above that; a meaningful User-Agent is required and polling is explicitly
  discouraged. Persistent cache, negative results cached too.

### Config store

SQLite. The UI writes settings while the core reads them; concurrent access is
the deciding factor over plain files.

---

## 9. Plugins

**Separate processes with an IPC contract.** Not in-process modules.

Two reasons:

1. A crashing plugin cannot take down playback or the UI.
2. Plugins can be written in any language, and a plugin can live in a different
   repository, which makes the contract real rather than a convention inside
   one codebase.

### Contract fields

Minimum, derived from the three defaults. The decided form: JSON lines over a
Unix socket (ADR-0084), a manifest (ADR-0086) of kind `renderer` or `service`,
settings passed to the unit as environment (ADR-0088), installed and uploaded
plugins (ADR-0106) - `docs/PLUGIN-CONTRACT.md` is the reference.

- audio connection method (always `output`)
- acquisition events (one or more)
- release behaviour (disconnect | pause)
- pause capability, with success/failure reporting
- metadata capability declaration
- control surface

> **Amended by ADR-0013 (2026-09-25).** The three defaults stay in the core
> process and do not speak the protocol; the contract is derived from them, and
> plugin renderers are carried by the same arbitration (ADR-0089). The
> paragraph below was the original intent.

**The three default renderers are implemented against the public contract**, not
special-cased. If the built-ins are privileged, the contract will be incomplete
and the first external plugin will discover it.

---

## 10. Non-negotiable principles

**Spend the hardware on responsiveness.** Footprint and flash wear are not
selection criteria. Everything stays resident — Chromium never restarts,
renderers that are switched on stay loaded even when inactive (one switched
off is stopped, ADR-0077), arbitration controls who holds the device rather
than who is running. Cold start is the enemy.

**Protect the audio path with priority, not by doing less.** If UI load ever
causes audio underruns, the answer is scheduling priority and CPU affinity, not
a reduced interface.

**Never reference an ALSA card by index.**

**Findings state their scope.** What was tested, under what conditions, what was
not. A single negative result is not decisive.

---

## 11. Open questions

**Deferred to their ADRs:**

- ~~Peppy screen exit gesture.~~ Touch exits (ADR-0019).
- ~~Volume semantics in variable-output mode.~~ The renderer's own volume is
  the device's; the phone's slider moves it (ADR-0053).
- ~~`steps.per.degree` quantisation.~~ Moot: the native engine draws the
  skins (ADR-0026).
- Degraded metadata display rule beyond "blank the region".
- ~~How the UI represents "no renderer holds the device".~~ Home (ADR-0033);
  with LMS off, the waiting screens (ADR-0079).
- Bluetooth reconnection UX and whether inbound connection is reliable (§6:
  planned, not built).

**Needing measurement:**

- Takeover gap under direct ALSA, same-rate and cross-rate.
- ~~Finding 003 grid fill and mechanism.~~ Withdrawn (Finding 004).
- ~~Per-frame cost of the layered browser renderer.~~ Moot (ADR-0026).
- LMS CometD latency in practice.
- Pi 4 Wi-Fi/Bluetooth coexistence under simultaneous A2DP and network
  streaming.

**Needing investigation:**

- ~~Base OS.~~ **Decided: Raspberry Pi OS Lite 64-bit, built with pi-gen
  (ADR-0001, Accepted).** The original question, for the record: Raspberry Pi
  OS Lite vs DietPi, blocked on
  whether DietPi supports a reproducible, CI-drivable image build comparable to
  Volumio's `build.sh` or moOde's pi-gen wrapper. Note that DietPi on a Pi is a
  conversion applied on top of Raspberry Pi OS Lite and uses the same apt repos
  and kernel, so Phase 1 measurements transfer either way.
- ~~PeppyMeter skin asset conventions.~~ Moot: the native engine reads its
  own skins (ADR-0026).
- Spotify Web API scope availability for the account-navigation Should.
  **Partially resolved, Phase 2 (2026-09-05):** the Player API — transfer
  playback, play/pause, read playback state — is confirmed available to a
  brand-new Development Mode app, unaffected by either the Nov 2024 or Feb
  2026 endpoint restrictions (verified against developer.spotify.com, not
  assumed). That's what Connect device control needs, and it isn't blocked.
  **Still unverified:** the browse/library/playlist endpoints account
  *navigation* would need beyond playback control — the Feb 2026 change
  specifically restricted browse/categories and batch catalog endpoints for
  new apps, which was not checked against what navigation would require.
- ~~Synced lyrics sources for non-LMS renderers.~~ LRCLIB (ADR-0040).
- BlueZ AVRCP cover art in the controller role.

**No reference implementation exists for our display stack.** moOde and Volumio
run Chromium on X; piCorePlayer runs Jivelite on the framebuffer. Chromium on
Wayland under labwc is none of those.

---

## 12. Not described above (see the ADRs)

Areas the original architecture did not cover, decided since: updates over
the network - Debian packages from a signed repository and the updater's
units (ADR-0105, ADR-0107, ADR-0108, ADR-0110); first-boot setup over its own
access point (ADR-0031, ADR-0104; ADR-0128 proposed); the SMB pictures share
(ADR-0049); network settings (ADR-0123); problem reports and hardware
feedback (ADR-0125, ADR-0126). Ports: 8090 (the UI, REST and `/state`), 8091
(`/meter`), 9000 (LMS), 3678 (go-librespot, loopback).
