# Finding 002 — peppyalsa on stock alsa-lib, format sweep

**Date:** 2026-09-04
**System:** `rig` — Raspberry Pi 4 (4 GB), Raspberry Pi OS Lite 64-bit,
Debian 13 Trixie, kernel `6.18.34+rpt-rpi-v8`, headless, Wi-Fi.
**Question:** Does the metering path require moOde's patched alsa-lib?
**Answer:** No, for this hardware.

---

## Baseline

Confirmed clean before any test:

```
libasound2t64:arm64   1.2.14-1+rpt1
libasound2-dev:arm64  1.2.14-1+rpt1
```

No `moode` suffix. `/etc/asound.conf` absent. `/etc/alsa/conf.d/` **did not
exist** — that directory is convention, not shipped. moOde creates it.

## Hardware

The HAT is detected automatically from its EEPROM. No `dtoverlay` line is
present in `/boot/firmware/config.txt`; the card appears regardless.

```
3 [sndrpihifiberry]: HifiberryDacplu - snd_rpi_hifiberry_dacplushd
```

**Card index is not stable.** It is 3 on the rig and 2 on moOde, because stock
`config.txt` has `dtparam=audio=on`, adding `bcm2835 Headphones` at index 0.
Loading `snd-aloop` later added a card at index 4 without displacing the DAC,
but that was a post-boot load. **Always reference `hw:sndrpihifiberry`.**

### Codec and capabilities

```
id: HiFiBerry DAC+ HD HiFi pcm179x-hifi-0

FORMAT:   S16_LE S24_LE S32_LE
RATE:     [44100 192000]   (continuous range, not a discrete list)
CHANNELS: 2                (fixed — no mono)
```

`S24_3LE` (packed 3-byte) is **not** offered. 24-bit content must travel in a
4-byte container.

### Mixer

```
numid=1  'DAC Playback Volume'
  INTEGER, 2 values (stereo), min=0 max=240, step=0
  dBscale-min=-120.00dB, step=0.50dB, mute=1

numid=2  'DAC Invert Output Switch'   BOOLEAN
numid=3  'DAC Rolloff Filter Switch'  BOOLEAN
```

240 steps × 0.5 dB = 120 dB range. 0 = mute, 240 = 0 dB. Simple-mixer name is
`DAC` — this is the string `squeezelite -V` needs.

The PCM179x has an internal digital attenuator, so volume is applied **inside
the chip**, after the I²S data path. Samples leaving the Pi are unmodified.
This is the precise form of the bit-perfect claim: not "no digital processing
anywhere", but "no modification of the samples we send".

Two controls moOde does not expose on this HAT: hardware polarity inversion
(moOde does this with an ALSA `route` plugin and a `ttable` of −1) and the
PCM179x selectable digital filter. Both are free and both stay bit-perfect.

## Build

Upstream peppyalsa, `git clone https://github.com/project-owner/peppyalsa.git`,
identifies internally as `pimeter 0.44`.

```
aclocal && libtoolize && autoconf && automake --add-missing
./configure --prefix=/usr && make && sudo make install
```

Compiles and links against stock `libasound2-dev 1.2.14-1+rpt1`. Only
unused-parameter and one sign-compare warning; nothing structural. Four source
files: `peppyalsa.c`, `meter.c`, `spectrum.c`, `dop.c`.

Installs to `/usr/lib/libpeppyalsa.so`, **not** moOde's multiarch path.

Build dependencies: `git build-essential automake libtool libasound2-dev
libfftw3-dev`.

## Test chain

Deliberately minimal. No `plug`, no `softvol`, `hw:` not `plughw:`, card by name.

`/etc/alsa/conf.d/output.conf`:

```
pcm.output {
    type meter
    slave.pcm "hw:sndrpihifiberry"
    scopes.0 peppyalsa
}

pcm_scope.peppyalsa {
    type peppyalsa
    decay_ms 400
    meter "/tmp/peppymeter"
    meter_max 100
    meter_show 0
    spectrum "/tmp/peppyspectrum"
    spectrum_max 100
    spectrum_size 30
    logarithmic_frequency 1
    logarithmic_amplitude 1
    smoothing_factor 50
    window 3
}

pcm_scope_type.peppyalsa {
    lib /usr/lib/libpeppyalsa.so
}
```

`--dump-hw-params` on `output` returns FORMAT, RATE, CHANNELS and all
period/buffer ranges **identical** to `hw:sndrpihifiberry` directly. The meter
plugin adds no constraint. `ACCESS` gains `MMAP_NONINTERLEAVED` and
`RW_NONINTERLEAVED`, which widens rather than narrows.

## Format sweep

All 18 combinations the card advertises. 1-second 1 kHz sine, `sox`-generated,
played with `aplay -D output`.

|          | 44100 | 48000 | 88200 | 96000 | 176400 | 192000 |
|----------|-------|-------|-------|-------|--------|--------|
| S16_LE   | OK    | OK    | OK    | OK    | OK     | OK     |
| S24_LE   | OK    | OK    | OK    | OK    | OK     | OK     |
| S32_LE   | OK    | OK    | OK    | OK    | OK     | OK     |

**18 of 18 pass. No aborts. Audio audible throughout.**

### Harness note

The first run reported six S24_LE failures. Those were a harness error: `sox -b
24` writes **S24_3LE** (packed), which the card does not offer. The error text
gave it away — `Signed 24 bit Little Endian in 3bytes`, and the "Available
formats" list included `S24_LE`, so ALSA was rejecting the *file*, not the
chain. Re-run with 32-bit containers declared as `S24_LE` via `aplay -f S24_LE`:
all six pass.

## Conclusion, and what it rests on

The "no abort on unconvertible formats" half of moOde's patch is **not needed
for this hardware**. This rests on one line of evidence — this sweep, on this
card, with this chain. It generalises to our product because the DAC2 HD's
format list is the entire space we care about. It does **not** generalise to
moOde, which supports arbitrary DACs and DSD. Their patch has a reason; it is
not our reason.

**ADR-0005's blocker is closed.** Metering builds on stock alsa-lib. No patched
fork, no held packages, no coupling to moOde's build.

## Side finding

peppyalsa does **not** block when the FIFOs have no reader. Audio plays normally
with both pipes unread. This removes a startup-ordering dependency: the
visualisation service can attach and detach freely without stalling playback.

## Not established

- Behaviour with a reader actually attached to the FIFOs
- Whether `type copy` (which moOde uses twice, and we dropped) matters at all —
  on current evidence we do not need it
- Behaviour at rates outside the standard family, which the driver's continuous
  `[44100 192000]` range would accept
