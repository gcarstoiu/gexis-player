# Routine: disk clean-up and token trim

Asked for by George on 2026-10-12, after the first full run: *"Set this deep
thorough clean up and token optimisation as a routine task."* It keeps the
build machine's disk from filling and keeps what every session reads at the
start small.

**When:** after every release PR George merges, as part of its post-merge
steps; and otherwise once a week (Sunday evening) if no release came in
between. Each run ends with a short report to George: what was freed, what was
trimmed, anything found that needs him.

**Never while** an image build, a package build or a release publish runs
(check `docker ps` for `pigen_work_cont` and the build's background tasks);
never while anything plays on a player whose files are touched (`grep -q
RUNNING /proc/asound/card*/pcm*p/sub*/status`).

## 1. The disk (R2D2)

Look before deleting; delete only what is listed here as safe.

| What | Keep | Remove |
|---|---|---|
| Worktrees (`git worktree list`) | the main checkout, `-13d`, any whose branch is not yet in `origin/main` or has uncommitted or unpushed work | every other: `rm -rf` then `git worktree prune` (the pi-gen submodule refuses `worktree remove`) |
| Local branches | `main`, `phase-13b`, `phase-13d`, any not contained in `origin/main` | merged ones (`git merge-base --is-ancestor <b> origin/main`); remote branches are never touched |
| `image/deploy/` | the newest released image and its `.info` | older images (each is rebuilt from its tag) and stray `build*.log` |
| `packaging/out/` (both checkouts) | nothing needed | every `.deb` (rebuilt by the next build) |
| pi-gen volumes | the warm stage trees | `make prune` only - **never `make clean`** (a cold build is ~40 min) |
| Docker images | `pi-gen`, `gexis-deb-builder`, the Debian bases, anything a running container uses (`gexis-dev-*` is someone else's - leave it) | dangling images: `docker image prune -f` (not `-a`) |
| The session scratchpad | the test `venv`, `relkey.gpg`, the players' host-key files, `holddemo.py` **with its `pd/` folder** (the public-domain demo library; lost once, 2026-10-15, and rebuilt - a copy lives in `~/projects/gexis-blog/demo/`), `chipshot.py`, `film.py` | everything else (check first that no memory file, HANDOFF or test points into it) |
| The players' `/tmp` | - | `/tmp/pv` and any test script copied there |

## 2. What sessions read (tokens)

The start-of-session set is CLAUDE.md, the memory index, HANDOFF.md and
docs/LESSONS.md (≈ 5,000 words after the 2026-10-12 trim), plus the ADR
index when a decision is needed. Keep it there:

- **HANDOFF.md** stays current state (about 1,000-1,500 words): the release
  in force, devices, what is owed by George, what has not run on a device,
  what is next, open phases, current gotchas. Anything finished - a released
  version's block, a closed phase, a gotcha about a machine or tool no longer
  used - moves **verbatim** to `docs/HANDOFF-ARCHIVE.md` under a dated
  heading.
- **docs/LESSONS.md** holds one rule per lesson; a new lesson is written in
  full in `docs/LESSONS-ARCHIVE.md` and as its rule here. If a rule has grown
  into a story, cut it back and move the story.
- **docs/decisions/README.md** holds one line per ADR (link, title, status
  with date, at most ~15 words of decision); new rows the same way; a longer
  summary goes in `INDEX-FULL.md`. Check every ADR file has a row and every
  row a file, and that a row's status still matches its file.
- **The memory index** (MEMORY.md) stays one line per memory; merge or delete
  memories that are duplicated, out of date or now written in the repository.
- **CLAUDE.md** points at the archives as places to search, never to read.

## 3. What must not be in the repository

Scan every tracked file (`git grep -I`) for: LAN addresses
(`192.168.`, `10.`, `172.16-31.` as used at home), MAC addresses, the home
network's names, `claude.ai` links, session ids, paths into a session's
scratchpad (`/tmp/claude-`), and real artists, albums or places from
George's library. Replace with named placeholders or the documentation range
(192.0.2.x); a test that needs a real file reads it from an environment
variable and skips without it. History is not rewritten without George.

## 4. The report

Before and after: free space on `/home`, the start-of-session word count.
What was removed, what was moved to which archive, anything fixed under §3,
and any decision for George (each on its own line, at the end).
