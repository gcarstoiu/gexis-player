# Finding 155 — Room correction in time: what the research shows

**Date:** 2026-11-21. **For:** Phase 34 (`ph-room-correction-time`). George
asked on 2026-11-21 for the research to be done again in full. He wanted to
know whether correcting the room in time has any support beyond the sellers'
own claims. This finding re-examines
[Finding 141](141-room-correction-above-the-bass-what-is-known.md)'s
time-domain section, which found no listening test in its favour.

"In time" here means mixed-phase or excess-phase FIR correction, the kind that
changes the impulse or step response at the seat. Dirac Live, Trinnov,
Audiolense, Acourate, Focus Fidelity and DRC-FIR correct this way. The
question was whether listeners can be shown to hear a benefit from it beyond
what the player already does. The player corrects the level only:
minimum-phase IIR filters from several positions averaged by power, plus delay
and level alignment between the speakers.

## Scope

- **Method.** Desk research only, on 2026-11-21, in four parallel searches:
  - the controlled listening tests;
  - the psychoacoustics of what correction in time changes;
  - the physics and the costs;
  - the sellers' claims against their evidence.
  
  The searches were written up together afterwards. They were run fresh and
  were not handed Finding 141. Each one was asked to give the strongest case
  for correction in time as well as against it, and to grade every source.
  Nothing was run on a player.
- **Read in full:**
  - Toole 2015 (JAES);
  - both Aalto group-delay studies (Liski et al. 2018 and 2021);
  - Fazenda, Stephenson and Goldberg 2015 (JASA);
  - Radlović and Kennedy 2000;
  - Norcross 2004 (Canadian Acoustics);
  - the 2026 JASA preprint by Brooks-Park et al.;
  - Welti and Devantier 2006;
  - Dirac's patent US8194885;
  - two master's theses (Aalborg 2007; Chalmers 2026).
- **Abstract or secondary account only:**
  - the developers' own listening tests;
  - Harman 2009 (read through its author's blog);
  - Brännmark and Ahlén 2009;
  - Fielder 2003;
  - Hatziantoniou and Mourjopoulos 2004;
  - Mäkivirta et al. 2003;
  - Lipshitz et al. 1982;
  - Johansen and Rubak 1996;
  - Choisel and Martin 2008;
  - Antsalo et al. 2004.
- **Not reachable:**
  - the AES E-Library (no AES paper read in full);
  - MDPI, so Cecchi, Carini and Spors's 2018 review was not read;
  - dirac.com (HTTP 429), so Dirac's wording is taken from search excerpts;
  - Genelec's, B&O's and Audioholics' pages, also read as excerpts.
- **Not re-confirmed:** Finding 141's "typically around 7 ms" for Dirac's
  added delay. No Dirac page, FAQ or patent with that figure could be
  fetched this time. The figures that were found are 23 ms on miniDSP's
  hardware running Dirac Live, and up to 5 ms more for its LFE low-pass.

## Results

### 1. No published test isolates the time part

No blind, level-matched test was found that keeps the magnitude correction
the same and switches only the excess-phase part on and off, with music,
through loudspeakers in a room. Every other test changed magnitude and phase
together, or compared against no correction.

| Study | Run or funded by | Compared | Result |
|---|---|---|---|
| [Hatziantoniou, Mourjopoulos, Worley 2005](https://aes.org/publications/elibrary-page/?id=13177) | the method's developers (Patras) | their complex-smoothing correction against loudspeaker-only EQ and none | "significant improvement"; panel, blinding and level matching not in the abstract |
| [Primavera, Cecchi et al. 2012](https://aes.org/publications/elibrary-page/?id=16187) | the method's developers (Ancona) | mixed-phase multipoint EQ against their own earlier method | improvement; no magnitude-only condition |
| [Bahne 2010/2012](https://aes2.org/publications/elibrary-page/?id=16163) | Uppsala; the author is a co-inventor on Dirac's [US9781510](https://patents.google.com/patent/US9781510) | FIR-"optimized" small loudspeakers against the originals | significant preference; whether excess phase was corrected, and blinding, unknown |
| [Radlović & Kennedy 2000](https://users.cecs.anu.edu.au/~rod/papers/2000/00876311.pdf) | ANU | minimum-phase against full mixed-phase inversion, speech, one exact point | minimum phase left "a resounding metalic noise, resembling a bell chime"; mixed phase sounded like the clean speech; informal |
| [Norcross, Soulodre, Lavoie 2002-04](https://jcaa.caa-aca.ca/index.php/jcaa/article/download/1675/1422/1812) | Communications Research Centre, Canada (no product) | inverse filters; double-blind MUSHRA over headphones | can rate below no filter, through pre-echo and timbre changes; worse for non-minimum-phase responses |
| [Olive et al. 2009](https://seanolive.blogspot.com/2009/11/subjective-and-objective-evaluation-of.html) | Harman (two of the five were its own prototypes) | five products and none; double-blind, level-matched, 8 trained listeners, mono | three strongly preferred to none, one equal, one "very poor"; explained by steady-state magnitude; phase not analysed; products anonymised |
| [Brooks-Park, Bech, Østergaard, van de Par 2026](https://arxiv.org/html/2604.12439) | Oldenburg, Aalborg and B&O; EU Horizon 2020 | none, a minimum-phase inverse, an unnamed commercial correction, their own; 8 experts, loudness-matched, stereo | commercial against none p = 0.154 (power 0.35); the minimum-phase inverse worse than none (p < 0.001, d = 1.7) |
| [Günther & Lacouture Parodi 2007](https://projekter.aau.dk/projekter/files/9797324/Report_07gr1064.pdf) | Aalborg master's thesis | all-pass phase distortion through loudspeakers in a listening room | not audible through loudspeakers for any signal |

The notes disagree on the Radlović and Kennedy panel: either the two
authors through a small loudspeaker, or 13 subjects on headphones.

Below this level, nothing separates time from magnitude.
- **Enthusiast test.** In a 2021
  [AV Nirvana](https://www.avnirvana.com/threads/dsp-eq%E2%80%99ing-full-range-or-not-%E2%80%93-testing-the-ears.8992)
  comparison of Dirac full-range against partial-range correction, with three
  listeners and an operator who was not blind, the differences were slight.
- **Press reviews.** They are sighted and disagree with each other.
- **Vendors.** No vendor-published blind test of a time-domain feature was
  found.

### 2. The case for it is mechanism, not outcome

- **Rooms are non-minimum-phase.** Neely and Allen found synthetic rooms
  minimum-phase only below about 33-40 % wall reflectivity
  ([1979](https://jontalle.web.engr.illinois.edu/Public/Allen-pdf/NeelyAllen79.pdf)).
  Toole agrees that the interference above the transition "are
  non-minimum-phase phenomena that are not correctable by minimum-phase
  equalization" ([2015](https://linkwitzlab.com/Toole-Room%20calibration.pdf)).
- **The room's group delay is large next to the thresholds.** Rooms vary by
  "up to several tens of milliseconds". The ABX thresholds were about
  −0.56/+0.64 ms with a pink impulse, and 1.5-4.5 ms (positive) and −1.0 to
  −2.3 ms (negative) with real percussive sounds, over headphones
  ([Liski, Mäkivirta, Välimäki 2021](https://acris.aalto.fi/ws/portalfiles/portal/66449704/Audibility_of_Group_Delay_Equalization.pdf); Genelec part-funded).
- **Excess phase has been heard under idealised conditions.** These are
  Radlović and Kennedy (above) and
  [Johansen and Rubak 1996](https://www.aes.org/e-lib/browse.cfm?elib=7591),
  who found it audible on headphones but masked by the minimum-phase part.
- **Decay, not flatness, drives bass preference.** Fazenda and colleagues
  (JAES 2012, 20 listeners, 8 systems) found preference followed the decay
  time of the bass. The systems were mostly subwoofer layouts
  ([record](https://eprints.hud.ac.uk/id/eprint/17980), abstract only).
- **Phase between the channels.** Inter-channel phase differences from
  mismatched crossovers were audible over loudspeakers
  ([Choisel & Martin 2008](https://www.aes.org/e-lib/browse.cfm?elib=14711)).

### 3. The case against: controlled tests, physics, pre-ringing

- **Inverting a room has measured harm.**
  - Norcross (above).
  - Real-time inversion distorted "far greater in magnitude" than
    simulation predicted
    ([Hatziantoniou & Mourjopoulos 2004](https://www.aes.org/e-lib/browse.cfm?elib=13017)).
  - Practical equalisation is limited to "minimum-phase filters of
    relatively low order" ([Fielder 2003](https://aes2.org/publications/elibrary-page/?id=12249), Dolby).
- **It holds only near the microphone.** An exact inverse holds within about
  a tenth of a wavelength
  ([Radlović, Williamson, Kennedy 2000](https://researchportalplus.anu.edu.au/en/publications/equalization-in-an-acoustic-reverberant-environment-robustness-re/)).
  That is 34 cm at 100 Hz, 17 cm at 200 Hz and 3.4 cm at 1 kHz, so above
  about 200 Hz it cannot hold at both ears of one listener. DRC-FIR's manual
  warns of "unacceptable results for positions which are even few
  millimeters apart" ([manual](https://drc-fir.sourceforge.net/doc/drc.html)).
- **Dirac's own research basis makes the point.** Brännmark and Ahlén found
  that even the optimal multipoint mixed-phase filter pre-rings and overfits,
  and that using it directly "is questionable from a perceptual point of
  view" ([IEEE TSP 2009](https://manuscript.isc.ac/Inventory/49/1083165.htm),
  abstract only).
- **Dirac's patent narrows it.** It inverts only the zeros that recur across
  positions and stay under a pre-ringing limit. Its example has a zero
  crossing the unit circle between positions "slightly above 200 Hz", and
  uses 18 positions ([US8194885](https://patents.google.com/patent/US8194885)).
- **Common and local.** Resonances (poles) are common to every position;
  zeros are local ([Haneda et al. 1994](https://doi.org/10.1109/89.279281)).
- **Above the bass it becomes speaker correction.** DRC-FIR: above 1-2 kHz
  room correction "actually reduces to just minimalistic speaker correction".
  A 2026 Chalmers thesis found minimum-phase IIR peak cuts worked best. Its
  mixed-phase FIR needed a 100 ms modelling delay and corrected only the
  first few milliseconds
  ([Hanuš 2026](https://odr.chalmers.se/bitstreams/4abeb375-ff44-4504-97e5-60aef334eb58/download)).
- **Pre-ringing is the failure listeners hear most.** Negative group delay
  (energy before the attack) was more audible than positive. A hi-hat
  masked the positive kind but not the negative (Liski 2021). Backward
  masking lasts only about 5-20 ms
  ([Liski et al. 2018](https://acris.aalto.fi/ws/portalfiles/portal/52513428/Audibility_of_Loudspeaker_Group_Delay_Characteristics_AAM.pdf)).
  A minimum-phase IIR filter cannot pre-ring.
- **Phase matters less in rooms, with music.**
  - Thresholds in rooms are about 2-2.3 times those on headphones (Fleischer;
    Flanagan et al.); Suzuki and Bech found no difference. These are
    secondary accounts.
  - Group delay below 1 ms at 300 Hz-1 kHz was inaudible. Below 200 Hz it
    exceeded 10 ms on model signals without being heard (Liski 2018).
  - Lipshitz, Pocock and Vanderkooy found no "present requirement for phase
    linearity in loudspeakers for the reproduction of music and speech"
    ([1982](https://secure.aes.org/forum/pubs/journal/?elib=3824)).
- **The bass's ringing is heard only past a threshold.**
  - With music, a mode's decay is heard from about 0.51 s at 63 Hz down to
    0.12 s at 250 Hz. With test tones the range is 0.9 s at 32 Hz to
    0.17 s at 200 Hz. Below the threshold, control is "likely to be
    perceptually meaningless"
    ([Fazenda et al. 2015](https://eprints.hud.ac.uk/id/eprint/24317/1/FazendaStephensonGoldberg-PerceptualThresholdsModalDecay.pdf)).
  - With the magnitude equalised, decays of up to 2 s at 50 Hz went
    unnoticed ([Antsalo et al. 2004](https://www.aes.org/e-lib/browse.cfm?elib=12752)).
  - For minimum-phase resonances, matched parametric filters correct "both
    the amplitude and time-domain problems" (Toole 2015, said of
    transducers). A cut whose frequency or Q is off can lengthen the decay or
    beat (cited in Fazenda 2015).
- **The cautious side has interests too.** Genelec part-funded the Aalto
  studies, and its GLM is minimum-phase. An author of Fazenda 2015 worked
  for Neumann. Harman tested its own prototypes.

### 4. What the sellers claim and cite

- **Who corrects in time:**
  - Dirac Live, in its full-bandwidth tier only;
  - Dirac Bass Control and ART (a US$299 add-on);
  - Trinnov;
  - Audiolense TTD;
  - Acourate;
  - Focus Fidelity;
  - Neumann MA 1, in part.
  
  None cites a controlled test that separates the time part from the
  magnitude part. Their evidence is their own claims, patents ("patented and
  exclusive", Trinnov) and plots at the main seat. Dirac claims a better
  impulse response "throughout the listening area". Item 3 contradicts that
  for the room above the bass. For ART with two stereo speakers, Dirac says
  only that they help each other "in principle".
- **Who stays minimum-phase, and why:**
  - **Anthem ARC** cites pre-ringing, delay ("something like one second" for
    FIR) and video sync. Its engineer Peter Schuck saw no advantage in FIR
    filters
    ([SoundStage! Access](https://www.soundstageaccess.com/index.php/feature-articles/997-anthems-peter-and-mark-schuck-on-subwoofer-integration-and-room-correction)).
  - **Genelec GLM** and **Sonos Trueplay** (which uses no phase
    information).
  - **REW**.
  - **Lyngdorf RoomPerfect**, which appears to: its description speaks only
    of amplitude targets.
  
  These makers cite no tests of their own either, but the peer-reviewed work
  in item 3 agrees with them.
- **Audyssey is unclear.** It advertises "frequency and time domains", but
  press accounts describe it inverting only the minimum-phase part.
- **Dirac itself is careful.** It told Sound & Vision that impulse-response
  correction "must be more conservative than frequency-response correction"
  because of pre-ringing (search excerpt).

### 5. The costs, had it been built

- **Latency.** It is set by the design's modelling delay:
  - DRC-FIR: a few ms to about 12-46 ms (arithmetic);
  - Dirac Live on miniDSP hardware: 23 ms;
  - the Chalmers design: 100 ms;
  - long FIRs: about 1 s.
  
  The current IIR correction adds none.
- **A filter for every rate.** For the same length in time, the number of
  taps grows with the sample rate: a 1.49 s filter is 65,536 taps at
  44.1 kHz and about 1.14 M at 768 kHz. That means ten sets per speaker
  across both rate families.
- **CPU on a Pi 4.** CamillaDSP's README gives about 55 % for
  8 channels × 262k taps at 192 kHz. Scaled linearly (an estimate, not a
  measurement), stereo with 1.49 s filters would take about 4 % at 96 kHz,
  15 % at 192 kHz and 60 % at 384 kHz, and would not fit at 768 kHz.
- **The measurement must be phase-accurate.** A USB microphone's clock
  differs from the DAC's. A 100 ppm mismatch over a 10 s sweep is 1 ms,
  which is 36° at 100 Hz and 360° at 1 kHz (arithmetic). REW's remedy is an
  acoustic timing reference with clock adjustment, needed at every position
  ([REW help](https://www.roomeqwizard.com/betahelp/help/html/makingmeasurements.html)).

### 6. What would settle it

One blind test of one variable:
- **Room and positions.** A stereo pair in a domestic room, at the main seat
  and two or three positions 30-50 cm from it.
- **Conditions.** No correction; the current correction; and the current
  correction plus a constrained excess-phase FIR with the same magnitude
  (checked by measurement at every seat). Delay and loudness are matched.
- **Order.** ABX first, then preference ratings.
- **Panel.** About 34 listeners for 80 % power at d = 0.5. This is the
  report's own arithmetic, from the 2026 study's d = 0.47.

## What it means for the player

| Part of correction in time | Verdict | Here |
|---|---|---|
| Delay and level alignment between the speakers | supported: 9 of 10 listeners heard 0.06 ms or less between channels ([McMullin 2016](https://www.aes.org/e-lib/browse.cfm?elib=18467), abstract) | done (ADR-0175) |
| Shorter decay of bass modes | supported, given cuts that match the modes | the cuts are minimum-phase; the ringing is measured against Fazenda's thresholds (ADR-0187 C6/D7) |
| Excess-phase correction of the bass at the seat | unsupported: no test; pre-ringing and failure away from the seat documented | not built |
| Linearising the loudspeaker's own phase | unsupported for music in rooms; weak evidence it is inaudible | not built |
| Imaging, depth, clarity | unsupported: sighted reviews and vendor claims only | - |
| Two-speaker bass control (ART type) | unsupported: the vendor says only "in principle" | - |
| Removing reflections or the room's excess phase above the bass | contradicted | - |
| Exact inversion | contradicted in use | - |
| Phase difference between left and right | open: audible with mismatched crossovers; untested for room EQ | small here (below) |

**Left against right.** Both speakers get the same cuts in the bass
(ADR-0175), so the bass has no phase difference between them. Above the bass,
each speaker has its own broad filters (ADR-0177: Q 0.5, ±3 dB). The worst
case is one speaker at +3 dB and the other at −3 dB at 1 kHz. That differs
by at most 19.7° near 415 Hz (arithmetic on the RBJ peaking filter, not
measured).

**Phase 34 closed for now** (George, 2026-11-21, on this finding) without
being built. Nothing found shows an audible benefit. The parts of correction
in time that are supported are already done or already in Phase 37. It is
reopened only if a published blind test of the time part shows one.
