# Finding 011 — Fourth hardware round: two acquisition-signal fixes, two floor/fallback values flagged for a product call

**Date:** 2026-09-08 test session, investigated and fixed 2026-09-10 (the
gap is a context-limit interruption mid-investigation, not a gap in
testing - the log is the same `journalctl -b` capture pulled on
2026-09-08, still present on `gexis` at investigation time).
**System:** `gexis` — live hardware, patched in place via SSH, same
pattern as Findings 008/009/010. Logs pulled from `journalctl -b`
covering George's 2026-09-08 test session (17:17-17:53).
**Scope:** George reported four symptoms after Finding 010's fixes. Two
have precisely evidenced root causes with fixes deployed live on
`gexis` but **not yet verified against a fresh connect/takeover cycle**
(George was unavailable to test this round - the next session should
confirm before either fix is folded into an image build). Two more are
narrowed to a specific number needing George's call, not a mechanism
bug. One is a confirmation requiring no action.

---

## 1. Bluetooth's acquisition race (Finding 010 §3) — George approved a fix, implemented, not yet live-verified

**George's decision, 2026-09-08:** "let's go with your recommendation
for the Bluetooth part" - proceed with an earlier acquisition signal,
with a live verification pass before it's trusted, not a blind swap.

**Implemented:** `BluetoothAdapter` now also acquires on
`org.bluez.MediaTransport1` appearing (`InterfacesAdded` at a
`.../dev_XX/fdN` object path), alongside the existing `MediaPlayer1`
trigger. Confirmed, not assumed, from two independent sources before
writing this:
- BlueZ's own `doc/media-api.txt` ("MediaTransport1 hierarchy", object
  path `.../dev_XX_XX_XX_XX_XX_XX/fdX`).
- `gexis`'s own bluealsa log, which shows `fdN` appearing via
  `InterfacesAdded` several seconds before the transport's `State`
  property ever changes, and well before `bluealsa-aplay`'s own PCM-open
  attempt - e.g. `fd0` appeared at `17:39:13`, `bluealsa-aplay` didn't
  attempt to open its ALSA playback PCM until `17:39:25`.

This is the same "control plane, not stream start" acquisition
philosophy ADR-0010 already uses for `MediaPlayer1` - the transport
*object* exists once profile negotiation begins (`media-api.txt`: State
starts at `"idle"` or `"pending"`, only reaching `"active"` once
actually streaming), independent of whether `bluealsa-aplay` has managed
to open anything yet. `Supervisor.acquire()` is a no-op for an
already-current renderer, so whichever of the two D-Bus signals fires
first wins and the other is a harmless re-fire.

**Deployed live on `gexis`** (both adapter files copied into
`/opt/gexis-core/venv/lib/python3.13/site-packages/gexis_core/adapters/`,
`gexis-core.service` restarted, clean startup confirmed in the log - no
import or connection errors). **Not yet exercised against a real phone
connect/disconnect cycle** - George was not available to test this
round. Confidence is reasonably high (the signal exists and fires
earlier by a wide margin, several seconds not milliseconds, in the
captured log), but per George's own caveat this needs a real cycle
before being folded into an image build.

## 2. Spotify's own acquisition signal could never fire while LMS held the device — a real deadlock, root-caused from upstream source, fixed, not yet live-verified

**Symptom:** "Spotify cannot take over from lms while Lms is playing
unlike Bluetooth which takes over fine."

**This is not the same shape as Bluetooth's ~1s race - it's a genuine
catch-22, confirmed by reading go-librespot's own source, not
guessed.** `SpotifyAdapter` acquires on go-librespot's `"active"` WS
event; the adapter's own docstring (written before this round) assumed
it "fires when a device is selected in the app." Reading
`devgianlu/go-librespot`'s `daemon/controls.go` and `daemon/player.go`
(both the `"transfer"` and `"play"` command handlers, which cover the
two ways a phone can hand playback to `gexis`) shows that assumption was
wrong: `ApiEventTypeActive` is emitted only **after**
`loadCurrentTrackOrSkip()` returns successfully - and that call is what
opens the ALSA device. If the open fails, the function returns an error
and `"active"` is never emitted at all.

**Confirmed directly against `gexis`'s log**, not inferred from the
source alone:

```
17:44:15  lms: player mode -> play (acquisition)
17:44:15  acquire: lms takes the device (was spotify)
17:44:15  release[spotify]: polite stop freed the device (0.1s)
17:44:15  go-librespot: loading previously persisted zeroconf credentials
17:44:22  go-librespot: failed loading current track (transfer): ...
          ALSA error at snd_pcm_open: Device or resource busy
17:44:26  go-librespot: failed seeking stream: ... Device or resource busy
17:44:26  go-librespot: failed seeking stream: ... Device or resource busy
17:44:28  go-librespot: failed skipping to next track: ... Device or resource busy
17:44:47  go-librespot: playback was transferred to Pixel 10 Pro   <- phone gave up, re-transferred
17:44:47  go-librespot: loading previously persisted zeroconf credentials  <- fresh attempt
17:44:52  go-librespot: loaded track "Paranoid..." (paused: false)
17:44:52  spotify: device became active (acquisition)   <- 37s after the reclaim
17:44:53  release[lms]: polite stop freed the device (0.1s)
```

For 37 seconds, go-librespot repeatedly tried and failed to open the
ALSA device (busy, because LMS held it), and **had no way to tell our
arbitration it wanted the device**, because the only signal
`SpotifyAdapter` listens for depends on that same open already having
succeeded. The phone's own retry (re-initiating the transfer at
`17:44:47`) happened to land in a moment the device was free enough to
succeed - this is opportunistic, the same shape as the erratic,
sometimes-works-sometimes-doesn't symptom George described, not a fix.

**Fix: also acquire on `"will_play"`.** The same source read
(`daemon/controls.go`'s `loadCurrentTrack`) shows this event is emitted
earlier in the identical call chain, before any ALSA access is
attempted. Same "control plane, not stream start" shape ADR-0010
already uses for the other two renderers - a corrected signal choice,
not a new kind of trade-off. `Supervisor.acquire()`'s idempotency means
`"will_play"` also firing on ordinary in-session track changes (while
Spotify is already active) is harmless.

**Deployed live on `gexis`** alongside the Bluetooth fix, same restart,
same clean startup. **Not yet exercised against a real LMS-playing ->
Spotify-takeover cycle** - next test session should confirm, same
caveat as §1.

## 3. Spotify's first-ever acquisition falls back to a boot-safety value, even mid-session — narrowed to a specific number, needs George's call

**Symptom:** "switching for the first time from [l]ms to Spotify
results in no sound from Spotify until the volume button on the phone
is pressed."

**Confirmed directly in the log**, `17:41:40`:
`volume: restoring spotify to 60/240` - raw 60 is -90dB on the DAC's
0.5dB/step scale, the same value the boot script writes once at power-on
(`"boot volume: setting 'DAC' to 60/240 (fixed safe level, not
restored)"`, `17:17:53`). This was Spotify's first acquisition of the
session, over 20 minutes after boot, by which point LMS had already been
playing loudly (226-235/240) for minutes. `RendererVolumeMemory.
resolve_restore()` falls back to `boot_default` for *any* never-remembered
managed-renderer acquisition, not only a true cold-boot one, and its own
docstring already documents this as deliberate, not an oversight (see
`docs/decisions/0018`'s newly-added "To be recorded once resolved"
entry for the two options). **Not changed here** - this is
ADR-0018's own boot-safety rationale not covering the case it's actually
firing on, a product question about what the right fallback is for
"never used this renderer before, but the system is clearly already in
safe-to-be-loud territory," not a bug to silently patch.

## 4. Bluetooth's unmanaged floor-bump fired correctly and still wasn't enough — the mechanism works, the number needs George's call

**Symptom:** "Bluetooth connected and no sound came until I first
played something over lms and then reconnected."

**Confirmed directly in the log**, `17:39:16`: `volume: bluetooth is
not volume-managed, but the mixer was left at -45.0dB - bumping to the
-40.0dB floor rather than starting silent` - the floor-bump mechanism
added for exactly this class of symptom (Finding 006/`unmanaged_floor_raw`)
fired, and reached hardware via `write_hardware()` as designed. But
George's report on this same connection was still "no sound." The
"played over lms and then reconnected" recovery matches the mechanism
precisely: once LMS raised the real DAC to a loud level (226+/240) on
its own, Bluetooth's floor-bump check (`current >= floor_db`) found
nothing to bump and left the now-loud level alone.

**Not changed here** - the mechanism is doing exactly what it was
designed to do; `-40.0dB` (`restore_volume_floor_db`) is simply not
loud enough to register as audible on George's hardware/room, and
picking the right number is his call, not mine (see `docs/decisions/
0018`'s new entry).

## 5. Volume curves — confirmed good, no action

George: "the volume curves are good." Confirms Finding 009/010's
dB-linear curve fixes (LMS's dummy-control translation, Spotify's own
fraction-to-hardware translation) are working as intended in real use.
No further action.

---

## Not established

- Whether §1/§2's deployed fixes actually close the gaps they're aimed
  at, under a real connect/disconnect or takeover cycle - implemented
  and reasoned from strong evidence (BlueZ's own doc, go-librespot's own
  source, both cross-checked against `gexis`'s live log), but not yet
  exercised live. Do not fold into an image build before that
  confirmation.
- Whether `"will_play"` fires reliably for every path that can hand
  Spotify the device while LMS is playing - confirmed for the
  `"transfer"` and `"play"` dealer commands (both route through
  `loadContext -> loadCurrentTrackOrSkip -> loadCurrentTrack`, where
  `"will_play"` is emitted), not exhaustively checked against every
  entry point in go-librespot's command handling.
- The right numeric floor for §3 and §4 - deliberately left to George,
  not guessed at here.
