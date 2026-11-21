# Finding 156 — Room correction's stage on sofapi: its cost, *Hear it without*, and the cuts read back

**Date:** 2026-11-21. **For:** what Phases 29 and 30 left unmeasured
(to-dos `ph29-room-correction` and `ph19-room-full`):
- the stage's cost at 44.1, 96 and 192 kHz;
- whether *Hear it without* is bit-exact;
- the cuts read from CamillaDSP while a stream plays.

Measured at George's word (2026-11-21), with nothing heard and no setting
written.

## Scope

- **Device:** sofapi, Raspberry Pi 4 Model B. It runs gexis-core
  1.18.0+git22 (the Phase 37 research build), whose stage code is 1.18.0's,
  with CamillaDSP 4.1.3. The player was idle: no sound device open, before
  and during.
- **The stage as stored:**
  - room correction on, *Full range*, *Hear it without* off;
  - 11 filters active on each speaker;
  - the equaliser off, so its ten bands are at 0 dB.

  Read from the settings database read-only. The stage was built with the
  core's own `equaliser.camilla_config` and `Room.stage`.
- **Cost:** a second CamillaDSP ran that configuration, fed white noise at
  −20 dBFS on stdin by a feeder paced to the stream's rate, and wrote to
  `/dev/null`. For each rate:
  - its CPU over 20 s, from `/proc`;
  - its own processing load, read each second.
  
  A first run, with CamillaDSP's signal generator and no pacing, ran as fast
  as the CPU allowed (state *Starting*, 116-124 % of a core). It measured
  nothing and is not used.
- **Bit-exact:** the same stage was built for *Hear it without* with the
  equaliser off. 10 s of random 32-bit samples at 44.1 kHz went through it
  from a raw file to a raw file, compared sample by sample. A control run
  had room correction playing.
- **Read back:** 6 s of digital silence (zeros, so nothing is heard) went
  into the player's own output (`pcm.output`) at 44.1 kHz. Meanwhile the
  live CamillaDSP's configuration (`GetConfigJson`, `127.0.0.2:1234`) was
  compared slot by slot with `Room.stage`.
- **Not measured:**
  - the loopback's own copy and rate adjust in the kernel;
  - the stage at 768 kHz;
  - the stage with the equaliser on (its bands are in the pipeline at
    0 dB either way, so they are computed regardless);
  - a player other than sofapi;
  - the stage on a *Bass*-only measurement.

## Results

| Rate | CamillaDSP's CPU (one Pi 4 core) | Processing load, mean / highest | Rate seen |
|---|---|---|---|
| 44.1 kHz | 3.4 % | 1.5 % / 2.3 % | 44,031 Hz |
| 96 kHz | 5.2 % | 3.0 % / 4.9 % | 95,303 Hz |
| 192 kHz | 9.3 % | 6.3 % / 9.9 % | 192,509 Hz |

The feeder took 1.5-1.7 % of a core, not counted above. The stage always
computes all its slots: the ten bands and fourteen room slots on each
speaker, idle ones at 0 dB included (`equaliser.ROOM_IDLE`). So the cost
does not depend on how many filters a measurement plays.

**Bit-exact:**
- With every room filter at 0 dB and the headroom fader at 0 dB, the stage
  passed **882,000 of 882,000 samples unchanged**.
- The control run, with the correction playing, changed every sample.
- **But on sofapi *Hear it without* is not bit-exact as stored.** Its
  *Full range* correction boosts by up to 3 dB, so the headroom is 3.0 dB.
  ADR-0177 item 7 keeps that headroom whatever plays, so *Hear it without*
  is 3 dB lower than the source. That is by design: the comparison stays
  level-matched.
- A *Bass* measurement only cuts, so its headroom is 0 and *Hear it
  without* would be bit-exact.

**Read back:** the live CamillaDSP ran (*Running*, 44,353 Hz seen). All
**28 room slots matched the stored design exactly**, 22 of them playing:
the largest difference in frequency, gain or Q was 0.000000.

## What it means

- **The cost:**
  - The stage costs about 3 % of one core at 44.1 kHz, 5 % at 96 kHz and
    9 % at 192 kHz, with the CPU's load within a chunk under 10 % at 192 kHz.
  - Phase 35's acceptance 4 (192 kHz with room correction) has its stage
    figure now. The rest of that check, a page from Home Assistant on screen
    at the same time, is still open.
- ***Hear it without* is level-matched rather than bit-exact** whenever the
  correction boosts. The manual already says so (`docs/manual/README.md`,
  room correction): the level stays the same across *Full range*, *Bass* and
  *Without*, the music lowered by up to 3 dB and given back by the volume.
- **What the core designs is what plays**, filter for filter, at least at
  44.1 kHz on sofapi.
