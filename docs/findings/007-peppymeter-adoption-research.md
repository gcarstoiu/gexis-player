# Finding 007 — PeppyMeter/PeppySpectrum adoption: licence, NEON, and skin-format confirmations

**Date:** 2026-09-08
**System:** research only — repos cloned to a scratch directory, and Debian
Trixie arm64 tested under Docker `--platform linux/arm64` (QEMU user-mode
emulation via binfmt_misc, the same mechanism `pi-gen`'s `on_chroot` relies
on). No hardware. No vendoring performed — this is steps 1-4 of George's
ordered brief; step 5 (integration approach) is deliberately not attempted
here.
**Sources:** `github.com/foonerd/peppy_screensaver`,
`github.com/foonerd/PeppyMeter`, `github.com/foonerd/PeppySpectrum`,
shallow-cloned at HEAD on 2026-09-08. `github.com/foonerd/peppy_builds` was
not cloned — out of scope for the licence/NEON questions asked; noted for
whoever picks a Blocker 1 option that needs it.

---

## 1. Licence — three repos, and a nuance the framing didn't anticipate

| Repo | LICENSE file | Header on inspected source |
|---|---|---|
| `peppy_screensaver` | MIT (Copyright 2025 "Just a nerd") | — |
| `PeppyMeter` | GPLv3, full text (674 lines) | `circular.py`, `needlefactory.py`: "Copyright 2016-2024 PeppyMeter peppy.player@gmail.com ... GNU General Public License ... version 3" |
| `PeppySpectrum` | GPLv3, full text (674 lines) | inspected header: "Copyright 2022 PeppyMeter ... GPL v3" |

`peppy_screensaver/README.md`'s own "License" section says "MIT" and credits
PeppyMeter/PeppySpectrum to project-owner, the original Volumio plugin to
2aCD, and the Volumio 4 refactor to foonerd/Wheaten — consistent with the
LICENSE files above.

**The nuance:** the `volumio_*.py` handlers named in the brief
(`volumio_basic.py`, `volumio_spectrum.py`, `volumio_configfileparser.py`,
`volumio_indicators.py`, `volumio_compositor.py`, plus
`volumio_peppymeter.py`) do not live in PeppyMeter or PeppySpectrum — they
live inside `peppy_screensaver/volumio_peppymeter/`, i.e. physically inside
the MIT repo. None of them carry an explicit licence grant of their own —
no "free software... GPL" text and no "MIT" text, just copyright lines
("Copyright 2024 PeppyMeter for Volumio by 2aCD", "Copyright 2025 Volumio 4
adaptation by Just a Nerd"). They `import` directly from PeppyMeter's and
PeppySpectrum's modules (`configfileparser`, `spectrum.spectrum`,
`spectrumutil`, `spectrumconfigparser`) and do not function without them.

So: the repo-level MIT badge is foonerd's assertion covering his own plugin
code, matching the README's own credits section — but the handler files
that do the actual rendering are inseparable from, and only meaningful
combined with, GPLv3 engine code. This confirms the brief's framing at the
file level rather than just inferring it from the badge: if we vendor the
handlers, GPLv3 governs the combined work, regardless of what licence text
(or absence of one) sits atop the handler file itself. This still needs an
ADR and George's decision before anything is vendored, per the brief.

---

## 2. NEON / pygame (Blocker 1)

### (a) Debian Trixie's packaged python3-pygame

Ran `arm64v8/debian:trixie` under Docker `--platform linux/arm64`:

```
apt-cache policy python3-pygame
  Candidate: 2.6.1-1+b2   (source pygame 2.6.1-1)
  Depends: ... libsdl2-2.0-0 (>= 2.0.16), libsdl2-image-2.0-0, libsdl2-mixer-2.0-0, libsdl2-ttf-2.0-0
```

Dynamically linked against Debian's own `libsdl2-2.0-0` — not bundled, the
opposite shape from foonerd's package (below). Installed it and ran
foonerd's own verification command, unmodified, inside the container:

```
PYTHONPATH= python3 -c "import pygame; pygame.init()"
→ pygame 2.6.1 (SDL 2.32.4, Python 3.13.5)
→ no NEON warning
```

**The more important finding is architectural, not just this one clean
run.** The warning foonerd's README warns about ("neon capable but pygame
was not built with support") is meaningful on **armv7** (32-bit), where
NEON is an optional, runtime-detected CPU feature. On **aarch64** (arm64),
NEON/ASIMD is mandatory baseline ISA — not optional, not runtime-detected.
SDL2's NEON-guarded code paths key off the `__ARM_NEON` preprocessor macro,
which GCC/Clang define unconditionally when the compile target is aarch64.
Our build targets arm64 (confirmed: `image/pi-gen/build.sh:180: export
ARCH=arm64`; `stage1/00-boot-files/files/config.txt: arm_64bit=1`), so the
"was it built with NEON support" question the README raises for armv7
mostly doesn't apply to us the way it's framed.

The README's "Docker/QEMU cross-compilation produces non-NEON builds"
warning is plausibly about their own build toolchain — an autoconf-style
NEON feature *test* that runs a target-arch probe binary at configure time,
which fails under a cross-compile that has no way to execute target code —
rather than a property of arm64 itself. Debian's own arm64 buildds are not
QEMU cross-compiles (native/real arm64 build infrastructure), so this
concern doesn't touch how Trixie's `python3-pygame` got built regardless of
what our own Docker+QEMU pipeline does.

**One thing I could not resolve:** I compared foonerd's bundled armv8
pygame build against the official PyPI `pygame-2.5.2-cp311-cp311-
manylinux_2_17_aarch64.manylinux2014_aarch64.whl` (downloaded, sha256
verified against PyPI's index: `dc34696...eedf`, matched). The bundled
`.so` files are **not** byte-identical to the stock wheel (different
sha256 on `transform...so`), so foonerd's package does appear to be an
actually different build — consistent with a real "built natively on a Pi"
claim, not a relabeled stock wheel. I could not go further and compare
NEON instruction usage at the disassembly level in either build: this
host is x86_64 and its `objdump` has no aarch64 backend
(`objdump -i` lists no aarch64 target). Both builds' bundled SDL2
(`libSDL2-2.28.3` in foonerd's case) report `SDL_HasNEON`/
`SDL_HasARMSIMD` as linked symbols via `strings`, which only shows the
detection function is compiled in, not that any NEON-specific blitter
code path is actually taken. This is a genuine tooling gap in this
session, not a negative finding.

### Versions/dates

| | pygame | SDL | Python (ABI tag) |
|---|---|---|---|
| foonerd bundle (`packages/armv8/`) | 2.5.2 | 2.28.3 | cp311 (3.11) |
| Debian Trixie | 2.6.1-1+b2 | 2.32.4 | 3.13 (system) |

Both newer on Trixie. **The cp311 ABI tag is a second, independent problem
for option (b):** foonerd's prebuilt package is compiled against Python
3.11's ABI; Trixie ships Python 3.13 as system Python. It will not import
under Trixie's system interpreter without also vendoring a matching
Python 3.11 (a venv or a separate interpreter build) — this is on top of,
not instead of, the licence question below.

### (b) Vendoring their prebuilt package — licence/redistributability

`packages/armv8/peppy-python-packages.tar.gz` is a raw tar of ~30
third-party packages' site-packages trees (pygame, requests, Pillow,
cssselect2, bidict, charset_normalizer, idna, the cairosvg dependency
chain, etc. — 1031 files total), each with its own `*.dist-info` and, for
several, a bundled `licenses/LICENSE`. There is no single umbrella licence
file for the tarball itself. pygame's own `METADATA` states `License:
LGPL`. Redistributing this tarball means redistributing ~30
individually-licensed packages (mostly LGPL/MIT/BSD, individually
permissive) bundled together — legally workable in principle, but a
materially different vendoring shape than "one package, one licence," and
the cp311 mismatch above means it doesn't just drop into Trixie's Python
3.13 anyway.

### (c) Native-Pi build step

README points to a separate repo, `github.com/foonerd/peppy_builds`, for
build instructions and native-Pi build scripts. Not cloned or inspected in
this pass.

### Where this leaves Blocker 1

Option (a) looks like it dissolves the blocker for our specific target
(Pi 4, arm64, Trixie): Trixie's own `python3-pygame` imports and
initialises cleanly, under the identical Docker+QEMU emulation path our
build already uses, with no compilation step and no NEON warning. The one
thing this doesn't settle is instruction-level confirmation that SDL2's
blit routines are actually NEON-vectorized in Debian's build (tooling
limitation on this host, not a negative result) — and per Blocker 2, actual
frame-rate/CPU cost on real hardware is the measurement that matters more
than that instruction-level question anyway. **Recommend measuring stock
`python3-pygame`'s real frame rate/CPU cost on `gexis` before ruling this
fully closed** — one hardware pass answers both the residual NEON doubt
and the Blocker 2 headroom question at once.

---

## 3. ADR-0015 remaining items — resolved from source

### distance — confirmed, not inferred

`PeppyMeter/needlefactory.py`, `rotate_image()` docstring: *"distance:
distance between rotation origin and image center."* The implementation
matches: `image_bottom` (the sprite's bottom-center — the tail, per the
already-established tip-at-top/tail-at-bottom convention) is placed
`distance` px from the image's own center before
`pygame.transform.rotozoom` rotates the whole image about that center.
This confirms the inference in ADR-0015 exactly: `origin_x`/`origin_y`
(from `circular.py`) is the pivot **position**; `distance` is the radius
from that pivot out to the needle sprite's **centre** along the current
angle. Orthogonal, as suspected — not redundant.

**Consequence worth flagging:** rotation is about the sprite's own
image-center, with no per-skin correction for asymmetric transparent
margins anywhere in this code path. The Accuphase/Naim-green wobble noted
in the brief is **not** compensated by the fork — it's a straightforward
consequence of centre-based rotation meeting an asymmetric sprite, not
something upstream works around. Adopting this renderer as-is means
inheriting that wobble on those skins, not just the underlying convention.

### Font faces — confirmed

`peppy_screensaver/volumio_peppymeter/fonts/` bundles two families:

- `PeppyFont-{Light,Regular,Bold,Italic}.ttf` — default, maps to
  `font.size.light`/`.regular`/`.bold`/(`.italic`).
- `DSEG7Classic-{Regular,Bold,Italic,BoldItalic}.ttf` — 7-segment digital
  face; `DSEG7Classic-Italic.ttf` is the hardcoded default for
  `font.size.digi` (same default repeated in `volumio_basic.py`,
  `volumio_cassette.py`, `volumio_turntable.py`, `volumio_peppymeter.py`).

This is the default path (`use.system.fonts = False`, the setting
foonerd's README lists as "Use Volumio system fonts (Lato) instead of
PeppyFont"). When `use.system.fonts = True`, font paths instead come from
`font.path`/`font.light`/`font.regular`/`font.bold` in `config.txt`, which
in the Volumio install point at `Lato-{Light,Regular,Bold}.ttf`
(`install.sh:345-347`) — **Lato itself is not bundled in this repo**; it's
Volumio's own OS-installed system font. We don't run Volumio, so the
"system fonts" toggle isn't something we inherit for free — if we want it,
we source Lato ourselves (SIL OFL, freely available) or ship only
PeppyFont.

### playinfo.type icon set — confirmed, smaller than the brief anticipated

`format-icons/` bundles exactly **6** SVGs: `cd, dab, fm, qobuz, radio,
tidal`. Everything else a source might report (spotify, airplay,
bluetooth, upnp/dlna, any bare codec name) resolves through
`VOLUMIO_STOCK_ICONS = "/volumio/http/www3/app/assets-common/format-icons"`
(`volumio_typeformat.py`) — Volumio's own OS-installed icon set, which we
will not have. Lookup order (`resolve_icon_path()`): skin-local
`format-icons/{key}.png` then `.svg`, then plugin-local
`format-icons/{key}.svg`, then the Volumio stock path (which will simply
not exist for us). Tinting: only SVGs get `playinfo.type.color` applied —
rasterized via `cairosvg`→PIL→pygame surface, then recoloured pixel-by-pixel
keeping alpha; skin-supplied PNGs are explicitly left untinted ("preserve
authored colours", a comment in the source). **Practical consequence:**
none of our three renderers' actual sources (LMS, Spotify/go-librespot,
Bluetooth) has a bundled icon here except by coincidence — we'll need to
supply our own icon(s) for at least Spotify and Bluetooth if we want icon
mode rather than text mode. The bundled 6 reflect Volumio-context sources
(radio tuners, CD, Qobuz/Tidal Connect), not ours.

---

## 4. Criterion 2 amendment — proposal

Confirmed directly against `PeppyMeter/configfileparser.py`:

- **No `else` branch, confirmed at the line level.** `for section in
  c.sections(): available_meter_names.append(section); meter_type =
  c.get(section, METER_TYPE); if meter_type == TYPE_LINEAR: ...; elif
  meter_type == TYPE_CIRCULAR: ...` — nothing else. An unknown
  `meter.type` gets appended to `available_meter_names` (so it's
  selectable) but `self.meter_config[section]` is never populated. First
  selection, not parse time, is where this fails — a `KeyError` deep in
  playback code, not a build-time signal.
- **No key enumeration anywhere.** `get_common_options()`,
  `get_linear_section()`, `get_circular_section()`,
  `get_sdl_environment_section()` exclusively call `config_file.get(section,
  KEY)` for named keys — never `config_file.options(section)` or any other
  enumeration. Unknown keys in a section are never read, never checked,
  never flagged. Confirmed structural, not an oversight in one spot.

Given this, ADR-0015's current criterion 2 ("unknown keys or `meter.type`
values fail the build") describes behaviour the upstream parser cannot
produce without forking it — which conflicts with the adoption decision.
Proposed amendment, matching the brief's suggested shape:

> **Criterion 2 (amended):** A build-time validator (tier 4) parses all 84
> skins against a defined key set per `meter.type`; unknown keys or unknown
> `meter.type` values fail the build. The runtime parser (adopted from
> upstream, unmodified) remains permissive — this is upstream's existing
> behaviour, not a defect we're carrying forward by accident. The validator
> is a separate, additive check; it does not alter runtime parsing
> behaviour.

**Key-set choice: recommend ours** (the measured corpus — 155 sections
across 6 `meters.txt` files, `meter.type` only ever `circular` (119) or
`linear` (36), 24 keys present in all 155 sections) — not upstream's, not
foonerd's current set. One concrete reason surfaced in this session:
foonerd's fork **deprecates** `playinfo.maxwidth` in favour of
`playinfo.title.maxwidth`/`.artist.maxwidth`/`.album.maxwidth`/
`.samplerate.maxwidth` (confirmed verbatim in README.md's "Deprecation
Notices" section) — and our Gelo5 corpus uses `playinfo.maxwidth` in all
155 sections. A validator built from foonerd's *current* key set would
fail our entire actual corpus on day one over a rename that has nothing to
do with correctness.

**The compatibility question this raises has a good answer, checked in
this session:** does the current handler still honour the legacy,
undecorated `playinfo.maxwidth`? Yes — `PLAY_MAX = "playinfo.maxwidth"` is
still a live constant (`volumio_configfileparser.py:293`), read in all
three handlers (`volumio_basic.py:882`, `volumio_cassette.py:1223`,
`volumio_turntable.py:2055`) as `global_max`, and used as the **fallback**
for title/artist/album/next-* box widths whenever the field-specific key
is absent (`volumio_basic.py:967-994`, `get_box_width()`). So: our corpus
renders correctly under the current handler as-is. The deprecation is soft
(still functional, discouraged going forward per the README) — this is not
a blocker, just something the validator's key set needs to accept
(`playinfo.maxwidth` alongside the field-specific spellings), which is
exactly what "ours, not foonerd's current set" gives us.

---

## Not done in this pass

Deliberately, per the brief's ordering: no vendoring, no ADR written, no
licence decision made, no integration approach proposed. This finding is
the full report for steps 1-4; step 5 waits on George's ruling on §1.

## Not established

- Instruction-level confirmation of NEON code generation in either
  pygame build (tooling gap on this host — no aarch64 `objdump` backend).
- Real frame-rate/CPU cost of stock `python3-pygame` on `gexis` hardware —
  this is the measurement that would close both the residual Blocker 1
  doubt and Blocker 2 (Pi 4 headroom at 1280x800 with Chromium kiosk also
  running) at once.
- `foonerd/peppy_builds` was not inspected — relevant only if option (c)
  is chosen.
- Whether Debian's `libsdl2-2.0-0` build for arm64 specifically enables
  every NEON-guarded blit path SDL2 supports, versus just the baseline the
  `__ARM_NEON` macro forces on — not verified beyond symbol presence.

---

## Follow-ups to track (added 2026-09-08, after the licence ruling)

Not architectural decisions — recorded here, separately from ADR-0025, so
they aren't rediscovered later.

**`playinfo.maxwidth` fallback is load-bearing for our whole corpus.** It's
deprecated upstream (README's "Deprecation Notices") but still honoured as
a fallback in all three of foonerd's handlers (`volumio_basic.py:882`,
`volumio_cassette.py:1223`, `volumio_turntable.py:2055`, all reading
`PLAY_MAX = "playinfo.maxwidth"` as `global_max`). We validate against our
own measured key set (§4 above), which is what makes this safe today. A
future fork release that finishes the deprecation and drops the fallback
would silently break all 155 of our sections at once — the validator
wouldn't catch it, since the key would still be "known" to us, just no
longer read. Worth pinning the vendored commit, or adding a smoke check
that a `playinfo.maxwidth`-only section still produces a bounded text box,
rather than rediscovering this by watching text overflow the screen.

**The format-icon set (§3) doesn't cover any of our three sources.** Only
6 SVGs are bundled (cd, dab, fm, qobuz, radio, tidal); LMS, Spotify and
Bluetooth all fall through to Volumio's stock icon path, which won't exist
for us. George will supply icons for those — a design task, not an
implementation one. Blocks the `playinfo.type` layer the same way the
needle-sprite and font-asset conventions blocked implementation before
ADR-0015's "Blocked — assets not yet inspected" section was resolved:
tracked, not yet actionable.

**Needle-rotation wobble on asymmetric sprites is inherited, not a defect
we introduced.** Confirmed in §3: `needlefactory.py` rotates each sprite
about its own image-center with no per-skin correction for off-center
padding. Accuphase (+5.5px) and Naim green (-4.5px) will visibly wobble
under this renderer exactly as they would under stock PeppyMeter. Do not
"fix" this without a decision from George — matching the fork's rendering
behaviour is the reason it was adopted instead of written from scratch,
and a silent per-skin correction would mean our output no longer matches
what the skin author (or the fork) intended.
