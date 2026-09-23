# Finding 052 — The spectrum pipe had no frames in it

**Date:** 2026-09-23
**Question:** George, with a video: *"there is some sort of reset or refresh
that jumps some bars… It's not necessarily on the higher frequency
spectrum. Have seen it in other places."*
**Scope:** `gexis`, 2026-09-23, LMS playing, the raw peppyalsa pipe
`/run/gexis/spectrum.fifo` read directly with `gexis-meter` stopped, polled
at 30 Hz for 8–10 s per run: once before the patch, three times after.
Also 66 frames of George's video, measured. **Not tested:** the meter pipe
beyond reading its writer (one write per frame already), and what happens
with a spectrum size other than 30.

## What the video shows

Frame-to-frame change across the whole 66 frames averages 5.3 px per
column, standard deviation 4.2. **Three consecutive frames are more than
two standard deviations out**: 39, 40 and 41, at 16.5, 19.2 and 23.2.

Looked at, frames 39 and 40 have the **rightmost five or six bars jumped to
full height** while the rest of the envelope is unchanged — a block of tall
bars at the top of the spectrum, gone by frame 41. One display frame, seen
twice because the camera runs at 30 and the screen at 25.

## The cause

`peppyalsa`'s `spectrum.c` calls `send_to_pipe` **once per band**:

```c
for(m = 0; m < spectrum_size; m++) {
    ...
    send_to_pipe((unsigned int) (y * spectrum_max));
}
```

and `send_to_pipe` is one `write()` of four bytes. **Thirty separate writes
per frame**, so the FIFO carries a plain byte stream with nothing in it to
say where a frame begins.

`read_latest_frame` takes the last whole 120 bytes of whatever one read
returned. That is the newest frame **only if the read began on a frame
boundary**. When a poll lands part-way through a frame, the 120 bytes it
keeps are the tail of one frame followed by the head of the next — and the
head of a frame is the low bands, which are the loud ones. They land in the
*rightmost* bars. Which is exactly what the video shows.

The meter pipe does not have this fault: `meter.c` packs both channels into
one 4-byte write.

## Measured

Polling the raw pipe at 30 Hz and asking where each read ended:

| | reads ending mid-frame | distinct start offsets |
| --- | --- | --- |
| before | 1 of 239 | **2** — `0`, then `88` |
| after, 3 runs | **0 of 891** | **1** — `0` |

Rare, which is why it reads as an occasional glitch rather than a broken
display. Once it happens the offset persists until the next partial read
realigns it, so a single unlucky poll can spoil a run of frames.

## The fix

**One write per frame**, patched into peppyalsa in the image build
(`peppyalsa-one-write-per-frame.patch`). POSIX guarantees a write of at most
`PIPE_BUF` — 4096 on Linux — is atomic, and a frame is at most 257 values,
so the pipe becomes record-oriented and the splice cannot happen.

The patch is applied with `git apply`, which fails loudly rather than
fuzzily if the pinned upstream commit is ever moved, and the build asserts
the change is in the source before compiling it.

**On our side, the read is rounded down to a whole number of frames.** The
chunk limit is 65536, which is not a multiple of 120; a reader that had
stalled long enough to fill the pipe could truncate a record at the limit
and reintroduce the same splice from the other end.

Built on the device and measured, above.

## What this does not settle

- **Nothing was heard**, and nothing about how the spectrum *should* look.
- **The rate is still peppyalsa's**, one frame per ALSA period.
- **Three runs of ten seconds** is enough to show the fault is gone at that
  frequency, not to prove it cannot happen.
