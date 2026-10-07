# ADR-0111 — Skin sets follow the screen: one pack, chosen by the screen, with consent

**Status:** **Accepted** — George, 2026-10-01. Each decision is quoted below.
**Phase:** 13b ([DEVELOPMENT.md](../DEVELOPMENT.md)).
**Amends:**
- [ADR-0109](0109-other-screens.md) decision 8 (skins become plugins, with a
  size selector) and decision 2 (packages installed with the screen).
- [ADR-0022](0022-settings.md): the *Skin size* row goes.

**Builds on:**
- [ADR-0096](0096-turntable-and-cassette-skins.md) decision 2 (the hosting
  repository's licence as the basis);
- [ADR-0108](0108-how-a-release-is-published-and-found.md) (parts, each file
  uploaded once);
- [ADR-0100](0100-software-we-may-not-redistribute-is-fetched-on-the-device.md)
  (the download row);
- [ADR-0050](0050-skin-previews-are-the-skins-own-picture.md) (previews are
  the skin's own picture).

## Context

PeppyMeter skins are bitmaps drawn for one resolution. The visualiser is set
for 1280×800 today (`peppy-meter.txt`: `screen.width = 1280`,
`meter.folder = 1280x800`), and one package, `gexis-skins` (168 MB), carries
the 1280×800 set.

An audit of every pack this would ship, on 2026-10-01 (125 catalog packs at
`foonerd/peppy_templates` f80c166a, and Gelo5's five sets at
`project-owner/PeppyMeter.doc` 2024.03.02, each archive opened):
- **No pack states a licence or permission of its own.** The only terms are
  the hosting repositories': the catalog's MIT (*"Copyright (c) 2025 Just a
  nerd"*), and the GPL-3.0 of the repository Gelo5's sets were uploaded to
  (by its maintainer; its wiki credits *"Grzegorz Pietrzak (user Gelo5 on
  Volumio forum)"*).
- **About seven skins in ten show a real brand's logo or product face**
  (about 150 names: Pioneer, Kenwood, McIntosh, Technics, Naim...).
- **Some carry other third-party content:** cartoon and film characters, band
  logos and album art, photos of people, car marks, and Volumio's wordmark
  (about 150 skins).
- **Every catalog pack includes a `preview.png`,** mostly a playback
  screenshot with real album covers.
- **Many catalog `g5_*` packs duplicate the Gelo5 release byte for byte,**
  and each Gelo5 archive holds every skin twice.

| Size | Skins (unique) | Archives |
|---|---|---|
| 1920×1080 | ~407 | catalog 563 MB, Gelo5 341 MB |
| 1280×400 | ~267 | 92 + 122 MB |
| 1480×320 | ~255 | 84 + 105 MB |
| 800×480 | ~150 | 64 + 51 MB |
| 1280×800 | ~180 | 101 + 149 MB, plus the 1280×720 packs letterboxed as today |

## Decided

1. **The sizes:** 1920×1080, 1280×400, 1480×320, 800×480 and 1280×800 (with
   the 1280×720 packs letterboxed into it, as today). **Not 3840×2160**
   (*"We will not support 4k"*). Later, on request: 1024×600, 1366×768 and
   1920×480/515.
2. **One pack per device, chosen by the screen** (George: *"we rely on the
   resolution of the screen to automatically download the right package
   (exact resolution or nearest neighbour that doesn't get cropped - just the
   first one, not all)"*).
   - **Which pack:** the exact size, or else the largest pack that fits
     inside the screen without cropping, centred on black.
   - **After a change of screen** (and its Keep), the new size's pack is
     installed and the old one removed. Until the new one is in, the old one
     shows, letterboxed.
3. **The pack is a plugin.** It is listed on the Plugins screen and can be
   removed. **Removing it turns the visualiser off:** its button disappears,
   as with *no meters*. Installing it again from the Plugins screen turns it
   back on.
4. **Consent in setup** (*"I would add a step in the setup asking user to
   specifically give consent for the visualisation pack to be installed and
   the visualisation service to run"*; kept, *"Keep it"*).
   - The step says what the pack is and its size.
   - During setup the device is on its own Wi-Fi with no internet, so **the
     download starts once it has joined the home network**, as the Lyrion
     search does.
   - Declining leaves the visualiser off, and the Plugins screen can install
     it later.
5. **Redistributed from our signed releases**, not fetched from the
   publishers (*"If redistribution is permitted then why not redistribute
   them?"*).
   - One package per size, `gexis-skins-<W>x<H>`, in the release's `skins`
     part. Each file is uploaded once, ever (ADR-0108 as amended).
   - Installed and removed on the device by a root helper that reads the
     current release's repositories. The files are checked as an update's
     are.
   - Installed packs update with the release.
6. **The licence basis is the hosting repositories',** as ADR-0096 decision
   2 accepted for today's set (*"A"*). Each pack's source and the licence it
   is taken under appear in Legal and Credits.
7. **Everything ships,** brand faces and third-party content included
   (*"A - we take some risk"*).
8. **No previews and no duplicates** (*"Do it. It makes sense"*).
   - The catalog's `preview.png` files are not shipped: the picker shows the
     skin's own background (ADR-0050).
   - A skin that is byte for byte another is shipped once.
9. **The image ships no skins.** Nothing is installed without consent, and a
   device that never reaches the internet has no visualiser.
10. **Devices that already have `gexis-skins` keep it,** unchanged and
    unasked (*"They will continue working as is. No point in creating code
    for consent that is basically thrown away"*).
11. **The *Skin size* row is removed** from ADR-0022's inventory: the screen
    decides (*"Yes"*).
12. **Card space and the Pi's load go into the hardware requirements** (to
    be written: minimum and recommended). The 1920×1080 pack is the largest
    (*"It is fine. This should go into the minimum and recommended hardware
    requirements"*).

### Settled after the packs were first built (George, 2026-10-01)

The first build of the five packs (branch `skin-packs`) raised three
questions; each answer is quoted.

13. **A name that two different skins share keeps both, under separate
    names** (*"Keep under separate name"*). The visualiser chooses a skin by
    its name, so without this one of the two could never be shown. 11, 102,
    105, 117 and 74 names (800×480, 1280×400, 1480×320, 1280×800, 1920×1080)
    share a name in the first build.
14. **The 1280×800 pack includes `peppy_screensaver`'s stock skins** (15;
    *"Yes"*), as today's `gexis-skins` does. Their source is a third, under
    its MIT licence.
15. **The 1280×720 packs that could not be letterboxed are letterboxed**
    (*"Extend the tool"*): `letterbox.py` learns meters that do not start at
    the top-left corner, and spectra. In the first build it refused seven
    packs (102 skins).

## How it is built (technical, in order)

1. **Packages:** one per size, from Gelo5's set and the catalog's packs for
   that size, fetched at pinned versions and checked against their SHA256,
   built reproducibly.
   - Previews are dropped, duplicates and Gelo5's doubled skins removed, and
     1280×720 packs letterboxed into 1280×800 as `letterbox.py` does today.
   - `gexis-skins` stays for the devices that have it; new images do not
     install it.
2. **The device:**
   - a root helper (`gexis-update install-pack` / `remove-pack`) that
     installs from the current release's parts with the updater's
     verification;
   - pack rows on the Plugins screen (install, remove, download progress);
   - the setup consent step;
   - choosing the pack from `screen.env`.
3. **The visualiser:**
   - its screen size from `screen.env`;
   - `meter.folder` set to the pack's size;
   - a smaller pack centred on black;
   - the picker offers the installed pack's skins;
   - old `gexis-skins` installs still read.
4. **Legal and Credits:** each pack's sources and licences.

## Not settled here

- **Whether a Raspberry Pi 4 draws 1920×1080 meters fast enough,** and the
  bars. Measured on George's screens; the result feeds the hardware
  requirements.
- **Written permission from foonerd and Gelo5:** not asked (decision 6 rests
  on the repositories' licences).

## Amended 2026-10-07: a pack downloads gently while the player is in use

On a fresh card George connected his phone to Spotify a minute after setup,
and it took 38 s to play: the 1920 × 1080 pack (490 MB) was downloading at the
whole Wi-Fi link (~8 MB/s), Spotify's connection timed out after 10 s, and
go-librespot waited 25 s before trying again. Nothing was playing yet - the
phone was connecting. George: *"Both: capped while something plays, full
speed when nothing does"*, then, on what counts: *"Agree with your
recommendation on in use"*.

1. **In use** means: a sound card is playing, **or** Spotify or Bluetooth
   showed any activity in the last **10 minutes** - read from go-librespot's,
   BlueALSA's and BlueZ's own logs, which are quiet at rest and speak the
   moment a phone connects. Lyrion is covered by playing: its stream comes
   from the server on the home network.
2. **In use, a pack downloads at no more than 3 MB/s** (apt's own
   `Dl-Limit`); otherwise at full speed. The 490 MB pack takes about three
   minutes capped, one uncapped.
3. **Watched while it downloads:** when the player becomes in use, or has been
   quiet for 10 minutes, apt is stopped and started again at the other speed.
   It resumes the partial file, so nothing is fetched twice.
4. Updates are not affected: an update stops playback before it downloads.
