# Screens

Ten screens. Only Now Playing is in the first slice; the rest are described
here so the shape is known, and are all in `source/Now Playing.dc.html`
except Settings.

All are fixed 1280×800 except Settings.

---

## 1. Now Playing — the default view

Artwork 500×500 left, metadata right, progress and transport below. Four meta
tabs above the title switch the right column between Track, Lyrics, Artist and
Release without leaving the screen. Source pill top-right, 3px accent rule
along the top edge.

Bottom bar, three groups: Home and Visualization left, transport centred,
volume and queue right. Play button 92px, prev/next 68px, the rest 60px.

When synced lyrics exist, the Track panel shows five lines with the current
one centred and its neighbours fading — no zoom on the active line.

## 2. Mini strip — not a screen, but everywhere

96px bar at the bottom of every screen except Now Playing. Artwork thumb,
title, artist, connected renderer, elapsed, a hairline progress bar, volume
trigger, and play/pause. Tapping the strip opens Now Playing; tapping
play/pause toggles transport without navigating. Press feedback covers the
whole strip **except** the play/pause button.

Absent when `active` is null.

## 3. Library root — the landing screen

Five equal cards: Browse, Artists, Playlists, Radio, Settings. Below them the
New Music strip — the ten most recently added albums as large thumbnails,
scrolling horizontally with a soft mask at both ends.

This is what the device shows when nothing holds it. A pulsing indicator on
each waiting service says Bluetooth, Spotify and LMS are all available;
starting playback from the library activates LMS as a side effect.

## 4. Browse — three panes

Artists left, that artist's albums right, the album's tracks across the
bottom. Each level offers play now, add to queue and add to playlist through a
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

## 7. Album page

Reached from the artist page or the New Music strip. Artwork, title, artist,
year, track list with durations, and Play all. Back goes to the artist page,
not to wherever you came from.

## 8. Radio

The LMS radio tree, up to four levels deep. Rows are cards with a category
glyph drawn in CSS — arcs, waves, a tower, a globe — tinted per category.

## 9. Idle screen (ADR-0019)

Appears after the configured timeout once playback has been stopped past the
grace period. A clock that moves position periodically so the panel does not
burn in. Dismissed by touch only, never reachable from a button.

## 10. Handoff transition

1–3s overlay during a takeover. Both service marks with a musical note
travelling between them, directionally. Skipped for pairs in
`handoff_exempt_pairs`. Must read as a handoff, not a failure.

## 11. Settings

The only responsive screen; the only one the phone sees. See `settings.md`.

---

## Navigation

- Now Playing is the default once something is playing; the library root is
  the default when nothing is.
- Every library screen below the root has a Back button, and below the first
  level a Home button beside it that returns to the root in one tap.
- The mini strip is the way back to Now Playing from anywhere.
- Settings is reachable from the library root card and nowhere else on the
  panel.

## Motion

Pi 4 budget: transform and opacity only, one region at a time.

| Transition | Treatment |
|---|---|
| Now Playing → library | strip slides up 260ms `--ease`, screen cross-fades |
| library → Now Playing | strip slides down, screen cross-fades |
| modal / sheet | scrim opacity 180ms, panel opacity only |
| paused | artwork veil opacity 220ms |
| queue rail | `translateX` 260ms |
| handoff | note position, 1–3s, self-dismissing |

No blur transitions, no animated filters, no simultaneous region animations.
