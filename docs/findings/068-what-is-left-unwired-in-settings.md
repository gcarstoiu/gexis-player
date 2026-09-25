# Finding 068 — What is left unwired in Settings

**Date:** 2026-09-25
**Question:** Phase 9 criterion 1 — *every row in ADR-0022's settings
inventory is wired end to end (panel and phone), or marked out of scope with
the reason.* Which rows are not?
**Scope:** `gexis`, 2026-09-25, read from the running daemon's `/settings`,
which reports `wired` and `visible` per row. **A generated list, not an
audit** — the criterion asks for one, and `SettingsRegistry.set` raises
`NotWired` for a row nothing is listening to, so the answer is in the
daemon rather than in anybody's reading of the code.

## The shape of it

The daemon serves **74 rows**:

| | rows |
| --- | --- |
| wired and visible | **41** |
| wired, not visible | 3 |
| **visible but not wired** | **14** |
| not wired, not visible | 16 |

**The 16 that are neither are not the gap.** `surfaced: false` is ADR-0044
§3's permanent state: the row is inventoried so the decision is not lost, and
not shown because nothing would happen. They are Settings' own scoped-out
list, already written down.

**Two of the fourteen were over-reported, and George caught it.** A `list`
row does not take a value: `wifi` and `bt_trusted` are worked through
`POST /settings/<key>/items` — join, forget — and never through `set`, so
`wired: false` describes a route they do not use. Both function today.
George, 2026-09-25: *"WiFi already works - nothing to add there."*

**So the generated list is honest about the mechanism and not about the
feature.** `wired` means "something is listening for a new value", which is
the right question for twelve of these rows and the wrong one for two.

**The remaining twelve are criterion 1's work.** Each shows today's value and
each refuses to change it — the panel marks them `data-unwired="settings"`
and says *"not wired yet"* when tapped, which is the 2026-09-15 convention
that makes them greppable. They are tracked, not forgotten. They are also
not wired.

## The fourteen

| group | row | mark | what it would take |
| --- | --- | --- | --- |
| sources | `lms_enabled` | R | ~~stop arbitrating and starting a renderer that is off (ADR-0013)~~ **wired 2026-09-25, [ADR-0077](../decisions/0077-a-source-that-is-off-is-not-running.md)** |
| sources | `spotify_enabled` | R | ~~as above~~ **wired 2026-09-25** |
| sources | `bt_enabled` | R | ~~as above~~ **wired 2026-09-25**, and it powers the radio down as well |
| sources | `bt_pairing` | R | PIN-free vs confirmation. ADR-0024 leaves this `[?]` — **a decision is owed before wiring** |
| sources | `bt_trusted` | R | view and forget remembered devices; clearing breaks reconnection |
| sources | `bt_autotrust` | H | today `gexis-bluetooth-trust.service` does it unconditionally |
| handoff | `restore_transport` | R H | ADR-0027 plays only if it was playing |
| handoff | `reclaim_lms` | N | ADR-0027 deliberately never does this; the row is the opt-in |
| handoff | `show_transition` | N | whether the takeover screen appears at all |
| handoff | `handoff_threshold` | R H ? | ADR-0010's 1 s. The inventory calls it **evidence-gated rather than preference** |
| handoff | `handoff_duration` | N | how long the takeover animation stays |
| display | `headless` | R | ~~disable the local screen entirely — Must tier~~ **wired 2026-09-25**, three units |
| device | `version` | R ? | readonly and reporting **nothing**; the smallest of them |

**Not on the list after all:** `wifi` and `bt_trusted`, which work through
their own route.

## What this does not settle

- ~~**Which of them should be wired and which scoped out.**~~ **Settled by
  George, 2026-09-25:** Wi-Fi already works; `handoff_threshold` stays as it
  is, unwired, because the number is evidence's to set; and `bt_pairing` has
  its decision — **confirmation by default, PIN-free as a viable option** —
  so it is wired rather than scoped out. The other ten are to be wired.
- **What wiring each costs.** The table says what it would take, not how
  long.
- **The phone.** The criterion says panel *and* phone (ADR-0035); this was
  read from the daemon, which serves both, but nothing was tried in a
  browser.
