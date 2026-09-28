# ADR-0102 — Settings as an app on the phone, without a URL bar

**Status:** **Decided 2026-09-28: keep the bookmark.** George: *"Let's keep the bookmark. It is fine for now. Later we can reconsider if needed."* George, 2026-09-28: *"the settings need
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

George's phone is Android (a Pixel, from its logs on gexis).

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

## Result (George, 2026-09-28, Android)

*"Installing settings doesn't work. Only URL bookmark possible."* The manifest,
icons and page were served correctly (checked on gexis:
`application/manifest+json`, `image/png`). This is what the secure-origin rule
predicts: from `http://gexis.local`, Chrome makes a shortcut, not an app.

## The decision owed, with Claude's reading of each route

1. **A certificate authority of the device's own**, installed once on each
   phone.
   - The device makes a CA, restricted by *name constraints* to its own names
     (`gexis.local`, its address), and a certificate signed by it. Settings
     offers the CA to download.
   - The restriction matters: without it, a CA on the phone could vouch for
     any site, and its key sits on the device.
   - It needs no service of ours.
   - It costs the user one fiddly step per phone. On Android that is Settings
     → Security → Install a certificate, which shows a "network may be
     monitored" warning.
   - **Two things to verify before committing to it:** that Chrome installs a
     web app from an origin trusted only by a user-installed CA, and that it
     honours the name constraints.
2. **A public name with a real certificate**, as `plex.direct` does. It is
   seamless for the user, and it is a service we would run for as long as
   players exist, with DNS and certificates at our cost.
3. **Keep the bookmark.** Nothing changes; the URL bar stays.

## Decided (George, 2026-09-28): route 3, keep the bookmark

*"Let's keep the bookmark. It is fine for now. Later we can reconsider if
needed."*

- **The manifest and icons stay.** On the phone they make the bookmark's
  home-screen shortcut the gexis sound mark with the name *gexis*, rather
  than a page screenshot, and they cost nothing.
- Routes 1 and 2 are kept above for when this is reconsidered. Route 1 has
  its two checks still to do.

