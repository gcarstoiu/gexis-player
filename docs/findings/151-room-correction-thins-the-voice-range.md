# Finding 151 — Room correction in the bass, on sofapi: each speaker cut alone takes about 5 dB from what is heard together at 80-190 Hz; cuts designed from both together would not

**Date:** 2026-11-17. **Asked by:** George: with room correction on (*Bass*),
the sound seemed small and thin, as if the voices lost something too.
**For:** [ADR-0175](../decisions/0175-room-correction-for-the-bass.md),
whose bass cuts are designed for each speaker alone.

## Scope

- **Device:** sofapi (Pi 4) through its USB DAC; the measurement stored by
  its run of 2026-11-10 (three positions, *Bass*), with that run's check -
  the after, measured with the cuts on, each speaker alone and both
  together.
- **Read:** the stored filters and curves (read-only); each speaker's cuts
  summed with the core's own Peaking response (`room_dsp.peaking_db`, at
  48 kHz); the cuts redesigned from the *Both* sweeps with the core's own
  `room_dsp.design` and the same target.
- **Not measured:** a new run; the redesigned cuts played (their *after* is
  predicted - exactly, as the same cuts on both speakers scale their sum);
  the speakers' placement; listening tests.

## Results

| | Left | Right |
|---|---|---|
| The room against the target, 80-110 / 110-140 / 140-190 Hz | +9.8 / +11.8 / +8.9 dB | −11.6 / −5.0 / −3.5 dB |
| The same, at each of the three positions, 80-110 Hz | +9.7, +8.8, +10.6 | −16.6, −11.0, −10.2 |
| The cuts | 46 Hz (two, −16.3 together), 68 Hz −8.2, 121 Hz −11.1 (Q 2.1), 172 Hz −5.5, 216 Hz −6.0 | 46 Hz (two, −14.8), 63 Hz −5.0, 226 Hz −2.7 |
| The cuts' sum at 100 / 121 / 172 / 216 Hz | −9.4 / −12.9 / −10.0 / −8.9 dB | −0.4 / −0.2 / −0.2 / −1.8 dB |
| Pink noise through the cuts, 85-255 Hz | −7.9 dB | −0.5 dB |

| Both speakers together | 30-55 Hz | 55-80 | 80-110 | 110-140 | 140-190 | 190-250 |
|---|---|---|---|---|---|---|
| Before, against the target | +7.8 | +6.0 | +3.0 | +4.4 | +0.7 | +1.4 |
| Change, the cuts as they are (measured in the check) | −7.9 | −6.9 | **−8.1** | **−9.8** | **−5.5** | −1.6 |
| Change, cuts designed from *Both* (predicted) | −8.0 | −4.8 | −1.2 | −2.7 | −1.0 | −0.7 |
| After, against the target: as they are / redesigned | −0.1 / −0.2 | −1.0 / +1.1 | **−5.1** / +1.8 | **−5.4** / +1.7 | **−4.9** / −0.4 | −0.1 / +0.7 |

Designed from *Both*, the same on both speakers: 46 Hz (two, about −16
together), 59 Hz −4.1, 131 Hz −3.7 (Q 5), 218 Hz −1.5. The predicted change
is the redesign's own, added to the stored before (the redesign's offset
came out 1.15 dB from the stored one, so only changes are compared). The
measured change carries the run-to-run difference too: 1.7 dB at 250-300
Hz, where the cuts do almost nothing. Distance from the target over 20-250
Hz, as heard: 7.9 dB RMS before, 6.5 with the cuts as they are, 5.5
redesigned. The check also found one position of three made worse by
2.3 dB.

## What it means

1. **The two speakers disagree by up to 21 dB at 80-110 Hz**, the same at
   every position: the left has a broad peak, the right a deep dip
   (ADR-0175 already named it a cancellation, 8 to 18 dB deep). Heard
   together they nearly made up for each other: *Both* was only 3-4 dB
   above the target there.
2. **Correcting each speaker alone takes that away.** The left's peak is
   cut to the target, the right's dip cannot be filled (cuts only), so what
   is heard at 80-190 Hz ends about 5 dB *below* the target - 5.5 to 10 dB
   less than before. Voices' fundamentals (about 85-255 Hz) and their body sit
   there: what George heard.
3. **Designing from both together would not.** The sweeps of both speakers
   are already taken at each position (ADR-0175 item 4, shown but never
   designed from). Cuts designed from them keep 80-190 Hz within 2 dB of
   the target, still take the 46 Hz mode down, and land closer to the
   target overall. The cost: a speaker's own peak heard alone - bass panned
   hard to one side - is cut only as far as the sum needs.
4. **A placement may cause the disagreement** (not measured): a wall 0.76 to
   1.0 m from a speaker cancels its sound at 85-113 Hz (a quarter
   wavelength), and a corner lifts a speaker's bass. Moving a speaker
   changes both, and a new run would show it.
