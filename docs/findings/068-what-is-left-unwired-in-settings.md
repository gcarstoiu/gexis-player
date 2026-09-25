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

**The 14 visible ones are criterion 1's work.** Each shows today's value and
each refuses to change it — the panel marks them `data-unwired="settings"`
and says *"not wired yet"* when tapped, which is the 2026-09-15 convention
that makes them greppable. They are tracked, not forgotten. They are also
not wired.

## The fourteen

| group | row | mark | what it would take |
| --- | --- | --- | --- |
| sources | `lms_enabled` | R | stop arbitrating and starting a renderer that is off (ADR-0013) |
| sources | `spotify_enabled` | R | as above |
| sources | `bt_enabled` | R | as above |
| sources | `bt_pairing` | R | PIN-free vs confirmation. ADR-0024 leaves this `[?]` — **a decision is owed before wiring** |
| sources | `bt_trusted` | R | view and forget remembered devices; clearing breaks reconnection |
| sources | `bt_autotrust` | H | today `gexis-bluetooth-trust.service` does it unconditionally |
| handoff | `restore_transport` | R H | ADR-0027 plays only if it was playing |
| handoff | `reclaim_lms` | N | ADR-0027 deliberately never does this; the row is the opt-in |
| handoff | `show_transition` | N | whether the takeover screen appears at all |
| handoff | `handoff_threshold` | R H ? | ADR-0010's 1 s. The inventory calls it **evidence-gated rather than preference** |
| handoff | `handoff_duration` | N | how long the takeover animation stays |
| display | `headless` | R | disable the local screen entirely — Must tier |
| device | `wifi` | R | joining a network. Overlaps **Phase 13**, which raises an access point for exactly this |
| device | `version` | R ? | readonly and reporting **nothing**; the smallest of the fourteen |

## What this does not settle

- **Which of them should be wired and which scoped out.** Three are
  candidates for scoping — `handoff_threshold` because the inventory says
  the number is evidence's to set, `wifi` because Phase 13 owns network
  setup, and `bt_pairing` because ADR-0024 owes a decision first. **That is
  George's call, not this record's.**
- **What wiring each costs.** The table says what it would take, not how
  long.
- **The phone.** The criterion says panel *and* phone (ADR-0035); this was
  read from the daemon, which serves both, but nothing was tried in a
  browser.
