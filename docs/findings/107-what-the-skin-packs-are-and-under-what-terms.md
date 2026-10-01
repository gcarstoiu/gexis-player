# Finding 107 — What the skin packs are, and under what terms

**Date:** 2026-10-01
**Question:** Before redistributing a skin pack per screen size (ADR-0109,
ADR-0111), under what terms is each pack published, and what does it show?

**Scope:**
- **Every archive in scope was opened:** 125 packs from
  `foonerd/peppy_templates` at f80c166a (sizes 1920×1080, 1280×400,
  1480×320, 800×480, 1280×800 and 1280×720), each matching the catalog's
  SHA256, and Gelo5's five sets from `project-owner/PeppyMeter.doc` release
  2024.03.02. Only the 1280×800 set's SHA256 could be compared with a
  recorded one (`packaging/skins/build.sh`), and it matches.
- **Designs were judged by eye,** once each, on a composite of its
  background images about 470 px wide, and that judgement was applied to
  same-named skins at other sizes. Small logos may be missed; needles were
  not composited.
- **This is an observation, not a legal opinion.** "Logo visible" versus
  "name only" is what the picture shows, not a trademark assessment.
- **The table:** one row per catalog pack and per unique Gelo5 skin, with
  licence words quoted, author, derivation and the brand evidence:
  [data/107-skin-packs.csv](data/107-skin-packs.csv).

## Terms

- **No archive states a licence, copyright or credit of its own.** They hold
  only images, `meters.txt` / `spectrum.txt`, and one `.py`.
- **The catalog** is MIT, *"Copyright (c) 2025 Just a nerd"*. Its README:
  *"Individual templates may have their own licenses. See each template's
  README."* None has one.
- **Gelo5's sets** sit in a GPL-3.0 repository, uploaded by its maintainer.
  Its wiki credits *"custom meters created by Grzegorz Pietrzak (user Gelo5
  on Volumio forum)"*.
- **No restrictive terms were found** (non-commercial, no redistribution,
  personal use), because no terms exist at all.

## What they show

| Size | Catalog packs (skins) | Gelo5 skins | Logo or product face visible | Name only | Generic | Other third-party content |
|---|---|---|---|---|---|---|
| 1920×1080 | 17 (289) | 118 | 241 · 93 | 8 · 3 | 39 · 21 | 1 · 1 |
| 1280×400 | 35 (149) | 118 | 102 · 82 | 8 · 8 | 39 · 28 | 0 · 0 |
| 1480×320 | 8 (139) | 116 | 104 · 87 | 10 · 6 | 25 · 23 | 0 · 0 |
| 800×480 | 33 (90) | 60 | 68 · 43 | 0 · 3 | 16 · 14 | 6 · 0 |
| 1280×800 | 12 (96) | 84 | 77 · 67 | 2 · 2 | 16 · 14 | 1 · 1 |
| 1280×720 | 20 (237) | – | 196 | 6 | 34 | 1 |

Counts are catalog · Gelo5.

- **Brands:** about 150 names. The most frequent are Volumio (156 rows),
  Pioneer, Kenwood, McIntosh, Technics, Naim and NAD. Names are often
  misspelt while the face shows the real mark ("Caltec" shows ALTEC).
- **Other third-party content:**
  - South Park and Minions characters, and a Star Wars skin;
  - Metallica, AC/DC and *The Dark Side of the Moon* artwork;
  - what appear to be photos of real performers;
  - the Mercedes star and a Red Bull F1 steering wheel;
  - Volumio's wordmark on about 150 skins, and photos of Volumio's
    hardware.
- **Previews:** each catalog pack carries a `preview.png` (146 files,
  190.6 MB), mostly playback screenshots with real album covers.
- **Duplicates:**
  - The catalog's `g5_*` packs largely duplicate the Gelo5 release byte for
    byte (114 of 116 at 1280×400, 113 of 116 at 1920×1080).
  - Each Gelo5 archive holds every skin twice (118 unique where the name
    says 120).
  - `1280x400_rose rs150` and `1280x400_rose_rs150` are one pack.
- **The catalog repository** is now `foonerd/glass_templates`; the old raw
  URLs still answer.

## What it bears on

ADR-0111: George chose to ship everything on the hosting repositories'
licences, as ADR-0096 decision 2 did (*"A - we take some risk"*), and to drop
the previews and the duplicates.
