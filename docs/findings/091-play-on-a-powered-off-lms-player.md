# Finding 091 — Pressing play on a powered-off LMS player while another renderer holds the device

**Date:** 2026-09-26
**Question:** George, after a round of takeovers: *"once lms seemed to have
issues starting - at least the progress bar was going to zero then advancing
then going to zero again ... Especially with Lms I remembered we fixed these
issues and now I am seeing them back."* Is it a regression, and what is it?

**Scope:** `gexis`, image `v0.2.1-608-gd29ee48` plus this session's hand-deployed
core. squeezelite `2.0.0-1517+git20241227.262994a-1+b1` (Debian's package). LMS
at `192.168.178.188`, player `gexis`, one track queued. **Plexamp** was the
renderer holding the device, not Spotify, so George's paused Spotify session was
not touched; George's own two occurrences (20:56:35, 20:57:14) were against
Spotify and show the same signature. `play` was sent through LMS's JSON-RPC, the
same request an LMS app's play button makes. One run of each case below, plus
George's two - a trace of a mechanism, not a distribution.

## Not a regression - a path the fixes never covered

[ADR-0027](../decisions/0027-lms-power-as-arbitration-mechanism.md) made
**powering the player on** the acquisition, and everything measured since was
measured that way: [Finding 020](020-criterion8-takeover-gap-adr0027.md)'s
335 ms Spotify → LMS says *"LMS is driven by activation (`power 1`)"*, and
concludes squeezelite *"never makes a failed open"*. That holds for activation.
ADR-0027's own *Open* section names the other path - *"Pressing play rather than
activating loses the position"* - and the seek-back that followed fixed the
position. **Nothing fixed the device.** None of this session's changes touch the
LMS acquisition path.

## What happens

Pressing play on a powered-off player makes LMS power it on **and** send the
stream at once. squeezelite tries the device within ~0.1 s and it is busy; the
core only hears of the power-on from LMS's CometD push **1.45-1.5 s** later
(20:56:35.47 → 36.95; 20:57:14.32 → 15.79; 21:25:37.84 → 39.29). Freeing the
device from there is fast (0.1-0.2 s). **squeezelite then waits out its own
retry tick, a fixed 5 s** (Finding 020), so audio starts about 5.5 s after the
press - and LMS reports positions for a stream that is not playing meanwhile:

Nothing to go back to (player released at 89.8 s by a core since restarted):

```
+0.12s  power=1 mode=play time=  0.0
+0.45s               time=154.7      <- the end of the track
+1.98s               device freed
+5.44s               time=  0.0      <- audio, from the start
```

Released at 18.9 s by the core, so the seek-back applies:

```
+0.01s  time=  0.0
+0.24s  time= 14.0
+1.98s  time= 18.9  device freed; core: "position was 14.3s, seeked back to 18.9s"
+3.55s  time= 62.8
+5.50s  time= 18.9  <- audio
```

That is the bar George saw. With more than one track queued, the jump to the
end presumably moves LMS to the next track; not measured, one track was queued.

## What would change it

- **squeezelite retrying the open quickly.** The only lever that removes the
  5 s. It is a compile-time sleep, not an option, so it means building
  squeezelite ourselves with a patch instead of taking Debian's package. The
  same kind of patch would close ADR-0091's residual race in go-librespot, which
  also gives up on a busy device.
- **Hearing the power-on sooner does not help**: squeezelite fails within
  ~0.1 s of the press, and the push arrives in 0.5-1.5 s.
- **Restarting squeezelite once the device is free** would skip the tick and is
  Finding 013 §1's restart storm, reverted twice. Not proposed.

## What this does not establish

- Whether a queue of several tracks moves on to the next one.
- Any number for George's Spotify-holding case beyond the two log timestamps.
- Whether a patched retry leaves LMS's position reporting clean, or only
  shorter.
