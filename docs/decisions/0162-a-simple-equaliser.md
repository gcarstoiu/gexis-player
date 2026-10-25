# ADR-0162 — A simple equaliser

**Status:** **Proposed** — 2026-10-25. Phase 20 (`ph-equaliser`). The
product decisions are George's, the same day (below); the technical ones are
proposed and are confirmed or changed by the phase's first measurement, then
recorded here: its silent part, the same day
([Finding 138](../findings/138-the-equaliser-on-a-loopback-first-measurement.md)),
changed D1, D3, D6 and D7 below. Nothing built. Builds on
[Finding 124](../findings/124-room-correction-what-open-source-offers.md)
(CamillaDSP as the engine), [ADR-0124](0124-software-volume.md) and
[ADR-0127](0127-one-volume-row.md) (the volume types),
[ADR-0144](0144-native-dsd-on-a-dac-that-takes-it.md) (native DSD).

## Context

- **Every source already shares one way out.** Squeezelite (`output_wait`),
  go-librespot, Plexamp (through `pcm.!default`) and bluealsa-aplay all play
  to `pcm.output`, a `meter` PCM (the visualiser's tap, peppyalsa) over the
  card (`image/stage-gexis/00-alsa/files/output.conf`). One renderer holds
  the card at a time. An equaliser placed on that path is heard from every
  source.
- **CamillaDSP** (Finding 124: aarch64 ALSA builds, used by moOde and
  Volumio on the Pi 4; v4.1.3, v5 in beta) has a `GraphicEqualizer` filter
  with any number of bands, evenly spaced on a log scale, one peaking biquad
  per band, a band at 0 dB skipped. A new configuration sent over its
  websocket (`SetConfigJson`, `PatchConfig`, `SetConfigValue`) is applied
  directly, and, where the change allows it, without interrupting the
  processing (its README, *Reloading the configuration*); a filter's gains
  are such a change. The core drives it with pycamilladsp.
- **What an equaliser cannot do**: keep the output bit-perfect while it
  changes the sound; process native DSD (CamillaDSP is PCM only); boost
  without headroom (a boost on a full-scale signal clips).

## Decided (George, 2026-10-25)

1. **Ten bands**, one an octave - 31, 63, 125, 250, 500 Hz, 1, 2, 4, 8,
   16 kHz - each from −12 to +12 dB. 31 bands would not fit the touch floor
   (44 logical px, ADR-0109) across the panel.
2. **The presets are genres, plus Vocal and Late night**, not single-purpose
   corrections (more or less bass, more or less treble): George prefers
   genres. With *Flat*, the list below.
3. **Up to ten of the owner's own**, named, beside the presets: saved from
   the bands as set, renamed, deleted. **The choice follows the output**: the
   DAC, HDMI and optical each keep whether the equaliser is on and which
   preset or setting it uses; the owner's settings are shared by all.
4. **Where it is**: *Settings → Audio → Equaliser* for the whole of it, and
   close to the music for a quick change - the phone's pull-up tray (with the
   touchpad), the panel's volume drawer on Now Playing, the bar's tray.
   **Drawn in Claude Design first** and seen by George before it is built
   (brief: `design/briefs/20-equaliser.md`).
5. **Native DSD skips the equaliser**: it stays native and bit-perfect, as
   ADR-0144 has it; the equaliser applies to PCM only.

### The presets (starting values)

Gains in dB per band, low to high. They are a starting point, gentle on
purpose (a boost costs headroom, D3 below), and are tuned by ear on George's
players before the phase closes.

| Preset | 31 | 63 | 125 | 250 | 500 | 1k | 2k | 4k | 8k | 16k |
|---|---|---|---|---|---|---|---|---|---|---|
| Flat | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Rock | 4 | 3 | 2 | 0 | −1 | −1 | 0 | 2 | 3 | 4 |
| Pop | −1 | 0 | 2 | 3 | 2 | 0 | −1 | −1 | 0 | 1 |
| Jazz | 3 | 2 | 1 | 2 | −1 | −1 | 0 | 1 | 2 | 3 |
| Classical | 3 | 2 | 1 | 0 | 0 | 0 | 0 | −1 | −1 | −2 |
| Electronic | 4 | 4 | 1 | 0 | −2 | 1 | 0 | 1 | 3 | 4 |
| Hip-hop | 5 | 4 | 1 | 2 | −1 | −1 | 1 | −1 | 2 | 3 |
| Acoustic | 3 | 3 | 2 | 1 | 1 | 1 | 2 | 3 | 2 | 1 |
| Vocal | −2 | −1 | −1 | 0 | 2 | 3 | 3 | 2 | 0 | −1 |
| Late night | 5 | 4 | 2 | 0 | 0 | 0 | 0 | 1 | 2 | 3 |

*Late night* lifts bass and treble for listening quietly, a fixed loudness
curve. A loudness that follows the volume is not in this record: CamillaDSP's
`Loudness` filter follows its own volume control, which is not the player's.

## Proposed (technical)

**D1 — CamillaDSP on the shared path, driven by the core.** The renderers
keep playing to `pcm.output`; with the equaliser on, its slave is an ALSA
loopback that CamillaDSP captures, and CamillaDSP plays to the card. The
core starts and configures it (pycamilladsp) and sends every change over the
websocket. CamillaDSP ships as a package of ours from upstream's aarch64
release, with its licence (ADR-0107's parts). **Measured 2026-10-25
(Finding 138):** the bands are **ten Peaking filters**, one an octave at the
ISO centres, not CamillaDSP's GraphicEqualizer, which rebuilds its filters on
every change (a click at −18 dBFS under a −20 dBFS tone) and cannot place a
16 kHz band at 44.1 kHz. Ten bands cost 2.3 % of one core at 44.1 kHz and
4.9 % at 192 kHz. The loopback is kept out of the outputs the player lists.

**D2 — A change is heard at once.** Moving a band, choosing a preset or
another of the owner's settings changes the filter's gains in the running
CamillaDSP: no restart, no gap. Measured: a band dragged in 0.5 dB steps
every 30 ms left nothing above −63 dBFS under a −20 dBFS tone; whether that
is heard is for the ear. Turning the equaliser on or off changes the
path (D5), so it may cost a moment of silence; measured and stated in the
manual.

**D3 — Headroom by the curve, never clipping.** Before the bands, the signal
is lowered by the highest point of the combined curve (adjacent boosts add
up, so it is computed from the filters, not read off the largest band), and
rounded up to 0.5 dB. A setting with no boost lowers nothing. A plain gain
stepped by 0.5 dB left −53 dBFS (Finding 138), so the lowering moves through
a ramped volume stage; to be measured. Under *Fixed*
volume the music plays that much quieter and the amplifier is turned up; the
equaliser's row says by how much.

**D4 — The meters before the equaliser.** The visualiser shows the music as
it is: the equaliser's lowering (D3) would otherwise make the meters read
low under every preset, as software volume did before Finding 135.

**D5 — Off is bit-perfect.** Off, `pcm.output`'s slave is the card, as
today. *Flat* is a preset, in the path; *Off* is the switch.

**D6 — A change of sample rate.** CamillaDSP runs at one rate. ~~On the
loopback it stops when the rate changes (`stop_on_rate_change`), and the core
starts it again at the new rate.~~ **Changed 2026-10-25 (Finding 138):** the
loopback cannot be held across a change (a 96 kHz stream was given the
44.1 kHz already open), and `stop_on_rate_change` needs three readings a
second apart. Instead CamillaDSP lets the loopback go at each stream's end
(`stop_on_inactive`); the core watches the loopback's controls (*PCM Slave
Active*, *PCM Slave Rate*, announced 5-10 ms after a stream begins) and
starts it at that stream's rate. Measured cost: 12-24 ms off a stream's
start and up to a chunk (8-15 ms) off its end, nothing inside it - at every
change of rate and every resume after a pause (Squeezelite lets the device go
1 s into one). If that is heard, a per-stream start (alsa_cdsp, dormant since
2022) is the alternative tried.

**D7 — DSD past it.** Native DSD (Fixed volume and a card that takes it,
ADR-0144) does not go through CamillaDSP. The loopback takes DSD formats
(Finding 138), so Squeezelite can open it as it is; the core tells a DSD
stream by the loopback's format and sends it on to the card untouched
instead of starting CamillaDSP. To be tried with Squeezelite and a DSD file.

**D8 — The volume types.** Hardware: the DAC's control, after the
equaliser. Software: after the equaliser, as the last stage. Fixed: no
volume, D3's note.

**D9 — The API.** The equaliser's state and presets in the documented API
(Phase 15), so the phone, the panel and Home Assistant use one route; marked
stable once the phase closes.

## Settings (ADR-0022)

Proposed, not appended until George confirms:

- **[N] Equaliser** - on / off, per output; off by default.
- **[N] Equaliser preset** - one of the presets or the owner's settings, per
  output; *Flat* by default.
- **[N] Your equaliser settings** - up to ten, named, shared by all outputs.

## Measured before it is called done

- Its cost on a Pi 4 with the visualiser running.
- The delay it adds, and whether players in sync through Lyrion stay in
  sync.
- A gap at a change of sample rate (D6), and at turning it on or off (D2).
- A click while a band is dragged.
- No preset or setting within its limits clips (D3), with test tones.

## Not in this record

- A loudness that follows the volume.
- Bands set by hand (frequency, gain, width): room correction's (Phases 21
  and 22).
- The equaliser from Home Assistant (a preset to choose): possible once D9's
  route exists.
