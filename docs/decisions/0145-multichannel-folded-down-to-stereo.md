# ADR-0145 — Multichannel files folded down to stereo

**Status:** **Accepted** — 2026-10-13. George: *"We do downmixing now before
release and have another phase for mpd right after."*
**Amends:** [ADR-0021](0021-deployment-flashable-image.md) (Squeezelite becomes
a package we build, as peppyalsa is).

## Context

Finding 121: Lyrion's player, Squeezelite, is stereo - the Squeezebox protocol
it speaks describes PCM as mono or stereo. What it does with a file of more
channels, read in its source at Debian's commit (`262994a`, 2024-12-27):

- **FLAC** (`flac.c`, `write_cb`): channel 0 and channel 1 are played, the
  rest dropped - a 5.1 file loses its centre (the voice, usually), LFE and
  surrounds, without a word;
- **WAV/AIFF** (`pcm.c`): "unsupported channels" - nothing plays;
- **DSD** (`dsd.c`): channels past the second are skipped
  (`d->consume = d->block_size * (d->channels - 2)`).

Real 5.1/7.1 needs a renderer that outputs more than two channels: MPD, its
own phase after the first public release. Until then, a multichannel file
through Lyrion should at least be heard whole.

## Decision

1. **Squeezelite folds a file of more than two channels down to stereo**, in
   the decoder, before anything else sees it - so every Lyrion server works,
   not only the player's own. Stereo and mono files are untouched, sample for
   sample.
2. **The fold-down is the standard one** (ITU-R BS.775, as ffmpeg's default
   rematrix): left = front left + 0.707 centre + 0.707 left surround(s); right
   the same on the right; LFE left out; the result scaled so the largest
   possible sum is full scale - nothing can clip, at the cost of a quieter
   track. Not bit-perfect, and cannot be: six channels become two.
3. **The formats, by how they reach Squeezelite:** FLAC, WAV/AIFF and DSD
   (converted to PCM first when it has more than two channels - DSD cannot
   be mixed as one-bit audio), in the channel orders their specifications
   give. AAC uses the decoder's own downmix (FAAD2's `downMatrix`). Formats
   whose decoders already give stereo are left as they are; any other
   multichannel format is logged and plays as before.
4. **Our own package**, `gexis-squeezelite`: the upstream source at Debian's
   commit, Debian's build options, our patch, replacing Debian's
   `squeezelite` (same binary path, same unit); pinned by the player
   package as our other components are.

## Consequences

- A 5.1 or 7.1 file through Lyrion is heard complete, as stereo, at a lower
  level than a stereo track; the visualiser sees the folded signal.
- We carry a patched Squeezelite, rebuilt when upstream moves.
- Native DSD (ADR-0144) is stereo only: a multichannel DSD file is converted
  and folded, not sent as DSD.

## Unverified

When written: every format on a device; AAC's downmix level against the
others.
