# Gexis Player

Custom high-fidelity music player distribution for Raspberry Pi 4.

## Read these first

- `HANDOFF.md` — current state and next action. **Start with its "Start
  here" block**; it orients you in a few hundred words.
- `docs/LESSONS.md` — how verification itself has failed here. Short, and
  the cheapest thing to read: every entry is a mistake already made that
  looked like a normal result at the time.
- `docs/ARCHITECTURE.md` — layer model and requirements
- `docs/decisions/` — numbered ADRs, one per decision. Use
  `docs/decisions/README.md` as the index; do not read all of them.
- `docs/findings/` — measured results, each with scope stated

Reading everything listed here is ~100,000 words. Don't. Take `HANDOFF.md`
and `docs/LESSONS.md` in full, then the specific records the task touches.
`docs/HANDOFF-ARCHIVE.md` is dated history — search it when you need to know
why something is the way it is, never as orientation.

## Roles

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits.

## Rules

- **No session links in commits or pull requests** (George, 2026-09-18). The
  repository is public and those links point into his own Claude account;
  whether anyone else can read them was never established. `Co-Authored-By`
  stays. The mapping from sessions to commits lives in
  `docs/SESSIONS.local.md`, which is not committed.

- Every architectural decision becomes a numbered ADR before implementation.
- Findings state their scope: what was tested, under what conditions, what was not.
- Do not characterise size, difficulty or risk without naming the evidence.
- Never reference an ALSA card by index. Use `hw:sndrpihifiberry`.
- Update `HANDOFF.md` at the end of every session. Keep it *current state*:
  when a session's narrative is finished with, move it to
  `docs/HANDOFF-ARCHIVE.md` verbatim rather than letting it accumulate.
- A verification that finds nothing has not proved nothing happened — see
  `docs/LESSONS.md`. Before overturning an earlier conclusion, search this
  repository for it first.
- **Keep the public documents current with every change** (George,
  2026-10-07). A change that alters what a user sees or does, how the
  player works inside, or what a plugin author relies on updates, in the
  same piece of work:
  - the user manual (`docs/manual/`) and its screenshots — taken only from
    the public-domain demo library, never a real one;
  - the FAQ (`docs/FAQ.md`);
  - the technical guide (`docs/tech/`);
  - the GitHub overview (`README.md`);
  - the plugin manual (`docs/WRITING-A-PLUGIN.md`, `docs/PLUGIN-CONTRACT.md`);
  - `docs/HARDWARE.md`.
  Say in the hand-back which of them changed, or that none needed to. The
  manual, FAQ and technical guide are drafts held on the local branch
  `docs-drafts` until George approves releasing them; until then update them
  there, never on a release branch.
- Implementing anything that comes — or might come — with a setting: propose
  it for ADR-0022's inventory and append it **only after George confirms**.
  Mark it as that record does ([R] recorded / [H] hardcoded today / [N] new
  suggestion / [?] a decision still owed).
