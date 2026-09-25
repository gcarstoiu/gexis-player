# Finding 066 — Every picture the panel draws, and the size it asked for

**Date:** 2026-09-25
**Question:** George: *"Check as well all places where thumbnails are shown,
fanart or lms, artists or albums, for them to be displayed nearly
instantaneous."*
**Scope:** `gexis`, 2026-09-25, every screen visited in turn and every
`<img>` on it read from the page: what the URL asked LMS for, what the CSS
draws it at, and whether it had decoded. `devicePixelRatio` is **1** and the
panel is 1280×800, so a drawn pixel is a real one. **Not measured: a phone**,
where the ratio is not 1.

## What each place asks for, and what it shows

| where | source | asked | drawn | over |
| --- | --- | --- | --- | --- |
| now playing's well | LMS cover | 500 | 500 | 1.0× |
| home's New Music strip | LMS cover / fanart | 200 | 174 | 1.1× |
| artist grid | fanart / LMS plugin | 200 | 177 | 1.1× |
| artist page portrait | LMS plugin | 300 | 262 | 1.1× |
| artist page discography | LMS cover | 200 | 136 | 1.5× |
| queue rows | LMS cover | 100 | 42 | 2.4× |
| now playing's artist tab | fanart | 300 | 64 | 4.7× |
| **the mini strip** | LMS cover | **500** | **64** | **7.8×** |
| the background's bleed | LMS cover | 500 | 1702 | 0.3× |

**The mini strip was the one worth fixing.** It is on every library screen
and it changes with every track, and it was given now playing's 500 px
cover: **52,328 bytes and a quarter of a million pixels to fill four
thousand**. The same cover at 100 px is 3,817 bytes — 14 times less to
fetch and 25 times less to decode.

## What was changed, and what was left

[ADR-0070](../decisions/0070-a-cover-at-the-size-it-is-drawn.md): the LMS
adapter publishes the cover **twice**, at 500 and at 100, and the two places
that draw 64 px take the small one. Measured after: the mini strip asks 100
and draws 64, 1.6×.

**Left deliberately:**

- **Queue rows at 2.4×.** 100 px is what the rows already asked for, and it
  is now the mini strip's size too, so **one cached picture serves both**.
  Asking 64 for the rows would save 1.6 KB a row and split the cache in two.
- **The artist tab at 4.7×.** It draws the *same URL* the artist page draws
  at 262, so it costs no fetch and no extra decode — the picture is already
  there.
- **The bleed**, which is upscaled and blurred, and shares now playing's URL.

## How quickly a picture arrives

Counted inside the page, over only the screen being opened:

| | screen appears | first picture | every visible one decoded |
| --- | --- | --- | --- |
| queue rail | 21–24 ms | same instant | **22–25 ms** |
| artist grid | 152–169 ms | same instant | 169 ms, 492 ms on a cold kiosk |

**A picture now arrives with its screen**, which is what ADR-0068's prefetch
bought for the grid and what the browser's own cache buys everywhere else —
a reopened screen makes zero network requests, because LMS serves the proxy
with `Cache-Control: max-age=31536000`.

## The measurement that was wrong first

The first version counted *every* visible image, so it counted the mini
strip — already on the panel, already decoded — and reported 32–37 ms for
every screen, which was the polling interval. Restricting it to the arriving
screen's own container is what produced the table above. **Two screens
answering identically was the tell**, the same shape as LESSONS 32 and 33.

## What this does not settle

- **A phone**, where `devicePixelRatio` is not 1 and every "drawn" number
  above is wrong by that factor.
- **Whether 100 px is right for a 64 px box.** It is 1.6×, chosen for the
  shared cache rather than measured against 64.
- **Decode time itself.** Bytes and pixels were counted; the decode was not
  timed separately from the frame it lands in.
