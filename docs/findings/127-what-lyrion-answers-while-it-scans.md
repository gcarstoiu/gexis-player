# Finding 127: What Lyrion answers while it scans

**Date:** 2026-10-18. **Asked by George:** can the home screen's tiles show the
library as Lyrion indexes it, or does it wait until the scan is done?

**Answer:** during a full rescan Lyrion keeps answering with the library it had
before, and the new one takes its place when the scan ends. Albums and album
artists did not move from the first second to the last; the song count dipped
once in between.

## Scope

- **Tested:** sofapi (Raspberry Pi 4, 4 GB), the player's own Lyrion Server
  9.1.1, a library of 760 songs on 47 albums in two SMB shares on a NAS,
  rebuilt with Lyrion's own `wipecache` (*Clear library and rescan
  everything*). Every 3 s, the queries the panel's tiles make: `albums 0 1`,
  `artists 0 1 role_id:ALBUMARTIST`, `titles 0 1`, and `serverstatus`.
- **Not tested:** the first scan of a library that was empty before (a new
  player's), a library of tens of thousands of files, a scan of changes only
  (*Look for new and changed music*), and what Lyrion's own web page shows
  meanwhile.

## Measured

The scan took 94 s.

| From | Step (Lyrion's `progressname`) | Albums | Album artists | Songs |
|---|---|---|---|---|
| 0 s | (starting) | 47 | 5 | 760 |
| 9 s | Discovering files/directories (1/0) | 47 | 5 | 760 |
| 18 s | Scanning new music files, 38 to 332 of 422 | 47 | 5 | 760 |
| 61 s | the second share, 1 to 84 of 133, then 118 | 47 | 5 | **509** |
| 79 s | Building full text index; Looking for contributor pictures | 47 | 5 | 509 |
| 94 s | done (`rescan` gone) | 47 | 5 | 760 |

## What follows

- **A library that exists stays browsable through a rescan**, as it was
  before it; nothing the tiles count changes until the end.
- **A new player's first scan, not measured**, would by the same behaviour
  leave the library empty until it ends - hours on a large library. The
  home screen needs something to show meanwhile; the options are George's
  decision.
- **`progressname` is Lyrion's own readable text**, and its count is that
  step's: files for *Scanning new music files*, none for *Discovering
  files/directories* (1/0). `lyrion_stage` shows the text with its count
  (ADR-0115 decision 28).
