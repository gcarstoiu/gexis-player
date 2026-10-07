# ADR-0120 — Backgrounds cropped by what they show; Pexels and TheAudioDB

> **Amended 2026-10-07: Pexels removed** (George: *"remove pexels completely as they are not providing API keys anymore"*). Its source, row and key are gone; Pixabay is the online wallpaper source. The Pexels parts below are history.

**Status:** **Accepted** — George, 2026-10-05, on the comparison page
*Bar Backgrounds* and in the session: *"Let's do this but with some
modifications"*, then **1.a**, **2. agreed**, **3. that is fine for pexels -
and also agreed for the terms**. Measured before the build, below.
**Builds on:** [ADR-0047](0047-the-idle-screen-gains-backgrounds-and-weather.md)
(the idle screen's backgrounds), [ADR-0059](0059-artist-portraits-in-the-list.md)
(the artwork updates), [ADR-0109](0109-other-screens.md) (bars), and
[ADR-0022](0022-settings.md) (three rows, below). On
[Finding 043](../findings/043-the-idle-screens-two-providers.md) (the
providers' terms).

## Context

George, 2026-10-05: *"For artists sometimes the head is cropped leaving only
the body or animals have only their feet shown ... Nothing is off the table.
We need better solutions here."*

Today every background is drawn `object-fit: cover` at a fixed
`object-position: 50% 35%`. A 1280 × 400 bar shows about a third of a 16:9
picture's height, so the band lands wherever 35 % puts it, whatever the
picture holds.

### What was measured (2026-10-05)

On 49 of George's artists' fanart backgrounds and 49 animal wallpapers,
cropped to 1280 × 400 three ways (the comparison page holds the sheets):

- **Faces, placed by the eyes** (a third of the way down the band): YuNet,
  232 KB, found faces in 48 of 49 artist pictures; **86 ms** a picture on
  gexis.
- **A person or animal, kept from its top** (heads are nearly always at the
  top): YOLOX-S (36 MB, Apache-2.0) found 19 of 25 animals, NanoDet-Plus
  (3.7 MB) 15; the large one was better on 4 pictures and the small one on
  none. **2.2 s against 180 ms** a picture on gexis.
- **What stands out** (spectral-residual saliency) as the last resort - it
  finds where an animal is, not where its head is.
- Close-ups where the subject is far larger than the bar (a dog's face, an
  ostrich's) lost to today's crop.

## Decision

### 1. Each picture is placed by what it shows, once, on the player

In this order: **faces** (the band set by the eyes) → **a person or animal**
(the band from its top) → **what stands out**. Worked out once when a
picture arrives, in the background, remembered beside it; the panel receives
where to place it with the picture, in place of the fixed 35 %. Every
screen, not only bars: the same placement serves a 16:9 panel and the
square photos Lyrion's own artist pictures often are.

The large detector (YOLOX-S), for the four animals in 25 it finds that the
small one does not: at most one picture a minute, in the background, 2.2 s
costs nobody a wait.

### 2. A subject too big for the band: shrink it, or skip the picture

George: *"The 'too close' fallback just moves to the next picture rather
than having more than half the screen blurred. If it can be zoomed out so
that the blur takes less than let's say 25% of the screen then it might
work."* A picture whose subject the band would cut is **shrunk until the
subject fits, as long as the picture still fills at least 75 % of the
screen's width**, the rest filled with its own blur; past that, **it is
skipped** and the next one is shown.

### 3. More sources, the better ones first on a bar

- **Pexels** beside Pixabay for wallpapers, with **the topic words as search
  terms** (it has no categories; George: *"that is fine for pexels"*). Its
  terms name backgrounds and screensavers as allowed, with the credit worked
  into the display - *Photo by … on Pexels*, drawn as Pixabay's is.
- **TheAudioDB** beside fanart.tv for artist backgrounds (its fanart, 16:9).
- **fanart.tv's 4K backgrounds** (3840 × 2160) asked for first: more room to
  place the band at full sharpness.
- **On a bar, the sources measured better for bars are asked first** - by the
  share of each one's pictures that are wide enough, and how often the
  placement finds a band - **counted by the player as it runs**, with no
  setting.

### 4. TheAudioDB in the artwork updates too

George: *"Use theAudioDB also for enriching the artists portraits and album
covers ... The more coverage we have, the better."* Enrichment's *Update
artist portraits* and *Update album covers* ask TheAudioDB **after fanart.tv
and before Lyrion's own** pictures.

**Measured while building (2026-10-05):** the shared test key's album
list (`album.php`) holds **one album per artist** (Coldplay: one), while its
per-album lookup by release group (`album-mb.php`) answers for any. So a
cover fanart.tv lacks is asked for alone, one request per album at 30 a
minute: an update of a large library takes about an hour more on the
shared key (estimated, not measured), and a personal key's full album list
saves most of those requests.

### 5. Keys

- **TheAudioDB (1.a):** an optional key row; the owner's own key when there
  is one, **TheAudioDB's free shared test key (`123`, 30 requests a minute)
  otherwise**. The shared key is public and TheAudioDB's own; this records
  that it is a testing key, shared by every player that has no key of its
  own.
- **Pexels:** the owner's own key, as Pixabay's (Finding 043: per-owner keys
  are what both allow).
- **Unsplash: not used.** Its guidelines forbid asking users to register
  developer accounts, and a public repository cannot hold a shared key;
  writing to Unsplash about its open-source route is George's to do, should
  he want its photography.

### 6. Settings (ADR-0022, confirmed by George, 2026-10-05: "2. agreed")

- **Pexels API key** [N] - Idle screen, shown only with online wallpapers.
- **TheAudioDB key** [N] - Enrichment; empty means the shared test key.
- **Wallpaper API key** renamed **Pixabay API key** (the key stays
  `wallpaper_key`).

## Measured before building (2026-10-05)

- **The runtime: OpenCV.** Installed for aarch64, Python 3.13:
  `opencv-python-headless` 83 MB + numpy 53 MB = 136 MB; ONNX Runtime 54 MB +
  Pillow 22 MB (it reads no pictures itself) + numpy 53 MB = 129 MB, plus
  protobuf and flatbuffers. About equal, and OpenCV is one package that ran
  both models and the face finder on gexis. The device already carries
  Debian's numpy 2.2.4 (`python3-numpy`); whether the core can use it instead
  of a second copy is for the build.
- **Artist sources**, 80 of George's 910 artists with a MusicBrainz id, at
  random: fanart.tv has backgrounds for **47**, TheAudioDB for **64**, either
  for 64 - **TheAudioDB adds 17 artists fanart.tv lacks**. fanart.tv's 4K
  backgrounds exist for **2**: asked for first, they rarely answer. Both
  sources' pictures are 16:9 and place alike on a bar (30 each: placed by
  faces or a subject 25 and 23; a face too big for the band 5 and 7).
- **Pixabay on a bar**: George's Animals category gave **0 wide pictures**
  in its 200-result page, every time the bar asked (gexis's log, two days) -
  so every animal on the bar is a cropped landscape picture.
- **Pexels**: not measurable without a key, which only exists once George
  registers. So **the order on a bar is measured by the player as it runs**
  (§3): per source, the share of pictures that arrive wide enough or place
  without being skipped, the better source asked first.

## Built (2026-10-05)

- **Step 1, placement** and **step 2, TheAudioDB**: live on gexis as a
  preview the same day.
- **Step 3, Pexels**: built to Pexels' published API (search by the topic
  word, `orientation=landscape`, 80 a page, the key as the `Authorization`
  header, `large2x` downloaded, *Photo by … · Photos from Pexels* on
  screen) and tested against a stand-in only. **Pexels issued no new keys**
  when it was built (George: *"it will be empty for now as they are not
  releasing any new keys"*), so the row ships empty and the first real
  answer is untried. The bar's source order is measured per page read: the
  share of each source's pictures at least 2.4 to 1, the source measured
  wider asked first, one not yet measured tried first so it gets measured.

