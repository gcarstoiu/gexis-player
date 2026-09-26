# Finding 081 — The first image built with the plugin stage

**Date:** 2026-09-25
**Question:** Does `image/stage-gexis/07-beszel` work? Everything it installs
had been put on the device **by hand** at the same paths, modes and user
([Finding 079](079-what-the-plugin-contract-carries-to-a-unit.md)), so the
download, the checksum, the chroot step and the resulting artefact were all
untested.
**Scope:** one build on R2D2, `2026-09-25-gexis-player-v0.2.1-559-gf475cfa.img`,
from `main` at the merge of PR #27. Verified **as a file** with
`image/verify-image.sh` (debugfs, no loop device, no root) — this says nothing
about booting it, and **nothing here has been flashed.**

## The build

```
Build took 660s
Image version: v0.2.1-559-gf475cfa
```

11 minutes, against the 12m29s warm baseline. The stage itself:

```
cached     dbb292d7309ca00cfd7f3d8f86480991f7c959e65af6506754a55d3e345452ab  beszel-agent_linux_arm64.tar.gz
[17:24:25] End /pi-gen/stage-gexis/07-beszel/00-run.sh
[17:24:25] Begin /pi-gen/stage-gexis/07-beszel/01-run-chroot.sh
[17:24:26] End /pi-gen/stage-gexis/07-beszel/01-run-chroot.sh
```

The tarball came from ADR-0042's content-addressed cache — it was already there
from the manual install — and its checksum matched the pin. **One second for
the chroot step**, which creates the `beszel` account and the state directory.

## What the image holds

`verify-image.sh` gained a section for it, so this is a check that runs on every
future build rather than a thing done once:

```
  ok   /etc/systemd/system/beszel-agent.service
  ok   /usr/local/lib/gexis/beszel-agent-listen-check.sh
  ok   /usr/share/gexis/plugins/beszel/plugin.json
  ok   beszel-agent installed (9502880 bytes)
  ok   beszel-agent is the build that was tested
  ok   beszel-agent not enabled (ADR-0087: an unenrolled device runs nothing)
  ok   the beszel system account exists
  ok   plugin manifests: beszel bluetooth lms spotify
  ok   zz-gexis-default.conf points the ALSA default at our output
```

**"The build that was tested" is the one worth naming.** The binary in the image
is sha256 `4c95b91e7c07912c8f8b6ea4286a6be926cc0616ba49b079082120bea3b203ed`,
byte-identical to the one that was run, enrolled against George's hub and
measured on `gexis` before the stage existed (Findings 078 and 080). The stage
pins the *tarball*; this pins what comes out of it, so a future build that
silently shipped something else would fail here.

ADR-0085's ALSA default also ships for the first time, and the three built-in
manifests are in the image beside the new one.

## The trap this nearly fell into, and how it was settled

**The build bind-mounts the live working tree.** `core`, `ui/dist`, `skins` and
`stage-gexis` are mounted read-only into the container, not copied, and each
stage reads them when it runs — so an edit landing between two stages produces
an image that is half one commit and half another **while the `.info` still
reports the version it started with.**

Phase 11's first code landed 25 seconds after `03-core` finished, by host-clock
arithmetic. **That arithmetic proves nothing**: the container runs two hours
behind the host, and the two numbers came from different clocks. What settled it
was looking inside the rootfs:

```
ls .../stage-gexis/rootfs/opt/gexis-core/venv/.../gexis_core/adapters/
__init__.py  base.py  bluetooth.py  lms.py  spotify.py
```

No `plugin.py`, no `register` in `arbitration.py`, no `PluginAdapter` in
`__main__.py` — so the image holds exactly the merged commit. Recorded in
`HANDOFF.md`'s build-environment section as the fifth entry.

**A second instance of the same shape:** `verify-image.sh` compares the image
against *this checkout*, and the first run reported `venv differs` — correctly,
because the checkout had moved on to Phase 11. Re-run from a `git worktree` at
the built commit, everything passed. **The verifier is only as true as the tree
it is pointed at**, which its own header implies and nothing enforced.

## What this does not show

- **Nothing was booted.** Every statement above is about a file. The boot, the
  panel, the agent actually starting under its own unit on a fresh image, and
  whether `--listen -1` survives the `ExecStartPost` check on a device that has
  never had the agent installed by hand — all unverified.
- **The UI comparison did not run in the worktree.** `ui/dist` is a build
  product and is not in git, so that check was vacuous there; it passed in the
  main checkout, where the directory exists, but against a `dist` that may have
  been rebuilt since.
- **No enrolment on a fresh image.** The keys are in the settings database,
  which a flash destroys and a restore brings back
  ([ADR-0083](../decisions/0083-a-backup-leaves-the-device.md)). Whether the
  hub accepts a restored fingerprint as the same system is still untested, and
  it is the reason that file is in the backup at all.

## The second image, with Plexamp in it — 2026-09-25

`2026-09-25-gexis-player-v0.2.1-579-g0646b8e.img`, **690s**, exit 0.
`08-plexamp` ran in **three seconds** — both downloads came from ADR-0042's
cache, having been fetched and checksummed while the stage was being written.

```
  ok   /etc/systemd/system/plexamp.service
  ok   /etc/systemd/system/gexis-plexamp.service
  ok   /usr/share/gexis/plugins/plexamp/plugin.json
  ok   /usr/share/gexis/plugins/plexamp/mark.png
  ok   /opt/gexis-plexamp/src/gexis_plexamp/main.py
  ok   /home/pi/plexamp/js/index.js
  ok   node installed
  ok   plexamp not enabled
  ok   gexis-plexamp not enabled
  ok   the manifest names the unit the release ladder escalates against
  ok   plugin manifests: beszel bluetooth lms plexamp spotify
```

**It cost 150 MB**: 4,966,055,936 → 5,117,050,880 bytes. ADR-0090 estimated
~92 MB for Node plus Plexamp; the rest is what apt brings with `nodejs` and the
filesystem's own overhead. The estimate was the right order and low.

**And the verifier was lying by omission until that last line was fixed.** The
manifest check grepped for the four names it already knew, so `plexamp` could
not have appeared in its output even with its manifest sitting beside the
others — a check that could only ever confirm what it already believed. It now
lists what is there and names what is missing.

**Still not booted.** Every statement here is about a file.

## The third image — everything Phase 11 produced, 2026-09-25

`2026-09-25-gexis-player-v0.2.1-585-gb74e95f.img`, **695 s**, exit 0. Both
Plexamp downloads came from the cache; the plugin is pinned at **v0.2.0**, the
release carrying the repeat mapping.

**Checked for the two things that missed the previous image**, because "a stage
ran" is not the same as "the fix is in it":

```
  /opt/gexis-peppy/gexis_peppy_render.py: PLUGIN_MARKS present = True
  the image's UI bundle: index-CGKf9H2v.js
  the built UI bundle:   index-CGKf9H2v.js
```

The Peppy badge fallback and both panel mark lookups are in. `verify-image.sh`
passes every check, including the 47 `.py` files of the core venv byte-identical
to `core/src` at the built commit.

**Still not booted.**
