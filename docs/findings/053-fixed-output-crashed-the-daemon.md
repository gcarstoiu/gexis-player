# Finding 053 — Fixed output crashed the daemon

**Date:** 2026-09-23
**Question:** George: *"Check it to make sure"* — on my claim that the
meters see no attenuation in fixed output because the DAC sits at full
scale, which I had read from the code and not watched happen.
**Scope:** `gexis`, 2026-09-23, nothing playing, LMS holding the device at
30%. `output_mode` set to Fixed and back through `PUT /settings/output_mode`,
before and after the fix. **Not tested:** fixed output with something
playing (it defers to the next stop by design), and the headphone jack.

## It did not work at all

The check was meant to confirm one link. It found the feature broken:

```
BEFORE  mode Variable  attenuation 26.00  dac [-26.00dB]
FIXED   mode Fixed     attenuation 26.00  dac [-26.00dB]
```

The DAC never moved, and three seconds later systemd restarted the daemon.

```
21:11:33 gexis_core INFO  output: fixed - DAC to full scale, the panel can no longer lower it
21:11:33 AttributeError: 'VolumeBridge' object has no attribute '_volume_memory'
21:11:33 systemd: gexis-core.service: Main process exited, code=exited, status=1/FAILURE
```

## The cause

**A deletion left one call behind.** The per-renderer volume memory was
removed on 2026-09-23 on George's instruction (*"Point 1 -> delete them"*),
because ADR-0054 §5 asks a renderer where it is when it takes the device.
`renderer_volume.py`, the setting, the constructor argument and the
attribute all went. One line in `VolumeBridge.run` did not:

```python
self._volume_memory.remember(active, raw)
```

**It is on a path almost nothing reaches.** The `alsactl monitor` loop
skips writes it recognises as ours, and every ordinary write goes through
`write_hardware`, which arms that recognition. A write that does *not* —
and entering fixed output is exactly one, `set_raw` straight to full scale
so that `write_hardware`'s refusal cannot block it — looks external. With a
renderer active, the next line ran.

So the one action that makes the mode work is also the one that killed the
process before it could finish.

**This is [LESSONS](../LESSONS.md) case 20's shape again** — a declaration
and the thing it declares in two files, with nothing comparing them — and
case 20's own remedy, `test_registry_wiring.py`, does not cover attributes
inside a class.

## The fix

The line is gone, and `test_volume.py` now drives the monitor loop with a
fake `alsactl` and a fake mixer read: an unexpected hardware change with a
renderer active must reach the adapter rather than raise. **Checked both
ways** — the test fails with the line restored, exactly as the daemon did.

## What it looks like now

Same process throughout, no restart:

```
BEFORE  pid 27160  mode Variable  attenuation 26.00  dac [-26.00dB]
FIXED   pid 27160  mode Fixed     attenuation  0.00  dac [  0.00dB]
AFTER   pid 27160  mode Variable  attenuation 26.00  dac [-26.00dB]
```

**So the link George asked about holds**: entering fixed output puts the DAC
at full scale, the mixer monitor sees it, and the published attenuation
becomes 0 — which is what makes the meters show the source level there
without a special case ([ADR-0057](../decisions/0057-the-meters-follow-the-volume.md)).

The first version printed `-0.00`, because negating 0.0 dB gives negative
zero. It read back as 0 and behaved correctly, and it is still wrong to
leave in a file a person might open; it is `max(0.0, …)` now.

## What this does not settle

- **Nothing was heard**, and nothing was playing. Fixed output *with* music
  defers to the next stop, and that path is still only read, not watched.
- **How long the daemon had been able to die this way.** The line was
  orphaned on 2026-09-23; any `amixer` from outside while a renderer held
  the device would have done it too.
