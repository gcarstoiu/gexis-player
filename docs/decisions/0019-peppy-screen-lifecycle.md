# ADR-0019 — Peppy screen: entry, exit and lifecycle

**Status:** Accepted
**Date:** 2026-09-04
**Relates to:** ADR-0014 (distinct screens), ADR-0015 (skin format), ADR-0010
(arbitration and the accountability rule)

## Context

ADR-0014 settled that the Peppy screen is display-only and capability-blind:
metadata plus levels, identical regardless of what is playing. ADR-0015 settled
what it renders.

What is not settled is its behaviour as a screen — how it is entered, how it is
left, and what it does when the world changes underneath it.

The Must requirement is that switching to it has **no visible render-in delay**.
That is an implementation constraint on everything below: the screen is
pre-rendered and hidden, never constructed on demand.

## Settled

### Entry

Two paths, both already in the display model:

- **Explicit** — a button on the now-playing screen
- **Implicit** — idle timeout while playing

It is never entered when nothing is playing. That state belongs to the idle
screen.

### Pre-rendering

Skin assets are decoded and layered at load, not at entry. Entry is a visibility
change on an already-composited set of layers.

This is what makes the no-delay requirement achievable and it is the reason the
renderer is in the browser rather than a separate process (ADR-0014): there is
no process to start and no compositor handoff.

### Playback stops while displayed — five-minute grace

The Peppy screen **remains** for five minutes after playback stops, then the
idle screen takes over.

Not an immediate exit. A stopped or paused system that still shows the last
track with meters at rest reads like a hi-fi at rest, not like a fault. Five
minutes is long enough to cover a pause and short enough that an abandoned
device does not sit on a static screen.

The five-minute value is configurable; this is the default.

---

## Resolved

### Exit is touch. There are no controls.

**The Peppy screen is purely visual and carries no controls of any kind.** Touch
anywhere exits to now playing. To change track or volume, the user goes to now
playing.

The transient-transport-overlay option was rejected. It would have saved a tap
when skipping a track, at the cost of a hidden gesture nothing advertises, and
it would have made "display-only" a claim with an exception attached. The screen
either has controls or it does not.

This matches PeppyMeter's own `exit.on.touch` convention.

### Idle timeout is reset by local touch only

Nothing else resets it. Not a remote browser interacting, not a track change,
not a volume change from a phone.

*Rationale:* every one of those is somebody interacting with something other
than this screen. A track change resetting the timer would mean a device playing
an album never reaches the Peppy screen at all.

### Skin rotates per track

A new skin is selected on each track change.

The user chooses **which corpus** to draw from — meter-only, or meter+spectrum —
as a setting. Within the chosen corpus, selection rotates.

#### Consequence: pre-rendering is not a one-time cost

ADR-0014 and the no-render-delay requirement assumed a pre-composited layer
stack. Rotation makes that a per-track operation: each track change swaps the
entire stack, including a full-screen JPG background.

The renderer therefore **decodes and composites the next track's skin while the
current one is displayed.** Loading all 84 skins is not viable; loading one
lazily at track change would produce exactly the visible construction the
requirement forbids.

This also means skin selection for a track must be decided at track start, not
at the moment of display, so that entering the Peppy screen mid-track shows the
skin already prepared for that track.

### Bluetooth shows the codec, not a rate

The sample rate field carries the codec name — "SBC", "AAC" — rather than the
A2DP decode rate.

*Rationale:* the decode rate is the codec's, not the source's. "44.1 kHz" beside
a lossy stream is true and misleading at once. The codec is the most informative
thing actually available.

If the field cannot carry text, it does not render, per ADR-0015.

### The panel does not sleep

No blanking, no backlight timeout. The device is powered down at night by an
external trigger, outside our control and outside our concern.

#### The idle screen loads an external URL

The idle screen displays a **user-configured external URL, lazy loaded**. We
render it; we do not generate it. Imagery, rotation logic and content are
entirely outside this implementation.

*Rationale:* it keeps the idle screen trivial to build and gives the user
unlimited freedom over what it shows, at the cost of us controlling nothing
about it.

**Consequence for burn-in: the mitigation is delegated, not solved.** Burn-in
protection now depends on whether the configured page changes what it displays.
A user who points it at a static page will have a static screen for hours. That
is their choice, but it should be stated in the documentation rather than
discovered.

Two cases the implementation must handle and which nothing else specifies:

- **The URL is unreachable** — no network, page down, typo. The idle screen
  cannot simply be blank white, and it cannot be an error page.
- **No URL is configured** — the out-of-box state.

A minimal built-in fallback is therefore required regardless of how simple the
external path is.

### Renderer takeover exits to now playing, and the timeout brings it back

**A renderer change while the Peppy screen is displayed exits to now playing.
The idle timeout then runs normally and returns to the Peppy screen after the
configured period without touch.**

#### The problem this solves

ADR-0010 requires that the user never sees a state they cannot account for, and
names handoff as a displayed state. The Peppy screen has nowhere to display it:
no controls, no status area, no overlays.

Without this rule: someone is watching the meters on LMS playback. Another
person in the house selects the device in Spotify. The needles keep swinging,
the track name changes, different music plays, and nothing says why.

#### Why this resolution

- **The handoff appears on the screen designed to show it.** No exception to
  ADR-0010 is needed, and ADR-0010 does not need amending.
- **No overlay is introduced.** The decision that this screen is purely visual
  survives intact. A transient banner was considered and rejected on exactly
  this ground.
- **The disruption is bounded and self-healing.** The user is not stranded on
  now playing; the existing idle timeout returns them. No new machinery — it is
  the same timer, restarted.

#### A property worth noting

The Peppy screen has no controls, so **a renderer change while it is displayed
is by definition externally caused.** There is no case where this rule
interrupts something the user did themselves from this screen.

#### Cost, accepted

Someone else's phone takes the display away from a person watching it. Mitigated
by automatic return, and preferable to leaving that person with an unexplained
change.

## Raised, needing its own record

**A settings section in the UI.** Confirmed as required, and not only for
display settings. It must expose fixed versus variable output (ADR-0018), skin
corpus and idle timeout (this record), and further values as they accumulate.

That is a screen and an information architecture, not a paragraph. It needs its
own ADR, and the list of settings should be assembled from the records rather
than invented.

**Whether the Peppy screen is available on remote browsers.** ADR-0014 makes it
possible, since the renderer is in the browser, but no requirement asks for it.

## Unverified

- Perceived latency of a visibility switch on an already-composited layer stack
  at 1280x800 on a Pi 4. The no-delay requirement is assumed achievable by
  construction; it has not been measured.
