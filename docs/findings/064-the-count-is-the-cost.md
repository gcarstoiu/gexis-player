# Finding 064 — The count is the cost: nothing in a card matters

**Date:** 2026-09-24
**Question:** George: *"It worked again the first try and then the second
time it went slower... the artists and browse should be nearly
instantaneous."*
**Scope:** `gexis`, 2026-09-24, ADRs 0060, 0061 and 0065 live, music
playing. Each variant served from a fresh page load and opened three times.
Times from the tap, measured inside the page; blocking from the browser's
own `longtask` entries. **Not measured: a phone.**

## What opening the artist grid actually costs

ADR-0065 moved the work behind the first paint, and it is still there:

| | swap | painted | settled | **main thread blocked** | longest task |
| --- | --- | --- | --- | --- | --- |
| artist grid | 145–206 ms | 268–375 ms | ~1.9 s | **1255–1358 ms** | 295–443 ms |
| browse pane | 121–156 ms | 188–226 ms | ~1.0 s | 273–523 ms | 115–294 ms |

**Six chunks, each a task of 300–443 ms.** The panel is unresponsive for
each of them. That is what is felt after the screen has already changed.

## Five things a card is not

Each suppressed in a build of its own, served from its own page load, three
opens each. Against 1255–1358 ms blocked as it ships:

| the artist grid, with | blocked |
| --- | --- |
| **nothing suppressed** | 1255–1358 ms |
| one shared `IntersectionObserver` instead of 917 | 1061–1268 ms |
| no observers at all | 1032–1219 ms |
| no per-artist tint | 1066–1127 ms |
| no photos | 1150–1586 ms |
| observers, tint and photos all gone | 987–1225 ms |

**Not one of them moves it.** A card with no picture, no tint and nothing
watching it costs what a card costs. 917 of them is about 1.3 ms each, and
that is the elements existing — being created, styled and laid out — rather
than anything in them.

**This is Finding 058's shape again**, on the other side: there, eight
candidates failed to move a *scroll*, and the answer was that the cost was
the area being redrawn. Here five fail to move a *build*, and the answer is
the number of elements being built.

## What follows

**Deferring cannot fix it and cheaper cards cannot fix it.** ADR-0065 was
right that the work should not be in front of the first paint, and it moved
1.9 seconds of dead time to 270 ms — but the work is still done, and a
person using the panel in that second feels it.

The only lever left is **not creating the elements**. A viewport holds about
40 cards; the grid creates 917. At 1.3 ms each that is the difference
between roughly 50 ms and 1200.

## What this does not settle

- **How to window a grouped grid.** The artist grid is 27 letter groups in a
  six-column grid, so a row's height depends on the panel's width and a
  group's height on how many artists it holds. That is ADR-0067.
- **The other lists.** A playlist paints in 104 ms and George reports it
  fixed; the queue rail is untested at length.
- **Whether 1.3 ms a card is normal.** It was not compared against anything.
