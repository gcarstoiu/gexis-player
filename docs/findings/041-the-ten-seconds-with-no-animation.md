# Finding 041 — The boot animation stops 10.2 s before the panel appears

**Date:** 2026-09-20
**Question:** George, 2026-09-20: *"the console is still shown"*, and *"the
main aim is to have a continuous animation until the player takes over"*.
ADR-0043's fixes were all installed by hand on 2026-09-19 and this is the
first boot with them. What did that boot actually do?
**System:** `gexis`, booted 2026-09-20 07:58:31 CEST, boot id
`8c55018e…1f885`, Pi 4B Rev 1.5, serial `10000000c1653df6`. Kernel
6.18.50+rpt-rpi-v8, Chromium 153.0.8010.47, labwc on Wayland.
**Scope:** **one boot, one device, read from its logs after the fact.**
Nothing here was seen on the panel — there is no photograph and no video, and
§4 is explicit about which claims that limits. Times are kernel-monotonic;
PID 1 starts at 5.913 s, which is the offset reconciling `systemd-analyze`
with the journal.
**Relates to:** [ADR-0043](../decisions/0043-boot-animation-and-a-silent-boot.md),
[Finding 038](038-what-the-panel-shows-while-it-boots.md) (the budget),
[Finding 039](039-what-only-a-real-boot-found.md) (the five defects this boot
was meant to have fixed)

## The point

**The animation ends at 25.64 s and the UI paints at 35.79 s.** For 10.15 s
of every boot nothing this project controls is drawing an animation, and for
5.93 s of that nothing is drawing at all. ADR-0043 names neither interval.
It treated the handover as a seam to be closed and it is not a seam; it is
ten seconds, and it is most of what somebody watching the device actually
sees after the logo settles.

The console complaint is a separate question and **this finding does not
answer it** — see §4.

## 1. The timeline

| t (s) | what happens | on the panel | evidence |
|---|---|---|---|
| — | firmware, **duration unmeasured** — there is no clock before the kernel | black (`disable_splash=1`) | `config.txt:57` |
| 0.00 | kernel | black | `printk: legacy console [tty3] enabled` |
| **~1.8 – 4.0** | **plymouth starts, from the initramfs** | ▶ **animation** | see §2 |
| 5.91 | PID 1 | animation | `UserspaceTimestampMonotonic=5913195` |
| 10.71 | plymouthd tells systemd to print status | animation | `Received SIGRTMIN+20 from PID 180 (plymouthd)` |
| 10.70 → 33.06 | `gexis-panel-warmup` reads 483 MB | animation | `gexis-panel-warmup: warmed 483MB` |
| 19.42 → 25.31 | `NetworkManager-wait-online` — **5.996 s** | animation | `systemd-analyze blame` |
| 25.44 | `gexis-kiosk.service` starts; VT clear runs, exits 0 | animation | `printf "\033c" > /dev/tty1`, pid 2318 status=0 |
| **25.64** | **plymouth quits — animation ends** | ■ **gap opens** | `Received SIGRTMIN+21 from PID 180` |
| 25.65 | labwc exec'd | gap | `ExecMainStartTimestampMonotonic=25648513` |
| 26.28 | PAM session opens | gap | `pam_unix(login:session): session opened for user pi` |
| 27.91 → 31.50 | **3.6 s with no log output from anything** | gap | journal gap |
| **31.55** | compositor ready; `swaybg` draws `boot-0100.png` | ▣ **frozen still** | `gexis-kiosk: compositor ready` |
| 31.56 | chromium exec'd | still | `gexis-kiosk: exec chromium` |
| 34.76 | Chromium's window appears | ◻ white | `Started app-org.chromium.Chromium-2408.scope` |
| **35.79** | **UI paints** | ◆ UI | `POST /panel/painted HTTP/1.1 200 201` |
| 94.13 | backstop timer fires, quit returns 1, unit succeeds | no effect | Finding 039 §3's fix, working |

### The three intervals

| | from → to | length | what is drawn |
|---|---|---|---|
| **D1** | 25.64 → 31.55 | **5.93 s** | nothing under this project's control |
| **D2** | 31.55 → 34.76 | **3.21 s** | a frozen frame (`swaybg`) |
| **D3** | 34.76 → 35.79 | **1.01 s** | white — Finding 039 §5, parked by George |

**D1 is structural, not a bug.** Plymouth is DRM master for as long as it
runs, so it must die before labwc can open the GPU (ADR-0043 §3, corrected).
labwc then needs its own start-up time, during which the device it was handed
is held by nobody drawing. D1 is that start-up: ~2.0 s of PAM, logind and the
user manager, then ~3.9 s of labwc itself.

**D1 also grew.** Finding 039 measured `gexis-kiosk.service` starting at
21.9 s; here it is 25.44 s, because `NetworkManager-wait-online` took
5.996 s rather than its previous cost. The gap tracks the compositor's
start-up, so it is not fixed-length and cannot be covered by a fixed-length
asset.

## 2. Plymouth does start from the initramfs

ADR-0043 §2 claimed this and Finding 038 corrected an earlier denial of it.
It is now positively evidenced, two ways:

- **`plymouthd` is PID 180.** `systemd-journald` is 332 and `systemd-udevd`
  is 384, both with `NRestarts=0`. `plymouth-start.service` is ordered
  `After=systemd-udevd`, so a daemon it forked could not hold a PID below
  384. 180 predates the root filesystem's systemd.
- **`/var/log/boot.log` opens with the initramfs's own `e2fsck` output**
  (`rootfs: recovering journal`, orphan-inode clearing) before any systemd
  line. Plymouth captured it, so plymouth was running then.

What is **not** established: the exact moment the first frame is drawn. The
1.8 s lower bound is `vc4drmfb`'s registration; the 4.0 s upper bound is the
first timestamp in `/run/initramfs/fsck.log`.

## 3. The logger

**It is Plymouth's own `/var/log/boot.log`** — not something this project
added. `dpkg -S /etc/logrotate.d/bootlog` → `plymouth`, and
`strings /usr/sbin/plymouthd` carries `/var/log/boot.log` and
`plymouth.boot-log=`. **Nothing in this repository knows it exists.**

It matters because **journald on this image is volatile**, not persistent:
`/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf` sets
`Storage=volatile`, `/var/log/journal` exists but is empty, and
`journalctl --list-boots` returns exactly one boot. `boot.log` is the only
cross-boot record the device keeps, and it holds six sections, one per boot,
back to 2026-09-19 16:12:59.

> **Corrected here:** Claude told George earlier in this session that journald
> was persistent, from the presence of `/var/log/journal`. The directory
> exists and is empty; the drop-in overrides it. The check answered "does the
> directory exist", not "does anything survive a reboot" —
> `docs/LESSONS.md`'s shape exactly.

### What it shows, and the switch that is doing nothing

`systemd.show_status=false` is on the kernel command line **and is overridden
at runtime by plymouthd**:

```
[   10.709584] systemd[1]: Received SIGRTMIN+20 from PID 180 (plymouthd).
[   25.640238] systemd[1]: Received SIGRTMIN+21 from PID 180 (plymouthd).
```

`SIGRTMIN+20` enables console status messages; `+21` disables them. So for
14.9 s of every boot systemd writes its full status list to `/dev/console`,
because plymouth turns it on in order to display it, and turns it off when it
quits. `boot.log` holds all ninety-odd lines of it. **The quieting ADR-0043
attributes to `systemd.show_status=false` is in fact being done by plymouth's
interception**, which is why that text lands in a log file rather than on a
screen. The option can be removed or kept, but it is not what is working.

Comparing the 22:27 section (the boot before the `console=tty1` → `tty3`
edit) with the 07:58 section: **the captured text is identical and ends in
the same place.** The console change altered where console text would land,
not what is produced.

## 4. The console — answered by George, not by the logs

> **Resolved 2026-09-20.** Asked where on the screen it was, George: **"a
> couple of lines at the bottom"**. That is candidate 1 below — the echoed
> cursor-position replies sitting in tty1's buffer — and it rules out
> candidates 2 and 3. **It is not systemd output, not a getty, and not an
> earlier boot.** The section below is left as written, because the reasoning
> that narrowed it to three is what made one observation sufficient, and
> because it records that the logs alone could not have got there.
>
> **What it means for the fix.** The text is revealed for the whole of D1 and
> is covered the moment anything draws. So ADR-0043's amendment part 1 (the
> rest frame surviving the handover) removes it, and part 3 (D1 ≤ 2.0 s)
> shortens it — **neither needs the emitter identified**. What still wants
> finding, separately and at leisure, is what writes `ESC[6n` to tty1 after
> the clear; the likeliest source is systemd's own terminal handling for
> `TTYPath=/dev/tty1` with `TTYReset=yes`, `TTYVHangup=yes` and
> `PAMName=login` on `gexis-kiosk.service`.

**`console=tty3` was already in effect on the boot George is complaining
about.** The previous boot was 22:27; `cmdline.txt`'s hand edit is timestamped
23:02:42 and the initramfs rebuild 23:19:26. `/proc/consoles` → `tty3` alone,
and the card's own `cmdline.txt.bak` still reads `console=tty1`. So the fix
from commit `6bde2bd` was live and did not remove what he saw.

Every other text source was checked and **none reproduces the complaint**:
`getty@tty1` never started this boot (`InactiveExitTimestampMonotonic=0`,
zero `getty@` lines in the journal — `Conflicts=` drops its job), the VT clear
ran and exited 0, no VT switch occurred (`fgconsole` → 1, session `VTNr=1
Type=wayland Active=yes`).

Three candidates survive, and **nothing here discriminates between them**:

1. **tty1 held renderable escape-reply glyphs during D1.** Read at 08:45,
   before any interference, `/dev/vcs1`'s last rows carried the literal text
   `^[[1;1R^[[50;160R` — ANSI cursor-position *replies* (50 rows × 160 cols =
   1280×800 at an 8×16 font), echoed because nothing was reading the tty, and
   written *after* the `\033c` clear succeeded. tty1 is the foreground VT.
   **Established:** the buffer held it. **Not established:** that anything
   painted it.
2. **D1 is simply black**, and an animation stopping dead for six seconds is
   what George is describing. No `plymouthd-fd-escrow` process existed, so
   `--retain-splash` probably retained nothing — consistent with Finding 039
   §4's record of the screen going straight to black.
3. **An earlier boot.** Every boot before 23:02 had `console=tty1`, where
   cloud-final's `Completed socket interaction for boot stage final` at
   26.36 s lands on the foreground VT 0.7 s into D1. `/dev/vcs3` still holds
   exactly that line.

**What would discriminate:** where on the screen it was. Two lines of
gibberish at the very bottom → 1. A full screen of `[ OK ]` lines → 3, and an
earlier boot. Nothing, just black → 2. Twenty seconds of phone video settles
it outright.

> **The evidence for candidate 1 was destroyed during this session, by us.**
> A capture script restarted `gexis-kiosk.service` at 09:02:19, which re-ran
> the VT clear; `/dev/vcs1` has read blank since. The restart was authorised;
> the cost to the evidence was not anticipated.

### The framebuffer capture proves nothing

45 samples of `/dev/fb0` were taken across a kiosk restart. **Every one is
uniformly black, a single 16-bit value** — including samples that must
postdate labwc's own surface being up. Under vc4 KMS, fbdev emulation is not
the scanout buffer while a DRM master holds the device, so the instrument
reads black whether or not anything is on screen. **It cannot distinguish
"the panel is black" from "fb0 is blind",** and it is recorded here only so
nobody runs it again expecting an answer. It also simulated D1 with a warm
restart rather than a boot.

## 5. What else the boot says

- **`gexis-panel-warmup` warms the wrong things, in the wrong order** — see
  §7, measured after the rest of this finding was written. It is the
  strongest explanation D1 has.
- **Everything is gated behind a network the panel does not need.**
  `gexis-kiosk` → `gexis-core` → `network-online.target` →
  `NetworkManager-wait-online`, 5.996 s, directly on `critical-chain`.
- **cloud-init runs on every boot despite `ENABLE_CLOUD_INIT=0`**
  (`image/config:24`). All five of its units are
  `StandardOutput=journal+console` and it costs 4.172 s.
- **An unverified intro restart at ~9.1 s.** `plymouth-start.service` carries
  `ExecStartPost=-/usr/bin/plymouth show-splash`, fired against the
  already-running initramfs daemon. If that resets the theme script's state
  the intro replays seven seconds in, which would be a discontinuity *inside*
  the animation. **Not determinable from logs.**

## 6. What this does not say

- **Nobody has seen the panel.** Every claim about what is *visible* is
  inferred from logs and mechanism, not observed.
- **One boot.** D1's length depends on `NetworkManager-wait-online` and on
  labwc's start-up, and both varied between Finding 039's boot and this one.
  No distribution was measured.
- **Whether `--retain-splash` leaves anything on screen here** is still
  inferred, from the absence of an escrow process, never observed — while
  three places in the tree still rely on it.
- **Plymouth's memory cost** — ADR-0043's open question — is untouched. The
  process is gone and the journal is volatile.
- **Nothing here was re-verified from an image.** Finding 039's statement
  still holds, and the device is now further from the newest artefact than it
  was: `cmdline.txt` and `initramfs8` were both changed by hand after it.

---

## 7. Addendum, same day — what labwc spends D1 on

**Added 2026-09-20 after George accepted the amendment and chose to start by
shrinking D1.** Same device, same boot's logs, plus `/proc/PID/maps` read
from the labwc that is running now.

### Two hypotheses died first, and they are worth recording

1. **"The warmup is reading Chromium and starving labwc's libraries."**
   Plausible and wrong as stated: `ldd /usr/bin/labwc` is 83 shared objects
   totalling **4 MB**, which at the warmup's own measured 21.6 MB/s is 0.2 s.
   Nowhere near 3.6 s.
2. **"`gexis-meter` is spamming the journal through D1."** It logs
   `cannot open /tmp/peppymeter` in a tight cluster at 27.0 s, which looked
   like ~30 Hz. Counted: **10 lines in the entire boot.** Not a factor.

Both were checked before being reported, and both would have been confident
wrong answers.

### What labwc actually maps

`ldd` is the wrong instrument, and that is the whole point: Mesa is
**`dlopen`'d**, so it does not appear in the binary's link-time
dependencies. From the running compositor's own address space:

| mapped by labwc | size | in the warmup's list? |
|---|---|---|
| `libLLVM.so.19.1` | **117 MB** | no |
| `libgallium-26.2.2-…so` | **49 MB** | no |
| `libz3.so.4` | **25 MB** | no |
| `librsvg-2.so.2.60.0` | 5 MB | no |
| `/usr/bin/labwc` | 0.5 MB | yes |

`vc4_dri.so` and `v3d_dri.so` are both symlinks into `libdril_dri.so`, and
Gallium pulls in LLVM as its shader compiler, which pulls in z3. **~196 MB,
none of it warmed**, read off the SD card at exactly the moment labwc starts
— while the warmup is concurrently reading Chromium's 482 MB through the
same card at idle I/O priority.

### And the order was backwards

```
WARM=( /usr/lib/chromium  /usr/bin/labwc  /usr/bin/swaybg )
```

Chromium is 482 MB and came **first**. The warmup ran 10.70 → 33.06 s and
logged one line, `warmed 483MB`, so essentially the whole window went on
Chromium; `/usr/bin/labwc` was read at the very end, **7.4 s after labwc had
started and 1.5 s after Chromium had**. The compositor is needed at ~25 s and
Chromium at ~32 s, and the list had them the other way round.

`Before=gexis-kiosk.service` with `Type=simple` orders the warmup's *start*,
not its *finish*, so nothing prevented the overlap.

### What was changed

`gexis-panel-warmup` now warms the compositor's set first — labwc, swaybg,
the Mesa/LLVM/z3 libraries above by glob, and `dri/` — then Chromium. Budget
raised 600 → 700 MB because 198 + 482 = 681 and truncating either set is
worse than 100 MB of page cache. Verified on the device: every glob matches,
and unmatched globs stay literal and are skipped by the existing `-e` test.

It also now logs one line per target, so **the next boot's journal states
whether the compositor's set finished before `gexis-kiosk` started** instead
of leaving it to be inferred, which is what this finding had to do.

### What this still does not establish

**Nothing here has been booted.** ~196 MB of cold reads at a contended
21.6 MB/s is ~9 s of I/O if every page were touched, and these are
demand-paged mappings so not every page is — which means this explains
labwc's 3.6 s comfortably but does not predict what D1 becomes. **The claim
is "the warmup was warming the wrong things in the wrong order", which is
measured. The claim "fixing it shrinks D1" is not, until a boot says so.**
One boot, no control run, and D1's length also tracks
`NetworkManager-wait-online`, which is not held constant between reboots.

---

## 8. Addendum — the still halved the kernel phase

**2026-09-20.** George replaced the animation with a still (§7's frames were
the last animated set). Four boots of the same device that afternoon, the
only difference between them being what the plymouth theme holds:

| boot | theme | kernel phase | total | plymouth quits | UI paints |
|---|---|---|---|---|---|
| 07:58 | 100 frames, 4.1 MB | 5.91 s | 27.35 s | 25.64 s | 35.79 s |
| 09:42 | 100 frames, 3.3 MB | 5.32 s | 25.78 s | 25.58 s | 35.44 s |
| 09:57 | 100 frames, 2.8 MB | 5.29 s | 25.58 s | 25.58 s | 35.29 s |
| **10:36** | **1 still, 40 KB** | **2.64 s** | **22.14 s** | **21.78 s** | **31.74 s** |

**The kernel phase halved and the panel is usable 3.6 s sooner.**

`systemd-analyze`'s "kernel" figure covers everything before PID 1, which on
this image includes the initramfs — and plymouth runs *in* the initramfs
(§2). The initramfs itself only shrank 20,018,347 → 18,507,411 bytes, 7%,
which cannot account for a 50% drop. What can: **plymouth was decompressing
and loading all 100 PNGs at start-up**, and now loads one.

That is ADR-0043's open question — *"whether Plymouth holds all 100 frames in
memory, roughly 400 MB decompressed"* — finally showing itself, as time
rather than as bytes. The memory was never measured and now cannot be, since
nothing loads a hundred frames any more. **The cost was real and it was paid
on every boot, in the phase nobody was looking at**, because Finding 038's
budget started at `multi-user.target` and this sits before PID 1.

**What this does not establish.** Four boots, one device, no control run and
no repetition — `NetworkManager-wait-online` alone moved 3.5 s between two of
them. The frame-loading explanation is the only one offered that fits a 50%
drop, but it was not isolated: nothing was measured inside the initramfs, and
a build with 100 frames and a no-op theme script would have separated
"loading the images" from "having the images present". That experiment was
not run and the frames are gone.

### The gaps, on the still boot

| | from → to | length | on the panel |
|---|---|---|---|
| **D1** | 21.78 → 26.81 | **5.02 s** | nothing drawn — black, sometimes with escape-reply text |
| **D2** | 26.81 → 30.89 | 4.08 s | the still, via `swaybg` |
| **D3** | 30.89 → 31.74 | 0.85 s | white — parked |

**D2 is no longer a discontinuity.** The splash and the wallpaper are the
same file now, so 21.78 → 30.89 would be one continuous image if D1 were
covered. **D1 is the whole remaining problem**, and it is also where the
console text appears.

### The console is intermittent, and that is now established

George, on a manual reboot between the 09:57 and 10:36 boots: *"i saw the
console again — something containing 160R"*. `^[[50;160R` is the
escape-reply text of §4's candidate 1, so that candidate is confirmed twice
over. But `/dev/vcs1` read empty immediately after both the 09:42 and 10:36
boots. **So it does not happen every boot** — whatever echoes those replies
races the VT clear in `gexis-kiosk.service`'s first `ExecStartPre`, and wins
sometimes. A fix that covers D1 with an image makes the race invisible
regardless of who wins it; a fix that only clears harder does not.

---

## 9. Addendum — the three flashes, located and two of them closed

**2026-09-20.** George, watching the still boot: *"There were 3 black screen
flashes during the entire period. The white flash is gone. No console text."*
Locating them needed `labwc -d`, added as a drop-in override for two boots
and removed afterwards.

### Where they were

| | window | cause |
|---|---|---|
| **F1** | plymouth quits → the still is written | `gexis-splash-fb` spending 490 ms starting Python before it wrote a byte |
| **F2** | labwc takes DRM master → `swaybg` draws | labwc scanning out its own empty buffer |
| **F3** | Chromium's window maps → the UI paints | where the white flash used to be |

### F1: caused by the fix for it

The first attempt painted before *and* after `plymouth quit`, reasoning that
whichever side worked would cover the gap. Neither did, for a reason that
invalidates the whole belt-and-braces idea:

**Plymouth renders through DRM/KMS, not fbdev.** It holds DRM master and
scans out its own buffer, so a `/dev/fb0` write while plymouth is up lands in
the fbdev buffer, which is not the scanout, and achieves nothing. Only the
write *after* the quit was ever visible — and it arrived 480 ms late, because
that is how long this helper takes to import PIL and numpy.

> **The live test that authorised this approach had no DRM master at all.**
> The kiosk was stopped, so fbdev *was* the scanout and the image appeared.
> That condition does not hold at boot. `docs/LESSONS.md`'s shape again: the
> check ran against a plausible substitute — an idle device for a booting
> one — and the difference was invisible in the result.

**Fixed** by doing the whole sequence in one process, in the order that
matters: `KD_GRAPHICS`, decode the image *while plymouth is still drawing*,
quit plymouth, write. Measured on the clean boot of 11:32:

```
[24.742516] Received SIGRTMIN+21 from PID 181 (plymouthd)
[24.751951] gexis-splash-fb: plymouth quit returned
[24.753299] gexis-splash-fb: painted 2048000 bytes
```

**1.3 ms uncovered**, from 480 ms.

### F2: halved, and the warmup is what did it

Between the two traced boots, with `gexis-panel-warmup`'s reordering deployed
in between:

| | 11:19 (old warmup) | 11:29 (new warmup) |
|---|---|---|
| `Initializing DRM backend` → first EGL line | **1.88 s** | **0.24 s** |
| DRM backend → `swaybg` draws | **3.86 s** | **2.13 s** |

**This is the measurement that attributes the warmup change**, and it does
what the whole-boot timings could not: it is bracketed by two labwc log lines,
so variance in `cloud-init` or `NetworkManager-wait-online` cannot reach it.
Section 7's claim — that ~196 MB of `dlopen`'d Mesa/LLVM/z3 was being read
cold at exactly the moment labwc started — is confirmed.

**The residual 1.8 s is labwc between EGL being ready and its session script
running**, and nothing has looked inside it.

**F2 cannot be covered, only shortened.** Once labwc holds DRM master nothing
else can put pixels on that screen — not the framebuffer, not plymouth — and
labwc 0.20.1 has no root-colour or background option (`--help` and the theme
were both checked). The boot screen necessarily disappears at the instant the
compositor takes the GPU.

### F3: untouched

Chromium's window at 32.41 s, the UI painting at 33.88 s: **1.47 s**. Finding
039 §5's parked overlay applies directly and is simpler now that it is a
still rather than an animation — a layer-shell surface showing the same image
above Chromium's window, removed on `POST /panel/painted`. Not built; it
needs George, because it introduces something that covers the panel and must
be told to go away.

### The boot as it stands

```
0 → 2.6s     black      firmware, kernel, initramfs
2.6 → 24.7   the still  plymouth, from the initramfs
24.7         handover   1.3ms uncovered
24.9 → 27.5  BLACK      labwc holds DRM, nothing drawn yet   (F2, 2.1s)
27.5 → 32.4  the still  swaybg, the same file
32.4 → 33.9  BLACK      Chromium mapped, not yet painted     (F3, 1.5s)
33.9         the player
```

**`cloud-init` is the largest single item left and is not a flash.** 6.0 s,
directly on `critical-chain` ahead of `gexis-core` and therefore of
everything, on an image whose `image/config` sets `ENABLE_CLOUD_INIT=0` —
pi-gen's stage only skips its boot-partition templates, not the package.
