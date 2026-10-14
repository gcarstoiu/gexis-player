# ADR-0148 — Text size

**Status:** **Accepted** — 2026-10-14, George.

## Context

George asked for *"a scale factor setting based on which everything on the
display scales upwards or downwards"*, its default what the screen has now.
The first approach, the browser's zoom (the same device scale factor a TV
gets, ADR-0147), was tried on sofapi's live screens before anything was
built: every screen is laid out for a fixed page, 1280 x 800 points on a
Standard screen and 400 high on a bar, and a zoom changes the page's size,
not the screen's. At 125 % Now Playing lost its volume and queue buttons off
the right edge and the mini strip its controls; at 75 % a third of the
screen stayed empty. Making every screen lay itself out for other page
sizes touches all 34 screens on both families.

Offered *text size only* instead, George: *"Try the text and see how it
looks."* At 115 % every screen looked at held; at 130 % Home's tiles broke
(*My Music* wrapped and pushed its count out, *Album Artists* overflowed).
George: *"Let's do 90 to 130 and the home tiles stretch to fit the text."*

## Decision

- **A Text size row** under *Settings → Display → Panel* (`text_size`):
  90 to 130 % in steps of 5, default 100. Hidden while the player is
  headless. It applies at once, without restarting the screen.
- **Every font size scales**: the type tokens and the 460-odd sizes written
  in pixels in the screens are multiplied by `--text-scale` at build time
  (`ui/vite.config.js`, a PostCSS step), so no screen is edited by hand and
  a new one is included without thinking about it.
- **On the player's own screen only.** A phone's page keeps its own size.
- **Home's tiles grow with the text** above 100 %: on a Standard screen in
  both directions (200 x 200 becomes 260 x 260 at 130 %), on a bar sideways
  only, the bar's height being the screen's; both rows scroll. Below 100 %
  they keep their size.
- **Layouts, icons, buttons and pictures do not change size.** Long titles
  are cut short sooner at large sizes.

## Verified

In a headless browser against sofapi's live data (the page sending nothing
back), at 90 and 130 %: Now Playing and its tabs, Home, Browse, Album
Artists, a Spotify list and Settings on a Standard screen (1280 x 800) and
the 11.9" bar's page (1850 x 400); Home also on a TV's page (1280 x 720)
and the 7.9" bar's (1280 x 400). No tile name is cut at either end.

## Unverified

When written: the row changed from Settings on a device; the bar's other
screens at 130 %; the idle screen, the handoff screen and setup.
