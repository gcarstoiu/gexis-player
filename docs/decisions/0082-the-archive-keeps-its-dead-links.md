# ADR-0082 — The archive keeps its dead links

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** `docs/HANDOFF-ARCHIVE.md` (the promise this upholds),
`core/tests/test_docs_links.py` (the check that exempts it)

## Context

A sweep of every relative link in the records, 2026-09-25, found 98 that do
not land. Twenty-four were ordinary mistakes — a link written from a record's
title rather than its filename — and were fixed.

**The other seventy-four are all in `docs/HANDOFF-ARCHIVE.md` and are all one
kind.** They are repo-root paths (`docs/decisions/0027-…`), which is correct
in `HANDOFF.md`, where every one of them was written. The archive lives inside
`docs/`, so from there the same path resolves to `docs/docs/decisions/…` and
misses.

They broke on the move, not in the writing. And the archive's own header says
why they were moved that way:

> **Nothing here was edited.** The blocks below are verbatim, in their
> original order, so a `git log -p` trail still matches. What was removed from
> `HANDOFF.md` is exactly what appears here — the split was line-counted, not
> eyeballed.

## Decision

**The archive stays verbatim, and keeps its dead links.** George, 2026-09-25,
choosing between that and relaxing the promise for link targets only:
*"Keep it."*

`core/tests/test_docs_links.py` exempts the archive by name and states this as
the reason. It also asserts that the archive still declares itself verbatim —
if that promise is ever dropped, these links stop being a consequence of a
decision and become ordinary rot, and the exemption should go with it.

## Rationale

**The promise is worth more than the clicks.** The archive exists to answer
*why* something ended up the way it did, and its value is that it is provably
the same text that was current at the time. A `git log -p` trail that still
matches is the whole point; a hundred small edits to make links resolve would
be exactly the kind of tidying that makes a historical record stop being one.

**And the cost is low and self-limiting.** The archive is read rarely, by
somebody chasing a specific date or decision, who has the record's *number* in
front of them — every one of these links names it in the link text. The
records are all still there under the numbers. What is lost is a click, in a
file nobody navigates by.

### Rejected: rewrite the 74 paths

The obvious fix, and it looks more reasonable every time somebody runs a link
checker — which is why it is written down here. Rejected because it edits what
the file promises is unedited, and because the promise cannot be half-kept:
once the text has been touched to suit a tool, "verbatim" is a claim nobody
can check without a diff.

### Rejected: move the archive to the repository root

It would make every one of the 74 paths correct, and costs nothing in history.
Rejected because the root is what a new reader sees first, and `docs/` is where
CLAUDE.md sends them for records. Moving a file nobody should start with into
the place everybody starts, to fix links nobody follows, is the wrong trade.

## Consequences

- A link checker run over the whole tree will always report 74 failures in that
  one file. The test does not, because it is told to skip it by name.
- Anything moved into the archive in future arrives with the same defect, by
  design. The archive's header now says so, so it is found before it is
  puzzled over.
