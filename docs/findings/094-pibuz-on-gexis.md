# Finding 094 — Pibuz on gexis: part 1 and George's first casts

**Date:** 2026-09-27
**Question:** ADR-0098 step 1. Does Pibuz, the receiver moOde uses, work on this
device and through our audio path?

**Scope:** `gexis`, the `peppy-next` image plus hand-deployed Phase 12 work.
Pibuz 2.5.0 `linux-aarch64` was run by hand from `/tmp`, with scratch
configuration under `/tmp`. George cast to it from the Qobuz app on his phone,
on his own account. Observations come from Pibuz's log and `/proc`. **Not
tested:** another household account (there is none); a gapless album (George
ran out of time).

## Setup

- **The release matches its author's checksum** (`04a59815…`). Every library it
  links against is already in our image.
- **Configuration:** `audio.backend alsa`, `audio.device output` (our shared
  PCM), `audio.cache_to_disk false`. It then logs that nothing is written to
  the card.
- **It advertises itself with its own mDNS responder** on udp 5353, beside
  avahi, plus a pairing service on tcp 8183. Pairing needs no login.
- **Its control API listens on 0.0.0.0:8182**, so anyone on the LAN can
  control playback. The integration must bind it to localhost, or set a token.
- **Setting `audio.device` opens the card at once**, not only when a stream
  starts. With LMS playing, the card was busy, and it retried 9 times with
  backoff and then gave up. LMS was not disturbed.

## George's casts

- **It appeared in the app and played.** George: *"I can connect to the device
  and it plays. Volume control works. Playing well."*
- **Rates are native.** It opened `output` at 88.2 kHz and at 44.1 kHz, S32_LE
  (24-bit sources), and re-opened on a rate change. ALSA's plug layer inside
  `output` refused nothing.
- **Quality falls back.** It asks Qobuz for UltraHiRes first. For one track
  that tier was "restricted", and it took HiRes.
- **It holds no sound-card file descriptors while paused.** The card is free for
  another renderer without stopping it. **Corrected 2026-09-28
  ([Finding 096](096-qobuz-connect-with-the-adapter.md)): only 2.06 s after
  the pause.** Too late for go-librespot, which needs the card within 0.26 s.
- **It reports state to Qobuz's servers** about every 1.8 s: position,
  duration and playing state. Volume changes are logged. Its MPRIS and JSON
  events are what the adapter will read. **Nothing on the panel shows it yet**
  (no metadata, no volume screen): as expected, since there is no adapter.
- **A harmless warning repeats:** `login1 Inhibit` fails, because it runs as
  `pi` without polkit.

## George's second round (18:30-19:00)

| Test | Result | Why, from the logs |
|---|---|---|
| 1. Qobuz playing, Spotify takes over | **Fails.** Spotify does not play; the transition screen shows | go-librespot: `failed starting playback: ALSA error at snd_pcm_open: Device or resource busy`, five times from 18:31:01. The core does not know Pibuz holds the card, so no release was sent. |
| 2. Spotify playing, cast to Qobuz | **Fails.** Spotify keeps playing; the Qobuz app shows time advancing with no sound | Pibuz: `Device busy` → nine retries (18:34:23-29) → `Backend system init failed for Play`. **It tells the app it is playing anyway.** |
| 3. Qobuz paused, Spotify plays, Qobuz resumes | Works | A paused Pibuz holds no descriptors on the card - **2.06 s after the pause** (Finding 096). Here the pause came well before Spotify. |
| 4. Disconnect in the app, then Spotify | Works | — |
| 5. 24/192 | **Works** | `format_id=27`, `Hardware configured: 192000 Hz`. Across the session: 44.1, 88.2, 96 and 192 kHz, each at its own rate. |
| 6. Seek, next, previous | Work | Gapless not tried. |

**What this means for the adapter** (ADR-0098 step 3): it is what makes Pibuz
a renderer the arbitration knows about. Test 1 needs a release - pause, which
frees the card (test 3), then stop. Test 2 needs Pibuz's intent to play reported
to the core as an acquisition, *before* it opens the card. Its hook script and
JSON events are the candidates. Pibuz reporting "playing" to the app while it
has no device is a bug to report upstream.
