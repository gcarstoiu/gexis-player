# Finding 001 — moOde reference recon

**Date:** 2026-09-04
**System:** moOde on SD card 1. Debian 13 Trixie, kernel `6.18.39+rpt-rpi-v8`, aarch64.
**Method:** Read-only inspection over SSH. Nothing installed, nothing modified.
**Purpose:** Understand the reference implementation before building our own chain.

---

## Packages

Relevant, with hold status (`hi` = held, `ii` = normal):

```
hi  libasound2t64:arm64        1.2.14-1+rpt1moode1
hi  libasound2-data            1.2.14-1+rpt1moode1
hi  libasound2-dev:arm64       1.2.14-1+rpt1moode1
hi  peppy-alsa:arm64           2026.07.26-1moode1
hi  peppy-meter                2026.7.20-1moode1
hi  peppy-spectrum             2024.5.26-1moode1
hi  squeezelite                2.0.0-1541+git20250609.72e1fd8-1moode1
hi  bluez-alsa-utils           4.3.1-3
hi  libasound2-plugin-bluez    4.3.1-3
ii  alsa-utils                 1.2.14-1+rpt1
```

Version lineage: `1.2.14-1` (Debian) → `+rpt1` (Raspberry Pi) → `moode1` (moOde).
"Stock" on Raspberry Pi OS already means `+rpt1`, not plain Debian.

## The alsa-lib patch

```
alsa-lib (1.2.14-1+rpt1moode1) UNRELEASED; urgency=medium
  * Added PCM meter scope patches: no abort on unconvertible formats,
    DSD levels
 -- Tim <tim@moodeaudio.org>  Sun, 26 Jul 2026 18:16:36 -0400
```

Two changes, both in the `meter` scope:

1. **No abort on unconvertible formats.** Implies stock alsa-lib aborts on some
   formats. Which formats is not stated. → tested in Finding 002.
2. **DSD levels.** Out of scope — the DAC2 HD has no DSD path. peppyalsa carries
   DoP handling in a separate source file (`src/dop.c`), confirming this half is
   structurally separable.

Marked `UNRELEASED` — a local moOde build, not upstreamed.

peppyalsa itself is **unpatched**. Its `README.Debian` is the upstream project
changelog, latest entry 2021-10-16, with no moOde-specific entries.

## The ALSA chain

`/etc/asound.conf` is empty. Routing lives in `/etc/alsa/conf.d/`.

```
_audioout          type copy
  └─ peppy         type plug
      └─ softvol_and_peppyalsa   type softvol → "DAC Playback Volume", card 2
          └─ peppyalsa           type meter, scopes.0 peppyalsa
              └─ _peppyout       type copy
                  └─ plughw:2,0
```

DSP options (`alsaequal`, `crossfeed`, `eqfa12p`, `invpolarity`) each slave to
`peppy`, so they sit above the whole stack.

### Observations

**`_audioout` is a logical-device indirection.** Every renderer targets one name.
`_sndaloop.conf` swaps what sits behind it by adding and removing trailing
underscores from `pcm.!_audioout__`, driven by a job from `snd-config.php`. The
rename mechanism is crude but the pattern is validated by a shipping product.
This is the direct precedent for our `output` device (ADR-0009).

**peppyalsa is a scope plugin, not a PCM plugin.** It loads through stock
alsa-lib's `type meter` extension point:

```
pcm_scope_type.peppyalsa {
    lib /usr/lib/aarch64-linux-gnu/libpeppyalsa.so
}
```

**This chain is not bit-perfect.** `type plug` at the top, `type softvol` in the
middle, `plughw` at the bottom — three conversion opportunities. moOde must
route around it for bit-perfect playback, which is what the swappable
`_audioout` exists for.

**Meters follow volume.** Audio passes `softvol` *before* the meter tap, so
needles drop when volume drops. `/tmp/peppy_gain_db` and
`/tmp/moode_peppy_gain.log` appear to exist to compensate. With hardware volume
on the DAC2 HD, attenuation happens inside the DAC chip — after our tap — so
our meters will show programme level, not output level. Behaviour difference
from moOde; deliberate.

**Card index is hardcoded twice** — `card 2` and `plughw:2,0`. moOde regenerates
these files so it gets away with it. We do not: index varies with configuration
(see Finding 002).

## peppyalsa scope parameters

```
decay_ms 400
meter "/tmp/peppymeter"          meter_max 100      meter_show 0
spectrum "/tmp/peppyspectrum"    spectrum_max 100   spectrum_size 30
logarithmic_frequency 1          logarithmic_amplitude 1
smoothing_factor 50              window 3
```

Two named pipes, both present and live. Values scale 0–100, spectrum 30 bands.
Byte layout on the wire not yet determined.

## Not established

- Whether `type copy` is upstream alsa-lib or a moOde addition
- The FIFO byte format
- What `/tmp/peppy_gain_db` contains or how it is consumed
- Whether the alsa-lib patch is needed for any format we care about
  (→ Finding 002)
