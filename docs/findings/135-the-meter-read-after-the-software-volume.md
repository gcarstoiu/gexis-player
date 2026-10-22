# Finding 135 — With software volume the meter read the music after the cut

**Date:** 2026-10-22. **For:** George (*"Fix also the last two so I check
everything"*), on what Finding 133 left open: sofapi's needles had no level.

## Scope

- **Device:** sofapi (Pi 4), output HDMI 2 with Volume on Software
  (`meter → softvol → plug → hw:vc4hdmi1`), gexis-player `1.3.1+git48`, the
  software control at 292 of 361 (−17.25 dB, Lyrion volume 47).
- **Silent:** every test played through a private ALSA configuration
  (`ALSA_CONFIG_PATH`) built like `output.conf` but ending in `null` or a
  `file` sink; the software stage named the real control and only read it.
  A 440 Hz sine at −6 dBFS, 4 s, fed in real time; the peppyalsa scope's own
  FIFOs read as the meter service reads them, the first quarter left out.
- **Not tested:** a real card under the new chain; Spotify, Bluetooth and
  Plexamp through it (they open the same `output`); the DAC chains on
  Software (`meter → softvol → hw:`), which have the same shape.

## Results

1. **The meter saw the cut.** Meter level (peppyalsa's 0-100, both channels):

   | Chain | S16_LE | S32_LE |
   |---|---|---|
   | `meter → null` | 9.0 | 9.2 |
   | `meter → softvol → plug → null` (shipped) | 1.3-1.4 | 1.3-1.4 |
   | `meter → copy → softvol → plug → null` | 9.0 | 9.2 |
   | `meter → plug → softvol …` | 1.3 | 1.3 |
   | `meter → hooks → softvol …` | 1.3 | 1.4 |
   | `meter → route → softvol …` | 9.0 | 10.0 |

   9.0 → 1.3 is −16.8 dB: the control's −17.25 dB. ALSA's `type meter` reads
   the samples its slave holds, and a `softvol` slave holds them already
   scaled; `plug` and `hooks` add no buffer of their own; `copy` does. The
   spectrum fell with it (79 → 61 at the top band).
2. **So the meters took the cut twice.** The meter service then applies the
   needles' half and the bars' whole of the cut (ADR-0146), as for the
   card's own control. At Lyrion volume 5 (−50 dB) the needles had nothing,
   which Finding 133 saw; at 47 they stood about 25 dB down instead of 8.5.
   ShelvesPi (Hardware volume, `meter → hw:`) is not affected.
3. **`copy` passes everything byte for byte:** `meter → copy → file`, 6 MB
   of random bytes, S16_LE 44.1 kHz, S24_3LE and S24_LE 96 kHz, S32_LE 192
   and 384 kHz, plain writes and mmap (`-M`), with readers on the scope's
   FIFOs: every file identical to its input, no error, no assertion.
4. **A running renderer kept the old chain.** After the update the core
   rewrote `output.conf` at its start, as it does whenever the file differs;
   squeezelite - running since the evening before - played a new stream
   through it and the meter still read zero (95 reads, all 0). Restarted,
   the same music read 10.6 / 13.1, peaks 24, at Lyrion volume 5. The core's
   log had said *"renderers pick it up on their next open"*: alsa-lib did not
   read the file again for a process that had read it once.

## What changed

- `outputs.render` writes `meter → copy → softvol` for both `output` and
  `output_wait` (ADR-0124 as amended).
- **A chain rewritten at the core's start restarts the renderers** whose
  source is on, as a change of output does (ADR-0055 §2): once the card is
  free, never under something playing.
