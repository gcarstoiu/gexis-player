# ADR-0037 — Transport commands: one route to the active renderer; controls visible when the renderer has them, disabled when they cannot work now

**Status:** Accepted
**Date:** 2026-09-16
**Raised by:** Phase 6 (now playing, full), plan agreed with George 2026-09-16
**Amends:** [0020](0020-library-browse-tree.md)'s unusable-controls rule — adds
the case of a control that exists and works here, but not *right now*.
Fills in [0013](0013-defaults-implement-public-contract.md)'s "control surface"
contract field and [0014](0014-nowplaying-and-peppy-are-distinct.md)'s
"hidden or greyed".

## Context

Now playing has drawn Previous, Play/Pause and Next since Phase 4, plus Shuffle
and Repeat for LMS, all disabled and marked `data-unwired="phase-6"`. The daemon
has never sent a transport command on a user's behalf: `Capabilities.controls`
is empty for Spotify and Bluetooth and holds only `activate` for LMS
(Phase 4 criterion 7).

Three things need settling before any of it is wired: where a command goes,
how the UI knows a button would work, and what it shows while it would not.

## Decision

### 1. One route, to the active renderer only

    POST /transport/{command}

| command | body | meaning |
|---|---|---|
| `play` | — | resume or start |
| `pause` | — | pause |
| `next` | — | next track |
| `previous` | — | the renderer's own previous (restart or go back is its call) |
| `shuffle` | `{"on": true\|false}` | set, not toggle |
| `repeat` | `{"mode": "off"\|"all"\|"one"}` | set, not toggle — three states (design data contract) |

- **Addressed to whoever is active**, never to a renderer by name. A command to
  a renderer that is not active would be an acquisition, and acquisition has
  one path already: arbitration, and for LMS the explicit
  `/renderer/lms/activate` (ADR-0010, ADR-0027). No active renderer → `409`.
- **Play and pause are separate commands**, not a toggle. The UI picks one from
  `metadata.transport`. A toggle sent twice by a double tap lands where it
  started; two `pause`s do not.
- **Answers:** `200` when the adapter has sent it, `409` when the active
  renderer does not declare the command or cannot take it right now, `502`
  when the renderer refused or was unreachable, `503` when unwired (the
  existing routes' convention).
- **The result is read from `/state`, not from the response.** A `200` means
  "sent", not "happened".

### 2. Capability in two layers

| layer | where | changes | example |
|---|---|---|---|
| **has** — what this renderer can ever do | `capabilities[id].controls` (static, exists) | never at runtime | LMS has `shuffle`; Spotify does not (design: "the other two renderers just hand us a stream") |
| **can now** — what works at this moment | `controls` on `/state`, for the active renderer | as the renderer reports | LMS playing a radio station (a one-item playlist): `next` is not available |

`controls` carries `available` (the commands that would work now) and the
current `shuffle` (bool) and `repeat` (`off`/`all`/`one`), each `null` when the
active renderer has no such thing. Names may still move while step 2 builds it;
the shape is the decision.

### 3. What the panel shows (George, 2026-09-16)

| the renderer… | the control is |
|---|---|
| does not have it | **hidden** |
| has it, and it works now | shown, enabled |
| has it, but it cannot work now | **shown, disabled** — never hidden |

George: *"If a capability is there for a renderer it should be visible at all
times unless it cannot work (like the next button) when it becomes disabled but
still visible."* This amends ADR-0020's rule, which had two branches (absent:
hide; present but not operable *here*: show and say where). The new case is
about *when*, not *where*: the control is operable on this panel, just not at
this moment, so there is nowhere else to point to and nothing to say.

A disabled button is not a dead button: it does not accept the press. What
ADR-0014 forbids is a button that looks usable and silently does nothing.

### 4. State shown is the state reported

Play/Pause, Shuffle and Repeat show what the renderer last reported, never what
the button was pressed to. Press feedback is the design's own CSS; the state
change follows when the renderer confirms it. A button that flipped on press
and flipped back when the renderer disagreed would show a state the user
cannot account for (ADR-0010, decisions/README.md).

### 5. What each renderer declares is measured, not assumed

`controls` for each built-in adapter is filled from a hardware finding, the
way ADR-0013 derives every contract field. **Measured 2026-09-16,
[Finding 028](../findings/028-transport-commands-on-three-renderers.md)** —
every command worked on all three:

| | play / pause | next | previous | shuffle / repeat | Next and Previous disabled when |
|---|---|---|---|---|---|
| LMS | `pause 1` / `pause 0` | `button jump_fwd` | `button jump_rew` (restarts, or goes back near the start — as LMS's apps do) | `playlist shuffle`, `playlist repeat` | the playlist holds one item (a radio station): both only restart the stream |
| Spotify | `/player/pause`, `/player/resume` | `/player/next` | `/player/prev` | not shown (design) | never: go-librespot reports no "has next" |
| Bluetooth | `Pause`, `Play` | `Next` | `Previous` | not shown (design) | never: track numbering is not sequential |

The Finding 014 risk did not occur: `/player/resume` *within* a live Spotify
session kept the phone connected (George watched). An LMS playlist has no end
for Next: it wraps even with repeat off.

A command that fails its measurement is not declared, and so is hidden — the
first row of §3. A command that works in general but not in some state
(a radio station on LMS) is declared and disabled in that state — the third.
George's own example, the end of a queue, does not arise on LMS, which wraps;
the rule stands for any renderer where it does.

## Consequences

- The panel's transport row becomes data-driven; the `lmsOnly` checks in
  `NowPlaying.svelte` are replaced by `capabilities[active].controls`.
- A plugin renderer (Phase 9) gets transport by declaring commands and
  reporting availability; nothing in the UI names a renderer.
- The mini strip's play/pause (Phase 7) uses the same route.
- A remote browser gets no transport: it renders settings only (ADR-0032).
- A skip from the panel is also a touch, so it already counts as attention for
  the Peppy screen (ADR-0036); nothing new is needed there.
- **Bluetooth reports a Previous late** (about 4 s, Finding 028): the progress
  bar keeps counting until the phone's report arrives. §4 applies; it is not
  masked.
