# Finding 141 — Room correction above the bass: what is known

**Date:** 2026-11-07. **For:** Phase 30 (`ph-room-correction-full`), before
its ADR (George asked for the research on 2026-11-07): what correcting above
the bass is worth and how, how many positions, and the time-domain part with
its cost. Follows [Finding 124](124-room-correction-what-open-source-offers.md),
which it does not repeat.

## Scope

Desk research only, 2026-11-07, in three parallel searches. Every source cited
was opened. Where only an abstract could be read, that is stated. Nothing was
run on a player. The headline claims were checked again against their sources
before writing:
- Toole's paper, Hopkins's paper and REW's help;
- Harman's 2009 test and the 2026 JASA test;
- Anthem's limits and CamillaDSP's releases;
- the drift paper, Dirac's latency and the UMIK-1's datasheet.

Readings from a paper's figure are approximate and marked as such.

Not reachable that day:
- dirac.com (HTTP 429);
- the AES e-library (403), so no AES paper was read in full;
- support.genelec.com, support.sonarworks.com, Lyngdorf's FAQ and minidsp.com (403);
- MDPI and its mirrors (403);
- diyAudio (a browser check).

Some manufacturers' pages were read as Wayback Machine copies, as marked.

## What the research says about correcting above the bass

**Where the room stops ruling.** From Toole
([JAES 63(7/8), 2015](https://linkwitzlab.com/Toole-Room%20calibration.pdf),
read in full):
- In small rooms the transition is about 200-300 Hz. Below it the room is the dominant factor; above it the loudspeaker is "substantially in control".
- A room curve predicted from a speaker's anechoic data matches a six-seat average above about 300-400 Hz.

**What is heard above it.**
- The direct sound "has a high priority in perception". Reflections are mostly benign, even beneficial, from a speaker whose directivity is even.
- Three speakers kept their double-blind ratings in four very different rooms (Toole).

**Why correcting there can harm.**
- **Interference:** the peaks and dips above the transition are interference, not minimum phase. Equalising them at a few positions adds new ones elsewhere, and "equalization cannot repair faulty loudspeaker directivity" (Toole).
- **Small moves:** a few tenths of a wavelength from the corrected point, the result degrades badly, worst at high frequencies (Radlović, Williamson and Kennedy, IEEE TSAP 8(3), 2000, abstract).
- **REW's help:** for one listener held still, EQ might hold "up to a few kHz"; with normal head movement, "a few hundred Hz is more likely" ([REW](https://www.roomeqwizard.com/help/help_en-GB/html/iseqtheanswer.html)).
- **EBU:** Tech 3276 (1998) advises correcting below 300 Hz only ([EBU](https://tech.ebu.ch/docs/tech/tech3276.pdf)).

**What Toole recommends.**
- With good speakers, no room equalisation above the bass; the aim is a flat direct sound.
- If in-room curves are used at mid and high frequencies, "much reduced frequency resolution", showing broad trends.
- Bass and treble controls for taste, since one target does not suit every listener.

**The case for some.**
- Harman's 2009 test (below) found the preferred corrections filled a broad dip in the speaker's sound power around 2 kHz.
- Olive places the risk above 500-600 Hz with speakers whose directivity is uneven.

## Target curves

| Curve | Above the bass | Source |
|---|---|---|
| B&K, 1974 | about −0.9 dB per octave from 200 Hz to 20 kHz, −3.4 dB at 20 kHz against 2 kHz (read from its figure) | [B&K 17-197](https://www.bksv.com/doc/17-197.pdf) |
| A good speaker's own room curve | about −0.5 dB per octave in a typical room, −0.85 in a very reflective one, flat in a dead one (read from Toole's figure 13a) | Toole, 2015 |
| Harman's in-room target | "gently falls about 1 dB per octave from 20 Hz to 20 kHz"; listeners set bass and treble themselves, trained ones choosing less treble | [Olive, Acoustics Today 2022](https://acousticstoday.org/issues/2022AT/Spring2022/files/basic-html/page60.html); the 2013 paper not read |
| EBU Tech 3276, ITU-R BS.1116-3 | tolerance masks for studios, not targets: ±3 dB, the lower limit falling above 2 kHz | EBU; [ITU](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1116-3-201502-I!!PDF-E.pdf) |
| The X-curve (cinemas) | flat to 2 kHz, then −3 dB per octave; used nowhere else (Toole) | the standard not read |

The right slope depends on the speaker's directivity and the room's
reflections:
- Toole says so, and Olive in his blog.
- Olive's patent ([US 8,311,232](https://patents.google.com/patent/US8311232B2/en)) gives wider-dispersion speakers a shallower slope.
- No listening test that varies directivity was found.

## Smoothing, windowing and positions

**Smoothing.**
- REW's variable smoothing (1/48 octave below 100 Hz, 1/6 at 1 kHz, 1/3 above 10 kHz) is its recommendation for a response to be equalised. Its psychoacoustic smoothing approximates the perceived response ([REW](https://www.roomeqwizard.com/help/help_en-GB/html/graph.html)).
- Hatziantoniou and Mourjopoulos (JAES 2000, abstract; and their later papers): smoothed responses are "less position-sensitive", and corrections from them more robust than long inverse filters.

**Windowing.**
- REW's frequency-dependent window keeps less of the late sound as frequency rises, which it likens to the ear picking out the direct sound. It is set in cycles, with no default given ([REW](https://www.roomeqwizard.com/help/help_en-GB/html/impulseresponse.html)).
- Trinnov uses 3 cycles by default.
- A correction from windowed data aims at the direct sound, Toole's aim. One from smoothed steady-state data aims at the room curve.
- Gating cannot isolate the direct sound at a seat below about 500 Hz. With speaker and ear 1 m high and 2.5 m apart, the floor's reflection arrives 2 ms after it (arithmetic, from B&K 17-196's rule that the lowest valid frequency is one over the gate; [17-196](https://www.bksv.com/media/doc/17-196.pdf)).

**How many positions.** From Hopkins
([JASA 129(5), 2011](https://livrepository.liverpool.ac.uk/3109636/),
accepted manuscript):
- The spread of an average of N uncorrelated positions falls as 1/√N.
- Positions are uncorrelated half a wavelength apart: 0.7 m at 250 Hz.
- Building-acoustics standards use at least 5 or 6 positions.
- Phase 29's positions, 40 cm apart, are half a wavelength apart only above about 430 Hz.

**The moving microphone.**
- **Hopkins:**
  - a 0.7 m circle, traced at a steady speed over at least 15 s, equals at least five fixed positions above 200 Hz;
  - a helix equals more than ten;
  - three semicircles 45-60° apart do where furniture is in the way;
  - the arm held out.
  - This is diffuse-field theory from building acoustics.
- **REW's author** (forum, 2025): it measures a small volume; for a large area, several of them.
- **Sonos's Trueplay** works this way (above).

**Averaging.** Hopkins and the standards average power, as Phase 29 does. REW also offers a dB average, which weighs peaks and dips equally
([REW](https://www.roomeqwizard.com/help/help_en-GB/html/graph_allspl.html)).

## What the commercial systems do above the bass

From each maker's own manual or knowledge base unless marked. "n/p" means
not published in any source opened.

| System | Positions | How far up, by default | Limits above the bass | Target above the bass | In time? | Added delay |
|---|---|---|---|---|---|---|
| Dirac Live 3.14 | 9, 13 or 17; at least 30 cm apart over a sphere of at least 1 m; the first carries most weight | the owner's "curtains"; the full range is a paid tier | n/p | automatic since 3.3.0, from the measurement, "to preserve" the speaker's character | yes, mixed phase | "typically around 7ms" (its manual) |
| Trinnov Optimizer | 3-5 around the seat, little gained beyond 5; weights 0-100 | the full range | +6 dB, −10 dB | flat; presets incl. a gentle downward slope | yes, from about 150 Hz by default | 17-44 ms (2018 manual) |
| Audyssey MultEQ-X | at least 3, 8 recommended, up to 32 (an AV receiver's: up to 8, about 60 cm apart) | "the top end of the audible frequency range" | boost "often" up to 9 dB | a treble roll-off by room size, and a midrange step | magnitude target, FIR filters | n/p |
| Anthem ARC Genesis | 5 (up to 10), an X 60 cm (at most 90 cm) around the seat, at varied heights | **5 kHz**, settable up to 20 kHz | **boost +6 dB**, cut unlimited | flat up to the limit, then the speaker's own; tilt and bass controls | **no**: IIR only, FIR rejected for pre-ringing and delay | n/p |
| Genelec GLM (AutoCal 2) | one, or several within 0.5-1 m | "low and low-mid frequencies" | model-specific; boost mainly for notches at 100-300 Hz | flat | not stated | n/p |
| Lyngdorf RoomPerfect | a focus position, then random ones (at least 50 cm apart) until it "knows" 90-95 % of the room | n/p | n/p | **none**: keeps the speaker's character | no | n/p |
| Sonos Trueplay | a phone moved through the room, more than 150 measurement periods in 45 s | n/p | model-specific, 16 filters | a product's own, not flat | no, minimum-phase IIR | n/p |
| Neumann MA 1 | 7 | n/p | n/p | computed per room; some bass lift, a gentle treble roll-off, some ripple left | arrival times only | n/p |
| Sonarworks SoundID | 37 | the owner can limit it | n/p | flat; B&K 1974 offered | the owner's choice | 0, 24 or 47 ms (2018 review) |

Sources:
- Dirac: [user manual](https://mavenoidfiles.com/fqckpdh2av52mqaegi0rjkj4877vvpqpst1s), [positions](https://helpdesk.dirac.com/en/dirac-live/How-many-positions-do-I-need-to-measure-a82), [3.3.0 changelog](https://helpdesk.dirac.com/en/dirac-live/Dirac-Live-330-Software-Changelog-8b16), [500 Hz tier](https://helpdesk.dirac.com/en/dirac-live/Why-am-I-only-seeing-up-to-500Hz-in-Filter-design-9f1f).
- Trinnov: [reference manual](https://www.trinnov.com/site/assets/files/1696/opt_refman_05_12_18_pro_sd.pdf), [positions](https://kb.trinnov.com/en/knowledge-base/single-or-multiple-measurements), [targets](https://kb.trinnov.com/en/knowledge-base/target-curves-excursion-curves).
- Audyssey: [MultEQ-X guide v1.0, Wayback](http://web.archive.org/web/20260608090655/https://audyssey.com/MultEQ-X%20User%20Guide.pdf).
- Anthem: [ARC Genesis](https://arc.anthemav.com/arc-genesis/), [limits](https://arc.anthemav.com/faq/how-does-arc-keep-speakers-safe-when-creating-correction-curves.php), [positions](https://arc.anthemav.com/arc-genesis/users-guide.php), [targets](https://arc.anthemav.com/arc-genesis/advanced-settings/adjust-arc-settings-adjust-targets.php), [the science](https://arc.anthemav.com/advanced-topics/the-science-of-arc.php).
- Genelec: [GLM 5 manual, ManualsLib](https://www.manualslib.com/manual/3430649/Genelec-Glm-5.html?page=74), [AutoCal 2 boosts, Wayback](http://web.archive.org/web/20250515054108/https://support.genelec.com/hc/en-us/articles/4404366109458-Why-does-GLM-AutoCal2-use-filters-with-positive-gain).
- Lyngdorf: [TDAI-3400 manual](https://cdn.shopify.com/s/files/1/0875/3864/files/Lyngdorf_TDAI-3400_Integrated_Amplifier_User_Manual_Eng.pdf).
- Sonos: [Trueplay's spectral correction](https://tech-blog.sonos.com/posts/trueplay-spectral-correction/).
- Neumann: [MA 1 manual](https://ma1download.blob.core.windows.net/manual/manual.md).
- Sonarworks: [quick start](https://s1.files.sonarworks.com/soundid-reference/guides/QuickStart-Guide-EN.pdf), [audioXpress review](https://audioxpress.com/article/fresh-from-the-bench-sonarworks-reference-4-studio-edition-loudspeaker-and-headphone-correction-system).

What they share:
- **Positions:** 3 to 9 spread over 0.5-1 m is usual. Dirac and Lyngdorf go wider for a "room" result, and Sonos moves one microphone through the room instead of stopping at positions.
- **How far up:** where it is published, either the correction stops well short of 20 kHz (Anthem 5 kHz by default) or the target is the speaker's own response above the bass (Dirac's automatic target, Lyngdorf, Anthem's blend).
- **Boosts above the bass:** every system that publishes its limits allows some: +6 dB in Trinnov and Anthem, "often" up to 9 dB in Audyssey; Genelec added them, for notches at 100-300 Hz.
- **In time:** Dirac and Trinnov correct in time; Anthem chose not to, citing pre-ringing and delay; Lyngdorf and Sonos correct magnitude only.

## What listening tests show

- **Harman, 2009** (Olive, Jackson, Devantier, Hunt and Hess, AES 127th, preprint 7960; read from
  [Olive's own summary](https://seanolive.blogspot.com/2009/11/subjective-and-objective-evaluation-of.html),
  the preprint not reached):
  - **Setup:** the Harman reference room, B&W 802N with a JBL subwoofer, eight trained listeners at the main seat, double-blind, level-matched, no correction hidden among the conditions.
  - **Compared:** five corrections - Anthem, Audyssey and Lyngdorf, and two Harman prototypes - each calibrated over six seats as its maker says.
  - **Result:** three corrections strongly preferred over none, one rated equal to none, one much worse. The post's numbering of them is not consistent.
  - **What won:** smooth, extended responses sloping gently downward; flat targets sounded thin and bright. Olive concludes that a flat in-room target is "clearly not the optimal target curve".
  - **Which curve predicted it:** the measurements at the main seat explained the ratings better than the six-seat average.
  - **Where they differed:** the largest differences were below 100 Hz and around 2 kHz, where this speaker's sound power dips; filling that dip was preferred.
  - **In the comments,** Olive says equalising above 200 Hz improved this speaker. Above 500-600 Hz it risks the direct sound when a speaker's directivity is not even. Harman's own rooms are corrected mostly below 300 Hz.
  - **Not tested:** correction above the bass against the bass alone.
- **Cecchi, Carini, Primavera and Piazza, EUSIPCO 2012** ([full text](https://zenodo.org/records/52548)):
  - **Setup:** magnitude only, 50 Hz-16 kHz, ten expert listeners, ITU-R BS.1284, 70 dB SPL.
  - **Result:** the multi-position design scored 1.2-1.5 above uncorrected. A single-position design scored 0.15 above it on rock.
- **Brooks-Park, Bech, Østergaard and van de Par, JASA 159(4), 2026** ([arXiv](https://arxiv.org/html/2604.12439v1)):
  - **Setup:** eight listeners, B&W D3 speakers, a room of 0.4 s.
  - **Result:** a plain inverse of the magnitude, 70 Hz-20 kHz, minimum phase and regularised, was **significantly less preferred than no correction** (p < 0.001, d = 1.7). An unnamed established commercial system was not significantly different from none (p = 0.154).
- **Radlović and Kennedy, 2000** ([full text](https://users.cecs.anu.edu.au/~rod/papers/2000/00876311.pdf)):
  - **Setup:** speech to 4 kHz at one point, on headphones.
  - **Result:** flattening the response partly was preferred; flattening it almost completely scored below no correction.
- **No controlled test was found** that compares correction in time with magnitude-only correction over several positions above the bass, nor correction above the bass against the bass alone.

Read together, these say three things:
- Correction above the bass has helped when it was smooth, from several positions, and aimed at a gently falling target.
- It has hurt when it inverted a response in detail, even from 70 Hz up.
- A flat target is not the preferred one.

## The time-domain part

**What it is.** Dirac's patent ([US8194885B2](https://patents.google.com/patent/US8194885B2/en), Brännmark, Sternad and Ahlén):
- one filter designed from a model of several listening positions (its examples use 18 and 9);
- an inverse of the magnitude times a causal FIR that inverts only some of the room's non-minimum-phase zeros;
- those zeros chosen so that pre-ringing stays under a set limit.

Brännmark and Ahlén's IEEE paper (2009, abstract only) finds that a plain multi-position design still leaves pre-ringing and overfits a few positions, hence the constraints.

**Its size**, as published:

| Source | Taps | Delay |
|---|---|---|
| DRC-FIR's `normal-44.1.drc` | 65,536 | 918 samples, 20.8 ms at 44.1 kHz |
| miniDSP DDRC (Dirac) | n/p | "23mS" overall |
| Trinnov, at 48 kHz | 1,024 (default FIR) | 23-25 ms in all |
| Dirac Live | n/p | about 7 ms (its manual) |

**What goes wrong.** Pre-ringing: energy before the sound, heard as a pre-echo.
- DRC-FIR windows the phase correction from 20.8 ms at 20 Hz down to 0.5 ms at 20 kHz, and its manual suggests minimum phase to avoid pre-echo ([manual](https://drc-fir.sourceforge.net/doc/drc.html)).
- Liski, Mäkivirta and Välimäki ([AES 144th, 2018](https://acris.aalto.fi/ws/portalfiles/portal/52513428/Audibility_of_Loudspeaker_Group_Delay_Characteristics_AAM.pdf)) found group delay under 1 ms between 300 Hz and 1 kHz inaudible.
- Norcross ([Canadian Acoustics 32(3), 2004](https://jcaa.caa-aca.ca/index.php/jcaa/article/view/1675)) found some inverse filters scored below no correction.

**Open source, November 2026:**
- **DRC-FIR 3.2.3:** unchanged since 2019. Mixed phase by default, one position only, 44.1 kHz sample configurations in Debian.
- **New since Finding 124:**
  - [OptiMIMO](https://github.com/alex-vyverman/OptiMIMO) (MIT): a weighted multi-position least-squares design writing FIR filters for CamillaDSP. Commits from 2026-06-25 to 2026-07-26, three stars.
  - The Rust crate [autoeq](https://docs.rs/crate/autoeq/latest) 0.4.46 (2026-06): IIR, linear-phase FIR or both, one or several positions.
  - [ORCA](https://github.com/LukasB97/ORCA) (MIT): several positions, magnitude only.
- **Still none** does Dirac's constrained mixed-phase design from several positions end to end.

**CamillaDSP:**
- **Releases:** the player ships v4.1.3, still the latest release (2026-04-09). v5.0.0 is in beta (beta.2, 2026-10-18), with faster convolution.
- **Per sample rate:** a FIR is made for one sample rate. A file name with `$samplerate$` picks the one for each stream's rate, so one filter is needed per rate the player plays. The same length in time at 768 kHz takes 16 times the taps it takes at 48 kHz.
- **Delay:** the chunk size adds delay as well as the filter's own.
- **The Pi 4's cost:** no figure has been published for v4 or v5; the README still carries v0.5.0's (Finding 124), and the issue asking for a new one is unanswered.
- [Releases](https://github.com/HEnquist/camilladsp/releases), [issue #473](https://github.com/HEnquist/camilladsp/issues/473).

**Elsewhere:**
- **moOde:** its "quick convolution" uses one pair of impulse responses at one rate ([cdsp.php](https://raw.githubusercontent.com/moode-player/moode/develop/www/inc/cdsp.php)).
- **Volumio:** its FusionDsp plugin offers DRC-FIR and switches FIR by rate (last changelog entry 2024).

## The two clocks

- **The drift paper.** Bryan, Kolar and Abel ([AES 129th, 2010](https://ccrma.stanford.edu/groups/chavin/publications/AES129_ClockDrift.pdf), read in full):
  - Drift between the playing and the recording clock convolves the measured response with an allpass, so it bends the impulse and the phase but **not the magnitude**.
  - Between professional interfaces they measured 1-2 ms per minute, steady within a session but not from day to day.
  - Estimating it and resampling compensated it "near perfect".
- **REW** places a short sweep before and after the measurement and computes the clock difference from the time between them ([help](https://www.roomeqwizard.com/help/help_en-GB/html/makingmeasurements.html)).
- **For magnitude-only correction** with sweeps of about 5 s, the drift is negligible. At 50 ppm it shifts 20 kHz by 1 Hz and the level by about 0.0002 dB (from the paper's model). It matters only to the time-domain part.
- **The UMIK-1's clock:** REW's author writes (forum) that it takes its clock from the computer's USB. miniDSP does not say, and ADR-0175 assumed a clock of its own. Either way it is not the DAC's clock. It can be read from the microphone's USB endpoint on a player with it plugged in.

## Measuring above the bass with the UMIK-1 at 60 dB

- **The microphone** ([miniDSP's datasheet, 2021](https://cdn.shopify.com/s/files/1/0809/2387/files/miniDSP-Umik-1-datasheet.pdf)):
  - 20 Hz-20 kHz ±1 dB with its calibration;
  - 133 dB SPL at 1 % distortion;
  - calibration on axis and at 90°;
  - no self-noise figure published. A reviewer's measurement of the UMIK-2 implies about 28 dB SPL for the UMIK-1 ([one measurement](https://archimago.blogspot.com/2026/01/minidsp-umik-2-measurement-microphone.html)).
- **Pointing up, the 90° file**, as Phase 29 does: miniDSP's advice for multi-position correction ([miniDSP](https://support.minidsp.com/support/solutions/articles/47000681633-which-direction-should-i-point-the-umik-1)). Pointing up keeps every speaker near 90° from every seat.
- **Signal against noise:**
  - REW measures at about 75 dB SPL; each doubling of a sweep's length gains almost 3 dB.
  - A sweep from 20 Hz to 20 kHz in 5 s spends 0.50 s per octave, against Phase 29's 0.75 s, about 1.8 dB less.
  - One long sweep is better than many short ones averaged (Farina, [2000](https://angelofarina.it/Public/papers/134-AES00.PDF) and [2007](https://angelofarina.it/Public/papers/226-AES122.pdf)).
  - Whether 60 dB at the seat is enough above the bass is not answered by any source. A measurement would show it.

## What it means for Phase 30 (for the ADR; nothing decided here)

- **How far up:**
  - The sources lean to broad trends only above about 300-500 Hz.
  - Several stop in the low kHz: Anthem at 5 kHz by default, REW's "a few hundred Hz" to "a few kHz", EBU at 300 Hz.
  - Toole would correct nothing there with a good speaker.
- **Target:** a flat target is not preferred. The preferred ones fall gently, about 0.5-1 dB per octave, or follow the speaker's own trend (Dirac's automatic target, Lyngdorf, Anthem's blend).
- **Resolution:**
  - coarse above the bass, 1/3 octave or variable;
  - a few broad filters, not many narrow ones;
  - an inverse in detail is what listeners rejected.
- **Positions:**
  - five or six, about 0.7 m or more apart, for 250 Hz up; or a moving microphone.
  - Phase 29's three, 40 cm apart, are correlated below about 430 Hz.
  - Harman found the main seat's measurements predicted preference better than a six-seat average (its listeners sat at the main seat).
- **Boosts:** the commercial systems allow capped boosts above the bass, and the dip Harman's listeners wanted filled, at 2 kHz, was the speaker's, not the room's.
- **Without the time-domain part:**
  - Phase 30 can stay on the filters Phase 29 runs: Peaking and shelving filters in the same CamillaDSP stage, one design for every sample rate, no added delay, the drift irrelevant.
  - That is what Anthem, Sonos, Lyngdorf and Genelec do above the bass.
- **With it:**
  - a FIR for every sample rate (to 768 kHz);
  - about 20-45 ms more delay where it is published;
  - the drift solved first;
  - a design of our own (OptiMIMO the nearest start);
  - a cost on the Pi 4 that no one has published.
  - No listening test found shows it preferred over magnitude-only correction from several positions.
  - With grouped players out (George, 2026-11-07), the delay no longer has a group to keep in step with.

## Not verified

- **Dirac:** its default curtains, limits, smoothing and run time.
- **Measurement times:** Trinnov's.
- **Unconfirmed shapes:** Audyssey's treble roll-off and midrange step.
- **Upper limits:** Genelec's, Lyngdorf's and Sonos's.
- **Full text not read:** the review by Cecchi, Carini and Spors (Applied Sciences, 2018), and Fielder's papers on pre-echo.
- **The Pi 4's cost:**
  - CamillaDSP v4.1.3's convolution on a Pi 4 at our lengths, with the visualiser running (still owed from Finding 124);
  - DRC-FIR's run time on a Pi 4.
- **The UMIK-1:** how it is clocked, and its self-noise.
- **AES papers, none read in full:**
  - Olive et al. 2009 and 2013 (the Harman target's own figures);
  - Hatziantoniou and Mourjopoulos 2000;
  - the comparisons of moving and fixed microphones by Peace, Nageli and Sprinkle (2018) and Sprinkle (2023).
- **Books and standards not read:** Toole's book, CTA-2034-A, SMPTE ST 202.
- **Listening tests not found:** none varying directivity to find the best target; none comparing correction above the bass with the bass alone.
