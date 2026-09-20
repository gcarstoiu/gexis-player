# ADR-0047 — The idle screen gains backgrounds and weather

**Status:** Proposed — the shape follows from the design being the point of
truth ([ADR-0022](0022-settings.md)'s 2026-09-20 amendment), but **two
third-party providers are unchosen and that is the substance of it**.
Scheduled as Phase 9 subphase 9g.
**Date:** 2026-09-20
**Raised by:** the 2026-09-20 design drop, diffed against the device in
[Finding 042](../findings/042-the-device-against-the-new-design.md)
**Amends:** [ADR-0033](0033-idle-and-home.md) — which resolved *what the idle
screen shows* as the external page, with the clock as fallback
**Relates to:** [ADR-0019](0019-peppy-screen-lifecycle.md) (the panel never
blanks), [ADR-0044](0044-settings-row-vocabulary.md) (`onlyWhen`, which every
row below depends on), [Finding 030](../findings/030-free-enrichment-providers.md)
(the same shape of question, already answered once)

## Context

**What the device does today**, read from `IdleScreen.svelte` rather than from
any record: a clock that moves position every minute so the panel does not
burn in, over black, with an embedded external page when `/idle` reports one
is configured and embeddable. 115 lines. That is all of it.

ADR-0033 resolved the question deliberately and narrowly — *"the external
page, per ADR-0019. The design's drifting clock is the fallback."* The new
design keeps both and makes them two choices among several.

## Decision

**`idle_screen` chooses between the panel's own idle screen and an external
URL. When it is the panel's own, `idle_background` chooses what is behind the
clock.**

### 1. Four backgrounds

| `idle_background` | source |
|---|---|
| Artist pictures | the library's own artist images |
| Wallpapers online | a third-party service, keyed by `wallpaper_key` |
| Wallpapers on device | local storage |
| Black | what it does today |

**`idle_screen: External URL` replaces all of it** with that page — which is
ADR-0033's resolution, kept, demoted from the answer to one option.

### 2. Weather is off unless a key exists

`idle_weather` turns it on; `weather_key` is what makes it work. The four rows
that *shape* a forecast — `weather_location`, `idle_days`, `idle_minmax`,
`idle_icons` — are `onlyWhen: ['weather_key', ANY]`.

**Without a key the idle screen shows the clock alone**, so rows that shape a
forecast have nothing to shape and are not drawn. `wallpaper_key` is revealed
the same way, only when *Wallpapers online* is chosen.

This is why the subphase cannot precede ADR-0044: **every row here is
conditional**, and building them against a registry with no `onlyWhen` would
mean building them twice.

### 3. The timeout is counted from when playback stops

Already true of ADR-0033's definition — idle is *not playing and not touched*.
The design states it explicitly and merges the old separate grace period into
`idle_timeout`, which is one of the six rows already wired.

## Consequences

- **The panel acquires two network dependencies it has never had**, both
  optional, both keyed, and both on a device that ADR-0031 intends to work
  without a network at first boot. The idle screen must degrade to the clock
  when either is unreachable, and that path has to be built rather than
  assumed — the same rule the artist page follows: **the region blanks, never
  the screen**.
- **Two more API keys on a surface reachable from the phone**, joining
  `listenbrainz_token` and `fanart_key`. `secret: true` masks them; ADR-0028's
  unauthenticated-on-the-LAN stance is unchanged and is the thing that makes
  this worth naming.
- **Local wallpapers need somewhere to live** — a directory, and a decision
  about who puts files in it on an appliance with no file manager.
- **Artist pictures come from the library**, so that background is the only
  one that needs no network and no key, and it is the obvious default.

## Open — and this is most of the record

- **Which online wallpaper service, and whether it needs a key at all.** The
  drop lists this as open in its own words. `wallpaper_key` exists so that the
  answer can be "yes"; it is not evidence that it is.
- **Which weather provider.** Finding 030 answered exactly this shape of
  question for enrichment by comparing free providers and recommending a
  key-free combination without deciding it. **The same method applies and the
  work is not done.** George, 2026-09-20, on the open questions generally:
  *"The open questions you mentioned will be handled as part of the work when
  it comes."*
- **Where on-device wallpapers live**, and how they get there.
- **What the three icon sets are** (`idle_icons`: solid, duotone, neon) and
  whether they are drawn in CSS like every other glyph on this panel, which
  has no icon font.
- **Whether artist pictures on the idle screen should avoid the artist
  currently playing**, or prefer them. Not asked by the design.

## Alternatives considered

- **Keep ADR-0033's answer and add nothing.** Rejected: the design carries all
  four backgrounds and the weather stack, and ADR-0022's amendment makes the
  design the point of truth for what the screen offers.
- **Build the backgrounds now and the weather later.** Tempting, and the two
  are genuinely separable — but both are `onlyWhen` rows and both are in the
  same subphase, so splitting them would mean touching the same screen twice
  for no gain.
- **Ship a provider choice inside this record.** Rejected as premature: the
  enrichment precedent is that provider comparison is a finding with measured
  results, not an assertion in an ADR.
