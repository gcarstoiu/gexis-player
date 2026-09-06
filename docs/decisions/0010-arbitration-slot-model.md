# ADR-0010 — Arbitration: base slot, connection acquisition, uniform disconnect

**Status:** Accepted
**Date:** 2026-09-04
**Amended:** 2026-09-04 — the silence rule was restated. See "Rules" below.
**Answers:** ADR-0004 (one active renderer — semantics were left open)

## Context

One renderer plays at a time. No dmix. The question was what "one at a time"
means in practice: how a renderer takes the device, what happens to the one it
takes it from, and what happens when it lets go.

This model went through four revisions during design. The rejected versions are
recorded below because they will look reasonable again later and the reasons
they were dropped will not be obvious.

## Decision

### Slot model

**Base slot + active slot. Not a stack. No history.**

- **Base slot** is permanently LMS. Squeezelite's connection to the server is
  structural, not a user session.
- **Active slot** holds at most one other renderer.
- Release empties the active slot; the base becomes current. Nothing is
  restored, because nothing was stored.

### Acquisition — on connection

Connection is a deliberate user act, so the user owns the consequence. Connect
events are also D-Bus signals and API state changes, which are more reliable
than hooking stream starts.

Each adapter declares its acquisition events:

| Renderer | Acquisition |
|---|---|
| LMS | explicit play or resume — no connect event exists, it is always connected |
| Spotify Connect | device selected in the app |
| Bluetooth | A2DP profile connect |
| Qobuz Connect | device selected in the app |

### Release — disconnect, uniformly

**Takeover disconnects the outgoing renderer. LMS is the only exception and
pauses instead, because it is the base.**

| Renderer | On losing the device |
|---|---|
| LMS | pause, stay connected |
| Bluetooth | disconnect |
| Spotify Connect | disconnect |
| Qobuz Connect | disconnect |

### Rules

- **No auto-resume.** Release never starts playback. Release of the active slot
  leaves LMS current but not playing, which means the idle screen.
- **Takeover acts through the outgoing renderer's control channel.** Blocking
  the audio path is not sufficient — the source would still show "playing" into
  a silent room. Adapters must disconnect or pause on demand and report success
  or failure.
- **Never show a state the user cannot account for.** This is the rule that
  matters, and it is broader than the wording it replaces.

  The failure it exists to prevent is specific: the system believes it is
  playing, the room is silent, and the user has no way to understand why.
  Handoff is therefore a displayed state, and a renderer must not lose the
  device without its source being told.

  It is **not** a prohibition on silence. Several legitimate states are silent
  while playing, and all of them pass because the user caused them, they are
  displayed, and they are reversible by the same action:

  - **Mute** (ADR-0018) — user-initiated, indicated, one action to undo
  - **Fixed output into a powered-down amplifier** — nothing we can detect, and
    nothing the user needs told
  - **Volume at minimum** — self-evident from the control

  The earlier wording — "never show playing while silent" — would have required
  an exception for each of these, and the list would keep growing. The rule is
  about accountability, not about silence.

### LMS power state

Power on/off in the LMS interface plays no role in arbitration. A powered-off
player is one that will not play; it neither acquires nor releases. If someone
presses play on a powered-off player, LMS powers it on and starts — still play,
still acquisition, no special case.

Our UI shows nothing special for a player powered off in LMS. It is not a state
a person standing in front of the device can act on. Power state matters for
multiroom sync groups, which is LMS's concern.

## Rejected alternatives

### Stack ordered by connection time

Considered so that releasing Bluetooth would return to a still-connected
Spotify rather than to LMS.

Rejected because **stack order is invisible state.** The user cannot see it, so
cannot predict it. A Spotify session connected an hour ago and forgotten should
not win the device back because Bluetooth dropped. The slot model always returns
to one known place.

### Acquisition on stream start rather than connection

Rejected on the grounds that connection is the deliberate act and stream-start
detection is mechanically fiddlier.

Accepted cost: A2DP connect does not open the PCM, so a phone can connect and
send nothing. **This makes a UI requirement non-optional:** the screen must say
"Bluetooth connected — waiting for audio", not show an empty now-playing.

### Pausing Bluetooth via AVRCP instead of disconnecting

Designed in full and then rejected. The intent was to avoid tearing down the
A2DP profile link, since on some phones an unexpected disconnect bounces audio
to the phone's own speaker.

It fails because **no signal available to us distinguishes deliberate playback
from incidental audio.** If a paused-but-connected phone reacquires on stream
start, then a notification chirp, an autoplaying video in a feed, or a
navigation prompt all count as acquisition. Music stops because someone scrolled
past a video. That is routine, not an edge case.

Three fixes were examined and none works:

- **Duration threshold** — delays every legitimate start and does not help with
  a long autoplaying video.
- **Signal level** — notification sounds are often loud. No separation.
- **App identity** — A2DP does not carry it. AVRCP session state does not
  reliably reflect where audio is going: a phone that has handed Spotify
  playback to our Connect renderer may still report "playing", because Spotify
  *is* playing, just elsewhere. Treating that as acquisition ping-pongs the
  device.

The speaker-bounce objection is largely addressed by pausing before
disconnecting, so it does not outweigh the notification problem.

## Consequences

- The supervisor is simple: it receives "renderer X wants the device" and
  applies one policy. Per-renderer weirdness lives in adapters.
- Disconnect is self-explaining. The phone shows the device gone rather than
  showing "playing" into silence. No invisible state anywhere.
- **Cost:** Bluetooth reacquisition requires reconnecting from the phone. This
  is mitigated in the UI, not the audio layer — the idle and now-playing screens
  list recently-connected devices and can initiate an inbound connection, which
  BlueZ supports for trusted devices. **Unverified:** how reliably a phone that
  has moved on accepts it.

## Implementation note

Squeezelite holds the ALSA device open by default. `-C <seconds>` makes it close
after idle, which is part of how release is implemented, not a tuning option.

**Amended, 2026-09-06, measured on `gexis`:** `-C` alone is not fast
enough for a takeover. A commanded LMS pause does not make squeezelite
release the device any faster than `-C`'s own idle timer — measured
~8.5s from an LMS CLI pause to the ALSA device actually freeing, against
`-C 10`. That is well past what a user tolerates as a takeover gap.
Contrast go-librespot, which frees the device in under 100ms via its own
`/player/stop`. One shared release mechanism cannot serve both
renderers. **Decision (George):** the supervisor does not wait out `-C`
during a takeover — it sends the LMS pause as a courtesy (so LMS's own
state reflects "paused," not "disconnected," consistent with this
record's release table) and then drives squeezelite's release actively,
escalating straight to `SIGTERM` with no polite-grace wait
(`LmsAdapter.release_ladder`, `core/src/gexis_core/adapters/lms.py`).
`-C 10` still governs the *non-arbitration* idle case (LMS stops on its
own, nothing else wants the device) — only the takeover path bypasses
it.

## Open

- **Sync group interaction — deferred, but no longer only theoretical.**
  Squeezelite stays in its LMS group while another renderer holds the
  device, so a group play command becomes an acquisition that
  interrupts. Consistent with the rule, possibly surprising. Unverified
  how LMS handles a member that goes silent mid-group. **Criterion 3
  (Phase 2b) ships without resolving this** — a decision, not an
  oversight; see `docs/DEVELOPMENT.md`. **Sharper as of 2026-09-06:**
  the LMS release mechanism is now `SIGTERM` on squeezelite (see the
  Implementation note below), not just a device going silent — the
  process itself dies and restarts (`Restart=on-failure`), dropping out
  of its LMS sync group on the way rather than merely pausing within it.
  Measured on hardware, not inferred. May need un-deferring before this
  ships further than Phase 2b — George's call.
- **Empty base slot — deferred.** Valid if run headless with no LMS.
  Undefined behaviour. **Criterion 3 (Phase 2b) ships without resolving
  this** — a decision, not an oversight; see `docs/DEVELOPMENT.md`.
- **Takeover gap — not deferred, scheduled.** Unmeasured, same-rate and
  cross-rate. This is Phase 2c, criteria 8-10 — active work, not a
  deferral.
