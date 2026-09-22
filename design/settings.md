# Settings — row vocabulary

**Provisional.** ADR-0032 has the API matching this vocabulary rather than the
reverse, so treat the list as a snapshot: it will change as rows are confirmed.

Source: `source/Settings.dc.html`. Responsive by mount width — two-pane at
≥720px, drill-down below. It measures its own container, not the viewport,
because it is embedded on the panel and standalone on the phone.

---

## Row types

Eight, of which seven are settable and one is a separator.

| Type | Payload | UI | Notes |
|---|---|---|---|
| `toggle` | `value: bool` | inline switch | no sheet; acts immediately |
| `choice` | `value: string`, `options: string[]` | sheet, single-select | options are display strings |
| `number` | `value: number`, `unit`, `min`, `max`, `step?` | sheet; slider when bounded, stepper otherwise | |
| `text` | `value: string` | sheet with field | **the only type needing a keyboard** |
| `readonly` | `value: string` | row, no control | GET only |
| `action` | none; `confirm?: string`, `danger?: bool` | sheet with Cancel / confirm | POST only, no stored value |
| `list` | `items`, `empty` | sheet listing items with a per-item action | navigation, not a command |
| `group` | `label`, `accent` | separator | not addressable |

Two modifiers, on any settable row:

- `onlyWhen: [key, value]` — the row is **absent** unless that other row holds
  that value, never shown disabled. `skin` uses it against `skin_rotate`.
  `value` may be the sentinel `ANY`, which means "that row holds anything at
  all" — used for the weather rows, which depend on a key being present
  rather than on its value.
- `optionsFrom: key` — a `choice` whose options are derived from another
  row's value rather than fixed. `skin` derives from `skin_corpus`, so the
  spectrum skins are not offerable while the corpus is meter-only. Narrowing
  the corpus falls the value back to the first skin the new corpus offers.

### The skin corpus is real, and large

`skin` is a **new key** — the registry defines `skin_corpus` and
`skin_rotate` but no selection key. Its options are the INI section names
parsed by `core/src/gexis_core/skins.py`, verbatim:

- `skins/templates/meters.txt` — 71 skins, `01G5_Accuphase` … `71G5_Nixi Spectrum`
- `skins/templates_spectrum/meters.txt` — 13 more, `101G5_Free S+M` … `113G5_Old Spectrum S+M`

So "Meter only" offers 71 and "Meter + spectrum" offers **84**. The `NNG5_`
prefix is the corpus sort order plus the Gelo5 marker (the stock
Volumio-branded skins are not the image default, per `HANDOFF.md:231`), so
**the stored value is the full section name** and only the display strips the
prefix: `06G5_McIntosh` shows as `06` / McIntosh.

### Picking a skin

`skin` carries `picker: true`, so it opens a **full-width picker** rather
than the 560px sheet — 84 visual things cannot be chosen from a narrow list.

**A list on the left, the preview of the tapped entry on the right.** The
list is 380px, rows 62px: ordinal in 32px of mono, name, and a check on the
row that is in use. The tapped row takes a `--accent-visualization` left rail
and tinted ground; the row in use is inked in `--accent-lms`. The pane holds
a 16:10 preview capped at 58% of its height, the name at 26px, the full
section name and in-use state in mono, and one 60px button — "Use this skin",
or "In use" as an inert outline when it is already the value. **Tapping a row
previews only.** The write happens on that button, so reaching a skin costs
no commitment.

Below 720px the pane covers the list and carries a "back to list" step; above
it they sit side by side and the pane opens on the current value.

A 4-across thumbnail grid was built first and replaced: at 84 entries the
tiles were too small to judge and too large to scan. A one-at-a-time carousel
was rejected earlier for taking too many taps to reach the far end.

**The previews are placeholders.** `skins/` holds only the three INI files,
so no preview render exists for any skin. Real previews must come from the
image build; until they do it is the previews, not the layout, that decide
whether this control works.

**Grouping by make was tried and dropped.** The section names carry no brand
field, and tokenising them gives 63 groups for 84 skins with 51 holding a
single skin — a longer list than the grid it was meant to shorten. If brand
grouping is wanted later it needs an authored mapping, not derivation.

`readonly` and `action` are the asymmetric pair: one never accepts a write,
the other has nothing to read.

Every settable row also carries:

- `k` — stable key, e.g. `lms_server`, `boot_volume`. Use these verbatim.
- `label` — short, sentence case.
- `note?` — one or two sentences, shown under the label and in the sheet.
- `marks` — provenance from the record: `R` recorded, `H` hardcoded today,
  `N` new suggestion, `?` a decision still owed.

`marks` is kept in the data as provenance, but **nothing renders from it any
more** — George removed the amber dots and the amber value ink on
2026-09-19. A row that is still owed a decision looks like any other.

---

## Groups

**Six categories**, in this order. Grouped by what the user is changing, not
by subsystem. The subtitle is the second line on each category card.

| Group | Accent | Subtitle |
|---|---|---|
| Audio | `--accent-lms` | Level and output |
| Sources | `--accent-bluetooth` | Renderers and services |
| Handoff | `--accent-warn` | Who gets the device |
| Display | `--accent-display` | Screen and idle |
| Enrichment | `#e8a0b4` | Lyrics and artist info |
| Device | `#8fc4d8` | Identity and network |

There is no System category: `version` and `reboot` are the last two rows of
Device.

Inside them sit **seven `group` separators** — LMS, Spotify Connect and
Bluetooth under Sources; Panel, Home screen, Idle screen and Visualization
under Display.

---

## Rows still owed a decision

The four rows whose `marks` carry `?`. Nothing on screen distinguishes them —
the amber dot was removed — so this table is the only place they are listed.
Each ships whatever the placeholder happens to be unless someone decides:

| Key | Why |
|---|---|
| `handoff_threshold` | evidence-gated rather than a preference — exposing it may be wrong |
| `version` | nothing on a running device reports which build it is |
| `listenbrainz_token` | needed for Popular; the endpoint began requiring one mid-phase |
| `fanart_key` | optional, for better artist photographs than the LMS plugin's |

`wallpaper_key` is marked `N`, not `?`: the row is settled, and what is still
open is which wallpaper service it points at.

`restore_floor`, `boot_default_scope` and `image_build` were on this list
and are not rows any more — see "Changed since the first handover".

---

## Changed since the first handover

From `IMPLEMENTED-DIFFERENTLY.md`, 2026-09-18 — the shipped panel, not
proposals:

- **`idle_grace` is gone.** The post-stop grace period was merged into
  `idle_timeout`, which is now counted from when playback stops.
- **`travel_curve` is decided**: Perceptual. It no longer carries a dot.
- **Handoff is three rows.** `seek_reanchor`, `release_ladder` and
  `idle_close` removed; `handoff_threshold` ranges 0.5–4 s in half-second
  steps.
- **Display**: `theme` and `brightness` removed (no themes yet). The
  visualization timeouts are in minutes on the idle timeout's 1–60 range,
  and a second one — `viz_stop` — stops the visualizer when nothing is
  playing.
- **Enrichment**: `confidence` removed.
- **`bt_pairing` is decided**: Confirmation required, now the default. The
  confirmation UX it was waiting on is designed — see `screens.md`.
- **`max_ceiling` is decided**: 100%, on the same percent scale as every
  other level. It no longer carries a dot.
- **Three Audio rows removed**: `restore_floor`, `boot_default_scope` and
  `volume_managed`.
- **`boot_volume` is in percent**, defaulting to 60%.
- **Two rows carry a `warn`**, shown as an amber block in the sheet above
  Save. The field takes two forms: an object keyed by option, which appears
  only while that option is selected — `output_mode`, where choosing Fixed
  warns that the signal goes out at 100% — or a plain string, always shown,
  for a row whose side effect does not depend on the value. `device_name`
  uses the string form: saving restarts the services that carry the name,
  which stops playback and drops any connected renderer.
- **`bt_trusted` is a `list`** — a seventh settable row type: items with a
  per-item action, plus an empty state.
- **`plugins` removed**; the three per-service name rows are all `readonly`
  "Advertised name", Bluetooth included.
- **Two drawer rows added** under Display › Panel: `drawer_on_external` (a
  remote volume change raises the drawer; the panel's own changes and a
  restored level do not) and `drawer_autohide` (3 s).
- **`idle_background` is four choices**: Artist pictures, Wallpapers online,
  Wallpapers on device, Black. Online wallpapers come from a third party
  service, on-device ones from local storage. Picking Wallpapers online reveals
  `wallpaper_key` (a secret `text` row) — the service is not chosen yet, so
  whether a key is needed at all is still open.
- **Two API keys added** under Enrichment: `listenbrainz_token` and
  `fanart_key`. Both are `text` rows and both carry a dot — how they should
  present is open.
- **No blur behind the sheet.** Its scrim dims only (ADR-0041: live readback
  costs 24.5 ms a frame against a 16.7 ms budget).
- **Press feedback**: controls scale to 0.95; rows that carry a selection
  background take no press animation at all.

### Changed 2026-09-19

- **`bt_discoverable` defaults to Always.**
- **`home_strip` is three choices**: New music, Most played artists,
  Recently played artists. The third is the same artist card as the second,
  ordered by last play and captioned with when — see `screens.md`.
- **`show_transition` moved** from Display › Panel into Handoff, above the
  two timings, which are now `onlyWhen: ['show_transition', true]`.
- **`time_display` removed.** Now Playing shows elapsed and remaining
  together, so there was nothing to choose.
- **Weather rows reordered.** `weather_key` sits directly under the
  `idle_weather` toggle, and Location, Forecast, Show min and max and
  Weather icons are all `onlyWhen: ['weather_key', ANY]` — visible only once
  a key exists. Without a key the idle screen shows the clock alone, so the
  rows that shape a forecast have nothing to shape.
- **`timezone` is a two-step picker.** The zone comes from the network; the
  row exists for the case where that guess is wrong. Tapping opens region
  (Africa, America, Asia, Australia, Europe, Pacific, UTC), then city, and
  the sheet's Close button reads **Back** while a region is open. Two short
  lists, no search field, no keyboard — 350 IANA names in one list is not a
  touch target.
- **`readonly` rows take no tap** and draw no chevron.
- **The header carries the IP**: `gexis · gexis.local · 192.168.178.51`.
  The build stamp that sat at the right of the header is gone; `version` in
  System still reports the build.
- **The LMS server sheet's hint line was removed.**

That makes it **49 settable rows** under 7 group separators, across 6
categories, 6 wired.

---

## Two behaviours to preserve

**Device name.** `device_name` is one name feeding mDNS, Spotify and
Bluetooth. The header shows the name **as typed** with the sanitised hostname
beside it, and the device's address after that — `gexis · gexis.local ·
192.168.178.51`. Never substitute silently. The sanitiser
folds accents, lowercases, replaces illegal characters with hyphens, trims
them from the ends, and caps at 63 characters.

Its sheet carries a string `warn`: saving restarts the services that carry
the name, so playback stops and any connected renderer is dropped. The
warning is unconditional — it does not wait for the text to change — because
the sheet cannot know whether Save will be pressed on an edited value.

**Fixed output mode.** When `output_mode` is Fixed there is no volume to
set, and the design says so in words rather than disabling a control. The
volume trigger stays where it is with its icon dimmed; opening it shows a
locked row in place of the slider — a padlock, *"Level is set downstream. Set
it on your amplifier."*, and a `100%` tag on the right. **Never render a
disabled slider.**

---

## Text entry

**Decided 2026-09-19: `text` rows are editable on both surfaces, and render
identically on each.** There is no on-screen keyboard. The sheet
renders a real `<input>`, pre-filled with the current value; Save writes it,
Cancel discards. The panel assumes an attached keyboard, the phone uses its
native one. **No on-screen keyboard is planned**, and none is drawn.

`secret: true` on a row renders `type="password"`. `placeholder` sets the
field's hint.

A row with `join: true` reports the attempt instead of closing: **Joining
<network>** (spinner, 1.8 s), then **Connected** — which holds 1.4 s, saves and
closes itself — or **Could not join**, which keeps the typed password and
offers Try again. The
mock fails a password under 8 characters, WPA's own minimum, so both outcomes
are reachable.

This removes the phone-only route for Wi-Fi: a secured network now opens a
password sheet on whichever surface you are using, and the row's caption reads
"Password needed" rather than "On your phone". Saved and open networks still
join in one tap without a sheet.

Typing is still worth avoiding where a value can be discovered instead, and
both opportunities are now taken:

- **`lms_server` is a discovery list**, not a text row — `type: 'list'` with
  `kind: 'server'`. Servers announce themselves; tapping one sets it. A
  `manual` label on the row puts "Enter an address" in the sheet's action
  position, which opens a text sheet for a server discovery cannot reach.
  That is the fallback, not the route.

  `discover: true` makes the sheet **search on open** — a spinner and
  "Searching the network" for ~2 s before any result appears, and the empty
  state is withheld until the search finishes, since "no servers found" is
  not true while still looking. "Enter an address" stays available
  throughout, so knowing the address means never waiting for the scan.
- **One name for every renderer.** `lms_player` and `spotify_name` are gone.
  `device_name` feeds the mDNS hostname, the LMS player, Spotify Connect and
  Bluetooth, with **no per-service override** — so Sources has no name rows at
  all.

Two `list` kinds now exist. `kind: 'server'` items are
`[address, description, state]` with `state: 'current' | 'found'`, no signal
bars and no forget action; Wi-Fi items stay `[ssid, meta, bars, state]`.
