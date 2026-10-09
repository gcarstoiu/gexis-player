# ADR-0117 — DACs beyond the two on the bench

**Status:** **Accepted** — George, 2026-10-04 (decisions below).
**Builds on:** [ADR-0009](0009-logical-output-device.md) (the output is named,
never numbered), [ADR-0018](0018-volume-and-output-modes.md) (the DAC2 HD's volume
scale), [ADR-0055](0055-which-output-the-device-plays-to.md) (which output the
device plays to), [ADR-0022](0022-settings.md) (every setting is
inventoried). On [Finding 106](../findings/106-what-is-known-about-dacs-without-owning-them.md).
**Phase:** 13d (`docs/DEVELOPMENT.md`).

## Context

George, 2026-10-01: *"how can we make sure we support more DACs without me
having to go and buy and test each?"* Finding 106 read what exists and what
the player can learn by itself. Decided then: its own phase after 13b;
seeded from Volumio's list (GPL-3.0-only; credited in `THIRD-PARTY.md`);
tested on the two boards George owns, the HiFiBerry DAC2 HD and the IQaudio
DAC+.

### What the player assumes today

Read in the code on 2026-10-04 (`phase-13d` at 06d2e91):

- **The volume scale is the DAC2 HD's, as constants** - `volume.py`:
  `HARDWARE_MAX = 240`, `DB_MIN = -120.0`, `DB_STEP = 0.5`. Any other
  control is driven with wrong raw values.
- **The card is named in four places**: `alsa.CARD_ID = "sndrpihifiberry"`,
  `config.mixer_name = "DAC"` as the fallback, and the image's
  `output.conf` (three lines) - the file ADR-0055's picker rewrites once an
  output is chosen.
- **Only a board that loads its own overlay is seen.** Nothing writes an
  audio `dtoverlay=` into `config.txt`; the DAC2 HD's EEPROM loads its own.
- **The output is otherwise found, not named** (ADR-0055):
  `outputs.discover()` reads `aplay -l`, the first `* Playback Volume`
  control, and whether a `plug` is needed.

### What the card says about itself

Measured on `gexis` (DAC2 HD), 2026-10-04:

```
/proc/device-tree/hat/product   DAC 2 HD
/proc/device-tree/hat/vendor    HiFiBerry
amixer: 'DAC Playback Volume'   min=0, max=240
                                dBscale-min=-120.00dB, step=0.50dB, mute=1
```

**Every number `volume.py` hardcodes is on that line.** So the scale need
not come from any list - only from the card.

## Proposal

### 1. Detection and the list: who does what

**The card is the authority for everything it can say; the list only for
what it cannot.**

| Question | Answered by |
|---|---|
| Which card, and does it play? | `aplay -l` (as today) |
| Its volume control | `amixer contents`: the first `* Playback Volume` (as today), the list's mixer name preferred when the board is in it |
| **The volume scale** | **the control's own `dBscale` and range - always; never the list** |
| Which board it is (a name for people) | the EEPROM (`/proc/device-tree/hat/product`), matched to the list's EEPROM name; else the card name matched to the list's; else the card's own name |
| A board with no EEPROM | **the list**: the user picks it, its overlay is written to `config.txt`, the player restarts |

A USB DAC needs no list: it is a card like any other, class-compliant.

### 2. Three states

Shown wherever the board is named (Settings' output row, setup's Audio
step):

- **Tested** - played and measured here, with a finding: the DAC2 HD and,
  once 13d's tests pass, the IQaudio DAC+.
- **Known** - in the list (from Volumio's, read and corrected - Finding 106
  found a duplicate row and a stray space), not tried here.
- **Detected** - working by discovery alone: not in the list (a USB DAC,
  or a board the list lacks).

### 3. The board picker: a setting

For a board with no EEPROM, a row in Settings → Audio, and the same choice
in setup's Audio step: **"Sound card board"** - *Found by itself*
(the default; nothing written) or one of the list's boards. Choosing writes
its `dtoverlay=` (and parameters) to `config.txt`, removes any other audio
overlay ours wrote, and restarts. **If no card appears after the restart, the
overlay is taken out again and the row says the board was not found** - the
same safety as a screen's Keep, without a question, since there is no sound
to judge by on a panel.

### What 13d does not do

- **Init scripts.** Nine of Volumio's rows run one (amplifier unmutes, and
  the like). The IQaudio DAC+'s is the overlay's own `unmute_amp`
  parameter, so it needs none. A board whose row needs a script is *Known*
  with a note, and is not offered until someone has one to try.
- **DSD** (decision 4). Neither tested board plays it (the DAC2 HD, per the ADR index note on 0003; the IQaudio DAC+ is a PCM5122, PCM only).

## Decided (George, 2026-10-04)

1. **Who does what, as in §1** - the card answers everything it can; the
   list names boards and is the only source for one with no EEPROM. George
   asked whether the card can always answer the volume. It cannot, in four
   cases, and each is settled:

   | Case | The player |
   |---|---|
   | The control gives a dB scale | uses it |
   | No volume control | fixed output, as today (ADR-0046, ADR-0055) |
   | Several controls (the IQaudio DAC+: *Digital*, and *Analogue*, a 0 / -6 dB gain switch) | the list's mixer name first, else the first `* Playback Volume` |
   | **A control with no dB information** | **not used for volume: fixed output**, and the row says the board's volume cannot be controlled by the player (**(a)**, George: *"Yes agreed with a"*). Not treated as linear: that is the bunched-up slider ADR-0054 removed |
   | dB information that is wrong | found only by testing; a *Tested* board may carry corrected values, with its finding |

2. **The three states, as in §2** (*"The three states are fine"*).
3. **The board picker as a setting** (*"Understood the decision now. Let's
   keep the setting"*) - appended to ADR-0022's inventory as **[N]**,
   *Sound card board*.
4. **DSD is postponed** (*"Let's postpone dsd playback then"*). Found
   2026-10-04: the Pi's I2S carries PCM only (`bcm2835-i2s.c`: S16, S24,
   S32), so a board on it can take DSD only as DoP, which ESS Sabre boards
   decode (four rows of Volumio's list, by their makers' pages - not
   measured). Today a DSD file plays converted to PCM by squeezelite, which
   runs without `-D` (read from its options, not played here). DoP would
   need: a bit-perfect chain checked per board; `-D` only for boards that
   decode it, since any other plays it as full-scale noise; the meters to
   recognise DoP, which they would read as full-scale noise; and the
   board's volume in DSD measured. It needs an ESS board on the bench.

## Acceptance (from DEVELOPMENT.md's draft)

1. The volume scale is read from the card; both boards driven correctly,
   as measured.
2. A board that names itself is recognised; one that does not can be chosen,
   its overlay written, the player restarts, and the card appears.
3. Every DAC shows one of the three states.
4. The IQaudio DAC+ plays bit-perfect through every renderer, with its own
   mixer, as the DAC2 HD does.
5. A USB DAC tried once if one is to hand; otherwise *Detected*, untried.

## Amended 2026-10-07: the second board is a Pi-DAC PRO

George's IQaudio board, tested on `guestpi`, is an **IQaudio Pi-DAC PRO** by its
EEPROM - not the DAC+ this record planned (Finding 114). It loads the DAC+'s
driver and makes the same card, `IQaudIODAC`, so it is recognised by its EEPROM
(`Pi-DAC PRO`) through a row of ours beside Volumio's list. Acceptance items 1
and 4 measured for Lyrion, Spotify and Bluetooth; Plexamp not. George: *"let's
move it to tested"* - it is **Tested**. The DAC+ itself stays *Known*.
