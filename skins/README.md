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
