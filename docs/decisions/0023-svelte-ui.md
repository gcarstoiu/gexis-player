# ADR-0023 — The UI is Svelte

**Status:** Accepted — **decision re-confirmed 2026-09-13 on different grounds**
**Date:** 2026-09-04
**Binds:** Phases 4–7
**Amended:** 2026-09-13 — the rationale below that ranked Svelte *above React*
is void, because [ADR-0026](0026-peppymeter-native-process-integration.md)
moved the thing it was about out of the browser. The conclusion survives on
new grounds. See "Re-confirmed, 2026-09-13" at the end.

## Context

One UI codebase serves the touchscreen at 1280x800 under Chromium kiosk and any
remote browser. It renders four screens, a generic SlimBrowse browser
(ADR-0020), and a skin renderer of stacked layers animating at 30 fps
(ADR-0015).

Candidates were Svelte, vanilla JavaScript, React and Vue.

## Decision

**Svelte.**

## Rationale

### The browse tree decides this

The SlimBrowse browser is the largest single piece of UI work in the project:
nodes of unknown shape, recursive rendering, in-place refresh on
`setSelectedIndex`, pagination over thousands of items, and scroll position to
preserve across all of it.

In Svelte that is a component rendering itself recursively, with keyed `{#each}`
handling reconciliation. In vanilla it is a hand-written keyed list reconciler —
create, update, remove, preserve scroll, cope with a node type never seen before
— written correctly, because subtly wrong reconciliation produces bugs that
surface only on particular navigation paths.

That is the difference between using a solved problem and solving it again.

### It does not compromise the skin renderer

The concern that pushed against frameworks was the skin renderer: stacked layers
where one changes per frame via CSS transform, GPU-composited, others untouched.
A virtual-DOM model works against that.

**Svelte has no virtual DOM.** It compiles to direct DOM updates, so a transform
on a needle is a transform on a needle. This is why Svelte ranked above React
here — React's rendering model is the worst fit of the four for a 30 fps
compositing renderer.

### It ships nothing at runtime

Svelte compiles ahead of time. The image serves static files, exactly as it
would with vanilla. There is no framework library in the payload.

## What this costs

**A build step.** `npm run build` in the image pipeline. That is the whole cost,
and it is the only advantage vanilla had — the output is static files either
way.

**A smaller corpus than React.** For a public repository hoping for
contributors, and for Claude Code working from examples, React's documentation
and example base is much larger. Svelte's is smaller but not thin. This is a
real if secondary cost and it is the strongest remaining argument against.

**A toolchain to keep current.** Minor, but non-zero on a device expected to run
untouched for years. Mitigated by the build being ahead-of-time: a stale
toolchain affects building a new image, not a running device.

## Rejected

**Vanilla JavaScript** was recorded as the decision in the first version of this
record and reversed. The reasoning for reversal: the three patterns proposed to
keep vanilla disciplined — a state store, a keyed list renderer, a
mount/update/unmount view contract — amount to building a small framework by
hand. Presented as a discipline measure, that list was really an admission of
the cost. Avoiding one build step is not worth hand-writing reconciliation for
the browse tree.

**React** ranked below vanilla for this application. Its rendering model is the
poorest fit for the skin renderer, and its main advantage over Svelte is social
rather than technical.

**Vue** offered nothing the others did not.

## Consequences

- The image build gains a Node build step. Node is already on the dev machine;
  the image pipeline needs it at build time, not at runtime.
- The browse tree remains the largest UI piece but is no longer the largest UI
  *risk*.
- Reactivity for the playback model is a store fed by the WebSocket. Views
  subscribe; nothing reads the socket directly.
- Chromium is pinned by the image, so no transpilation for browser
  compatibility is needed beyond what Svelte does itself.

## Re-confirmed, 2026-09-13 — and why the original reasoning no longer holds

George raised the right challenge while preparing Phase 4's designs: if the
design tool emits React components, wiring those directly would avoid a
translation step and the things lost in it. Checking that properly turned up
a stale record.

**What is void.** "It does not compromise the skin renderer" above is the
only argument that ranked Svelte over *React* specifically — everything else
in the Rationale argues Svelte over *vanilla*, and React answers those
equally well (recursive keyed lists are not a Svelte speciality). That
argument was about a 30 fps layered compositing renderer running in the
browser. [ADR-0026](0026-peppymeter-native-process-integration.md) moved the
Peppy screen to a **native PeppyMeter process** with labwc-mediated screen
ownership. ADR-0015 and ADR-0019 were both amended to point at that
reversal; this record was missed. So its decisive technical differentiator
has not been weakened — it no longer exists.

That also leaves "a smaller corpus than React", which this record already
called "the strongest remaining argument against", standing unopposed.

**Why Svelte survives anyway.** The design is delivered as `.dc.html`
artboards plus static PNG exports (George, 2026-09-13) — not as React
components. That decides it on the grounds that actually matter here:

- **There is no React structure to preserve.** The risk George was pointing
  at is real but specific: it is losing a component decomposition in
  translation. An HTML/CSS artboard has none to lose.
- **The fidelity-critical parts transfer verbatim either way.** Markup, CSS,
  tokens and CSS-expressed motion are copied, not re-derived, whichever
  framework wraps them. The framework only governs logic this project writes
  itself — and the largest piece of that, the browse tree, is ours
  regardless of the design.
- Switching would cost a runtime, a larger toolchain and an ADR, to solve a
  translation problem that does not arise for this deliverable.

**What would reopen it:** design delivered as structured React components.
The decision would then turn on preserving that decomposition, and the
reasoning above inverts. Recorded so the question is re-answered from the
evidence rather than re-argued from this record's original, now-void,
premise.

## Unverified

- Per-frame cost of the layered skin renderer at 1280x800 on a Pi 4, under any
  approach. **Largely moot for this record since ADR-0026** — the layered
  renderer is a native process now. It remains a live question for *that*
  record, not for the framework choice.
- Whether Svelte's compiled output loads without issue under Chromium's kiosk
  configuration, served from our own HTTP server. **Due in Phase 4b**, which
  builds exactly that path.
