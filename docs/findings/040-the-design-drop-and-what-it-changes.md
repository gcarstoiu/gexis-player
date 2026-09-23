# Finding 040 — The 2026-09-19 design drop, and what it actually changes

**Date:** 2026-09-20
**Question:** George: *"have you thoroughly checked the new design screen by
screen? … I suggest you really check the designs, do not just skim them
through. There were also some things that were not implemented from the first
round so let's be thorough."*
**Scope:** the full `design/` package delivered 2026-09-19, diffed against the
package in this repository and against the shipped `ui/src`. Nothing here was
built; this is the input to that work.
**Status of this record:** reviewed by George, whose corrections are inline
below and are **the authoritative reading** wherever they differ.

## Why this needed a second pass

The first review was a skim, and George said so. The two `.dc.html` files
carry **2,461 lines of diff** between them and hold every screen — `screens.md`
says all of them except Settings live in `Now Playing.dc.html` — and neither
had been opened. Almost everything of substance was in those two files.

**The correction that matters most for anyone reading this later:** a first
pass classified a group of changes as *new in the drop* when they are the
opposite — **they are changes we made on the panel, which Claude Design has
now folded back into the designs.** The drop is partly a catch-up with
reality, and reading it as all-new invents work that is already done.

## George's corrections, verbatim in substance

| # | first reading | George |
|---|---|---|
| 1 | "two new secrets" | *"there is only one more API key for weather. What is the other?"* — the second is `wallpaper_key`, for the online wallpaper service. The drop itself says the service is unchosen and may not need a key at all, so **one new secret is certain, the second is conditional** |
| 2 | play counts and last-played "nobody has asked LMS for" | *"LMS provides both directly"* — the gap is in our queries, not in the data |
| 3 | real text input "supersedes ADR-0029" | *"this i've mentioned already several times. No difference between panel and phone. If the user wants to change anything on the panel he needs a keyboard"* — settled policy, not a new position |
| 4 | bio More/Less "new" | **ours**, 2026-09-18; the design caught up |
| 5 | credit lines under bio and lyrics "new" | **ours** (ADR-0040 §4); the design caught up |
| 6 | station counts and Podcasts gone "new" | **ours** (ADR-0038 §8); the design caught up |
| 7 | playlist creation removed "new" | **ours**, George's call during Phase 7; the design caught up |
| 8 | 67 elements press with `scale(0.95)` "new" | **ours** in origin — *"maybe though not for all elements"*. The drop extends it to elements we never touched |
| 9 | similar artists are dead chips | *"are they navigable now on the panel? same question on the genre and tag chips"* — **answered below** |
| 10 | Lyrics tab duplicates the Track tab | *"they are different. Track contains a smaller lyrics section while the lyrics tab is longer"* — **both true, see below** |
| 11 | Back from a New Music album goes to the root | *"no it does not. it goes to artist"* — **unresolved, see below** |
| 12 | Lyrics tab dim state missing | *"there is no dim state"* — dropped |
| 13 | paused artwork veil missing | *"there is no veil"* — dropped |

### On 9 — no, neither is navigable

Similar-artist chips are inert `<span>`s in both places:
`ui/src/screens/Library.svelte:1037` and
`ui/src/screens/NowPlaying.svelte:397`. No handler, no photo. The same finding
came out of the Phase 9 criterion-2 audit independently. `openArtistByName()`
already exists (`Library.svelte:241`), so wiring them is one line each.

**Genre and tag chips do not exist at all** — not in the UI, and there is no
`tags` field anywhere in `Enrichment` (`core/src/gexis_core/enrichment.py`).
Building them needs a provider field first.

### On 10 — they look different; they show the same five lines

Both are correct, which is why this is worth writing down rather than
resolving one way. Measured: the Track tab and the Lyrics tab both render
`window5` — `NowPlaying.svelte:230` and `:281` — which is **exactly five
lines** either way. The difference is styling: Track adds `lyrics--fill` and
smaller type, the tab renders larger and taller. So the tab *is* longer, as
George says, and shows *no more of the song*, as the audit says.

The design's Lyrics tab is a different thing again: the **whole song**,
rendered and translated to follow the playhead
(`Now Playing.dc.html:1869-1918`). Whether we want that is George's call and
is not assumed here.

### On 11 — the code disagrees, and hardware decides

`Library.svelte:670` opens a New Music album with an **empty** parent path,
`openAlbum(tile.id, tile.title, [])`, and `back()` pops that single entry,
clears `album` and lands on the library root (`Library.svelte:521-536`). From
a discography the path *is* passed (`:1015`), so Back correctly reaches the
artist there.

George reports it reaching the artist from New Music too. **One tap on the
panel settles it**, and this record should be corrected by whichever answer
that gives rather than by argument.

## What is genuinely new in the drop

With the corrections above applied, the new material is:

**Needs a record before implementation**

- **Pairing confirmation screen** — six-digit code at 72px, Accept / Reject,
  a real 30s countdown and four end states. Makes `bt_pairing` default to
  "Confirmation required", which reverses [ADR-0024](../decisions/0024-bluetooth-pairing-no-pin.md).
- **The idle screen rebuilt** — photographic background with a text contour, a
  date line, and a weather band with a 3-5 day forecast in three icon styles.
- **Weather and wallpaper settings** — nine keys, one certain new secret
  (`weather_key`) and one conditional (`wallpaper_key`).
- **Home strip variants** — most-played and recently-played artists. LMS holds
  both; our library queries do not ask for them.
- **Settings gains five mechanics** — a `list` row type (Wi-Fi with signal
  bars and a join flow, LMS discovery, Bluetooth forget), `warn` on a choice
  option, `onlyWhen` conditional visibility with an `ANY` sentinel,
  `optionsFrom` derived options, and a full-screen picker for the 84 skins.

**Decisions, no new machinery**

Add to queue on the album page (verified new: no `onQueueAlbum` in the old
design) · discography becomes a wrapping grid instead of a horizontal
scroller · Release tab hides unknown chips and specs rather than drawing "—" ·
Radio becomes a two-up grid · Now Playing follows the queue rather than a
static track.

**Restyling**

Source pill loses its ground · amber "unconfirmed" dots gone everywhere ·
seven list rows lose press feedback entirely · the `rgbaa(...)` typo in four
library cards is fixed as a side effect.

## Font sizes, measured

| element | old | new |
|---|---|---|
| meta tabs | 13px | 17px |
| source word, top right | 13px/700 | 17px/600, mono |
| mini-strip source word | 12px | 21px (icon 15 → 28) |
| Track tab, no lyrics: title / artist / album / year | 58 / 29 / 19 / 16 | 38 / 25 / 22 / 19 |
| Track tab, with lyrics: artist / album / year | 22 / 17 / 15 | 25 / 22 / 19 |
| lyrics: compact / synced / unsynced | 22 / 27 / 21 | 28 / 31 / 24 |
| waiting-service discs / icons | 58px / 24px | 90px / 38px |

`tokens.css` gains only two values: `--ink-tab-off` (0.50 alpha, for the
unselected 17px tab) and `--track-wide` (0.16em). The new alpha measures
**4.64:1** on `--bg-base` — it clears the package's own 4.5:1 floor by 0.14.

## Settings inventory

**21 keys removed, 20 added**, 51 → 50 rows, counted from the file rather than
taken from the prose. The `system` category disappears entirely; `version` and
a new `reboot` move into Device.

## Designed and never built

Seventeen items, after dropping the two George says do not exist (the Lyrics
tab's dim state and the paused artwork veil).

**Missing features**

1. **Fixed output mode does not exist.** No Fixed row, no padlock on either
   volume trigger, no fixed/variable field in `/state`. The design is explicit
   that a fixed device must *hide* the slider - *"a slider would be a lie"* -
   and the code does what that forbids: `disabled={!volume}`
   (`NowPlaying.svelte:463`, `MiniStrip.svelte:86`). The oldest unbuilt
   decision in the project ([ADR-0018](../decisions/0018-volume-and-output-modes.md)).
2. **No long-press anywhere in the library** - zero handlers in
   `Library.svelte`. The design calls it *"the universal fallback"*: artist
   cards and radio folders navigate on tap, so without it they can never be
   played, queued or added from where they are drawn.
3. **The artist page has no offline state and no Retry.** The code computes
   `state: 'error'` (`Library.svelte:286`) and never branches on it, so a
   failed lookup is indistinguishable from an artist nobody has written about.
   Now playing's Artist tab does have it.
4. **Similar artists are dead chips** - see George's question 9 above.
5. **Genre/tag chips** - absent, and no field to build them from.

**Visibly incomplete**

6. **The Lyrics tab shows the same five lines as the Track tab** - see 10.
7. **Radio glyphs** - two untinted shapes where the design has ten tinted per
   category, and no category field from the core to key off.

**Small omissions**

Radio station count on the root card · artist album counts in Browse and in
the grid · Popular and Similar pending skeletons · Popular row actions ·
Back from a New Music album (see 11) · station artwork · the album year on the
Track panel, where the code comment claiming it is unpublished is now stale ·
the Release format chip.

**Eight need a data field before they can be built at all**, which makes them
core work rather than UI work.

## Problems in the drop itself

For Claude Design, and already with George:

- `settings.md` says "54 rows, 6 wired"; the file has **50**.
- `travel_curve`'s note still explains dB-linear travel under a Perceptual
  default.
- The "Still undecided" table lists three rows that no longer exist.
- `.srcpill` carries a mono face in the `.dc` source but not in
  `now-playing.css`.
- `homeStripCount` is read but never declared as a prop.
- The Motion table still specifies the library cross-fade that was removed
  because it blinked through the shared backdrop.
- **The drop reverts `design/fonts/`** - its README again says "someone must
  add four files", because it was built before that commit.

## What this finding does not say

- **Nothing here was built or landed.** `design/` in this repository is still
  the previous package.
- **The three ADRs it calls for were written after it** and are the place
  those decisions live; this record is the survey, not the decision.
- **No screen was compared on hardware.** Every claim about the shipped UI is
  from the source, which is how item 11 came to be disputed.

---

# Appendix — the diff itself

**Why this is here.** Everything above is a conclusion. This is the evidence
it was drawn from, recorded because the next session has to compare a
*revised* drop against this one, and re-deriving 2,461 lines of diff to do
that would be a day's work repeated.

Sizes, for scale: `Now Playing.dc.html` 2614 → 2967 lines (1585 diff lines);
`Settings.dc.html` 422 → 886 (876); `settings.md` 96 → 258 (236);
`data-contract.md` (95); `README.md` (126); `now-playing.css` (93);
`screens.md` (73); `now-playing.html` (20); `tokens.css` (18).
`now-playing.js`, `geometry.json`, `fonts.css`, `source/support.js` and every
asset are **byte-identical**.

## A. Settings — every key that moved

Counted from the files, not from the prose. **51 → 50 keyed rows.**

**Removed (21):** `api_loopback`, `backup`, `boot_default_scope`,
`brightness`, `confidence`, `factory_reset`, `idle_close`, `idle_grace`,
`image_build`, `lms_player`, `log_level`, `plugins`, `power`,
`release_ladder`, `restore_floor`, `seek_reanchor`, `spotify_name`, `theme`,
`time_display`, `updates`, `volume_managed`.

**Added (19, plus one synthetic):** `drawer_autohide`, `drawer_on_external`,
`fanart_key`, `handoff_duration`, `home_strip`, `home_strip_count`,
`idle_background`, `idle_days`, `idle_icons`, `idle_minmax`, `idle_screen`,
`idle_weather`, `listenbrainz_token`, `reboot`, `skin`, `viz_stop`,
`wallpaper_key`, `weather_key`, `weather_location`. (`wifi_pass_<ssid>` is
synthesised at runtime by the Wi-Fi join flow, not a registry row.)

**The `system` category is gone**; `version` and the new `reboot` move into
Device. Group separators 6 → 7: a new **Home screen** group in Display.

**Type changes — three rows become `list`:** `lms_server` (was `text`, gains
`kind: 'server'`, `discover`, `manual`), `bt_trusted` (was `action`),
`wifi` (was `action`, gains signal bars and the join flow).

**Value, unit and range changes:**

| key | was | now |
|---|---|---|
| `boot_volume` | −90 dB, −90…−20 | **60%**, 0…100 |
| `max_ceiling` | Not set, dB, −60…0, `R?` | **100%**, 0…100, `R` |
| `travel_curve` | default dB-linear, `N?` | **Perceptual**, `N` |
| `handoff_threshold` | 0…5 | 0.5…4, step 0.5, `onlyWhen show_transition` |
| `viz_timeout` | 30 s, 0…300 s | **10 min**, 1…60 min |
| `bt_pairing` | PIN-free | **Confirmation required** (options reordered) |
| `bt_discoverable` | 3 min after boot | **Always** |
| `timezone` | 3 literal options | two-step picker, 7 regions / 43 zones |
| `idle_url` | always shown | `onlyWhen idle_screen = External URL` |
| `show_transition` | Display › Panel | **moved to Handoff** |

**11 rows carry `onlyWhen`.** At shipped defaults 7 of the 21 Display rows
are hidden.

## B. The five new mechanics, concretely

- **`list`** — 66px item rows. Wi-Fi items: 4 signal bars (6/10/14/18px),
  a lock glyph when secured, a `Forget` button (44px, amber
  `rgba(224,167,88,0.14)`), joined items tinted `rgba(126,214,188,0.12)`.
  Empty state is a 58px dashed circle plus copy. `discover: true` shows a
  searching spinner for 2200ms and **withholds the empty state while
  scanning** — "no servers found" is not true while still looking.
- **Wi-Fi join** — a state machine (`connecting`/`ok`/`error`), 1800ms to
  resolve then 1400ms before auto-close, a 64px status disc, and **Give up /
  Try again** on failure with the password retained. Mock rule: under 8
  characters fails, so both outcomes are reachable.
- **`warn`** — amber block above the options list, shown only when the
  warning's option is the selected one. One use: `output_mode.Fixed`.
- **`optionsFrom`** — `skin.optionsFrom = 'skin_corpus'` → 71 or 84 entries
  parsed from the real corpus. Stored value is the full section name
  (`06G5_McIntosh`); only the display splits the ordinal.
- **`picker`** — full-screen layer, four-across grid, 16:10 tiles, ordinal
  badge and a check badge on the current one. Thumbnails are placeholders.

**Bounded numbers gain a live slider** (38px mono readout, 14px rail, 34px
knob, pointer capture, quantised to `step`), replacing the read-only value
block. **`readonly` rows take no tap and draw no chevron.** **Amber dots are
removed from all four sites** and `marks` no longer renders anywhere, though
it stays in the data.

## C. Now Playing — per area

- **Source indicator**: pill ground, padding, border and radius all removed;
  `top` 38 → 44px, gap 9 → 11px; mark `18×18` → `height:21px`, with a new
  `--bt` modifier at 24px; Lyrion bars 9/17/12 → 11/21/15.
- **Tabs**: row gap 26 → 34px; unselected ink 0.60 → **0.50 alpha**;
  selected underline `var(--src-accent)` → `var(--ink)` in CSS, while the
  `.dc` source keeps per-tab accents — **the two representations disagree**.
- **Track tab**: the no-lyrics branch is rebuilt to match the with-lyrics one
  — `position:absolute; inset:0`, one 38px title, then artist/album/year on a
  single baseline row. The 58px treatment and the 238px block are gone.
- **Artist tab**: bio switches from scroll-to-read (`max-height:128px;
  overflow-y:auto`) to measure-and-expand (`overflow:hidden`, 132px collapsed).
- **Release tab**: `relLabelDisplay` hides the chip for LMS; `relSpecs`
  filters out any value that is `—`; `ALBUM_FALLBACK` loses its placeholder
  specs entirely.
- **Transport**: no geometry, colour or icon change at all. Only the press
  state.
- **Progress and artwork**: byte-identical.
- **Library**: list container becomes a grid (`libCols`, `libGap`); row
  height **66 → 60px** for every non-Radio list, 96px on Radio root; Radio
  gets a border and a 54px icon.
- **Idle**: rebuilt around a photographic background with
  `-webkit-text-stroke` contour, a date line, and a weather band. Clock drift
  box narrowed (`y` 24+52 → 17+38) to clear it.

## D. The gaps, with lines

| # | gap | design | code |
|---|---|---|---|
| 1 | fixed output mode absent | `dc.html:1032`, `:1051-1061`, `:257-262`, `:969-974` | `VolumeDrawer.svelte:118-146`, `NowPlaying.svelte:463`, `MiniStrip.svelte:86` |
| 2 | no long-press | `dc.html:1598-1634`, wired at `:624` | zero handlers in `Library.svelte` |
| 3 | artist page offline + Retry | `dc.html:705-710`, `:753-755`, `:807-809` | `Library.svelte:286` computes `error`, `:954-981` never branches |
| 4 | similar artists inert | `dc.html:794-806` | `Library.svelte:1036-1040`, `NowPlaying.svelte:395-399` |
| 5 | genre/tag chips | `dc.html:674-684`, `:127-131` | absent; no field in `enrichment.py:140-170` |
| 6 | Lyrics tab = Track tab | `dc.html:1869-1918` (full song) | `NowPlaying.svelte:230` and `:281`, both `window5` |
| 7 | radio glyphs | `dc.html:1289-1301` (10 tinted) | `Library.svelte:695-703` (2, untinted) |
| 8 | radio station count | `dc.html:365` | `Library.svelte:640-643` empty span |
| 9 | artist album counts | `dc.html:422`, `:629-632` | `Library.svelte:785-789`, `:872-897` |
| 10 | Popular/Similar skeletons | `dc.html:720-728`, `:787-792` | `Library.svelte:984`, `:1031` render only when data exists |
| 11 | Popular row actions | `dc.html:733-748` | `Library.svelte:990-998` plays immediately |
| 12 | Back from New Music | `dc.html:2582-2588` | `Library.svelte:670` empty path — **disputed, see above** |
| 13 | album year on Track panel | `dc.html:77-80`, `:88-92` | `NowPlaying.svelte:260-263` comment, now stale |
| 14 | Release format chip | `dc.html:156-158` | `NowPlaying.svelte:315-317` type only |

**Needs a core field before it can be built at all:** artist album count,
tags, radio category, station artwork, format, fixed-vs-variable output,
station count.

## E. What to diff next time

1. `diff -u` both `.dc.html` files **and read all of it** — `wc -l` the diff
   first so you know what you are committing to. The prose files describe
   maybe a fifth of what changes.
2. Check `backdrop-filter` is still absent (ADR-0041) and that the Motion
   table no longer specifies the library cross-fade.
3. Re-run the key delta in section A against
   `core/src/gexis_core/settings_registry.json`.
4. Check `design/fonts/` and `IMPLEMENTED-DIFFERENTLY.md` survive the merge.
