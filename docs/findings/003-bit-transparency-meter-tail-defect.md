# Finding 003 — bit-transparency, and a tail defect in the meter plugin

**Date:** 2026-09-04
**System:** `rig` — as Finding 002.
**Question:** Does `type meter` with the peppyalsa scope alter samples?
**Answer:** Not in the interior. It loses frames at the end of a stream under
some conditions.

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

Source material is white noise, not sine — a sine wave has too much structure
to expose subtle errors. `sox` reported clipping during generation; that is
baked into the source file, so both sides of the comparison see the same data.
Not a confound.

Procedure: start `arecord` on `hw:Loopback,1,0`, sleep 1 s, `aplay` into
`looptest`, then locate the source pattern inside the capture and compare
byte-for-byte from that offset.

## Results

| Condition                   | Meter plugin | Result |
|-----------------------------|--------------|--------|
| S16_LE / 44100, 5 s         | in path      | bit-identical, all 960 000 frames, tail included |
| S32_LE / 192000, 5 s        | in path      | 959 232 frames identical; **last 768 frames absent** |
| S32_LE / 192000, 5 s        | **removed**  | bit-identical, all frames |

The control is the decisive line. Same source, same loopback, same capture
length, same comparison — meter plugin removed, zero differences.

### Establishing the defect is real, not an artefact

Two hypotheses were tested and one eliminated.

**Hypothesis: capture-window truncation.** Rejected. Capture window was extended
from 7 s to 9 s. The offset of the source within the capture moved (1 548 288 →
1 560 576 bytes) but the differences stayed pinned to **byte 7 673 856 of the
source**, with identical count and identical first and last differing byte. The
boundary is fixed to the source, not the capture.

**Hypothesis: the meter plugin.** Supported by the control run above.

### Shape of the loss

```
first differing byte : 7 673 856
last  differing byte : 7 679 999
span                 : 6 144 bytes
differing bytes      : 6 110
contiguous           : no (34 bytes within the span coincidentally match)
clean prefix         : 99.9200%
```

7 673 856 ÷ 8 bytes per frame = 959 232 frames. 960 000 − 959 232 = **768
frames**, which is 4 ms at 192 kHz. The 34 coincidental matches inside the span
are what you would expect from comparing audio against unrelated data by
chance, not from a partial fault.

The differing region is **terminal in every case** — never scattered. No
interior corruption at either extreme of the grid.

### Most likely mechanism — unverified

A final partial period not flushed on close. 768 is a plausible period size.
Candidates, none eliminated:

- alsa-lib's meter plugin not draining its last period
- peppyalsa's `level_stop` callback returning before the slave drains
- interaction with `aplay`'s drain sequence

Note that moOde's patch is described as *"PCM meter scope patches"* — the same
code area. Possibly unrelated, but Tim was working in this file.

### Note on the 44.1 kHz result

The first S16_LE/44100 run reported zero differences, but its capture window
truncated before the source ended, so **it never examined the tail**. A re-run
with a 9-second window was bit-identical including the tail. Both results stand;
the first simply did not look where the defect lives.

## What is established

Samples that pass through `type meter` + peppyalsa are **unmodified**. Verified
at both extremes of the format grid.

## What is not established

- Whether the variable is rate, format, data rate, or period size — two data
  points, four candidates, none eliminated
- The 16 intermediate grid cells
- Whether the loss occurs on every stream close or intermittently
- Whether the frames are absent or altered
- Whether `type copy` above the meter changes the behaviour
- The mechanism, which needs `pcm_meter.c` read
- Bearing on gapless playback — not thought through

## Assessment

768 frames at 192 kHz is 4 ms at the very end of a stream, at a track boundary
or stop. It is not audible as a defect and does not affect steady-state
playback.

But "bit-perfect" is the product's central claim, and a known systematic sample
loss — however small — must be characterised or fixed before that claim is made
in writing.

**Investigation stopped here deliberately.** Filling the grid is 16 more runs;
finding the mechanism means reading alsa-lib's meter implementation. Both are
worth doing. Neither was worth doing before the repo existed.

**Recommended next action:** fill the grid as an early hardware-in-the-loop test
on the self-hosted runner. This is exactly the class of thing that tier is for.

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
diffs = [k for k in range(len(src)) if seg[k] != src[k]]
print(f"differing: {len(diffs)}")
if diffs:
    print(f"first: {diffs[0]}  frames lost: {(len(src)-diffs[0])//8}")
EOF
```

Swap `looptest` for `hw:Loopback,0,0` for the control.
