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
| source mark + accent colour | `active` |
| play control shape (pause-shaped when paused) | `metadata.transport` — there is **no** state line and **no** artwork dim |
| elapsed | `metadata.position` |
| remaining | `metadata.remaining_time`, or `duration - position` |
| progress fill | `position` / `duration`, interpolated |

**Later phases on the same screen:**

| Screen element | Field | Phase |
|---|---|---|
| album year, beside the album name | `NEW` — release year. Not in `metadata`. | 7 |
| volume control and plate | `volume.percent`; `POST /volume { percent }` | 6 |
| volume hidden entirely | `NEW` — output mode is fixed vs variable | 6 |
| shuffle state | `NEW` — shuffle off/on | 6 |
| repeat state | `NEW` — repeat off / all / one (three states, not a bool) | 6 |
| transport buttons | `NEW` — play, pause, next, previous commands | 6 |
| queue rail contents | `NEW` — ordered upcoming tracks, and the playlist they came from | 7 |
| Lyrics tab | `NEW` — lines, plus per-line timestamps when synced | 8 |
| Artist tab | `NEW` — biography with its attribution line, tags, top tracks, similar artists. No confidence value: it was removed. | 8 |
| Release tab | `NEW` — release type, format and label as chips (label only off LMS, which holds none), a release note, and a spec row: Released, Tracks, Length, Recorded. A spec with no value is not rendered. | 8 |

Notes for the implementer:

- **Repeat has three states.** A boolean will not carry it.
- The **queue** needs to distinguish "empty" from "playing a playlist": the
  design shows a different empty state that offers a playlist chooser, and it
  must not claim to be playing from a playlist when the queue is empty.
- `source_type` duplicates `active` for the screens here; `active` is what the
  design keys off, because it also carries `null`.

---

## Mini strip (104px, on every non-Now-Playing screen)

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
| shown after | `NEW` — `idle_timeout`, counted from when playback stops; the separate grace period was merged into it |
| dismissed by | local touch only |
| clock | device time |
| external page | `NEW` — idle screen URL, from settings |
| background | `NEW` — `idle_background`: artist pictures from the library, wallpapers from an online service or from local storage, or black |
| wallpaper service key | `NEW` — `wallpaper_key`, only for the online source |
| weather | `NEW` — provider keyed by `weather_key`; `weather_location` names the place |

Needs a fallback for unreachable, unconfigured, **and reachable-but-refuses-framing**.

Neither wallpaper service is chosen. The online one may or may not need a
key, and the on-device one needs a folder the device owns. Both are open
questions for implementation, not design.

Without `weather_key` the idle screen shows the clock alone, and Settings
hides every row that shapes a forecast.

---

## Handoff transition

| Element | Field |
|---|---|
| from / to marks | `handoff.from`, `handoff.to` |
| shown at all | `handoff` non-null |
| skipped for | `handoff_exempt_pairs` |

Shown for 1–3s, then self-dismisses. Must not read as a failure.

---

## Pairing confirmation

| Element | Field |
|---|---|
| requesting device | `NEW` — device name from the agent |
| code | `NEW` — the six digits the phone shows |
| shown at all | `bt_pairing` = Confirmation required, first pair only |
| accept / reject | `NEW` — commands back to the pairing agent |
| expiry | `NEW` — the agent's own timeout, 30s; the panel counts it down and dismisses itself at zero |

The panel must not outlive the agent's request: when the timeout lapses the
frame reports **Request expired** and closes without trusting the device.

---

## Home strip

| Element | Field |
|---|---|
| which strip | `home_strip`: New music / Most played artists / Recently played artists |
| how many | `home_strip_count`, 4–20 |
| new music | albums by date added |
| most played artists | `NEW` — play counts per artist |
| recently played artists | `NEW` — last play timestamp per artist, rendered as a relative caption |

---

## Device

| Element | Field |
|---|---|
| name | `device_name`, shown as typed |
| hostname | derived by the sanitiser, never substituted silently |
| address | `NEW` — the device's own IP, shown in the Settings header |
| time zone | `timezone`, IANA. Taken from the network; the picker is the correction path |
| version | `NEW` — nothing on a running device reports its build |

---

## Library, Artists, Playlists, Radio (Phase 7)

None of this data exists yet. Everything below is `NEW`.

| Screen | Needs |
|---|---|
| library root | a count under Browse (albums), Artists (artists) and Playlists (playlist count). Radio carries no count — the tree is remote and unknown; Settings reads "Device and sources". |
| home strip | whichever `home_strip` names, `home_strip_count` long (4–20, default 10): recently added albums (title, artist, artwork), most played artists (play counts), or recently played artists (last-play timestamps) |
| browse (3-pane) | artists → albums → tracks, each pane independently filled |
| artist grid | artist name, album count, photo; grouped by folded initial |
| artist page | discography by release type, plus the Phase 8 enrichment fields |
| album page | track list with durations, album artwork, year |
| playlists | playlist name, track count, and each track's title/artist/duration/artwork |
| radio | the LMS radio tree, four levels deep, plus station artwork |
| row actions | play now, add to queue, add to playlist (existing playlists only — creating one on the device was removed) |

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

- **`/state` socket disconnected** — **deferred, not designed.** The panel's
  browser outlives daemon restarts, so a restart leaves the screen showing
  stale metadata for a few seconds before it reconnects on its own. Not worth
  designing for: it self-heals. The case that would not is the daemon failing
  to come back, where the panel would sit indefinitely showing a frozen track
  as if playing. George has not seen that happen, so this is deferred until
  it does. `ui/src/lib/state.js` already exposes the `connection` store
  (`connecting` / `open` / `reconnecting`) if it is ever needed.

- artwork URL present but 404 — should fall back to the pending glyph.
- a playlist that exists on the server but holds no tracks.
