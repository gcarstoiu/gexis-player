# ADR-0085 — The ALSA default is our output

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0009](0009-logical-output-device.md) (never a card by
index; `pcm.output` is the indirection), [ADR-0055](0055-which-output-the-device-plays-to.md)
(which output the device plays to), [ADR-0011](0011-meter-data-three-transports.md) /
peppyalsa (what the meter is on), [Finding 077](../findings/077-plexamp-on-gexis.md)
(where this came from), Phase 10 step 0

## Context

George, 2026-09-25: *"Why aren't we setting the default for the device to our
hat and let plexamp use it?"*

The question came out of a real dead end. Plexamp headless enumerates its own
audio devices — `default`, `sysdefault`, `bluealsa`, and one entry per
`hw:` card — and **`pcm.output` is not among them**, even though it is a real
ALSA PCM that `aplay -L` lists. Setting Plexamp's device to `output` is
silently ignored: its lookup misses, it falls back to "Follows System Output",
and audio went to **HDMI**.

That left two bad options for any renderer we do not control:

- **Name the card by index** — `hw:5,0` — which is exactly what ADR-0009
  forbids, and Finding 005 measured the same DAC at index 3, 2 and 1 on three
  machines. It is 5 on this one.
- **Take `default`**, which was ALSA stock: card 0, HDMI.

Either way the audio bypasses `pcm.output`, so **peppyalsa is not in the path
and the visualiser gets nothing.**

## Decision

**`pcm.!default "output"`**, in `/etc/alsa/conf.d/zz-gexis-default.conf`.

A plain alias. An application that offers only "Default" now gets the chosen
output, by name, through the meter — the same chain every renderer here
already uses.

## Rationale

### Nothing was using the default, and that was checked

- `squeezelite -o output`
- go-librespot `audio_device: output`
- `bluealsa-aplay --pcm=output`

All three name it explicitly, and nothing defined `pcm.default` at all. So
this takes nothing away from anything; it fills a slot that was holding
ALSA's stock answer and quietly pointing at HDMI.

### It restores ADR-0009's rule for software we do not control

ADR-0009 exists because a card index is not stable. We can hold our own
renderers to `output`; we cannot hold Plexamp to it, because its picker will
not show it. **Making the default correct is how the rule reaches software
that has never heard of it** — and it is the only lever we have over an
application that offers a fixed list.

### It follows the output picker for free

`outputs.render()` rewrites `pcm.output` whenever ADR-0055's row changes.
`default` is an alias, so it moves with it. An app on "Default" follows the
user's chosen output without knowing the row exists.

### A plain alias, not a `plug` layer

`pcm.!default { type plug; slave.pcm "output" }` was tried first and works.
The alias is better: **no conversion layer, so an app on the default gets the
same bit-perfect chain a renderer gets.** A `plug` on top would silently
convert rather than let the card refuse, which is the opposite of what this
device is for.

It also keeps well clear of the crash ADR-0055 records: `plug` *under* the
meter breaks the peppyalsa scope outright (`snd_pcm_scope_s16_get_channel_buffer:
Assertion 's16->buf_areas' failed`). Nothing here adds a plug anywhere.

### Its own file, not `output.conf`

`output.conf` is regenerated from `outputs.render()` on every output change,
and a test asserts the template and the shipped file have not drifted. A
stanza that never varies does not belong in a file that is rewritten; a
separate conf.d file cannot be lost by a rewrite.

## Consequences

- **Any application using the ALSA default now plays to the chosen output**,
  through the meter. That is the intent, and it is a behaviour change for
  anything that previously landed on HDMI by accident.
- **An application that genuinely wants HDMI has to name it**, which is
  correct: HDMI is one of four outputs ADR-0055 offers and is chosen by the
  row, not by being first.
- Plexamp's "Default Audio Device" is now the right answer rather than a trap.

## What this does not settle

- **Whether Plexamp becomes a renderer at all.** That is Phase 11. This
  removes one obstacle.
- **Whether the default should be `plug`-wrapped for robustness** if some
  future application cannot negotiate a format the card offers. Nothing has
  needed it, and the bit-perfect argument is against it until something does.
