# ADR-0175 — Room correction for the bass

**Status:** **Built** 2026-11-06, in 1.14.0 (Testing serial 66). **Accepted**
2026-11-03 (George: decisions 1-6), Phase 29
(`ph-room-correction`). How is Claude's proposal; the decisions are George's.
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
   line) and kept by the microphone's serial. Not yet verified: miniDSP's
   download address, and whether the UMIK-1 gives its calibration serial
   over USB; if it does not, the owner types the serial.
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

## Decided (George)

- **Decision 1, the target** (2026-11-03): (b), a gentle rise below about
  80 Hz (+3 dB), over flat and over the owner choosing. With cuts only
  (decision 2) the rise means the correction cuts less down there; it never
  lifts the deep bass.
- **Decision 2, boosts** (2026-11-03), as recommended: none, cuts only.
- **Decision 3, the bass limit** (2026-11-03), as recommended: 250 Hz, fixed.
- **Decision 4, the calibration file** (2026-11-03): (b), the player
  downloads it from miniDSP by the microphone's serial, over giving it from
  the phone.
- **Decision 5, the after** (2026-11-03), as recommended: measured again at
  every position, with the correction on.
- **Decision 6, the microphones** (2026-11-03), as recommended: the UMIK-1
  only at first; George has one to measure with.

**The flow on the phone** (2026-11-04, from a clickable mock-up of made-up
curves; three questions it raised, then one that followed):
- **Moving the microphone**: a tap at each position once the microphone is
  in place, then a 3-second countdown before its sweeps; it does not carry
  on by itself.
- **The check** (decision 5) can be skipped: the correction is kept as
  designed, and the result shows the predicted after, marked as not checked
  until the room is measured again.
- **A/B is a switch that stays** where the owner puts it, not a hold; it is
  saved for each output like the on/off switch and kept in backups. Set to
  *without*, the stage stays in the path with the cuts at 0 dB (item 2);
  *off* takes it out. The design keeps the two apart, and the volume drawer
  shows when *without* is set.

The brief for Claude Design: `design/briefs/29-room-correction.md`.

**The design** (Claude Design, 2026-11-05, `design/source/29/`), and
George's answers on it (2026-11-05):
- **The check waits for a tap at each position**, as the run does, with its
  countdown; Skip on every check screen. The design drew it walking the
  positions by itself, which George's flow decision rules out.
- **A run waiting for a tap is cancelled after 10 minutes**, the output left
  as it was; a sweep under way always finishes. The panel and the bars stay
  display-only while it measures.
- **Its proposals kept as drawn**: the panel's *Measure from your phone*
  sheet with a QR code and the player's address; the *Room* control (On and
  Without one tap; *Off* opens the page; none on an output never measured;
  dimmed and inert while DSD plays); *Hear it without* in its own card,
  tagged A/B and amber (the theme's warn colour) wherever *Without* shows;
  and its new copy, verbatim.

**Decision 4 changed** (George, 2026-11-05): **the owner gets the 90° file
from miniDSP's page and gives it to the player**, over the player
downloading it. Found while building: miniDSP has no API - the file comes
from an undocumented script behind their page's form
(`/scripts/umikcal/umik90.php/<serial>_90deg.txt`), behind Cloudflare, which
refused a script's request; their website's terms forbid automated tools
gathering data without written consent. **The UMIK-1 does not give its
serial over USB** (its USB serial is a placeholder, as three projects report);
the file's first line does (`"Sens Factor =-0.667dB, AGain =18dB, SERNO:
7103946"`), so with the file the owner types nothing on the player.

**The level** (George, 2026-11-05): **from the room's own noise** - the
quiet room heard first, then about 20 dB above its noise in the bass,
between 55 and 65 dB, and *too quiet* only below 55 dB - over 75 dB fixed
(item 4) and over 65 or 60 dB fixed. The 75 dB was Claude's, carried from
home-cinema calibration without a reason this player needs it; on sofapi's
first run it took the amplifier turned up three times to reach, and George
found it far too loud. **Then 60 at most** (George, the same day, after the
second run): 50 to 60 dB from the room's noise, taken from 45 dB when the
ceiling is reached short of the aim. **Measure answers at once and Cancel is
instant** (George): the run shows *place* while the player is prepared
behind it; Cancel stops the sound at once, and the player is put back after.

**After sofapi's first full run** (George, 2026-11-05, three decisions on its
chart: the left speaker's main peak at 45 Hz cut by 2 dB, the right's by 1):
- **Most positions decide a cut** (item 6, criterion 2 changed): a cut is
  held back only when more than half the positions would end more than 1 dB
  further from the target, over any one position doing so and over the
  average alone. On sofapi position 4 read 14-15 dB under the other four at
  45-47 Hz on both speakers, already at or under the target, and held both
  cuts back; with most positions deciding they are 12 and 11 dB.
- **Three positions** (item 5): the head and 40 cm to either side, over five
  and over the head alone - about 3 minutes instead of 5½, two of three
  still deciding a cut. The cost: the target's level rests on fewer places
  (on sofapi three instead of five moved it by 2 to 3.5 dB).
- **60 dB in every room** (item 4), the most allowed, over 50 to 60 from the
  room's noise and over 55: at 50 dB (−18 dBFS) sofapi's run swept 12 times
  more than the two a position needs, and one position's left speaker never
  had two sweeps agree in six.
- **How deep** (item 6): as deep as bringing the peak to the target takes,
  no cap at 12 dB in all - the aim is the target. Cuts stack where one is
  not enough, each still up to 12 dB: redesigned from sofapi's positions
  1-3, the left's 46 Hz peak takes two (15.4 dB together), and the stacked
  design leaves 0.85 dB RMS above the target where one deeper cut leaves
  1.26 (it loses the cut at 68 Hz). The screens list cuts at one frequency
  as one line.
- **Boosts**: decision 2 stands, none; George asked for their pros and cons
  the same day (Claude's answer: cuts only). The one dip all three of
  sofapi's positions share, the right's
  at 85-113 Hz, is 8 to 18 dB deep and moves from place to place - a
  cancellation - and option (b)'s +3 dB would lift it by about 2.
- **Both speakers together** (item 4), swept at each position after each
  alone, before in the run and after in the check, over the check only:
  what is heard is the two adding at the seat, which neither alone shows,
  and the store keeps levels, not the timing a sum would need. Shown as a
  third tab, never designed from; 6 dB lower each, so no louder than one.
  About 45 s more for the run and for the check.

**What else the microphone is** (research, 2026-11-05, sources kept outside
the repository): USB `2752:0007`, product *Umik-1  Gain: 18dB* (ALSA's card
id `U18dB`); 24-bit at 48 kHz only (`S24_3LE`), stereo on older units and
mono on newer; a capture volume. The 90° file is `<serial>_90deg.txt`, about
615 points from 10 Hz to 20 kHz, the microphone's response (subtracted);
miniDSP has changed files' sensitivity lines without renaming them. **The
sensitivity's meaning is not published**: REW reads it as the RMS level at
94 dB SPL at the capture's full volume, which this follows - so a level in
dB SPL here is approximate (two readings of it differ by 6 dB) until checked
against a calibrator.

## Settings (ADR-0022)

Appended to the inventory 2026-11-03 to 2026-11-05, confirmed by George:
- **[N]** Room correction on and off, for each output.
- **[N]** The measurement and its design, for each output (internal).
- **[N]** A microphone's calibration, by its serial (given as a file,
  2026-11-05).
- **[H]** The target: a gentle rise below about 80 Hz (decision 1).
- **[H]** The bass limit, 250 Hz (decision 3).
- **[H]** Three positions (George, 2026-11-05, over five), eight cuts of up
  to 12 dB, stacked where a peak needs more (George, 2026-11-05); the level
  60 dB SPL (George, 2026-11-05, over 75 dB and over 50
  to 60 from the room's noise).
- **[N]** A/B, with or without, for each output (2026-11-04).
- **[H]** A 3-second countdown at each position (2026-11-04).
- **[H]** A run waiting for a tap is cancelled after 10 minutes (2026-11-05).

## While building

On `ph-room-correction`, 2026-11-05; what differs from the proposal above:

- **The cuts follow the bands** in the stage, not before them (item 1): a
  `Filter` step for each speaker after the equaliser's; inside CamillaDSP's
  64-bit pipeline the order changes nothing. All sixteen slots are in the
  pipeline whenever the stage runs.
- **The level step** raises the noise digitally from −54 dBFS, never above
  −12 dBFS, with the output at 100 % of its *Maximum volume* for the run
  (Fixed stays fixed) and put back after - so "never above the output's
  maximum level" holds by construction. The noise is raised only while the
  microphone follows it: four steps that do not move its reading stop the
  run as *too quiet* (an unplugged or covered microphone does not make it
  louder). For 60 dB (George) the sweeps go further than the noise, whose
  peaks are near full scale at −12 dBFS: set from its last reading, the
  chain being linear, up to −6 dBFS, where a sweep's peaks are at about
  −1.5 dBFS.
- **The level before a run is the DAC's own** (its raw level, kept in the
  store and put back through the volume bridge), not the percentage shown:
  that is the playing renderer's own number while one is active. Kept as a
  percentage, two runs on sofapi put the output back at 100 %. While a run
  holds the level up, the software level kept across restarts stays the one
  before it.
- **A player in a group** does not measure (it plays into the group's
  loopback, and the others would play the sweeps): *Leave the group to
  measure the room.*
- **A run waiting for a tap** - Start, Measure here, Check it, Keep it, Try
  again - is cancelled after 10 minutes; a sweep under way finishes. Cancel
  stops at once.
- **The sensitivity** read as REW reads it (94 dB SPL minus the file's
  sensitivity line, at full capture volume): on sofapi a quiet room read
  −48 dBFS RMS, unweighted - 47 dB SPL that way, 77 dB the other reading,
  so the first fits a quiet room. Still to check against a calibrator, or
  another meter.
- **Two sweeps agree** within 1.5 dB from 20 to 250 Hz (1/6 octave), up to
  six tried; a made-up thump of −20 dBFS below 300 Hz spoils one by 2-3 dB.
  To be checked against the microphone's own repeats in a quiet room.

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
