# Finding 102 — Plugin memory limits hold once the kernel is asked

**Date:** 2026-09-29
**Question:** [ADR-0106](../decisions/0106-plugins-you-install-and-update.md)
caps an uploaded plugin's memory with `MemoryMax` (1 GB, George: *"Limit of
1gb"*). Does the cap hold on the device, and what does it cost?
**Scope:** the Pi 4 on the second card (`sofa-pi`, 4 GB, kernel
`6.18.50+rpt-rpi-v8`, image 755-era with `phase-13ac`'s units deployed by
hand). One reboot with `cgroup_enable=memory` added to `cmdline.txt`. The cap
proved with a throwaway unit, not with a plugin. **Not measured:** CPU cost of
the memory controller, audio under it, a plugin actually reaching 1 GB.

## Before: the cap did nothing

`/sys/fs/cgroup/cgroup.controllers` listed `cpuset cpu io pids`. With no memory
controller, systemd accepts `MemoryMax=` and enforces nothing; the running
plugin unit reported `MemoryCurrent=[not set]`.

## After `cgroup_enable=memory`

| | before | after |
|---|---|---|
| controllers | cpuset cpu io pids | cpuset cpu io **memory** pids |
| `MemTotal` | 3,886,832 kB | 3,886,832 kB |
| plugin unit | `MemoryCurrent=[not set]` | `MemoryCurrent` reported; `MemoryMax=1073741824` |

- **The cap holds.** A unit with `MemoryMax=50M` that allocated 200 MB was
  killed: `Finished with result: oom-kill`, the kernel logging
  `constraint=CONSTRAINT_MEMCG` and naming only that unit's process.
- **It cost no memory the kernel reports**: `MemTotal` is identical.

## What it bears on

- The image sets `cgroup_enable=memory`; the build fails without it.
- A plugin past its cap is killed and restarted by its unit (`Restart=on-failure`);
  nothing else on the device is touched.
