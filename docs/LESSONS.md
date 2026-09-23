# Lessons

Not findings (those state a measured result about the product) and not
ADRs (those record a decision). This is about how verification itself has
failed on this project — a recurring shape worth naming so it gets
recognised faster next time, rather than rediscovered as a surprise.

## The check ran against the wrong reality

Sixteen instances so far, same shape each time: the check ran against
something that *resembled* the thing being tested, closely enough that
the difference was invisible in the result. Not a broken check — a check
answering a different question than the one asked, confidently.

**1. `-e` vs `-L` on a chroot-built symlink** (Phase 2a). A build-time
assertion tested a symlink pointing at an absolute path
(`/etc/systemd/system/...`) that only resolves once the target filesystem
is the real root — i.e. after boot, not inside the build chroot. `-e`
follows the link and resolved it against the *build host's* filesystem,
where the path doesn't exist, and reported a correct symlink as missing.
`-L` (does the link itself exist, without following it) was the question
that was actually answerable at build time.

**2. One control run treated as decisive** (Findings 003/004). A single
clean control run was read as proof the meter plugin caused a defect.
`snd-aloop`'s own intermittent failure rate (roughly 30% per run) meant a
clean control was more likely than not by chance alone — the run answered
"did this one attempt fail," not "does this path have a defect." Fixed by
requiring 20 runs and a reported distribution before any verdict, now a
standing rule for tier 3.

**3. `git check-ignore` against a stale local clone** (provisioning
helper security review). Testing whether a `.gitignore` rule worked by
cloning from this machine's own local repository copy, whose `main`
branch ref predated the fix — the clone silently reproduced the *old*
state and the check reported the rule as broken (a false negative, this
time — the failure mode isn't always a false positive). The question was
about the remote's current state; the clone answered a question about a
stale local ref instead. Testing against the actual GitHub remote gave
the right answer immediately.

**4. `journalctl | grep oom-kill` to test "was it memory?"** (2026-09-13,
build-environment session). Image builds were dying at
`docker cp … | tar -xf -`, diagnosed as memory pressure. Re-checking that
diagnosis, the journal was searched for `oom-kill`, `Killed process`,
`earlyoom` and `systemd-oomd` across the whole persistent boot — nothing.
The diagnosis was retracted to George as "not supported by evidence."

It was right the first time. The kill came from the **supervising process**
(Claude Code's background-task memory guard), which leaves no kernel trace,
so the journal search answered "did the *kernel* OOM-killer fire" and was
read as answering "was this memory pressure." Reproducing the build made it
say so in one line: *"stopped because the system is running low on memory"*,
at exactly the step originally named.

Two aggravations worth recording. The absence of evidence was treated as
evidence of absence — an empty grep was reported as a disproof rather than
as "this particular killer did not fire." And **`HANDOFF.md` already
recorded the same failure**: the 2026-09-06 entry notes two build attempts
"killed by `C3PO`'s own low-memory condition." The project's own history
contradicted the retraction and was not consulted.

**5. Build-time assertions that could only ever check the build**
(Finding 022, 2026-09-14). `04-ui` installed the kiosk unit and asserted its
symlinks existed. They did — the assertions were correct and passed. The panel
still showed a console on the first flashed image, for two reasons that both
live *after* the build: our own `firstrun.sh` reaches `raspi-config
do_boot_behaviour B1`, which reset `default.target` away from the one the
stage had written; and `getty@tty1` held the VT the unit asked for, so
`labwc` exited 0 with an empty journal.

Same file and same stage as case 1, which is the point: "does the artefact I
just built look right" is not "will it do the right thing on a booted
device," and a stage can only ever ask the first question. **The assertions
now include what must be true of the *running* system** — the `Conflicts=`
line must be present, `default.target` must not be written — expressed as
checks the build *can* make about a property it cannot observe.

**6. A live test run with the contended resource free** (boot splash,
2026-09-20). The plan was to hold the boot screen across the gap between
plymouth releasing the GPU and labwc drawing, by writing the image into
`/dev/fb0`. Before building it, the write was tested on the device and George
confirmed the image reached the panel — so the approach was authorised on
evidence.

The test stopped `gexis-kiosk` first, so **nothing held DRM master**. That is
the one condition under which fbdev *is* the scanout. At boot plymouth holds
DRM master, and a write to `/dev/fb0` then lands in a buffer nobody is
scanning out. The resulting "paint before the quit as well as after" removed
zero of the three flashes it was written to remove, and George had to report
that before anyone looked again.

The check answered *"does writing the framebuffer work on an idle device"*.
The question was *"does it work on a booting one"*. An idle device was a
plausible substitute and the difference was invisible in the result.

**7. Measuring an interval from the wrong end of it** (same session). The
black gap after plymouth was reported to George as 3.9s, then 2.1s, bracketed
from labwc's `Initializing DRM backend` to `swaybg` drawing — on the reasoning
that the screen must go black the moment labwc takes the GPU. It does not.
labwc holds the device for ~1.6s doing EGL and output setup **while the
previous image is still on the panel**, and only blanks it at
`Attaching empty buffer to output for modeset`, 0.15s before `swaybg` draws.

The number was wrong by about 8x, in the direction that made the problem look
structural and unfixable, and an optimisation (the page-cache warm-up) was
justified partly by shortening a window that was not black. **The event that
bounds an interval has to be observed, not inferred from what ought to cause
it** — the log line naming the blank existed the whole time and was never
grepped for, because the grep was written from the hypothesis.

**8. A comment in this repository standing in for the device** (same
session). `06-splash/02-run-chroot.sh` asserted "Raspberry Pi OS ships
`update_initramfs=no`". The device reads `yes`, and its md5 is byte-identical
to the conffile `initramfs-tools` shipped, so it had never been edited.
The comment was read as fact, presented to George as *device drift*, and he
approved "restoring" a value that was never lost — so the change introduced
drift rather than removing it. It was reverted when the conffile checksum was
finally compared, which is one command
(`dpkg-query -W -f='${Conffiles}' initramfs-tools`).

Two things generalise. **A claim in our own documentation is not evidence
about the device**, however confidently it is written and however recently.
And **asking George to approve an action on a premise he cannot check makes
him a rubber stamp**: the premise has to be verified before the question is
put, not after he says yes.

**9. A build check that the substitution happened, not that it did
anything** (2026-09-21, Phase 9 subphase 9e's gate). `02-renderers/01-run.sh`
set BlueZ's adapter name with `sed -i 's/^#Name = BlueZ$/Name = gexis/'` on
`/etc/bluetooth/main.conf`, then asserted `grep -q "^Name = gexis$"` on the
result. The assertion passed on every build for months. **The setting does
nothing.** BlueZ's `hostname` plugin overrides it, and the vendor file says
so *two lines above the line being edited*: "The plugin 'hostname' is loaded
by default and overides the Name set here so consider modifying
/etc/machine-info with variable PRETTY_HOSTNAME=<NewName> instead."

It went unnoticed because **the hostname was `gexis` too**, so the adapter
reported the right string for the wrong reason. It surfaced the first time
the two could differ: renaming the device to `SofaPi` wrote `Name = SofaPi`
into main.conf, and the adapter still reported `sofapi` — the sanitised
hostname. Setting `PRETTY_HOSTNAME=SofaPi` and restarting bluetoothd gave
`Name: SofaPi`.

**A check on the file you wrote is a check on your own sed.** It confirms
the edit landed and says nothing about whether the program reads that
setting, and there is no amount of care in writing the assertion that
changes this — only checking the *effect* does. The replacement asserts a
value in the file the software actually reads, which is weaker than
observing the adapter but is what a build can see.

**Two identical names hid it.** Where a mechanism and its fallback produce
the same string, the check cannot tell which one answered. Worth making them
differ deliberately when the fallback is plausible — which is what the gate
"rename, restart, confirm all four" did, by accident of being a rename.

**10. `systemctl is-active` standing in for "the panel works"** (2026-09-21,
same subphase). A script was deployed to the device with `rsync -a`, which
copied the repository's `644` over the `755` the image installs with
`install -D -m 755`. labwc could no longer execute it, so **Chromium never
started** - and `systemctl is-active gexis-kiosk` still answered `active`,
because the unit is labwc and labwc was fine. The panel sat on a background
with no UI on it, and the deploy had been reported as good.

The check was not wrong about anything it claimed. `gexis-kiosk` *was*
active. It simply is not the question: the unit is the compositor, and the
browser inside it is a child that can be absent without the unit noticing.

**The check that works is the one that asks the far end.** After a kiosk
restart, `journalctl -u gexis-core | grep 'GET /assets/index-'` shows the
panel fetching the bundle it was given - which cannot be true unless
Chromium started, loaded, and reached the daemon. It is also how the
content-hashed filename confirms *which* build is on screen.

**And the deploy itself had a trap worth removing rather than remembering.**
Eight scripts were stored `644` in the repository and installed `755` by the
build, so every hand-deploy of one silently stripped its executable bit.
They are executable in git now, which makes `rsync -a` correct by
construction.

**11. Every server-side check passing while the screen was frozen**
(2026-09-21, Phase 9 subphase 9f). George: *"the countdown is not counting
down and pressing reject does nothing."* The daemon's log said otherwise -
`POST /bluetooth/pairing/reject` returned 200, the agent answered BlueZ
`org.bluez.Error.Rejected`, and `/state` read `pairing: null`. A second
WebSocket client, driven from a script, received all three transitions in
order. Every check available on the device said the feature worked.

**It did work. Nothing was re-rendering.** An `$effect` I had added the same
hour did `touches += 1`, which *reads* `touches` to increment it - so the
effect depended on what it wrote, re-triggered itself, and Svelte raised
`effect_update_depth_exceeded`, which stops updating that whole tree. The
frame drew once on mount and then froze: a countdown that never moved and
buttons whose answers landed perfectly and changed nothing on screen.

**The panel is a client, and a client's own console is the only place some
failures exist.** Checking the daemon proves the daemon. Here the two
disagreed and the daemon was right, which is the most misleading way for
them to disagree - every instinct says believe the instrument that is
answering. The kiosk's Chromium console is not in the journal, so there was
nothing to find without the debug port.

Also worth keeping: **it only fired when a pairing request arrived**, so it
survived its own deploy, the panel-load check, and every earlier test. A
reactive cycle reachable from one rare state is invisible until that state
happens - and the state that triggered it was the one being demonstrated.

**12. A summary line read as the rule** (2026-09-21, Phase 9 subphase 9g's
provider research). Finding 043 ruled out Unsplash *and* Pexels as sources
for the idle screen's wallpapers, on one line from each provider's
guidelines - Unsplash's *"You cannot replicate the core user experience of
Unsplash (unofficial clients, wallpaper applications, etc.)"* and Pexels'
*"You may not copy or replicate core functionality of Pexels (including
making Pexels content available as a wallpaper app)"*. Both quotes are
accurate. Both were quoted in the recommendation. **Both providers permit
this use**, and each says so on a page written to answer this exact
question.

Unsplash's *Guideline: Replicating Unsplash* gives the test - does the
application *"offer more value than simply the Unsplash integration"* - and
its approved example is **Trello showing Unsplash images as board
backgrounds**. Pexels' *Can I use the API as a wallpaper app?* says a
platform that serves a different purpose is *"absolutely welcome"* to
include a background feature, and names backgrounds and screensavers served
automatically as an accepted case with its own attribution rule.

George caught it in one line: *"Are you sure unsplash is not viable? Please
do a thorough check."*

**The search answered "is the word forbidden" and was read as answering "is
this forbidden".** A guidelines page lists rules; the article behind a rule
says what it covers, and a rule with a named exception is not a rule you can
apply from its title. The tell was there in the source that *was* read: the
API Terms name *"setting an Image as background wallpaper"* as an event to
be tracked, which is a strange thing to specify about something banned.

**It is also the first case here that cost a recommendation rather than a
measurement.** The check was research, the substitute was a summary for the
rule, and the output was a confident "ruled out by their own terms" - which
reads exactly like a finished answer.

**13. Looking for a design file instead of looking for the design**
(2026-09-21, Phase 9 subphase 9g). The idle screen was built against
`design/screens.md` §9 - eight lines of prose - after checking
`design/source/` and finding `Now Playing.dc.html` and `Settings.dc.html`
and concluding the drop did not draw this screen. `design/README.md` agreed
in so many words: *"Not in this package's first slice at all: the idle
screen…"*

**The drop draws it in full.** Background, scrim, clock, date line, a
weather bar across the bottom, three icon sets, every colour and every
size - in `Now Playing.dc.html`, lines 1093-1210. And `screens.md` says so
in its **first paragraph**, two pages above the section that was read:
*"the rest are described here so the shape is known, and are all in
`source/Now Playing.dc.html` except Settings."*

So the screen shipped with a layout nobody designed: the weather inside the
drifting clock block rather than pinned across the bottom, no date line at
all, a dark scrim plate under the type where the design **rejects a plate in
a comment and says why** (at `brightness(0.62)` a white field is ~2.6:1, so
legibility comes from a 4px contour on the glyphs instead), invented type
sizes where the design gives 104px / 36px / 26px / 21px, and grey monochrome
icons where the design has a spinning sun, a drifting cloud and falling rain
in three palettes. George, seeing it: *"Design was not followed."*

**The check asked "is there a file named after this screen".** The question
was "does the design draw this screen". A directory listing answered the
first confidently, and a README sentence about the *first slice* confirmed
what the listing seemed to show - while the file that contained the answer
was the one already open for every other screen.

**This is case 12's shape, one day later**: a summary read in place of the
source. Twice now the summary was accurate and the conclusion drawn from it
was wrong, so the rule is not "read more carefully" - it is **when a summary
implies something is absent, go and look at the source that would hold it.**

**14. Asking what the API returns instead of what the server knows**
(2026-09-21, Phase 9 subphase 9h). The home strip needs "most played
artists" and "recently played artists". Finding 044 established that LMS
had neither: `songinfo`'s whole field list has no last-played, `titles`
carries no play count under any of 33 tag letters, `sort:playcount` on
albums is not ordered by plays (its second album had 251 where its first
had 201), and no statistics plugin is installed. Every one of those
measurements is correct. The finding recommended building a play log on the
device, which George would have paid for in code and in a feature that
starts empty.

**The server has both, and its own interface shows them.** George:
*"have a proper look at lms as I am seeing both popular artists and
recently played built in the interface, so you should also be able to see
them."* They are not fields and not tags: they are **sorts** — `sort:popular`
and `sort:recentlyplayed` through `browselibrary` — over
`tracks_persistent`, a table the flat commands never hand over. Two calls,
no plugin, and both verified on his server within minutes of being told to
look again.

**The check asked "what does this API expose" and was read as answering
"what does this server hold".** Those differ whenever data is reachable
through one door and not another, which is most of the time in an interface
this old. The tell was available and ignored: **the product's own UI was
doing the thing I had just declared impossible.** Nothing about a screen
George can see should ever be concluded from an API probe alone.

**15. Reading the log instead of looking at the screen** (2026-09-22, Phase
9 subphase 9h). The visualiser's selection was declared verified on this
evidence: *"rotation off plus 'Spectrum' moved the screen to
`103G5_Marschal Spectrum` without a restart"*. That sentence is a quotation
from the driver's log. The driver prints `peppy: skin -> <name>` when it
**decides**, and the decision was right — but the spectrum engine had never
been built on this device, so a spectrum-only skin honoured
`meter.visible = False` and drew **nothing at all**. The screen was black
while the log was correct.

Two other things travelled in the same sentence. The engine's own random
mode overwrote the chosen skin at startup, so the first frame drew someone
else's skin — invisible in a log that only reports our own decisions. And
the spectrum engine's config was root-owned while the unit runs as `pi`, so
the write that selects a section raised `PermissionError` *after* the
display existed, leaving a black pygame window with no loop behind it,
owning every touch. George found all three in one tap: *"tapping on the
button in now playing displays a black screen that I cannot exit by
tapping."*

**The substitute was the process's own account of itself.** A log line is a
statement of intent by the code under test; on a screen, only pixels are
evidence. There was no capture tool on the device and the gap was noted out
loud — *"I can't visually confirm"* — and then the work was reported as
verified anyway. `grim` takes a screenshot of that panel in one command and
Claude can read the PNG. **When the deliverable is something drawn, the
verification is an image.**

`grim` was installed by hand on the device to close this out
(`apt-get install grim`, 14.8 kB) and is **not in the image**, so a reflash
removes it and the next session has to install it again. Whether it belongs
in the build is George's call; the argument for it is this page.

**16. A probe that ran the same code in a context where the bug is
invisible** (2026-09-22, Phase 9 subphase 9i). ADR-0052 §4 replaces the
`amixer` subprocess with libasound through `ctypes`. The approach was
proved first in a standalone probe on the device - it opened the mixer,
read the ranges and wrote values, and reported the timings this record is
built on. The same code inside the daemon **took it down with SIGSEGV, five
times in fifteen seconds**.

`ctypes` assumes a return type of `int` for any function it has not been
told about, which truncates a 64-bit pointer to 32. `snd_mixer_find_selem`
returns a pointer. Whether the truncation matters depends on where the
allocator happened to put the element that run - the probe's fitted, the
daemon's did not. **The probe did not test the code; it tested one draw
from a distribution**, and the draw that mattered was the one on the other
side of the deploy.

The tell was available: the probe never declared a single `restype` or
`argtypes`, which is the first thing to check in any ctypes binding.
**A probe that cannot fail for the reason the real thing will is not a
rehearsal of it.** Signatures are declared now, and the mixer handle is
pinned to one thread, which was the second thing the probe could not have
shown.

**Cheapest correction available:** when a server's own interface shows a
thing, find the call *it* makes before concluding the data is absent — here,
one request to `material-skin browsemodes` listed `myMusicTopArtists` and
`myMusicRecentlyPlayedArtists` with their exact parameters.

**17. A client that logged nothing when it matched nothing** (2026-09-23,
Phase 9 subphase 9i). `bluealsa_volume.py` was written to follow the A2DP
PCM's `Volume` property over D-Bus. It filtered on `Mode == "sink"` — the
right word for the wrong end. `bluealsa -p a2dp-sink` makes *this device*
the sink, so the transport is `A2DP-sink`, but a PCM's `Mode` is the
direction from the **client's** side, and a client reads this one: its Mode
is `"source"`. The filter matched nothing, ever.

**What made it cost a whole test round with George** is not the filter, it
is that the module logged only on success and on failure of the *bus
connection*. A total mismatch produced exactly the same output as a phone
not being connected: none. He reported *"the volume bar moves on the phone
but nothing happens on the panel"*, and the daemon's log for the whole
session had not one line from the module responsible.

**A component that can do nothing must say so.** It now logs what it is
watching and how many objects it found on startup, and logs every object it
declines with the properties it declined it on. The next failure of the
same kind is one `journalctl` away instead of a round trip through somebody
else's evening.

**18. The same `amixer` grep, a second time** (2026-09-23). Finding 045 §6
records `grep -oE "Playback [0-9]+"` matching `Limits: Playback 0 - 240`
and reporting the control's *floor* as its value. Verifying ADR-0054's
curve on the device, the same one-liner was written again and reported
**silence at every slider position**, on a device whose DAC was tracking
perfectly. It was caught because the result was absurd rather than merely
wrong — which is luck, not method.

**Reading a mixer with a regular expression is a known trap in this
repository and there is a correct parser in `volume.py`.** The probe
scripts should use it; where a shell one-liner is unavoidable, anchor it to
`Front Left:` rather than to the word `Playback`.

**19. The tests never ran the daemon's own wiring** (2026-09-23). A
settings row was removed from the registry and its entry in `__main__`'s
`defaults` dictionary was left behind. `Settings.__init__` **already checks
exactly this** and raises `not in the registry: [...]` - but nothing in the
suite constructs it with the daemon's real dictionaries, so the check only
ever ran on the device. 894 tests passed and `gexis-core` would not start.

**A validation that only runs in production is a deployment step, not a
test.** `test_registry_wiring.py` now reads the two dictionaries out of the
source with `ast` and checks them against the registry, and it asserts it
found the call at all - otherwise it would pass by finding nothing.

**20. Removing a thing leaves references that only production checks**
(2026-09-23, twice in one afternoon). A settings row was deleted and its
entry in `__main__`'s `defaults` stayed; then `boot_volume_steps` was
deleted from `Config` and stayed in the shipped `core.toml`. Both have a
correct, deliberate validation — `Settings.__init__` raises `not in the
registry`, `Config.load` raises `unknown config key(s)` — and **both
validations only ever ran on the device.** The suite was green each time
and the daemon would not start.

The second one also hit systemd's restart rate limit, so the service ended
`failed` and needed `reset-failed` rather than another `restart` — a
deployment that is *wrong* looks different from one that is merely broken.

**A declaration and the thing it declares are two files, and nothing was
comparing them.** `test_registry_wiring.py` now reads the daemon's
`defaults`/`wired`/`options` keys out of the source with `ast` and the
shipped `core.toml` against `Config`'s fields. Both assert they found
something first, so they cannot pass by looking at nothing.

## Common shape

Every case had a *plausible* substitute for the real target — the build
host's filesystem for the booted one, one run for the distribution, a
local ref for the remote, the kernel's OOM killer for any killer, an idle
device for a booting one, a comment for the machine it describes, a
summary line for the rule it summarises, a directory listing for the design
itself, a log line for the screen it describes, a lucky memory layout for
the one the daemon would get — and the check quietly accepted the
substitute. None of these failed loudly. Each
produced an answer that looked like a normal result, not an error.

**And a third corollary, from cases 17 and 18.** Silence is not evidence of
absence *unless the thing was built to break its silence* — a check that
cannot report "I found nothing to look at" is indistinguishable from one
that found nothing wrong. And a trap this page already records will be
walked into again: case 18 is case 6's own instrument, rewritten from
memory nine days later.

**What to check before trusting a verification result:** not just "does
this check look right," but "is the thing I just checked actually the
thing I care about, and could it be silently answering a related-but-
different question instead."

**Two corollaries, both from case 4.** A check that finds nothing has not
proved nothing happened — it has proved *that specific mechanism* left no
trace, which is a much smaller claim. And before overturning a previous
conclusion, search this repository for it: the answer was already written
down, and the retraction contradicted the project's own record.

**Not the same failure mode as the criteria gaps** (`docs/DEVELOPMENT.md`
criterion 3's root-access amendment, the provisioning `.gitignore`
defect). Those were correct checks against the right target, of a
spec that didn't ask the right question. This page is about the check
itself measuring the wrong thing. Related, worth keeping distinct.
