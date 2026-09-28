# Brief for Claude Design — gexis on other screens (Phase 13b)

Written 2026-09-28 for George to hand to Claude Design. Background:
[Finding 100](../../docs/findings/100-screens-what-the-pi-can-learn-and-what-exists.md),
[DEVELOPMENT.md, Phase 13b](../../docs/DEVELOPMENT.md).

---

**gexis** is a music player for the Raspberry Pi 4 with its own touchscreen
(the "panel"). Everything so far is designed for **one screen: 1280×800
(16:10), about 10", seen at arm's length**. The panel's screens are Now
Playing, Library (home, Browse columns, Artists grid, artist page, Playlists,
Radio), Settings, the volume drawer, the idle screen (clock, date, weather
over a wallpaper), the transition screen shown when one source takes over from
another, the Bluetooth pairing frame, and the setup screen (the network name,
password and two QR codes a phone scans to set the player up). A phone reaches
the player too, and already has Settings, a mini player and first-time setup,
so the panel is never the only way to do anything.

We want gexis to run on **other touchscreens**, and to look designed on each,
not stretched:

| Screen | Ratio | Physical |
|---|---|---|
| 800 × 480 | 1.67 | about 7" |
| 1280 × 800 (today) | 1.60 | about 10" |
| 1920 × 1080 | 1.78 | 13.3" (the largest) |
| 1280 × 400 | 3.2 | a bar, about 7.9", landscape |
| 1480 × 320 | 4.6 | a bar, about 11.9", landscape |

…and any size in between. **Please design by family, not by resolution.**

## Keep

- **The design system as it is**: `design/tokens.css` (colours, type, radii),
  the gexis mark, the step and source accents, Nunito Sans and IBM Plex Mono,
  the blurred-weave backdrop. One token set for every screen; only sizes change,
  and they change by a rule you state.
- **No on-screen keyboard anywhere.** Typing happens on a phone.
- **Nothing only the panel can do.** Anything left off a small screen must
  still be reachable from the phone.

## Family 1 — Standard (aspect 1.5 to 1.8)

Today's screens, **scaled uniformly to a logical width of 1280**. The logical
height then varies from **711 (16:9) to 853 (1.5)**; 800 is today's.

For each panel screen:
1. Mark **the region that absorbs the extra or missing height**, and what
   happens to it at the extremes (more rows, more spacing, a hidden secondary
   line, and so on).
2. Show it at **1280 × 711, 1280 × 800 and 1280 × 853** logical.
3. State a **minimum touch target in millimetres** and check it on the
   smallest screen: at 800 × 480 on 7", one logical pixel is about 0.1 mm, so
   today's 64 px targets become about 9 mm. Say which targets grow, if any.
4. Check the type on the largest screen (1920 × 1080 at 13.3", viewed from the
   same distance): if anything should not scale up 1.5×, say so.

## Family 2 — Bar (aspect 3 to 5, height 320 to 400)

A **reduced panel of strips**. Show each at **1280 × 400 and 1480 × 320**, and
state how a strip stretches between them.

- **Now Playing as a strip**: artwork, title and artist (with the source's
  mark), play/pause/next/previous, a volume control that works by touch, the
  progress. What is dropped from today's Now Playing, and where it goes.
- **The transition screen** (who is taking over from whom), as a strip.
- **Idle**: clock, date and weather as a strip, with or without the wallpaper.
- **Setup**: the setup network's name and password, **one QR code** (to join),
  the page's address as text; and the states "joining", "could not join"
  (with a large warning icon and the reason) and "can't reach its Wi-Fi".
- **The Bluetooth pairing request** (the code, Accept, Reject, a countdown).
- **Volume**: a strip version of the drawer, or none if the strip carries it.
- **Browse and Settings — an open question for George.** Our proposal is that
  on a bar they live on the phone only. If you see a usable one-row Browse
  (for example, a horizontal row of albums, or recently played), draw it as an
  option alongside the phone-only version, so he can choose.

## The visualiser (both families)

The visualiser shows PeppyMeter skins, **bitmaps made for one exact
resolution**; they are not designed here and do not scale. Each screen gets the
set drawn for its size, and there are plenty for every size above, including
about 170 for each bar size. **Design only what surrounds it**: how you enter
and leave it, and how a skin from the nearest size is letterboxed when a screen
has none of its own (today 1280 × 720 skins sit on the 1280 × 800 panel with a
40 px band above and below).

## Setup on the phone: a new "Screen" step

The phone's setup page (`design/source/Setup.dc.html`) gains a **Screen** step
in place of today's "Is a screen attached?":
- **Recognised**: "Waveshare 13.3", 1920 × 1080 — Standard layout", with
  *This is right* / *Choose another*.
- **Seen but uncertain**: what the screen reported (maker, resolution), and a
  list to choose from, grouped by maker, searchable.
- **Nothing on the screen yet**: the same list; choosing one says the player
  will restart and try it, and what to do if the screen stays dark.
- **Headless** stays an option.

And a **Screen** row in Settings → Display: the current model, *Change*, and
rotation (0, 90, 180, 270).

## What we need back

- Both families as artboards at the sizes named above, with the height-absorbing
  regions marked (standard) and the stretch rule stated (bar).
- The millimetre floor for touch targets, and the type scale per family.
- The bar-family screens listed, with the Browse option drawn.
- The Screen step and the Screen row.
- A short note of anything you would **drop** on the small or bar screens and
  why.
