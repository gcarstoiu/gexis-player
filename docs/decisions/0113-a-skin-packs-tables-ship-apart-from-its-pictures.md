# ADR-0113 — A skin pack's tables ship apart from its pictures

**Status:** **Accepted** — George, 2026-10-02: *"A for the next release"*.
**Phase:** 13b ([DEVELOPMENT.md](../DEVELOPMENT.md)). To be built after 0.7.0.
**Amends:** [ADR-0111](0111-skin-sets-follow-the-screen.md) decision 5 (what
a `gexis-skins-<W>x<H>` package carries).

## Context

Since 0.6.0 each skin pack carries, besides its pictures and `meters.txt`,
two tables made at build time: `badge-slots.json` (where the renderer's mark
is centred) and `names.json` (what each skin is called on screen). A pack is
one Debian package, so a change to either table is a new package of the
whole pack, and a release uploads it whole: about 880 MB for the five packs
in 0.7.0, for what is a few kilobytes of change (ADR-0108: each file is
uploaded once, but a changed file is a new file).

## Decided

1. **The tables leave the packs.** One small package carries every size's
   tables. The skin packs change only when their skins do.
2. **A rename or a slot correction is a release of kilobytes:** the small
   package, in the release's own part (ADR-0108).
3. **The tables stay keyed `<folder>/<skin>` per size**, as now. Where the
   tables live on the device, and how the core and the renderer find them,
   is settled when this is built; an installed pack without its table entry
   keeps today's fallbacks (declared box, section name).

## Not settled here

- Whether the slots, which are measured from the pack's pictures, are
  measured in the same build that makes the pictures or from the published
  packs.

## Amended 2026-10-07 (brought into line with the code)

The status stays **Accepted**: the decision stands, and it is not yet built.

**Not built (2026-10-07):**

- **Decisions 1 and 2: the tables have not left the packs.** Each
  `gexis-skins-<W>x<H>` package still carries its own tables in the pack's
  root: `packaging/skin-packs/slots.py` writes `badge-slots.json` and
  `packaging/skin-packs/names.py` writes `names.json` there, during
  `packaging/skin-packs/build.sh`. No tables package exists, so a rename or
  a slot fix is still a new skin pack.
