# ADR-0102 — Settings as an app on the phone, without a URL bar

**Status:** **Proposed: a test first.** George, 2026-09-28: *"the settings need
to become a web app installed by the browser and showing up as an app in the
phone, without a URL bar when opening."* He agreed to test first, then decide.
**Date:** 2026-09-28

## The question

A browser installs a site as an app, opening full screen from the home
screen, when the site offers a web-app manifest. What Claude understands, and
has **not** verified on George's phone:
- **Chrome on Android** installs one only from a **secure origin** (HTTPS).
  From `http://gexis.local` it offers a home-screen shortcut that opens in an
  ordinary tab, URL bar and all.
- **Safari on iOS** is more lenient about home-screen apps.

George's phone is Android (a Pixel, from the Qobuz pairing logs).

## The test (built on branch `phone-remote`)

- `manifest.webmanifest`: name *gexis sound*, `display: standalone`, dark
  ground, and icons at 192 and 512 px (maskable) plus an SVG.
- The icons are the gexis sound mark, the tiles alone with *s* lit, on the
  panel's ground (`design/brand/scripts/logo_svg.py … mark`). The brand guide
  gives the mark to favicons and avatars, and an app icon is the same use.
- `index.html` links them and carries the iOS home-screen tags.
- The core serves the five files at the site root, by name: no catch-all, as
  for the rest of the UI.

**George installs it** ("Add to Home screen" / "Install app") and reports
whether it opens without the URL bar.

## If Android needs HTTPS: the routes, for the decision after the test

1. **A self-signed certificate:** Chrome warns, and will not install from it.
   Not viable.
2. **Our own certificate authority, installed on each phone once:** it works,
   and it is a fiddly step for a user.
3. **A public name with a real certificate**, as Plex does with `plex.direct`:
   it works everywhere, and needs a service run by us.

Nothing is decided here until the test reports.
