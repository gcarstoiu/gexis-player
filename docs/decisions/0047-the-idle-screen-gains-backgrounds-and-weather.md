# ADR-0047 — The idle screen gains backgrounds and weather

**Status:** **Accepted — George, 2026-09-21**, both providers chosen on
[Finding 043](../findings/043-the-idle-screens-two-providers.md): **Pixabay**
for wallpapers (*"Based on this and the pictures I am seeing on their website
we will go with pixabay"*) and **Open-Meteo** for weather, on his answer to
the one question that decided it — a Gexis is not sold. Built as Phase 9
subphase 9g.
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

### 2a. The providers, chosen 2026-09-21

**Wallpapers online is Pixabay.** Of the three stock services whose terms
permit this use, it was chosen on the pictures rather than on the terms.
What it imposes:

- **A key per owner**, which is what `wallpaper_key` already is. The row's
  note stops saying the service is unchosen.
- **Categories, not search terms.** George: *"We start with categories and
  see later if we need to add queries too. I think not though as it should be
  enough."* So `wallpaper_topics` offers Pixabay's own twenty and nothing of
  ours — no topic vocabulary, no mapping table, and no invented words to
  maintain. `space` and `landscape` are not categories; `nature` and
  `science` are what covers them, and that is a thing the sheet shows rather
  than a thing we translate.
- **One category per request, so the rotation is ours.** George: *"the photos
  should come randomly from all the categories, not be stuck in only one of
  the many."* Each refresh picks a category at random from those selected and
  a photo at random from that category's results. **Random per refresh, not
  round-robin**: a rotation that visits categories in order is predictable on
  a screen that is watched for hours, and with one category selected the two
  are identical anyway.
- **The device is the cache.** Pixabay forbids permanent hotlinking — *"If
  you intend to use the images, please download them to your server first"* —
  its URLs expire after 24 hours, and its terms require requests to be cached
  for 24 hours. So a wallpaper is fetched to disk and shown from there.
- `largeImageURL` is the size we get; `fullHDURL` and `imageURL` need
  approved full API access, which a per-owner key does not have.

**Weather is Open-Meteo, and `weather_key` is removed.** The design has a
`weather_key` row gating four others, on the assumption that a weather
provider needs a key. Open-Meteo does not. **A row that gates nothing and
stores nothing is worse than no row**, so:

- `weather_key` **leaves the registry** — the first deliberate deviation from
  the drop's literal since ADR-0022's amendment made it the point of truth,
  and it is recorded as one in the registry test rather than left to be
  noticed.
- The four rows that hung off `onlyWhen: ['weather_key', ANY]` —
  `weather_location`, `idle_days`, `idle_minmax`, `idle_icons` — **hang off
  `idle_weather` instead**, which is what the design meant by them: weather
  is on, so the things that shape it are visible.
- **`weather_location` is geocoded once**, through Open-Meteo's own key-free
  geocoding API, and the answer is held for as long as the daemon runs. It is
  **not** stored beside the setting: a coordinate in the database is state the
  registry does not know about, and a restart costs one 140 ms lookup.
  **A place that cannot be found and a geocoder that cannot be reached must
  not share a message** — the first tells the user to type something else, and
  saying that when the network is down sends them to fix a row that was
  already right.
- **Open-Meteo's free tier is non-commercial**, which is why George's answer
  was needed before this could be Accepted. *"Personal home automation
  purposes"* is a use its terms name; a Gexis that was sold would not be, and
  that would be every unit rather than one. **If that ever changes, MET
  Norway is the swap** — Finding 043 measures what it costs: a daily
  aggregation loop, an identifying User-Agent, honouring `Expires`.

### 2b. Two rows the design does not have

Both confirmed by George, 2026-09-21, and appended to ADR-0022's inventory.

- **`wallpaper_topics`** — which Pixabay categories to draw from. A `multi`,
  the mechanic [ADR-0044](0044-settings-row-vocabulary.md) §7 adds for it.
- **`wallpaper_interval`** — how often the picture changes. Nothing in the
  drop says, and a wallpaper that never changes is a wallpaper nobody chose.

### 2c. Attribution is a requirement, not a courtesy

Open-Meteo's licence asks for `Weather data by Open-Meteo.com` as a link
beside the data; Pixabay asks that users be shown where the images come from.
**The idle screen has nowhere to put either** — it is a clock over a picture.
This record does not settle where the credit goes; it settles that the screen
cannot ship without it.

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

- ~~**Which online wallpaper service, and whether it needs a key at all.**~~
  **Closed 2026-09-21: Pixabay, and yes** — a key per owner, which is what
  `wallpaper_key` was drawn as. See §2a and
  [Finding 043](../findings/043-the-idle-screens-two-providers.md).
- ~~**Which weather provider.**~~ **Closed 2026-09-21: Open-Meteo, key-free**,
  which is why `weather_key` is removed. The same method as Finding 030, and
  the same shape of answer: terms read, calls made from the device, a
  recommendation, George deciding.
  **The correction that mattered is recorded** — the first pass ruled out
  Unsplash and Pexels on a summary line and was wrong about both
  (`docs/LESSONS.md` case 12), and the weather re-check George then asked for
  retired three of its own arguments.
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
