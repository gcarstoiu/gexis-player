# ADR-0078 — The transition screen waits for the threshold

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0010](0010-arbitration-slot-model.md) (which set the 1 s
threshold and what it is for), [Finding 020](../findings/020-criterion8-takeover-gap-adr0027.md)
(the measured pairs), ADR-0022's inventory (`handoff_threshold`),
[ADR-0077](0077-a-source-that-is-off-is-not-running.md) (the same criterion,
the other rows)

## Context

`handoff_threshold` was the last row in Settings carrying a `?` — a decision
still owed — and George found it by its orange dot: *"the transition screen
threshold set at 1 (also inside this should be a selection bar with 0.5
increments up to 3s)"*.

The bar is not the question. A `number` row draws a slider as soon as it is
wired; unwired it falls through to a readonly value, which is exactly what he
was looking at. The question is what the number does once it is wired, because
ADR-0010 introduced it without ever reading it at runtime.

ADR-0010's rule is *show the transition screen unless the pair is measured
fast*, and **1 second** is where it put the line: "roughly where a gap stops
reading as *the next thing is starting* and starts reading as *something is
wrong*". The exemption is a published list, seeded from Finding 020 —
LMS ↔ Spotify at 224.6 / 335.2 ms medians — and `handoff_threshold` was the
number those medians were compared against **by hand, once, when the list was
written**. Nothing on the device has ever read it.

ADR-0022 files it as *evidence-gated rather than preference*, which is why it
stayed unwired while the rows around it were wired.

## Decision

**The threshold is how long a takeover has to be in flight before the panel
explains it.** The handoff screen is not drawn when the takeover starts; it is
drawn `handoff_threshold` seconds later, and a takeover that finishes first is
never announced at all.

- **`0` means immediately**, which is exactly the behaviour before this record.
  It is the bottom of the bar for that reason.
- The row is a **slider from 0 to 3 s in 0.5 s steps**, George's own shape.
- `handoff_exempt_pairs` **stays** and still skips the screen outright. It is a
  published measured fact (Phase 4 criterion 4 required it as *data, not a
  constant*) and a guarantee that does not depend on a clock.
- `handoff_duration` is unchanged: once the screen is shown, it is held for
  that long so it cannot flash.

## Rationale

### A delay is more evidence-driven than a list, not less

ADR-0010's worry was that somebody would declare a pair fast because they
preferred no screen. A delay removes the declaration entirely: **every
takeover earns its screen by actually taking longer than the line.** A pair
that is usually fast and slow this once gets the screen exactly when it is
needed, which a per-pair list cannot do.

And the quantity being compared is the right one. The screen's whole failure
mode is appearing and vanishing inside a few hundred milliseconds — ADR-0010
calls that "a flicker — noise, not information". What decides that is **how
long the screen would be up**, which is the takeover's own duration. Comparing
it against the threshold is comparing like with like.

### Rejected: measure each pair live and rebuild the exempt list

The faithful-looking reading of ADR-0010: have the supervisor time each
takeover, keep a median per pair, and publish the exemption from whether that
median sits under the row. It was designed and dropped for two reasons.

**The numbers are not comparable.** Finding 020 measured *audible silence*
through the spectrum FIFO — old audio stops, new audio starts. What the
supervisor can time is its own sequence: release ladder, volume restore, retry.
Those are different quantities, and seeding a live measurement store with
Finding 020's medians would have compared one against the other while looking
entirely reasonable. That is the mistake `docs/LESSONS.md` exists for.

**And it is worse at the job.** A per-pair median cannot know that *this*
takeover is slow, which is the only thing the user is waiting on. It also
means the first takeover of every pair after a boot is unmeasured and
therefore announced, so a fast pair flickers once per boot by design.

### Rejected: leave it unwired and delete the row

Considered, because ADR-0022 calls it evidence rather than preference and an
honest answer to "this row does nothing" is to remove it. Rejected because
the preference is real and separable: measurement decides how long a takeover
took, and the person decides how long a wait deserves an explanation. Those
are different questions and the second one is George's.

## Consequences

- **For LMS ↔ Spotify, nothing changes.** The pair is exempt by list and never
  reaches the timer.
- **A Bluetooth takeover is announced 1 s later than it was.** Its measured
  release is 2.5–2.9 s, so the screen still appears — at 1 s in rather than at
  0. That is the point of the threshold, and `0` restores the old behaviour
  exactly.
- A takeover whose duration straddles the threshold shows the screen for a
  moment at the end of the handoff rather than not at all. `handoff_duration`
  already holds the screen past the handoff's end, so this is the existing
  shape of the animation, not a new one.

## What this does not settle

- ~~**Whether `handoff_exempt_pairs` should survive at all.**~~ **Parked
  2026-09-25**, George: *"handoff exempt we park for now."* With a working
  threshold it changes no outcome today: both its pairs are far under any value
  the bar offers. It stays because it is measured evidence and because removing
  published state is Phase 4 criterion 4's business, not this record's — and
  now because nothing is waiting on the answer.
