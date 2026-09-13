# Lessons

Not findings (those state a measured result about the product) and not
ADRs (those record a decision). This is about how verification itself has
failed on this project — a recurring shape worth naming so it gets
recognised faster next time, rather than rediscovered as a surprise.

## The check ran against the wrong reality

Three instances so far, same shape each time: the check ran against
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

## Common shape

Every case had a *plausible* substitute for the real target — the build
host's filesystem for the booted one, one run for the distribution, a
local ref for the remote, the kernel's OOM killer for any killer — and the
check quietly accepted the substitute. None of these failed loudly. Each
produced an answer that looked like a normal result, not an error.

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
