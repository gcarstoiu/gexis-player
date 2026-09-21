# ADR-0050 — A skin's preview is the skin's own picture

**Status:** Accepted — George, 2026-09-21: *"Let's keep it simple and use
what we have instead of generating thumbnails and cache and more logic."*
**Date:** 2026-09-21
**Raised by:** Phase 9 subphase 9h, which planned to *render* 84 skin
thumbnails at image build, and George's objection to what that costs:
*"The likelihood of the skins changing in general is extremely small which
means it doesn't make any sense to generate the thumbnails with each
build. It should be created, cached and reused, until a change in skins is
detected and even then only the diff."*
**Amends:** [ADR-0019](0019-peppy-screen-lifecycle.md) (the skin picker),
[ADR-0015](0015-skin-corpus-validation.md)'s corpus reading

## Context

The picker has to show what a skin looks like. The plan was to render each
one at image build — 84 skins, a pygame surface each, in a chroot under
QEMU — and ship the results. George's objection was the right one and it
pointed at a better answer than the cache it asked for.

**Every skin already ships a picture of itself.** `screen.bgr` is the
skin's full-screen background, 1280×800, and for this corpus it is the
whole instrument: the Accuphase skin's is a photograph of the amplifier
with its dials, lettering and glass. What the renderer adds on top at
runtime is the needles and the bars.

## Decision

**The preview of a skin is that skin's own `screen.bgr`, served from disk.
Nothing is rendered, nothing is cached, and nothing has to notice when a
skin changes.**

### 1. Because the file is already there

A cache exists to avoid repeating work. There is no work: the image is on
the device, named by the skin, in the same directory as the skin. The
build does not touch it, the daemon does not copy it, and a new skin pack
brings its own previews by existing.

**This is what makes the change-detection question disappear**, rather than
answering it. A cache keyed on a hash of the skin files, invalidated on a
diff, rebuilt for the difference — all of it is machinery for a problem
that only exists if we generate something.

### 2. What it costs: the preview is the skin at rest

No needles, no bars, no album art. A picker shows which instrument you are
choosing, not what it does while music plays — and the moving parts are
the same on every skin of a kind.

**If that is ever not enough**, the escape is the one George described: a
render step, a cache, and a diff. This record is the reason not to build
that yet, not an argument that it could never be worth it.

### 3. One route, whatever the picker looks like

`GET /skins` lists what there is — name, kind, and whether it is the one in
use. `GET /skins/{name}/preview` serves that skin's picture. **The picker's
design is George's and is being redrawn** (2026-09-21: a list, with the
preview shown only when a row is tapped), so the daemon offers the two
things any drawing of it needs and makes no assumption about the rest.

Serving one 500 KB JPEG when a row is tapped is why that redesign matters
here: the old drawing wanted 84 of them at once.

### 4. The name in a URL is not a path

Skin names are section headings written by whoever made the pack —
`01G5_Accuphase`, `Marschal Spectrum`, spaces and all. The route matches a
skin by name against the parsed corpus and serves the file that skin
declares, relative to that skin's own directory. **Nothing in the request
reaches the filesystem**: an unknown name is a 404, and a name that is a
path is simply not a skin.

## Consequences

- **9h loses its image-build job.** The subphase was scheduled as *"the
  panel plus an image build"* because of the thumbnails; the build is now
  only needed for [ADR-0049](0049-the-pictures-folder-is-a-share.md)'s
  share, which is a separate debt.
- **A preview is 500 KB** where a rendered thumbnail would have been ~20 KB.
  That is a local fetch over loopback on a device with the file already in
  its page cache, and one at a time under the new picker.
- **The corpus is parsed by the daemon at runtime** to answer these two
  routes, which it did not do before. `skins.py` already parses it for the
  build-time gate; this is the same parser with a different caller.
- **No build step means no build assertion.** What guards this is a test
  that every skin in the committed pack names a `screen.bgr`, and the
  route's own 404 for anything it cannot find.
