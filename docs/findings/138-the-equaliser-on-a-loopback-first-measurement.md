# Finding 138 — The equaliser on a loopback: the first measurement

**Date:** 2026-10-25. **For:** Phase 20 (`ph-equaliser`): ADR-0162's
technical decisions are confirmed or changed by the phase's first
measurement. This is that measurement's silent part.

## Scope

- **Device:** sofapi (Pi 4, 4 GB), gexis-player 1.6.0, nothing playing.
  CamillaDSP 4.1.3, upstream's aarch64 build (its checksum matches the
  release's), run from `/tmp`; `snd-aloop` loaded for the test and unloaded
  after.
- **Silent:** the test signals went into the loopback with `aplay`
  (`hw:Loopback,0,0`), CamillaDSP captured them (`hw:Loopback,1,0`) and
  played to the loopback's second cable or to a file. Nothing reached a card.
- **Signals:** a 1 kHz sine at −20 dBFS, S32_LE stereo, at 44.1, 96 and
  192 kHz; for the start of a stream, a ramp whose sample *i* holds *i* × 256,
  through a pipeline with no filters (bit-exact), so the first value out
  says how many samples were lost.
- **The core's part** was played by a script: CamillaDSP driven over its
  websocket, as pycamilladsp would, and the loopback's ALSA control events
  read with `alsactl monitor`.
- **Not tested:** the real card (the delay, the DAC's clock against the
  loopback's, rate adjust); players in sync through Lyrion; the visualiser
  running beside it; any judgement by ear; native DSD from Squeezelite;
  Spotify, Plexamp and Bluetooth opening the loopback (only `aplay` did).
  The kit is kept outside the repository.

## Results

1. **It costs little.** CamillaDSP's CPU over 15 s, as a share of one core
   (`/proc/<pid>/stat`), with ten Peaking filters, every band in use
   (*Acoustic*), and a Gain stage before them:

   | Rate | Chunk | No filters | Ten bands |
   |---|---|---|---|
   | 44.1 kHz | 1024 | 1.3 % | 2.3 % |
   | 96 kHz | 2048 | 2.1 % | 4.0 % |
   | 192 kHz | 4096 | 2.5 % | 4.9 % |

   CamillaDSP's own processing load stayed under 5.3 %; no sample clipped.
2. **CamillaDSP's GraphicEqualizer clicks on every change; ten separate
   filters do not.** The 1 kHz tone played while its band was dragged
   0 → +12 → −12 → 0 dB in 0.5 dB steps every 30 ms (97 changes, by
   `SetConfigValue`, none refused). Energy above 3 kHz, where a clean tone
   has none, in 10 ms windows:

   | Run | Highest | Windows above −60 dBFS |
   |---|---|---|
   | Ten bands, nothing moved | −99.4 dBFS | 0 |
   | Ten Peaking filters, one dragged | −62.9 dBFS | 0 |
   | GraphicEqualizer, one band dragged | −18.2 dBFS | 112 |
   | The Gain stage stepped 0 → −6 dB by 0.5 dB | −52.6 dBFS | 19 |

   The source says why: a GraphicEqualizer rebuilds all its filters on any
   change (`BiquadCombo::update_parameters`), so their state starts again
   from zero; a single Biquad changes only its coefficients. The
   GraphicEqualizer also places bands by a range that must stay below half
   the rate, so ten octave bands up to 16 kHz cannot be set at 44.1 kHz.
   The Gain stage's steps are 10 dB above the bands' changes.
3. **The loopback cannot be held open across a change of rate.** With
   CamillaDSP capturing at 44.1 kHz, a 96 kHz stream opened without an error
   and was given 44.1 kHz (`aplay`: *rate is not accurate*). Whoever opens
   either side first sets the rate.
4. **Letting go at each stream's end works, and costs its edges.** With
   `stop_on_inactive`, CamillaDSP let the loopback go when a stream ended
   (state *Inactive*, reason *Done*). The loopback announced the next
   stream on its control *PCM Slave Active* 5-10 ms after it began, with
   its rate on *PCM Slave Rate*; the script then sent the configuration at
   that rate. Four streams, 44.1 → 96 → 96 → 44.1 kHz:

   | Stream | Lost at the start | Lost at the end | Breaks inside |
   |---|---|---|---|
   | 44.1 kHz | 16.0 ms | none | none |
   | 96 kHz | 12.0 ms | 14.7 ms | none |
   | 96 kHz | 12.0 ms | 14.7 ms | none |
   | 44.1 kHz | 24.0 ms | 8.5 ms | none |

   `stop_on_rate_change` was not needed; by its documentation it needs
   three readings a second apart before it stops.
5. **The loopback takes DSD formats** (`DSD_U8` to `DSD_U32_BE`, any rate
   to 768 kHz), so Squeezelite's native DSD could open it; CamillaDSP
   processes PCM only.

## What it changes

In ADR-0162 (recorded there):

- **The bands are ten Peaking filters**, one an octave, not CamillaDSP's
  GraphicEqualizer (result 2).
- **A rate change stops CamillaDSP and the core starts it again**: it
  watches the loopback's controls and starts CamillaDSP at the stream's
  rate (results 3 and 4). Whether 12-24 ms off a stream's start, and up to
  a chunk off its end, can be heard is for the ear: Squeezelite closes the
  device 1 s after a pause (`-C 1`), so it happens at every resume after a
  pause as well as at every change of rate.
- **The headroom's change is smoothed** (result 2): a ramped volume stage
  is the next thing to try.
- **Native DSD**: the core can tell a DSD stream by the loopback's format
  and send it on untouched; how is for the test with Squeezelite (result
  5).
- **The loopback is not an output**: while loaded it is a sound card
  (`/proc/asound/cards`), which `outputs.discover` would list.
