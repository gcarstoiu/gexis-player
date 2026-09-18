# Finding 033 — The loop-device build failure: the module being loaded is not what decides it

**Date:** 2026-09-18
**Question:** `image/README.md` records the cause of the `export-image`
failure as *"the `loop` kernel module was not loaded"*. R2D2 now autoloads it
at boot (`/etc/modules-load.d/loop.conf`), so the first build after a reboot
was set up as the test: does an autoloaded module prevent the failure?
**System:** R2D2 (CachyOS, kernel 7.2.5-1-cachyos, Docker with `data-root`
`/home/docker`), pi-gen at `7dcb0c5`, repo at `65d62e3`.

**Scope:** one host, two builds on one day, plus the two builds of
2026-09-17 read from their logs. Nothing here was tried on another machine
or another kernel, and no fix was applied — the state was recorded, not
corrected.

## Result

**No. The module was loaded and the build failed exactly as before.** What
distinguishes a failing build from a passing one on this host is whether a
**`/dev/loopN` node already exists**, not whether the module is loaded.

### What was recorded before the build

`id` includes `docker` (950). Then, before anything was run:

```
$ lsmod | grep -w loop
loop                   45056  0
$ ls -l /dev/loop*
crw-rw---- 1 root disk 10, 237 17. Sep 13:28 /dev/loop-control
```

So: **module loaded, use count 0, and no `/dev/loop0`.** This is the state
the autoload was supposed to make safe.

### What the build did

`make image` ran every stage and failed at the same place as 2026-09-05 and
2026-09-17, after 210 s:

```
[09:10:45] Begin /pi-gen/export-image/prerun.sh
Creating loop device...
mknod: invalid minor device number '/dev/loop0 (lost)'
Error in losetup.  Retrying...
   … five more, identically …
ERROR: losetup failed; exiting
```

`losetup -f` reports `/dev/loop0 (lost)`: the kernel knows loop0 is free,
but there is no node to reach it by. pi-gen's `ensure_next_loopdev()` takes
the trailing digits of that string for a minor number, its sed pattern does
not match, and the whole string reaches `mknod`.

### What changed by itself

Immediately after the failed build:

```
$ ls -l /dev/loop*
brw-rw---- 1 root disk  7,   0 18. Sep 11:10 /dev/loop0
crw-rw---- 1 root disk 10, 237 17. Sep 13:28 /dev/loop-control
```

**`/dev/loop0` now exists**, created during the failed build. That is why
every *rerun* on this host has passed, including 2026-09-17's: the first
attempt leaves behind the node the second one needs. It is also why
`modprobe -r loop && modprobe loop` worked in September — reloading makes
udev create the nodes; it is the nodes, not the module, that were missing.

### The rerun

Started immediately after, with `/dev/loop0` now present and nothing else
changed: **it passed**, end to end in 464 s, and produced
`2026-09-18-gexis-player-v0.2.1-232-g65d62e3-dirty.img`
(`image/verify-image.sh`: all checks passed). `losetup -a` during the run
showed the export step holding `/dev/loop0` - the node the first attempt had
left behind. Two builds minutes apart, differing in nothing else.

## What this corrects

`image/README.md`'s "Known issue (resolved)" section names the root cause as
the module not being loaded. On the evidence above that is wrong, and the
fix it recommends works for a reason it does not state. The section needs
correcting.

**A durable fix has not been chosen** — it needs George, and `sudo`.
Candidates, none tried:

- create a node before the build (`sudo losetup -f` on the host, or
  `mknod /dev/loop0 b 7 0`), which is what a rerun does by accident;
- load the module with nodes asked for up front (`loop max_loop=8` as a
  module option, so udev creates `/dev/loop0-7` at boot);
- keep the reload, but in the build script rather than in a person's memory.

## Applied 2026-09-18, and what that does and does not prove

George ran the second candidate:

```
$ cat /etc/modprobe.d/gexis-loop.conf
options loop max_loop=8
$ sudo modprobe -r loop && sudo modprobe loop
$ ls -l /dev/loop*
brw-rw---- 1 root disk 7, 0 … /dev/loop0
   … through /dev/loop7 …
$ cat /sys/module/loop/parameters/max_loop
8
```

**Proved:** the option takes effect and the module creates eight nodes when
it loads; udev settles them to `root:disk`, `brw-rw----`, the same as the
node a build leaves behind. `/etc/modules-load.d/loop.conf` (contents:
`loop`) already loads the module at boot, and `/etc/modprobe.d` supplies
options to *any* load of it, including that one.

**Still not proved after the build of 2026-09-18 20:02** (the Phase 8
image, 478 s, first attempt, no `(lost)` failure). R2D2 had not rebooted -
`uptime` 1 day 6 hours - so `/dev/loop0-7` were still the ones `modprobe`
made by hand that morning. The build exercised the working case and says
nothing about the boot-time one.

**Not proved:** that the nodes are there at boot, which is the only thing
that matters. The one test is a **first build after a reboot** - this
finding's own test, run in the other direction. Until that has happened,
this is a reasoned fix, not a measured one. **The next person to reboot R2D2
should record `ls -l /dev/loop*` before building and note the result here.**

Until one is chosen, **the first build after a reboot on R2D2 will fail and
the second will pass.** That is a known, cheap failure - 210 s - but it must
not be read as a build problem.
