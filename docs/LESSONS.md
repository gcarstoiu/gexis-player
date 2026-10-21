# Lessons

Not findings (those state a measured result about the product) and not
ADRs (those record a decision). This is about how verification itself has
failed on this project — a recurring shape worth naming so it gets
recognised faster next time, rather than rediscovered as a surprise. Each
entry is the rule a case taught; the case itself is in
`docs/LESSONS-ARCHIVE.md` under the same number.

## The check ran against the wrong reality

Same shape each time: the check ran against something that *resembled* the
thing being tested, closely enough that the difference was invisible in the
result — a check answering a different question than the one asked,
confidently.

**1. `-e` vs `-L` on a chroot-built symlink** (Phase 2a). In a build chroot,
test a symlink with `-L`; `-e` resolves an absolute target against the build
host, not the booted device.

**2. One control run treated as decisive** (Findings 003/004). Against an
intermittent failure, one clean run proves nothing; tier 3 needs 20 runs and a
reported distribution before any verdict.

**3. `git check-ignore` against a stale local clone** (provisioning helper
security review). Test a question about the remote against the remote; a local
clone can carry a stale ref and give a false negative as easily as a false
positive.

**4. `journalctl | grep oom-kill` to test "was it memory?"** (2026-09-13,
build-environment session). An empty search proves only that the mechanism
searched for (the kernel OOM-killer) left no trace — another killer, such as
the supervising process, leaves none. Search this repository before retracting
a conclusion; the record already had the answer.

**5. Build-time assertions that could only ever check the build** (Finding
022, 2026-09-14). A stage can only check the artefact it built, not the booted
device; assert the build-visible properties the running system depends on
(`Conflicts=` present, `default.target` not written).

**6. A live test run with the contended resource free** (boot splash,
2026-09-20). Test under the conditions of the real moment: a framebuffer write
that works with nothing holding DRM master says nothing about boot, when
plymouth holds it.

**7. Measuring an interval from the wrong end of it** (same session). Observe
the event that bounds an interval in the log, never infer it from what ought to
cause it; grep for the event, not for the hypothesis.

**8. A comment in this repository standing in for the device** (same session).
A claim in our own documentation is not evidence about the device — check the
device (here, the conffile checksum). Verify a premise before asking George to
approve an action on it, not after.

**9. A build check that the substitution happened, not that it did anything**
(2026-09-21, Phase 9 subphase 9e's gate). A check on the file you wrote checks
your own `sed`; check the effect, or at least the file the software actually
reads. Where a mechanism and its fallback give the same value, make them differ
so the check can tell which answered.

**10. `systemctl is-active` standing in for "the panel works"** (2026-09-21,
same subphase). Ask the far end: after a kiosk restart, the panel fetching its
`/assets/index-` bundle proves Chromium started and which build it has. Store
scripts with the mode they install with, so `rsync -a` cannot strip it.

**11. Every server-side check passing while the screen was frozen**
(2026-09-21, Phase 9 subphase 9f). The daemon's checks prove the daemon; a
client's failures live in its own console (the kiosk's needs the debug port).
A fault reachable from one rare state is invisible until that state is
exercised.

**12. A summary line read as the rule** (2026-09-21, Phase 9 subphase 9g's
provider research). A rule with named exceptions cannot be applied from its
title; read the article behind it before ruling something out — a
recommendation is as exposed as a measurement.

**13. Looking for a design file instead of looking for the design**
(2026-09-21, Phase 9 subphase 9g). When a summary or a listing implies
something is absent, look in the source that would hold it — here the design
file already open for every other screen.

**14. Asking what the API returns instead of what the server knows**
(2026-09-21, Phase 9 subphase 9h). What an API exposes is not what a server
holds; if the product's own UI shows a thing, find the call that UI makes
before declaring the data absent.

**15. Reading the log instead of looking at the screen** (2026-09-22, Phase 9
subphase 9h). A log line is the code's statement of intent; when the
deliverable is drawn, the verification is an image (`grim`, which is not in the
image and needs installing after a reflash).

**16. A probe that ran the same code in a context where the bug is invisible**
(2026-09-22, Phase 9 subphase 9i). A probe that cannot fail for the reason the
real thing will is not a rehearsal; in any `ctypes` binding, declare every
`restype` and `argtypes` first.

**17. A client that logged nothing when it matched nothing** (2026-09-23,
Phase 9 subphase 9i). A component that can do nothing must say so: log what it
watches, what it found, and what it declined and why, so a total mismatch does
not look like no input.

**18. The same `amixer` grep, a second time** (2026-09-23). Do not read a
mixer with a regular expression — use the parser in `volume.py`, or anchor a
one-liner to `Front Left:`. A trap recorded here will be walked into again from
memory.

**19. The tests never ran the daemon's own wiring** (2026-09-23). A validation
that only runs in production is a deployment step, not a test; exercise it in
the suite with the real data, and assert the test found something to check.

**20. Removing a thing leaves references that only production checks**
(2026-09-23, twice in one afternoon). When a declaration and what it declares
live in two files, a test must compare them (registry, `defaults`, shipped
`core.toml`). A unit that hit its restart rate limit needs `reset-failed`, not
another `restart`.

**21. "No answer" folded into an answer** (2026-09-23). "I could not tell"
must be a different value from "I checked, and no" — use `None`, never cache
it, and write nothing that cannot be computed; make the question answerable
(stop the renderers) before asking it.

**22. The arithmetic was right and the cause was wrong** (2026-09-23). An
out-of-range number tells you where to look, not what is wrong; ask what would
make the number right (here, what file a value names), and confirm a capture is
of a live screen, not a held frame.

**23. The repository's own record was the wrong answer** (2026-09-23). Take a
decision from the record; take a fact about a dependency's code from the
dependency — a recorded reading can be checked in a minute.

**24. Fixed once, in one of the two places that had to agree** (2026-09-23).
When two processes must agree on a number, check how and when each learns it,
not only what each holds now; better, stop the number changing.

**25. Three faults, one symptom, and each fix made the next one visible**
(2026-09-23). A measurement that shows the fault gone shows *a* fault gone; if
the symptom survives a fix that demonstrably worked, look for another cause the
fix has just made visible.

**26. The check I ran to confirm a detail found the feature broken**
(2026-09-23). Say which parts of an explanation are measured and which read
from code — and flagging the unmeasured part does not replace measuring it.

**27. The percentage went to zero because the panel got slower** (2026-09-24).
A share of frames dropped falls whenever the compositor asks for fewer frames;
read the frame rate beside it, every time.

**28. CSS cannot fake a downscale, and the screenshot said so** (2026-09-24).
A change meant to look the same is photographed before its cost is measured;
cheap frame numbers can measure a fix that does not exist.

**29. A selector that matched nothing measured the page three times**
(2026-09-24). A CSS rule that selects nothing fails silently and looks like a
negative result; every probe proves its change applied (matched something)
before it measures.

**30. The frame counter under-counted exactly the change being tested**
(2026-09-24). Check whether an instrument's accuracy depends on what the
experiment changes; cross-check two counters where both are valid
(`PipelineReporter` and `DrawToScheduleOverlay`).

**31. Three fixes for the symptom, because I never asked what the row was**
(2026-09-24). Two failures of the same fix are a fact about the diagnosis —
recheck the model (here, a list keyed by position). An effect that clears state
must not also be woken by it.

**32. The probe waited behind the work it was timing** (2026-09-24). A poll
that runs on the thread under test queues behind it; measure from inside the
page (a `MutationObserver`), or measure something that is not the subject.

**33. The fix scheduled itself before the paint it was waiting for**
(2026-09-24). A fix that barely responds to its main parameter is not the fix.
`requestAnimationFrame` runs before the next paint; to yield to the screen, use
`requestAnimationFrame` then `setTimeout(…, 0)`.

**34. The count was reset by the wrong thing** (2026-09-24). Key a reset on
the event that matters (a new showing), not on the data (its length); a probe
opens the same screen several times, since some faults appear only on a second
visit.

**35. The probe thought the grid was an artist page** (2026-09-25). A class
shared by a container and its items does not identify a screen; a probe's
screen detector must use a selector unique to that screen.

**36. I explained the residual instead of chasing it** (2026-09-25). A
residual that reproduces exactly is a clue to structure, not noise; a sample
you cannot explain is evidence, not a transient.

**37. A box never reports a scroll height smaller than itself** (2026-09-25).
A test that cannot return false is not a test; measure the thing the question
is about (the paragraphs), not its container (`scrollHeight >= clientHeight`
is always true).

**38. The panel was still running the bundle from before the deploy**
(2026-09-25). Restarting the daemon does not reload the panel; the first step
of any probe is to confirm the code being measured is the code deployed.

**39. The renderer was switched off and stayed the active one** (2026-09-25).
A pass that switches something off also checks what it now says about itself.
Assert that state cannot contradict itself (unavailable yet active).

**40. The query was folded, and nobody had asked the catalogue** (2026-09-25).
A user's diagnosis is a symptom plus a hypothesis — confirming it is not
exhausting it. Ask the real external service what it does; a fake cannot catch
how the real one treats input.

**41. The throwaway plugin was never in the state a real one starts in**
(2026-09-25). A test double that cannot fail cannot exercise the failure path;
test the states the real subject reaches — for anything needing a credential,
"refuses to start, not yet configured" is its first state.

**42. The probe changed the device and left it changed** (2026-09-26). A probe
that changes the system restores it in the same script, and afterwards checks
the device's actual configuration, not memory of having undone it — state in a
URL leaves no file to sweep.

**43. "No warnings in the journal" while warnings were switched off**
(2026-09-27). A quiet log is evidence only if something can be heard in it;
provoke one warning on purpose and see it arrive before counting silence.

**44. One lookup fixed, the same cause left one step earlier** (2026-09-28).
Fix the cause, not the line: find every place the unexpected state can reach. A
step that exists for safety must not sit behind steps that can fail.

**45. The check was removed in the same change that needed it** (2026-09-28).
When a feature leaves, its presence check becomes an absence check, not no
check. A warm build keeps a deleted stage's output: clear `stage-gexis`'s work
directory.

**46. Every trial ran on a card that had already been given a country**
(2026-09-29, Phase 13 step 4). A mode entered by a switch on a configured
device is not a new device; "what a new device does" is answered only by a new
device (here, one with no Wi-Fi country).

**47. "Polite stop freed the device (0.1s)" was the check failing to look**
(2026-09-30, Phase 13a). A check that cannot find its subject must say so, not
answer; here the cgroup path differs for template instances. A fast "success"
deserves the same suspicion as a failure.

**48. The release's completeness check counted from the list it was checking**
(2026-09-30, Phase 13c). Count completeness from the source on its own terms
(every record dpkg calls installed, `hold` included), never from the output of
the step being checked.

**49. The release was published in a layout its own updater could not read**
(2026-09-30 to 10-01, Phase 13c). A format change arrives through a release
its old reader can read; a release is published only in a format its own
updater reads. "Same file as the release" is not "can read the release".

**50. Our own release tags renamed the build** (2026-10-01, Phase 13c). Name
the tags a version may come from (`git describe --match 'v[0-9]*'`) wherever a
version is described.

**51. The revert restored a file the running script was no longer reading**
(2026-10-01, Phase 13c). Never change a running script; stage the change in a
copy and swap it in after the run. The file on disk is not necessarily the file
the process reads.

**52. A merge's version came from the commit it merged** (2026-10-02, Phase
13b). Version the whole tree (`.`) from HEAD; compare an image's name with its
player's version, as two answers to one question.

**53. One version, two packages** (2026-10-03, Phase 13e). A package's version
names its content: one carrying our files beside upstream's takes our commit
too, and the release build refuses a name and version already published with
different bytes.

**54. Installed is not running** (2026-10-03, the first preview). A preview is
running only when the process is younger than the install and doing something
only the new code does; restart what the package does not.

**55. A preview removed the release** (2026-10-03, the first previews). A
preview installs the whole set of one commit, `gexis-player` with it, and reads
everything apt will remove — a removal is never a side effect to filter.

**56. A test that cleared the cable** (2026-10-04, the 13.3" panel). A test
clears only the mechanism it varied; before ruling a part out, name every way
it could fail and which of them the test touched.

**57. A swipe that only a script could do** (2026-10-04, the bars' tray). Check
a gesture with the input a finger produces (CDP `Input.dispatchTouchEvent`
with touch emulation), and run the check once without the fix to see it fail.

**58. Frames counted, positions not** (2026-10-04, the queue on the bar). A
check of movement logs where things went every frame, not only frame rate, and
drives it as a person does (a fling), not with a fixed scripted step.

**59. The test panel was not the only panel** (2026-10-05, ADR-0121). Before
driving a relay, find who else it reaches, and record any state stray input
could change (volume, playback, the screen) before and after. A test script's
own small moves can be read as taps.

**60. A write that could not fail** (2026-10-07, ADR-0124). A level is
believed when read back, never when written. A quiet test sets the volume of
every source it starts, not only the player's.

**61. A refusal tested against code that accepts** (2026-10-08, Beszel). A
write-test runs only after the change it tests is confirmed installed, in its
own command, never with a gated install; and never over a real setting — use a
row nothing reads, or put the value back.

**62. Old and new, identical to the decimal** (2026-10-08, peppyalsa, Finding
117). A comparison of two builds proves which build ran, per run (memory map,
version string, unique symbol), before comparing; a result too equal is a
warning.

**63. A repair that passed its tests, twice wrong on the device** (2026-10-09,
the updater after power cuts). A power cut does not break one thing; prove a
recovery on the damaged device itself, run to the end, before release — a fake
built from the first symptom proves only that symptom.

**64. A dry run that skipped the check it was meant to test** (2026-10-10,
setup's restart after a factory reset). A dry run proves only what it executes;
confirm it reaches the step the cause acts on, and if it cannot, log the real
call's answer and let the next real run say.

**65. A fake store hid a read-only database** (2026-10-08, a restore in setup
on 0.9.5, a new card). A fake answers only what it was written for; where the
order of writes against a file matters, test against the real store.

**66. The panel kept the old page** (2026-10-07 to 2026-10-09). The panel is a
page loaded once (it now reloads when the installed build changes); check a UI
change on the panel itself, not in a fresh browser elsewhere.

**67. Test failures that were a full disk** (2026-10-07/08, again 2026-10-10).
When failures do not match the change, check the machine before the code — a
full scratch disk (`df -h /tmp`) first; screenshot scripts delete their browser
profiles.

**68. A release checked where it could not fail** (2026-10-10, 0.9.8). Check a
release on the devices that ran its previews, or after a history rewrite put
those devices back on release packages (`--allow-downgrades`, dry run first)
before anyone updates them.

**69. A "restores afterwards" that did not** (2026-10-12, Lyrion's `playlist
preview` replaced a queue that was George's). Prove a restore on a queue that
does not matter first, and record what is in a queue (track ids) before
touching it, so it can be put back whatever the mechanism does.

**70. A power cut simulated by an exception** (2026-10-13, the bar's
cut-short update). A test that stops a process with an exception keeps every
write it made; a real power cut keeps only what was synced. Crash safety is
proved by a real cut, or by checking the sync itself.

**71. A package named after a commit it did not contain** (2026-10-14, the
panel's outline on sofapi). The UI package packs `ui/dist` as found; built
before the last edit, it went out under the next commit's version. Check
what a package holds, not its name: unpack it and find the change, and let
the build refuse a `ui/dist` older than its sources.

**72. A test the player itself undid** (2026-10-15, the bar's setup network,
Finding 126). Test access points raised on a player with its cable in were
taken down within 5 s by the core's own cable rule, and a second receiver was
trusted before it was shown to see a working network. Before reading a
device's behaviour from a test, check what of our own software acts on the
same thing, and prove the observer on a known-good case first.

**73. Tests that read the source while the code never ran** (2026-10-15,
the stand-in watcher, 1.0.0 and 1.0.1). The Finding 125 #10 fix moved the
whole lookup into a worker thread; the settings store refuses any thread but
its own, so it failed every 3 s and the jack never stood in. Its tests only
asserted the source's shape and passed. Run the changed code once - on a
device or in a test that executes it - and read the log after a change.

**74. A test environment emptied by the system's clean-up** (2026-10-16,
before 1.0.3). The test venv lived under `/tmp`, where the system deletes
files unused for 10 days: numpy, OpenCV and Pillow went, the tests that need
them skipped themselves, and one that does not failed - "47 skipped" became
"55 skipped". Keep the venv out of `/tmp`, and treat a change in the skip
count as a failure to explain.

**75. A commit chained after the tests** (2026-10-18, on `next`). The
commit ran in the same command as the suite, after it, so it went through
with a test failing (68c9ee85; fixed in fc18315c). Run the tests, read the
result, then commit in a call of its own.

**76. A channel count that hid silent channels** (2026-10-19, Finding 128).
The HDMI port opened at 6 channels for a 5.1 file through Lyrion's bridge,
and the finding said the channels arrived; by ear only front left and right
sounded - the bridge re-encoded six channels, four silent. A format or
channel count shows the stream's shape, not its content: check what is in
each channel (a capture, a per-channel signal, an ear) before saying it
arrives.

**77. A core that was active, and old** (2026-10-19, a preview on sofapi).
`apt install` of a preview's `gexis-core` does not restart it (the updater
does); `systemctl is-active` said active of the old process, and the new
setting was missing. After a preview install, restart what changed and check
its start time is after the install.

**78. A remedy expected, not measured** (2026-10-19, Finding 129). Finding
118 measured the idle screen at 4-6 % with its icons paused by hand, and
*Weather icon motion: Static* was built on that - "expected at the paused
figure, not yet measured with the setting itself". Measured nine days later
it was 45-58 %: the setting paused the icons, and other animations under the
idle screen ran on. A remedy is measured through the switch users will use,
not through the test that motivated it.

**79. A way in that was never tried** (2026-10-21, ADR-0156). Signing in to
Home Assistant "once, typing from the phone" went into the ADR, the manual,
the FAQ and advice to George, reasoned from the phone being able to type into
the panel. It cannot type into another site's frame: its input is simulated
inside the player's own page. George found it at the login. A path offered
to the user is tried end to end first; until then it is not offered.

**80. A meter measured at rest** (2026-10-21, Finding 133). Comparing Glass
with our visualiser, music played at volume 5 so the rooms stayed quiet. Our
needles follow half the volume's cut (`meter_follow`), so they stood near the
bottom and our spectrum bars barely rose; Glass, fed its own signal, moved.
Our needle skin read 4.1 % of a core against 13.7 % with the needles moving,
and the first results sent to George said the two were even. A screenshot
showed a meter, which looked like a meter working. Before measuring what
something costs, see it doing the work, at the conditions of the measurement.

## Common shape

Every case had a *plausible* substitute for the real target, the check quietly
accepted it, and the answer looked like a normal result, not an error.

**What to check before trusting a verification result:** not just "does this
check look right," but "is the thing I just checked actually the thing I care
about, and could it be silently answering a related-but-different question
instead."

**From case 41.** A probe built to work does not visit the states the real
subject starts in; test those states.

**From cases 17 and 18.** Silence is evidence only from a check built to break
it — one that can report "I found nothing to look at". A trap recorded here
will be walked into again from memory; reuse the recorded fix.

**Two corollaries, both from case 4.** A check that finds nothing proves only
that *that specific mechanism* left no trace. Before overturning an earlier
conclusion, search this repository for it.

**Not the same as criteria gaps** (`docs/DEVELOPMENT.md` criterion 3's
root-access amendment, the provisioning `.gitignore` defect): those were right
checks of a spec that asked the wrong question; this page is about checks
measuring the wrong thing.

The full cases, word for word, are in `docs/LESSONS-ARCHIVE.md`.
