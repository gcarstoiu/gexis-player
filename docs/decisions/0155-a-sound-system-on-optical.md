# ADR-0155 — A DAC, receiver or sound bar on optical, through a USB adapter

**Status:** **Accepted** — 2026-10-20, George, for Phase 16 (`ph-optical`),
from Finding 130: decision 2 (b), *"1b"*; decision 4 not built, *"Not yet.
We can check later"*; decision 5 yes, *"Yes"*.

## Context

A USB-to-optical adapter is a USB sound card: *Output* already lists it
(ADR-0117), and it plays. Measured on sofapi with a Realtek adapter into the
SMSL's optical input (Finding 130):

- it takes 44.1, 48, 96 and 192 kHz - **not 88.2 or 176.4** - and has no
  volume control;
- asked for a rate it lacks, it runs at the next one up without an error, so
  music sent that way plays about 9 % fast (heard);
- **Lyrion plays silence** for those rates (Squeezelite cannot open the
  card at them); **Plexamp converts** them itself and plays correctly;
  Spotify, AirPlay and Bluetooth send only 44.1 or 48 kHz;
- the library behind sofapi holds 59 tracks at 88.2 kHz.

The phase plan also expected sound bars that take only 44.1 and 48 kHz over
optical, while the adapter offers up to 192: the player would send 96 kHz and
the bar would stay silent. Not seen yet - the SMSL takes every rate.

## Decision

1. **Squeezelite converts only the rates the card cannot take** - its own
   resampler (soxr, built in: `-R` with the *exception* flag `E`), on every
   output. A rate the card takes is passed untouched, bit-perfect as today;
   only an 88.2 or 176.4 kHz track on a card without them is converted, and
   plays instead of staying silent. Plexamp already does this for itself.
   It needs no setting and changes nothing on the DACs that take every rate.
2. **Converted to what** - **(b), George, 2026-10-20**:
   - **(a) 44.1 kHz** for both: Squeezelite's default with `E` (the same
     family, an exact 2:1 or 4:1);
   - **(b) the next rate up**, 96 or 192 kHz (its `X` flag), as Plexamp did.
   Neither is measured here for sound. Chosen: **(b)**, so the two sources
   treat a file alike. Squeezelite's `X` flag converts to the card's highest
   rate (192 kHz on this adapter), not to the next one up; what the SMSL
   shows for 88.2 and 176.4 kHz is checked on sofapi before it ships.
3. **The adapter's volume: Fixed by default** when it is chosen, since optical
   feeds a device with its own volume (the SMSL here); Software stays
   available. Hardware is greyed, as on any card without a control.
4. **A maximum rate per output** for a receiver that takes less than the card
   offers (a sound bar at 48 kHz): **not built yet** (George, 2026-10-20) -
   nothing at hand needs it; to be checked when a sound bar is tried.
5. **The *Tested* mark** for this adapter (USB ID `0bda:4e27`) in *Output*,
   as the HiFiBerry has: **yes** (George, 2026-10-20), with
   `docs/HARDWARE.md` listing it as tested into a DAC, not into a sound bar.
6. **The adapter's second device** (48 kHz only, likely encoded surround) is
   not used: the player sends stereo PCM.

## Consequences

- `squeezelite.service` gains `-R -u` with the chosen recipe; checked on
  sofapi with the 88.2 and 176.4 kHz tones (they must play, at the expected
  rate on the SMSL, at the right pitch) and with 44.1 and 96 kHz (untouched).
- Not covered here: the Lyrion server Squeezelite joins after a restart
  (Finding 130, point 6) - a separate decision.
