# ADR-0036 — Peppy screen entry: the button, or five minutes of unattended playback; and no sample rate or codec anywhere

**Status:** Accepted; §2 amended 2026-10-02 (the visualiser shows LMS's sample rate)
**Date:** 2026-09-16
**Raised by:** George, settling Phase 5's two open questions before it starts
**Amends:** [0019](0019-peppy-screen-lifecycle.md) — renames its implicit entry
and states what resets it; removes its "Bluetooth shows the codec" rule.
Sits beside [0033](0033-idle-and-home.md), which took the word *idle* for the
screen-blanking timer.

## 1. Entry

Two ways in, unchanged in spirit from ADR-0019 but now defined:

- **The button** on now playing (Phase 5's last criterion).
- **Five minutes of unattended playback.** Music is playing and nobody has
  touched anything.

**What counts as attention, and so restarts the five minutes:**

| event | attention? |
|---|---|
| touch on the panel | yes |
| a forced track change | yes |
| a renderer change | yes |
| a volume change, from anywhere | **no** (George, 2026-09-16) |
| a track ending and the next one starting | no |

Volume is excluded deliberately: it is the one thing people adjust without
looking at the screen, and it already has its own surface (ADR-0034's drawer).

**Not the same timer as ADR-0033's idle screen.** That one counts while
*nothing* is playing; this one counts while something is. A device playing
music reaches the Peppy screen, never the idle screen.

## 2. No sample rate, no codec, anywhere

George, 2026-09-15 and 2026-09-16: neither is displayed on any screen, the
Peppy screen included. **ADR-0019's "Bluetooth shows the codec, not a rate" is
withdrawn** — it existed to make the rate field honest, and the field is gone.

Skins that carry a rate field simply do not render it, which is Phase 5
criterion 7's existing rule ("absent fields do not render their layer") rather
than a new exception. The `sample_rate` and `codec` fields stay in `/state`:
they cost nothing, and removing published data to match a rendering decision
would be the wrong direction.

### Amended 2026-10-02: the visualiser shows LMS's sample rate

George, on a skin whose renderer mark sat off-centre in its box: *"Wouldn't
it be easier to add the actual sample rate? I know it would go back on a
previous decision, but might be helpful for the user"*; then *"Let's do A"*.

- **On the visualiser only, where the skin reserves a place for it**
  (`playinfo.samplerate.pos`), **and only for LMS**, whose rate is the file's
  own. Every other screen keeps §2.
- **Spotify is not shown:** its 44.1 kHz is the decoder's rate for a lossy
  stream, which ADR-0015 calls true and misleading. Bluetooth and plugins
  report none.
- **Where the rate is drawn, the renderer's mark sits in the skin's own box**,
  as the skin was designed (an icon with the rate beside it). Where it is
  not, the mark is centred in the slot measured for the skin.

## Open — needs George

**How a forced track change is recognised.** The daemon sees *that* the track
changed, not who caused it. Our own transport commands (Phase 6) are
detectable; a skip from the LMS or Spotify phone app is not, directly.

Proposed rule, to verify on hardware: a track change is **forced** when the
previous track ended early — its last reported position was more than a few
seconds short of its duration — and **natural** otherwise. Bluetooth publishes
no position, so every Bluetooth track change would read as natural.

The alternative is to treat only our own commands as forced, which is exact
but calls a phone skip "unattended" and lets the Peppy screen arrive while
somebody is actively skipping tracks from the sofa.
