# Finding 012 — Bluetooth's frozen ceiling traced to BlueALSA's own SoftVolume, and a volume-before-release ordering bug fixed

**Date:** 2026-09-10.
**System:** `gexis` — live hardware, patched in place via SSH, same
pattern as Findings 008-011. George confirmed Finding 011's two
acquisition-signal fixes hold up ("clear improvement on all fronts")
and reported one remaining Bluetooth volume symptom.
**Scope:** both root causes below are confirmed directly on hardware
(BlueALSA's own persisted per-device state, its own upstream source,
and `gexis`'s own arbitration log), not inferred. Both fixes are
**deployed live on `gexis`, not yet re-tested by George** - this
finding is written to hand off for that confirmation before an image
build.

---

## 1. Bluetooth's volume ceiling was frozen, disconnected from the phone's own slider — BlueALSA's SoftVolume, not our mirror

**Symptom:** "the Bluetooth scale is lower than Spotify and LMS ... it
can do for sure more but it is somehow limited... if I play on
bluetooth on full volume and then change to LMS ... the sound gets
louder ... When I come back to bluetooth then the previous max volume
is present."

**This closes Finding 006's long-open "Bluetooth volume partly
software" question - it wasn't "below ~96%", it was the whole range,
the whole time.** Confirmed on the device directly, not guessed:

```
$ sudo cat /var/lib/bluealsa/64:9D:38:E3:E5:2A
[/org/bluealsa/hci0/dev_64_9D_38_E3_E5_2A/a2dpsnk/source]
SoftVolume=true
...
[/org/bluealsa/hci0/dev_64_9D_38_E3_E5_2A/a2dpsnk/sink]
SoftVolume=true
```

`bluealsa-aplay`'s own upstream source
(`utils/aplay/aplay.c:io_worker_mixer_volume_sync_alsa_mixer`) contains:

```c
/* Skip update in case of software volume. */
if (ba_pcm->soft_volume)
    return 0;
```

With `SoftVolume=true` persisted for this device, `bluealsa-aplay`
**never once** writes an AVRCP-driven volume change to our
`hw:gexisbtvol` mixer control - it applies the volume digitally to the
audio samples internally instead. Confirmed against the actual log:
across two full boot sessions (2026-09-08 and 2026-09-10), bluealsa's
own daemon log shows dozens of real `Updating A2DP volume` events
spanning the full 0-127 range, while `gexis_core`'s own `"bluetooth ->
hardware"` mirror line **never appears once**. The real DAC's gain
during a Bluetooth session is whatever it happened to be left at when
Bluetooth acquired (the floor-bump, or a leftover LMS/Spotify level) -
completely disconnected from the phone's own volume slider for the
rest of that session. This explains both halves of George's report at
once: a ceiling that doesn't track the phone ("it can do more but is
limited" - BlueALSA is digitally near-unity at the phone's reported
max, but our hardware gain is stuck below it), and the exact
"previous max reappears on reconnect" behaviour (each new session just
inherits whatever the DAC was left at, never anything the phone did
this session).

**Fix:** `bluealsa-aplay`'s `ExecStart` now adds `--volume=mixer`
(`image/stage-gexis/02-renderers/files/bluealsa-aplay-override.conf`).
Confirmed against this build's actual installed binary (`bluealsa-aplay
--help`) before deploying, not assumed. Per the same source read,
`--volume=mixer` makes `bluealsa-aplay` explicitly push
`SoftVolume=false` over D-Bus for the PCM on every connection whenever
it differs from the currently persisted value - so this will take
effect on the paired phone's **next** reconnect, not needing any manual
edit of BlueALSA's storage file.

**Deployed live** (`/etc/systemd/system/bluealsa-aplay.service.d/
override.conf` updated, `daemon-reload` + `systemctl restart
bluealsa-aplay.service`, confirmed active with the new `ExecStart`
argv). **Not yet re-tested** - needs a real Bluetooth reconnect and a
full-range slider drag to confirm `"bluetooth -> hardware"` mirror
lines now appear and the DAC tracks the phone's own volume.

## 2. Restoring the incoming renderer's volume before the outgoing one had actually released — a real, general ordering bug, not Bluetooth-specific

**Symptom, the "fraction of a second louder" half of George's report:**
"if I play on bluetooth on full volume and then change to LMS which is
set for example at 70%, then for a fraction of a second before LMS
takes over, the sound gets louder on the song playing on bluetooth."

**Confirmed directly in `gexis`'s own log**, a Bluetooth->LMS handoff
captured live during this investigation:

```
13:37:09,549  acquire: lms takes the device (was bluetooth)
13:37:09,549  volume: restoring lms to 240/240        <- real DAC set to max, right here
13:37:11,886  release[bluetooth]: polite stop freed the device (2.3s)   <- only now actually silenced
```

`Supervisor.acquire()` called `restore_volume(renderer_id)` (which
writes the **shared real DAC**, `write_hardware()`) immediately, before
`_release_with_ladder(outgoing)` ran at all - so for however long the
outgoing renderer's release ladder takes (Bluetooth's own polite-stop
grace measured at 2-3s repeatedly across this and prior sessions, not
instant), the real DAC sat at the **incoming** renderer's target volume
while the **outgoing** renderer's audio was still the only thing
actually playing through it. In this capture that's LMS's own 240/240
(0dB, full volume) landing on Bluetooth's still-playing audio for 2.3
seconds - a loud, audible blip, exactly George's report. This isn't
Bluetooth-specific - it's a property of the shared physical DAC and
applies to any renderer pair; Bluetooth's release ladder just happens
to be the slowest of the three (LMS's own `-C 1` release is usually
~0.1s, rarely long enough to notice).

**Fix: reordered `Supervisor.acquire()`** to release the outgoing
renderer first, restore the incoming renderer's volume only after
(`core/src/gexis_core/arbitration.py`). The incoming renderer generally
can't produce sound yet at the point `acquire()` runs anyway - the
shared device is still held by whoever's being released - so this costs
nothing and removes the blip. All 56 existing tests pass unchanged (the
two tests asserting `restore_volume` is called with the right
renderer_id don't assert its position relative to release).

**Deployed live** (`gexis-core.service` restarted, clean startup
confirmed). **Not yet re-tested against a real handoff** - needs a
Bluetooth-at-full-volume -> LMS-at-a-lower-level switch, watching for
the blip to be gone.

---

## Not established

- Whether §1's fix (`--volume=mixer`) actually restores Bluetooth's
  usable ceiling to match Spotify/LMS in practice, and whether the
  mirror log now fires - needs a real reconnect and slider drag,
  George's to confirm.
- Whether §2's reordering fully eliminates the blip in every handoff
  direction (LMS->Bluetooth, Spotify->Bluetooth, etc.), or only the
  specific direction captured here - the mechanism is general, but only
  one direction has been observed with timestamps precise enough to
  confirm the gap.
- Whether BlueALSA's `SoftVolume` defaults to `true` for every newly
  paired device, or whether this phone's `true` came from some earlier
  testing session (stock Volumio config, an earlier build) - doesn't
  change the fix (`--volume=mixer` forces the state we want regardless
  of how a device got here), but worth knowing if it recurs on a
  different phone unexpectedly.
