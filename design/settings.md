# Settings — row vocabulary

**Provisional.** ADR-0032 has the API matching this vocabulary rather than the
reverse, so treat the list as a snapshot: it will change as rows are confirmed.

Source: `source/Settings.dc.html`. Responsive by mount width — two-pane at
≥720px, drill-down below. It measures its own container, not the viewport,
because it is embedded on the panel and standalone on the phone.

---

## Row types

Seven, of which six are settable and one is a separator.

| Type | Payload | UI | Notes |
|---|---|---|---|
| `toggle` | `value: bool` | inline switch | no sheet; acts immediately |
| `choice` | `value: string`, `options: string[]` | sheet, single-select | options are display strings |
| `number` | `value: number`, `unit`, `min`, `max`, `step?` | sheet; slider when bounded, stepper otherwise | |
| `text` | `value: string` | sheet with field | **the only type needing a keyboard** |
| `readonly` | `value: string` | row, no control | GET only |
| `action` | none; `confirm?: string`, `danger?: bool` | sheet with Cancel / confirm | POST only, no stored value |
| `group` | `label`, `accent` | separator | not addressable |

`readonly` and `action` are the asymmetric pair: one never accepts a write,
the other has nothing to read.

Every settable row also carries:

- `k` — stable key, e.g. `lms_server`, `boot_volume`. Use these verbatim.
- `label` — short, sentence case.
- `note?` — one or two sentences, shown under the label and in the sheet.
- `marks` — provenance from the record: `R` recorded, `H` hardcoded today,
  `N` new suggestion, `?` a decision still owed.

**The amber dot is derived from `?`**, never hand-placed. A group's dot is
derived from its rows. Keep it that way: the dot is how an unconfirmed
placeholder is spotted, and it must not be possible to forget one.

---

## Groups

Seven, in this order. Grouped by what the user is changing, not by subsystem.

| Group | Accent | Contains |
|---|---|---|
| Audio | `--accent-lms` | level and output |
| Sources | `--accent-bluetooth` | LMS, Spotify, Bluetooth — subgrouped |
| Handoff | `--accent-warn` | who gets the device |
| Display | `--accent-display` | panel, idle screen, visualization — subgrouped |
| Enrichment | `#e8a0b4` | lyrics and artist info |
| Device | `#8fc4d8` | identity and network |
| System | `#b0bcc4` | updates and maintenance |

---

## Rows still owed a decision

These carry the amber dot. Each ships whatever the placeholder happens to be
unless someone decides:

| Key | Why |
|---|---|
| `max_ceiling` | ADR-0018 listed it "to be recorded"; still undecided |
| `restore_floor` | −40 dB placeholder, never confirmed; measured too quiet for Bluetooth |
| `boot_default_scope` | a renderer's first use mid-session starts as quiet as a cold boot |
| `travel_curve` | dB-linear travel puts everything usable in the top quarter |
| `seek_reanchor` | deferred twice; pressing play on a deactivated player loses position |
| `handoff_threshold` | evidence-gated rather than a preference — exposing it may be wrong |
| `bt_pairing` | needs this screen before it can be anything but hardcoded |
| `version`, `image_build` | nothing on a running device reports which build it is |

---

## Two behaviours to preserve

**Device name.** `device_name` is one name feeding mDNS, Spotify and
Bluetooth. The header shows the name **as typed** with the sanitised hostname
beside it — `gexis · gexis.local`. Never substitute silently. The sanitiser
folds accents, lowercases, replaces illegal characters with hyphens, trims
them from the ends, and caps at 63 characters.

**Fixed output mode.** When `output_mode` is Fixed, the volume slider
disappears **everywhere** — Now Playing, the mini strip, and Settings — and a
small lock badge appears on the volume trigger. Do not render a disabled
slider.

---

## Not built

`text` rows show their value and a confirm button but no input field. On the
panel that needs an on-screen keyboard decision; on the phone it is a native
input. Whichever comes first, the row type does not change.
