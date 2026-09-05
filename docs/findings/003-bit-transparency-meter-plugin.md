# Finding 003 — bit-transparency of the meter plugin

**Date:** 2026-09-04
**Revised:** 2026-09-04 — see the retraction below
**System:** `rig` — Raspberry Pi 4 (4 GB), Raspberry Pi OS Lite 64-bit,
Debian 13 Trixie, kernel `6.18.34+rpt-rpi-v8`.
**Question:** Does `type meter` with the peppyalsa scope alter samples?
**Answer:** No.

> **Retraction.** The first version of this document additionally concluded that
> the meter plugin loses the final frames of a stream. **That conclusion was
> wrong and has been withdrawn.** Finding 004 shows the same artefact occurs
> with the plugin removed, at similar magnitude, in roughly a third of runs. The
> original conclusion rested on a single control run, which cannot establish the
> absence of an intermittent fault. The transparency result below is unaffected
> and is the part that mattered.

---

## Method

The DAC2 HD has no ADC, so no hardware loopback is possible. It is also not
needed: the question is whether the *plugin* alters samples, and `hw:` is a
driver write with nothing to alter. `snd-aloop` isolates the plugin.

```
modprobe snd-aloop
```

`/etc/alsa/conf.d/looptest.conf`:

```
pcm.looptest {
    type meter
    slave.pcm "hw:Loopback,0,0"
    scopes.0 peppyalsa
}
```

Source material is white noise rather than a sine wave — a sine has too much
structure to expose subtle errors. `sox` reported clipping during generation;
that is baked into the source file, so both sides of the comparison see the same
data. Not a confound.

Procedure: start `arecord` on `hw:Loopback,1,0`, sleep 1 s, `aplay` into
`looptest`, locate the source pattern inside the capture, compare byte-for-byte
from that offset.

## Result

**Samples that pass through `type meter` with the peppyalsa scope are
unmodified.**

| Condition | Result |
|---|---|
| S16_LE / 44100, 5 s, 9 s capture | bit-identical, all 960 000 frames |
| S32_LE / 192000, 5 s, 9 s capture | 959 232 frames identical; remainder — see Finding 004 |
| S32_LE / 192000, 20 runs (Finding 004) | 8 of 20 fully clean; the rest differ only in a terminal region |

**In no run, at either extreme of the format grid, was any difference found in
the interior of the stream.** Every difference observed sits in the final few
thousand bytes.

That is the transparency question answered, at both corners of the 18-cell
format space established in Finding 002.

## Scope

- Two format/rate combinations examined in depth, chosen as the extremes.
- Sixteen intermediate cells were run once each (see the note on the grid script
  below) and are **not** reliable evidence.
- Nothing here tests behaviour with a reader attached to the peppyalsa FIFOs.
- Nothing here tests the real DAC. `snd-aloop` isolates the plugin deliberately;
  the card is a driver write with nothing to alter.

## Method errors, recorded

Two faults in the original work, both mine, both of which produced misleading
output:

**A single control run was treated as decisive.** The scope note said the result
was "confirmed against a control on the same hardware and same run conditions",
which was true and insufficient. Finding 004 establishes that a clean control
run occurs about 70% of the time by chance.

**A grid script assumed a contiguous tail.** It computed "frames lost" from the
position of the first differing byte, without testing whether the differences
actually ran contiguously to the end. They do not — Finding 004 shows every
failure is scattered. Every "frames lost" figure produced by that script was
meaningless, including the apparently compelling constant of 4 ms across rates.

The grid script also compared incompatible sample layouts for all six S24_LE
cells: `sox -b 32` writes a 32-bit file while `arecord -f S24_LE` captures
24-in-32, and the raw conversions differ. Those cells reported PATTERN NOT FOUND
and carry no information.

## Consequences

- **moOde's `alsa-lib` patch is even less relevant than Finding 002 concluded.**
  There was no meter defect to work around on this hardware.
- **ADR-0011's logged alternative loses its motivation.** Computing levels
  ourselves was recorded partly as an escape from this defect. The defect does
  not exist; the alternative stands or falls on its other merits.
- The metering path has no known defect.

## Reproduction

```bash
sudo modprobe snd-aloop
cd /tmp
sox -n -r 192000 -b 32 -c 2 src.wav synth 5 whitenoise vol 0.8
arecord -D hw:Loopback,1,0 -f S32_LE -r 192000 -c 2 -d 9 cap.wav &
sleep 1
aplay -D looptest src.wav
wait
sox src.wav -t raw src.raw
sox cap.wav -t raw cap.raw
python3 - <<'EOF'
src = open('/tmp/src.raw','rb').read()
cap = open('/tmp/cap.raw','rb').read()
i = cap.find(src[:16384])
seg = cap[i:i+len(src)]
n = min(len(seg), len(src))
d = [k for k in range(n) if seg[k] != src[k]]
print(f"differing: {len(d)}")
if d:
    print(f"first: {d[0]}  last: {d[-1]}  contiguous: {d == list(range(d[0], n))}")
EOF
```

**Run this more than once.** A single clean result means nothing — see
Finding 004.
