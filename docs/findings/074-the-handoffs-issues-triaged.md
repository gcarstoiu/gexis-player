# Finding 074 — The handoff's issues, triaged

**Date:** 2026-09-25
**Question:** Phase 9 criterion 4 — *the handoff's "issues to look at later"
are triaged: fixed, scheduled, or dropped.* What is on that list and what is
true of it now?
**Scope:** the list as `docs/HANDOFF-ARCHIVE.md` carries it, *Issues to look
at later (Phase 6 hardware rounds, 2026-09-16)* and the *Follow-ups, not
blocking* beneath it — ten items. Each checked against the current code, the
current device, or the record that closed it. **Two are dropped on a single
non-reproduction**, which is stated rather than dressed up.

## Issues

| # | item | disposition |
|---|---|---|
| 1 | **Plexamp over Bluetooth reports pauses 4.5–6 s late, or never** | **Scheduled — Phase 11**, confirmed by George 2026-09-25. Plexamp is that phase's named renderer, and the open next step ("with the speakers on: does Plexamp's audio stop at the tap?") wants the device and the app in hand at once |
| 2 | **LMS player on fixed volume (`digitalVolumeControl` 0), nothing warns** | **Fixed 2026-09-25.** See below |
| 3 | **Pausing LMS moved the DAC slightly** (dummy −47 → −50 dB, DAC 152 → 150) | **Explained, and the mechanism is handled.** LMS fades the player out on pause by sending volume steps — found independently on 2026-09-17, when mirroring them published the user's volume as 0 %. `DummyMixerBridge` takes an `is_playing` and waits for the control to settle. **The original measurement was never re-taken**, so this is an explanation that fits, not a re-test |
| 4 | **After a `gexis-core` restart, a connected phone is not active** | **Fixed 2026-09-18**, both halves — the entry says so itself. Spotify reads `/status` on connect, Bluetooth acquires from the startup scan when `Status` is playing. Neither acquires for a *paused* session, deliberately |
| 5 | **LMS once reported a position ~5 s ahead on resume** | **Dropped**, George's ruling 2026-09-25: *"non reproducible"*. One sighting, not reproduced on the second try, never seen since. A new finding if it returns |

## Follow-ups

| | item | disposition |
|---|---|---|
| a | `viz_timeout` read by the daemon but not in the registry | **Fixed.** Wired and surfaced; the device reports `viz_timeout` 5 min and `viz_stop` 1 min, both `wired: true` |
| b | The stock skins are Volumio-branded; Gelo5's are the image default | **Dropped — not an issue.** A statement of what ships |
| c | Long titles are cut with `…`; the wrapper scrolls them | **Dropped — a statement of behaviour**, and the behaviour is wanted |
| d | Fonts: DejaVu, DSEG7; PeppyFont not vendored | **Dropped — a statement of fact** |
| e | The spectrum once overlapped the remaining time on `dash-spectrum` | **Dropped** on the same ruling, *"non reproducible"*, and very probably already fixed. [Finding 049](049-the-spectrum-draws-more-bars-than-it-has-room-for.md) is *the spectrum draws more bars than the skin has room for*, corrected 2026-09-23, and an overflowing spectrum landing on neighbouring text is what that looks like. **Not proven to be the same sighting** — it was never reproduced, so there is nothing to compare against |

## Item 2, the one that needed work

`digitalVolumeControl` at 0 means **LMS moves its own number and always sends
full level**, so no volume change from LMS or a phone reaches the device.
George met it as *"phone volume does nothing while the panel is muted, and
LMS's volume bar is frozen"*, and mute became a trap, because the one change
that ends it ([ADR-0034](../decisions/0034-panel-volume-travel-and-mute.md))
never arrived. **Nothing in this repository sets it and nobody set it by
hand.** The cause is still unknown.

What was missing was not a fix but a name. The daemon now reads the pref once
the player id is known and says what it found:

```
lms: digitalVolumeControl=1 on 88:a2:9e:79:e1:32
```

and, with it at 0:

```
lms: player 88:a2:9e:79:e1:32 has digitalVolumeControl=0 (fixed volume). LMS
will move its own number and always send full level, so no volume change from
LMS or a phone reaches this device, and mute cannot be ended from there. Set
it to 1 in LMS's player settings.
```

**Both branches were exercised on the device**, by setting the pref to 0 on
George's server, restarting, reading the journal, and setting it back to 1 —
confirmed `1` before and after.

**It says so and does not act.** Writing a pref on somebody's music server
because we disagree with it is not ours to do, and 0 is a real choice for
anybody driving the DAC from elsewhere.

## What this does not settle

- ~~**Whether the warning should be visible anywhere but the journal.**~~
  **Settled 2026-09-25: no.** George, asked whether a readonly row or a notice
  should carry it: *"No."* The journal is where it lives.
- **Item 1's answer.** Scheduling is not diagnosing.
- **Item 3's numbers.** The explanation fits and the mechanism is handled; the
  measurement that raised it has not been repeated.
