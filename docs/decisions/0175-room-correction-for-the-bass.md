# ADR-0175 — Room correction for the bass

**Status:** **Proposed** 2026-11-03, Phase 29 (`ph-room-correction`). How is
Claude's proposal; the decisions below are George's.
**Builds on:** [ADR-0162](0162-a-simple-equaliser.md) (the equaliser's filter
stage) and [Finding 124](../findings/124-room-correction-what-open-source-offers.md)
(what open source offers, the microphones). **Followed by:** Phase 30
(`ph-room-correction-full`).

## Context

**What George set for this phase** (`docs/DEVELOPMENT.md`, Phase 29; 2026-10-14
and 2026-10-20): the player measures the room through a USB measurement
microphone at the listening seat and corrects what the room does. This phase
corrects only the bass, below the room's Schroeder frequency (about 200-300 Hz
in a living room), where its modes do most harm; several positions around the
seat (3-5 within about half a metre of the head), averaged; mostly cuts, no
deep boosts into nulls. The full range, with more positions and a target
curve, is Phase 30.

**What is there already** (ADR-0162, in 1.7.0):
- CamillaDSP on the shared path: with the equaliser on, `output` goes to an
  ALSA loopback that CamillaDSP captures and plays to the card. The core sets
  it up and changes its gains over the websocket without a restart.
- It starts at each stream's rate (12-24 ms off a stream's start), and
  converts a rate the card lacks.
- Native DSD goes past it untouched; the meters read before it; *Off* takes
  CamillaDSP out of the path, bit-perfect; changing the path restarts the
  renderers (C7).
- Headroom: the signal is lowered by the curve's highest point, and the
  volume gives it back (Hardware and Software, not Fixed).
- One setting per output, by the card's id, in the settings store.
- Ten Peaking filters cost 2.3 % of one core at 44.1 kHz and 4.9 % at
  192 kHz ([Finding 138](../findings/138-the-equaliser-on-a-loopback-first-measurement.md)).

**From Finding 124:** the miniDSP UMIK-1 first (driverless USB Audio Class 1,
per-serial calibration files for 0° and 90°, 24-bit at a fixed 48 kHz); the
microphone's and the DAC's clocks drift apart; a measurement must take
`output` and play through the same chain as music; an AV receiver may add a
correction of its own.

## Proposed (Claude)

1. **The correction is a set of cuts in the equaliser's CamillaDSP stage**:
   up to eight Peaking filters per channel below the bass limit, each a
   frequency, a cut and a width, before the equaliser's ten bands. Not a
   convolution (FIR): CamillaDSP computes a Peaking filter at the rate each
   stream has, so one correction serves 44.1 to 768 kHz with nothing made
   per rate or resampled. A room mode is a peak at one frequency, which a
   Peaking cut matches; HiFiBerry's roomeq and REW's automatic EQ work this
   way (Finding 124). Correction in time, which needs a FIR, is Phase 30's.
2. **The equaliser and the correction are two switches over one stage.**
   Either on puts CamillaDSP in the path (C7: the renderers restart); both off
   take it out, bit-perfect as today. With the stage in the path, the
   correction's A/B sets its cuts to 0 dB in the running CamillaDSP: heard at
   once, no restart. A Peaking filter at 0 dB has cancelling coefficients;
   whether the stage is then bit-exact is measured, not assumed.
3. **Headroom, volume types and DSD as the equaliser has them.** Cuts need no
   headroom; a boost (decision 2) joins the curve ADR-0162 D3 lowers by,
   given back by the volume. Native DSD goes past uncorrected, and the row
   says so while DSD plays.
4. **The measurement plays and records through the player.**
   - It takes the device as a source taking over does: what plays stops
     politely, and nothing else takes it until the measurement ends or is
     cancelled.
   - The sweeps go through `output` with the equaliser and the correction
     out of the stage: the room as it is, through the same card, volume and
     amplifier as the music.
   - **Each channel alone**: a mode is excited differently from each
     speaker's place, so left and right are measured and corrected each on
     its own.
   - A logarithmic sweep from 10 Hz to 1 kHz, about 5 s, twice per channel
     and position; the impulse response by deconvolution; its magnitude from
     15 to 500 Hz, the calibration file applied.
   - **Clock drift is left aside here**: magnitude below 500 Hz is all this
     phase uses, and 100 ppm between two crystals (to be read from a
     recording) moves a 300 Hz mode by 0.03 Hz. Phase 30's correction in
     time needs it.
   - **Level**: a short pink-noise burst, raised in steps until the
     microphone reads about 75 dB SPL by its calibration, never above the
     output's maximum level; a room or microphone that does not get there
     stops with the reason.
   - **Quiet**: the noise floor read before each sweep; a sweep is repeated
     when the two of a position disagree (a door, a voice).
5. **Positions**: five, the first where the head is (it sets the level), the
   others within about half a metre around it; the phone says where next.
   The average is of power, smoothed to 1/6 octave below the limit.
6. **The design**, in the core, with numpy (already in its environment; no
   pyfar, DRC-FIR or SciPy):
   - the target from decision 1, its level set by the average an octave
     above the limit, so the correction blends into what is left as it is;
   - the highest peak of the average above the target gets a Peaking cut
     fitted to its height and width, repeated up to eight times while a peak
     stands more than 1 dB above; then the cuts are fitted together (least
     squares on their gains and widths);
   - cuts up to 12 dB, Q from 1 to 15 (to be checked against measured
     rooms), nothing above the limit, boosts as decision 2;
   - a cut that makes any one position worse by more than 1 dB at its
     frequency is reduced until it does not (criterion 2: no position
     measurably worse).
7. **Before and after are shown**, the averaged response before, the target
   and after, with each position's curve (decision 5 for how the after is
   got).
8. **Where**: *Settings → Audio → Room correction*, beside the equaliser,
   for each output: its switch, *Measure*, the last measurement's date and
   curves, and A/B. Started and followed on the phone, which the owner holds
   while moving the microphone; the panel shows that a measurement is
   running.
9. **The microphone** is found by its USB identity, not its ALSA name (the
   UMIK-1's name carries its gain), its gain set explicitly. Its calibration
   (decision 4) is the 90° file, the microphone pointing at the ceiling at
   every position, checked as one (frequency and dB columns, a sensitivity
   line) and kept by the microphone's serial.
10. **What is kept**: for each output the measurement (average and
    positions at 1/24 octave, a few kB), the design and the switch; each
    microphone's calibration. In the settings store, so in backups and
    cleared by a factory reset.
11. **The API**: documented as the equaliser's is (ADR-0162 D9), internal
    until the phase closes.
12. **Multiroom**: each player has its own correction; the stage adds no
    delay beyond what the equaliser adds already.

### Decisions for George

- **Decision 1, the target.** (a) **Flat**, *recommended* for this phase:
  the bass as the speakers would play it without the room's modes; (b) a
  gentle rise below about 80 Hz (+3 dB), the "house curve" Dirac and REW
  offer; (c) the owner chooses between the two. Phase 30 brings a target over
  the full range.
- **Decision 2, boosts.** (a) **None**, *recommended*: cuts only - a dip at
  the seat is mostly a cancellation that more power does not fill, and a
  boost costs headroom and amplifier power; (b) up to +3 dB, only over a dip
  wider than a third of an octave that every position shows.
- **Decision 3, the bass limit.** (a) **250 Hz, fixed**, *recommended*:
  inside the 200-300 Hz the plan names; (b) the owner chooses 150, 200, 250
  or 300 Hz.
- **Decision 4, the calibration file.** (a) **Given from the phone**,
  *recommended*: downloaded from miniDSP by the microphone's serial and
  picked on the phone; (b) the player downloads it from miniDSP by the
  serial - one step less, but it rests on a web page of miniDSP's, not an
  API.
- **Decision 5, the after.** (a) **Measured again at every position**,
  *recommended*: about a minute more, and it is what shows that no position
  is worse; (b) predicted from the design only.
- **Decision 6, the microphones.** (a) **The UMIK-1 only** at first,
  *recommended*: the one Finding 124 found used on Raspberry Pis; others
  listed untested once someone tries them; (b) also the Dayton Audio iMM-6C
  and UMM-6 from the start, untested.

## Settings (ADR-0022)

Proposed, appended to the inventory only after George confirms:
- **[N]** Room correction on and off, for each output.
- **[N]** The measurement and its design, for each output (internal).
- **[N]** A microphone's calibration, by its serial.
- **[?]** The target (decision 1) and the bass limit (decision 3).
- **[H]** Five positions, eight cuts of up to 12 dB, 75 dB SPL.

## Measured before it is called done

- DEVELOPMENT.md's acceptance 1-4.
- The stage's cost with the equaliser and the correction at 44.1, 96 and
  192 kHz, the visualiser running.
- The A/B at 0 dB compared bit for bit through the stage.
- The clocks' drift, read from a recording (4).
- The level step never above the maximum level, on Hardware, Software and
  Fixed.

## Not in this phase

- Above the bass, correction in time, a target over the full range: Phase 30.
- Subwoofers and more than two channels.
