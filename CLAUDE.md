# Gexis Player

Custom high-fidelity music player distribution for Raspberry Pi 4.

## Read these first

- `docs/ARCHITECTURE.md` — layer model and requirements
- `docs/decisions/` — numbered ADRs, one per decision
- `docs/findings/` — measured results, each with scope stated
- `HANDOFF.md` — current state and next action

## Roles

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits.

## Rules

- Every architectural decision becomes a numbered ADR before implementation.
- Findings state their scope: what was tested, under what conditions, what was not.
- Do not characterise size, difficulty or risk without naming the evidence.
- Never reference an ALSA card by index. Use `hw:sndrpihifiberry`.
- Update `HANDOFF.md` at the end of every session.
- Implementing anything that comes — or might come — with a setting: propose
  it for ADR-0022's inventory and append it **only after George confirms**.
  Mark it as that record does ([R] recorded / [H] hardcoded today / [N] new
  suggestion / [?] a decision still owed).
