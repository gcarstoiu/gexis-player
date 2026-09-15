# Data contract — what each screen reads

Against the `/state` WebSocket message and the two REST commands.

`NEW` marks something a screen needs that `/state` does not publish today. I
have not invented field names for those; each says what the screen needs in
words so the implementation side can name it.

---

## Now Playing

**First slice (4c) reads only:**

| Screen element | Field |
|---|---|
| track title | `metadata.title` |
| artist name | `metadata.artist` |
| album name | `metadata.album` |
| artwork, 500×500 | `metadata.artwork` |
| source pill + accent colour | `active` |
| state line (Playing / Paused / Stopped) | `metadata.transport` |
| elapsed | `metadata.position` |
| remaining | `metadata.remaining_time`, or `duration - position` |
| progress fill | `position` / `duration`, interpolated |

**Later phases on the same screen:**

| Screen element | Field | Phase |
|---|---|---|
| album year, beside the album name | `NEW` — release year. Not in `metadata`. | 7 |
| format tier badge | `metadata.codec` + `sample_rate` + `NEW` bit depth | — |
| volume control and plate | `volume.percent`; `POST /volume { percent }` | 6 |
| volume hidden entirely | `NEW` — output mode is fixed vs variable | 6 |
| shuffle state | `NEW` — shuffle off/on | 6 |
| repeat state | `NEW` — repeat off / all / one (three states, not a bool) | 6 |
| transport buttons | `NEW` — play, pause, next, previous commands | 6 |
| queue rail contents | `NEW` — ordered upcoming tracks, and the playlist they came from | 7 |
| Lyrics tab | `NEW` — lines, plus per-line timestamps when synced | 8 |
| Artist tab | `NEW` — biography, tags, top tracks, similar artists, confidence | 8 |
| Release tab | `NEW` — album note, label, release type, track count | 8 |

Notes for the implementer:

- The **format tier** needs bit depth, which is not in the contract. `24/96`
  cannot be derived from `sample_rate` alone.
- **Repeat has three states.** A boolean will not carry it.
- The **queue** needs to distinguish "empty" from "playing a playlist": the
  design shows a different empty state that offers a playlist chooser, and it
  must not claim to be playing from a playlist when the queue is empty.
- `source_type` duplicates `active` for the screens here; `active` is what the
  design keys off, because it also carries `null`.

---

## Mini strip (96px, on every non-Now-Playing screen)

| Element | Field |
|---|---|
| artwork thumb | `metadata.artwork` |
| title, artist | `metadata.title`, `metadata.artist` |
| play/pause | `metadata.transport`; `NEW` command |
| elapsed | `metadata.position` |
| progress hairline | `position` / `duration` |
| connected renderer mark | `active` |
| volume trigger | `volume.percent` |

Absent entirely when `active` is null.

---

## Idle screen (ADR-0019)

| Element | Field |
|---|---|
| shown after | `NEW` — idle timeout and post-stop grace, from settings |
| dismissed by | local touch only |
| clock | device time |
| external page | `NEW` — idle screen URL, from settings |

Needs a fallback for unreachable, unconfigured, **and reachable-but-refuses-framing**.

---

## Handoff transition

| Element | Field |
|---|---|
| from / to marks | `handoff.from`, `handoff.to` |
| shown at all | `handoff` non-null |
| skipped for | `handoff_exempt_pairs` |

Shown for 1–3s, then self-dismisses. Must not read as a failure.

---

## Library, Artists, Playlists, Radio (Phase 7)

None of this data exists yet. Everything below is `NEW`.

| Screen | Needs |
|---|---|
| library root | counts per section: albums, artists, playlists, stations |
| New Music strip | ten most recently added albums: title, artist, artwork |
| browse (3-pane) | artists → albums → tracks, each pane independently filled |
| artist grid | artist name, album count, photo; grouped by folded initial |
| artist page | discography by release type, plus the Phase 8 enrichment fields |
| album page | track list with durations, album artwork, year |
| playlists | playlist name, track count, and each track's title/artist/duration/artwork |
| radio | the LMS radio tree, four levels deep, plus station artwork |
| row actions | play now, add to queue, add to playlist; create playlist |

Two design decisions that affect the API:

- **Artist filing is folded**: accents reduce to base letters and a leading
  article is ignored, so "Ándra" files under A and "The Beatles" under B. If
  the server sorts, it must sort this way, or the jump rail will disagree with
  the list.
- **Playing anything from the library activates LMS.** The design assumes this
  happens as a side effect, not that the panel calls
  `/renderer/lms/activate` first.

---

## Settings

No endpoints exist. See `settings.md` for the row vocabulary the API should
match, per ADR-0032.

---

## Empty and error states that need designing later

Named here so they are not forgotten:

- `/state` socket disconnected — distinct from `active: null`, and currently
  undesigned.
- artwork URL present but 404 — should fall back to the pending glyph.
- enrichment below the confidence threshold — shows nothing, by decision.
- a playlist created on the device but still empty.
