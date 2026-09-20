# Screens

Eleven screens and the mini strip. Only Now Playing is in the first slice; the rest are described
here so the shape is known, and are all in `source/Now Playing.dc.html`
except Settings.

All are fixed 1280×800 except Settings.

---

## 1. Now Playing — the default view

Artwork 500×500 left, metadata right, progress and transport below. Four meta
tabs above the title switch the right column between Track, Lyrics, Artist and
Release without leaving the screen. Source mark and word top-right — the mark
alone, no pill ground — and a 3px accent rule along the top edge.

The Track panel's header is one layout whether or not lyrics are there: 38px
title, then artist · album · year on one baseline row, pinned to the top of
the panel. Lyrics, when they exist, sit under a hairline below it.

Bottom bar, three groups: Home and Visualization left, transport centred,
volume and queue right. Play control 92px, prev/next 68px, Home 64px, every
other control 60px.

When synced lyrics exist, the Track panel shows five lines with the current
one centred and its neighbours fading — no zoom on the active line.

## 2. Mini strip — not a screen, but everywhere

104px bar at the bottom of every screen except Now Playing. A hairline
progress line along its top edge, then artwork thumb, title, artist,
connected renderer, elapsed, volume trigger, and play/pause. Tapping the strip opens Now Playing; tapping
play/pause toggles transport without navigating. Press feedback covers the
whole strip **except** the play/pause button.

Absent when `active` is null.

## 3. Library root — the landing screen

Five equal cards: Browse, Artists, Playlists, Radio, Settings. Below them one
strip, chosen by `home_strip` and `home_strip_count` items long, scrolling
horizontally with a soft mask at both ends:

- **New music** — the most recently added albums as large thumbnails.
- **Most played artists** — round artist pictures captioned with the album
  count.
- **Recently played artists** — the same card, ordered by last play and
  captioned with when ("2 hours ago", "Last week").

One strip or the other, never both.

This is what the device shows when nothing holds it. A pulsing indicator on
each waiting service says Bluetooth, Spotify and LMS are all available;
starting playback from the library activates LMS as a side effect.

## 4. Browse — three panes

Artists left and that artist's albums right in a 288px-tall top row (1fr and
1.25fr wide), the selected album's tracks across the full width below. Each
pane is a rounded card with its own mono header and a count. Each level offers play now, add to queue and add to playlist through a
tap-to-reveal row action — icons appear on the active row only, and only one
row reveals at a time.

## 5. Artist grid

Circular artist photos, six across, grouped under letter headers. A jump rail
down the right edge carries `#` then A–Z; letters with no artists stay visible
but dimmed and inert. Filing is folded — accents reduced, leading articles
ignored.

## 6. Artist page

Photo and name, then About, then Popular (filtered to tracks actually in the
library — the panel is skipped entirely if none are), then the discography
grouped by release type, then similar artists last. Everything except the
discography comes from the network or cache and may take seconds, so each
block has its own pending and offline state.

**The three network states are one value, branched three ways** — the design
carries all three, so implement all three:

| State | About | Popular | Similar artists | Section kicker |
|---|---|---|---|---|
| pending | four skeleton rules, staggered 0 / 110 / 220 / 330ms | skeleton rows | skeleton chips | `LOADING…` |
| ready | bio text plus its attribution line | numbered track rows | artist chips | `VIA METADATA SERVICE` |
| **error** | bordered row: *"Artist details unavailable offline. Your library is unaffected."* with a **Retry** button (36px, Bluetooth-blue ground) at its right | *"Not available offline."* | *"Not available offline."* | **`OFFLINE`**, in coral |

Retry returns the block to pending and re-requests. An error is never a
dialog, never blocks the page, and never touches the local half: the
discography keeps its `ON THIS DEVICE` kicker and its albums, because those
came off the disk. **The region blanks, never the screen** — the same rule as
null metadata.

A frequent implementation slip is computing the error state and then not
branching on it, which silently renders the ready layout against no data.

## 7. Album page

Reached from the artist page's discography or from the New music strip — both
routes open the same path, `Albums/<title>`.

A 264px left column: artwork, the title at 24px, `artist · year` in mono
beneath it, then **Play album** and **Add to queue** stacked full-width. The
track list with durations fills the rest.

**Back goes to that album's artist page**, not to wherever you came from,
because an album opened from a discography or from the strip has no parent
list to pop back to. From the New music strip that means: strip → album →
back → the artist. It does *not* return to the library root.

## 8. Radio

The LMS radio tree, up to four levels deep.

The nine top-level categories are a **three-up card grid**, 96px rows, 18px
radius, a hairline border and a 5% white ground. Every level below is the
same dense single column as the rest of the library: 60px rows, 14px radius,
no border — station and track lists run long.

Each category carries its **own glyph and its own tint**, all ten shapes drawn
in CSS, no icon font and no SVG:

| Category | Shape | Tint |
|---|---|---|
| Radio Now Playing | Arcs | `#7ed6bc` |
| My Presets | Star | `#e0a758` |
| Local Radio | Pin | `#9fb4e8` |
| Music | Note | `#f2a48f` |
| Sports | Ball | `#7ed6bc` |
| News | Lines | `#b0bcc4` |
| Talk | Mic | `#c8a2d8` |
| By Location | Globe | `#8fc4d8` |
| By Language | Speech | `#9fb4e8` |

The tenth shape, **Rss**, is in the set for feed categories LMS may report.
Any category not in this table — and every station row — falls back to
**Arcs** in `#8fc4d8`.

The glyph sits in a **circular disc**: 54px on a category card, 46px on a row
below it. The disc's ground is its tint at **14%**, its border the tint at
**30%**, and the glyph itself the tint at full strength. A selected row
replaces the ground with the LMS accent at 16% and turns its label
`#7ed6bc`.

Ten tinted shapes is the point: the grid is read by colour and silhouette
before it is read by word. Two grey shapes for nine categories is not a
simplification of this, it is a different screen.

## 9. Idle screen (ADR-0019)

Appears after `idle_timeout`, counted from when playback stopped. Dismissed
by local touch only, never reachable from a button.

A clock that moves position periodically so the panel does not burn in, over
the background `idle_background` names — artist pictures from the library,
an online or on-device wallpaper, or black. With `idle_weather` on and a key
present it also carries the current conditions, `idle_days` of forecast, and
optional min/max, with the icon set `idle_icons` chooses (solid, duotone or
neon). `idle_screen: External URL` replaces all of it with that page.

## 10. Pairing confirmation

Shown only when `bt_pairing` is "Confirmation required" and only on a
device's **first** pair — once trusted, every later connection runs the plain
handoff instead.

It uses the handoff frame rather than a separate overlay: the requesting
device, the six-digit code, Reject / Accept, and a countdown. The Bluetooth
disc carries the same two expanding rings as the waiting-for-source discs.
Accepting transforms the same frame into a tick and "Paired", then hands
straight into the handoff — **accepting is the takeover, whether or not audio
has started yet**. Rejecting shows the cross and **"Not paired"**, then
dismisses without a handoff.

The countdown is real: it runs 30 → 0, a second a tick. At zero the frame
shows the cross and **"Request expired"**, holds 1.8s and dismisses — no
handoff, the device is not trusted, the same outcome as Reject. Accepting or
rejecting cancels it. A request that lapses on the phone must lapse here too;
a frame still offering Accept after the phone gave up is a lie.

## 11. Handoff transition

1–3s overlay during a takeover. Both service marks with a musical note
travelling between them, directionally. Skipped for pairs in
`handoff_exempt_pairs`. Must read as a handoff, not a failure.

## 12. Settings

The only responsive screen; the only one the phone sees. See `settings.md`.

---

## Row actions

Play / Add to queue / Add to playlist appear on a row **when that row is
selected**, and by no other route. **There is no long press anywhere on the
panel** — a hold is invisible on a touch panel and it makes every tap wait on
a timer.

Which rows reveal actions:

- **Browse's three columns** — artist, album and track. A tap selects the row
  and reveals its actions; tapping the same row again puts them away.
- **Leaf rows in any list** — tracks and stations. First tap reveals, second
  tap plays.
- **Popular tracks on the artist page.**

Which rows have none, because they have no selected state:

- **the Artists grid** (the circular photo grid),
- **the Playlists list**,
- **every branch row in a list** — genres, years, radio categories, albums
  under an artist. A tap navigates and nothing else.

Queueing an artist, a playlist or a category therefore happens **inside** it,
where the actions are visible. A deliberate trade: one tap further, nothing
hidden.

## Navigation

- Now Playing is the default once something is playing; the library root is
  the default when nothing is.
- **Back is always present** in the library header, the root included. At the
  root it leaves the library for Now Playing; below the root it pops one
  level, except on an album page, which goes to the album's artist. When
  nothing holds the device the root has nowhere to leave to, so Back stays.
- **Home** appears beside Back only below the first level, and returns to the
  root in one tap.
- The mini strip is the other way back to Now Playing, from any library
  screen.
- Settings is reachable from the library root card and nowhere else on the
  panel.

## Motion

Pi 4 budget: transform and opacity only, one region at a time. One screen is
mounted at a time and the swap is not animated: over the shared backdrop every
cross-fade showed the bare backdrop as a blink.

| Transition | Treatment |
|---|---|
| Now Playing → library | strip appears, screen swaps — **no cross-fade** (ADR-0041) |
| library → Now Playing | strip goes, screen swaps — **no cross-fade** |
| modal / sheet | scrim opacity 180ms, panel opacity only |
| queue rail | `translateX` 260ms |
| handoff | note position, 1–3s, self-dismissing |

No blur transitions, no animated filters, no simultaneous region animations.
