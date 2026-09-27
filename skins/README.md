# Skins — Gelo5's 1280x800 corpus

**What is here:** the three configuration files only, 97 KB. The 82 MB of
backgrounds, foregrounds and needles they name are **not** committed; the
image build fetches the pack and extracts them, the way `go-librespot` and
`peppyalsa` are already pinned and fetched rather than vendored.

| file | sections |
|---|---|
| `templates/meters.txt` | 71 meter-only skins |
| `templates_spectrum/meters.txt` | 13 meter + spectrum skins |
| `templates_spectrum/spectrum.txt` | their 13 spectrum definitions |

84 skins, exactly the corpus [ADR-0015](../docs/decisions/0015-skin-renderer-peppymeter-format.md)
is written against: `meter.type` is `circular` (66) or `linear` (18), nothing
else.

## Provenance

Posted by **Gelo5** on the Volumio community forum
(`community.volumio.com/t/peppymeter-templates-width-1280/59939`), hosted as a
release asset of `project-owner/PeppyMeter.doc`:

```
https://github.com/project-owner/PeppyMeter.doc/releases/download/2024.03.02/Gelo5_1280x800.84skins.zip
sha256  3a0a99b1584915bc375bc6a2d137a22cbb29a45230ffb6e04a8ccb0bab466997
size    149,447,685 bytes
```

Both `PeppyMeter.doc` and `PeppyMeter` are GPL-3.0, as is this project
(ADR-0025). The forum post itself states no terms; the licence above is the
hosting repository's.

## What was left out, and why

The pack ships six template folders. `00-99 Skin_400` holds all 71 meter-only
skins; `01-20`, `21-40`, `41-60` and `61-80` are **the same 71 split into
groups of twenty** — verified 2026-09-16 by comparing section names, the union
is identical. Only the two non-duplicate folders are used here.

Finding 007 counted "155 sections across 6 `meters.txt` files, circular 119,
linear 36". That count included the duplicates; deduplicated it is 84
sections, circular 66, linear 18 — which is what ADR-0015 records.

## The animated packs (ADR-0096)

`animated/<pack>/meters.txt` - four packs that make things move: a turntable's
vinyl and tonearm, a cassette's or a tape recorder's reels. As with the corpus
above, **only the configuration files are here**, exactly as upstream ships
them; the image build fetches each pack, refuses one whose `meters.txt`
differs from the copy here, and letterboxes the 1280x720 ones into this panel
(40 px above and below).

From `github.com/foonerd/peppy_templates` at commit `f80c166a`, fetched from
`raw.githubusercontent.com/foonerd/peppy_templates/f80c166a/template_peppy/…`;
sizes and sha256 are the repository's own `catalog/index.json`, and all four
were checked against it on 2026-09-27:

| pack | skins | size | sha256 |
|---|---|---|---|
| `1280x720_g5_710_Turntables` | 48 turntables (Gelo5) | 31,913,568 | `e134e35c0f13ffa62d19f476ffe6ee90de185ae63128830f73f34a23e34c913e` |
| `1280x720_g5_711_Tape_Recorder` | 20 reel-to-reel (Gelo5) | 32,025,049 | `9c0d0161efd3d1886d29f2d185d06f4ec11b45cecc323a2bfc95a10dd10a52fc` |
| `1280x720_g5_712_Cassette` | 15 cassette decks (Gelo5) | 21,568,388 | `8e2d79fce2eb55cfea8628dc0c466226181495b7d3939b1923b7afcf2a85f798` |
| `1280x800_t1800_pack7` | 7, four with reels (Pakit S) | 4,478,810 | `d3874b563a44406ece770ab1278cb785b92c787f46e1d0ef122ef515173cb8ec` |

**Licence.** The templates carry no terms of their own - no licence file in any
zip, none stated in the forum threads they came from. The hosting repository's
`LICENSE` is MIT, and its README says individual templates may have their own;
none does. That is the same bar as the corpus above, whose grant is its hosting
repository's GPL (George, ADR-0096 decision 2).

**What the renderer draws of them.** The motion keys (`vinyl.*`, `tonearm.*`,
`reel.*`, `albumart.rotation*`) and everything the static corpus already has.
The progress bar, volume, mute, shuffle, repeat and play-state icons, the
ticker, the next track and elapsed/total time are **deferred** (ADR-0096
decision 3): the validator names them in `DEFERRED_PREFIXES`, so a key that is
neither drawn nor deferred still fails the build.
