# Finding 042 — The device against the 2026-09-20 design drop

**Date:** 2026-09-20
**Question:** George: *"compare it with what we have on the device — not what
is recorded in docs, but the actual device"*, and name what is needed to
satisfy the new designs, grouped by whether it needs an ADR.
**System:** `gexis`, running `ui/src` at HEAD; `Gexis_DAC_Player.zip`
delivered 2026-09-20.
**Scope:** **Not an exhaustive sweep, deliberately.** Now Playing and Settings
were compared element by element; Library, WaitingServices, Handoff and Idle
were sampled. George closed the gap-hunt on cost grounds (§8) after
demonstrating it was incomplete. Everything below is measured; what was not
measured is named in §8.

## 1. How the device was established as ground truth

Docs were not used as the source for what the device does.

- **The UI.** `npm run build` on `ui/` at HEAD produced
  `index-DTeZ26xn.js` and `index-D65NUZUo.css` — the exact filenames
  `/opt/gexis-ui/assets/` serves — and `cmp` confirms both byte-identical,
  as is `index.html`. Vite content-hashes its output, so this is proof that
  **the device runs this source**, not an inference from filenames. Only
  after that was `ui/src` read as a map.
- **Settings** from the live `/settings` endpoint.
- **State** from a real `/state` WebSocket frame, opened by hand.
- **Enrichment** from a live `/enrichment` response.
- **The design's inventory** by evaluating its own `INV` literal in node,
  not by reading its prose — which matters, because the prose and the
  literal disagree (§7).

## 2. Settings, key by key

**Device: 7 groups, 54 settable, 6 wired. Design: 6 categories, 49 settable,
7 separators.** The design's own count, reproduced exactly from its `INV`.

**On the device, absent from the design (20):** `api_loopback`, `backup`,
`boot_default_scope`, `brightness`, `confidence`, `factory_reset`,
`idle_close`, `image_build`, `lms_player`, `log_level`, `plugins`, `power`,
`release_ladder`, `restore_floor`, `seek_reanchor`, `spotify_name`, `theme`,
`time_display`, `updates`, `volume_managed`.

**In the design, absent from the device (15):** `handoff_duration`,
`home_strip`, `home_strip_count`, `idle_background`, `idle_days`,
`idle_icons`, `idle_minmax`, `idle_screen`, `idle_weather`, `reboot`, `skin`,
`viz_stop`, `wallpaper_key`, `weather_key`, `weather_location`.

**Changed in place:** `bt_trusted` and `wifi` `action`→`list`, `lms_server`
`text`→`list`, `show_transition` display→handoff, `version` system→device,
plus mark changes on `bt_pairing`, `max_ceiling`, `travel_curve`, the two
drawer rows and the two API keys.

### Three rows whose value does not describe the code

Found while pinning the surfaces, and each is a defect rather than a port:

- **`travel_curve` reports `dB-linear`.** The design defines that option as
  *"travel straight to dB, where 55% is already −54 dB"* — linear across the
  hardware's full −120…0 dB, and the arithmetic is exact. But the slider is
  ADR-0034's −45…0 dB window, where 55% is **−20.25 dB**. The row names a
  curve the code does not implement. Unwired, so nothing acts on it — but
  wiring it as written would make the slider 34 dB quieter at mid-travel.
- **`bt_discoverable` reports `3 min after boot`.** Nothing chose three
  minutes: `bluetooth-setup.sh` runs `bluetoothctl discoverable on` and never
  touches `DiscoverableTimeout`, so BlueZ's 180 s default reverts it. The
  device reads `Discoverable: no`, `DiscoverableTimeout: 0x000000b4 (180)`.
  **`docs/LESSONS.md` already records this exact trap** ("cost us blocker 3
  and 1h36m") and the script still hits it. None of the three options is
  implemented.
- **`max_ceiling` is `None`** — no ceiling is enforced at all.

### The device name is not a source for anything

`device_name` is **refused**: `PUT /settings/device_name` → `HTTP 409
{"error": "device_name is not wired yet"}`. The daemon's wired set is exactly
six rows and does not include it; it appears only under `defaults`, as
`socket.gethostname` — a reader.

The four names agree only because each was set to the same literal at build
time: `squeezelite.service` carries `-n gexis` in its `ExecStart`,
`/var/lib/go-librespot/config.yml` has `device_name: gexis`, the BlueZ alias
comes from the hostname, and the hostname is `gexis`. **Nothing propagates.**

## 3. Now Playing — the change the token diff hid

A token diff alone reads as four values. It is a layout change.

**The device branches**: a full header when there are no synced lyrics
(title 58 / artist 29 / album 19) and a separate compact one when there are
(38 / 22 / 17). **The design has one** `.trackblock`, `position:absolute;
inset:0`, always the compact geometry — its CSS says *"One header, whether or
not lyrics are there."* So `--t-title` 58→38 is the large variant being
deleted, not shrunk.

Against the layout that survives:

| | device compact | design |
|---|---|---|
| artist | 22px | **25px** |
| album | 17px | **19px** |
| album year | — | **16px mono, `--ink-quiet`** |
| lyrics, in Track | 22px | **25px** (line box 54px) |
| lyrics, Lyrics tab | 21px | **31px** (line box 70px) |
| meta tabs | 13px | **17px**, unselected `--ink-tab-off` |

**The source pill stops being a pill** — *"Mark and word only — the pill
ground and border were removed"*: no padding, radius or background; mono
17px/600 against the device's UI face 13px/700; `--track-wide` (0.16em);
top 38→44px, gap 9→11px. The LMS four-bar mark is 21px and pulses at 2.4 s
while playing.

**Each meta tab's selected underline is its own fixed colour** — Track
`--ink`, Lyrics `--accent-artist`, Artist `--accent-bluetooth`, Release
`--accent-lms` — **never the source accent**.

Both new tokens (`--track-wide`, `--ink-tab-off`) exist for the source mark
and the tabs. Artwork, the 3px accent rule, all transport sizes
(`--ctl`/`--ctl-lg`/`--ctl-play`) and the five-line lyric window are
unchanged.

## 4. Other screens

- **Album page has only "Play album".** The design specifies **Play album
  *and* Add to queue**, stacked full-width. Missing.
- **Album Back is a one-route defect.** `back()` pops unconditionally and has
  no album case. From the discography, `openAlbum(id, title, path)` leaves
  the artist as the previous entry, so Back reaches the artist and always
  has. From the New Music strip, `openAlbum(tile.id, tile.title, [])` passes
  a literal empty path, so Back falls to the root. The design names exactly
  this route.
- **Artist page has no genre/tag pills.** `artistmeta__chip` is the similar-
  artists chip. The data contract lists tags alongside the biography.
- **Radio is a flat single column with two untinted glyphs** (`i-waves`
  folder, `i-tower` station) against a three-up card grid with ten tinted
  shapes and tinted discs on the rows below as well.
- **Pairing confirmation does not exist** — no match for `pairing`, `Reject`,
  `Accept` or `Request expired` anywhere in `ui/src`.
- **Idle is a drifting clock plus an optional embedded URL** — no
  backgrounds, no weather.
- **The Settings header** shows `deviceName · hostname` in narrow mode only,
  and carries a build stamp the design removes; nothing publishes the IP.

## 5. What the drop gets wrong about the device

Recorded so the work is not sized from it:

- *"The four woff2 files are not in the bundle"* — they are **in the repo**,
  and the device's fonts come from npm `@fontsource` (`ui/src/main.js`),
  bundled by Vite. `design/fonts/` is a separate standalone copy. The drop
  cannot carry binaries out; its own README says so.
- `repo-context.md` calls `App.svelte` *"a deliberate Phase 4b skeleton"* —
  several phases stale; it is 7,726 lines across 12 components.
- The data contract marks `NEW`: shuffle, repeat, transport commands, queue
  contents, the Lyrics/Artist/Release tabs, and all of Library. **All are
  live** — `controls.{available,shuffle,repeat}` with repeat already
  three-state, `queue` with the playlist it came from, and `/enrichment`
  serving `lyrics`, `lyrics_synced`, `biography`+`_source`+`_url`, `similar`,
  `popular`, `release_type`, `label`, `released`, `track_count`, `length_s`.
- Album year is `NEW` "not in `metadata`" — true of `/state`, but
  `/enrichment.released` already carries it.

## 6. Decisions taken, 2026-09-20

George, in review:

1. **The design is the point of truth.** ADR-0022's inventory is a catalogue
   of possibilities, not commitments; omitted rows are deliberate exclusions,
   **kept on the list but not surfaced**.
2. **One name for everything** — `device_name` feeds LMS, Spotify, Bluetooth
   and future renderers. No per-service name rows.
3. **Renaming requires a restart**; the design owes warning text.
4. **Fonts stay as they are.**
5. **Percent is the only user-facing volume unit**; dB internal.
6. **Fixed output is a miss to fix**, bundled with the whole volume setup.
7. **Confirmation pairing, because it is secure** — attended first pair.
8. **`seek_reanchor`, `release_ladder`, `idle_close` are not shown** —
   behind-the-scenes values a user can break.
9. **Radio is a restyle**, not a new screen.
10. **Album Back goes to the artist, always.**
11. **`home_strip` is query-only** — LMS serves counts and last-played.
12. **Add the IP to the Settings header, remove the build stamp.**
13. **`skin` needs thumbnails**, not names; **`viz_stop` is needed** or the
    visualiser sits under the idle screen indefinitely.
14. Mini strip height is fine; `readonly` takes no tap; press feedback 0.95.
15. **Panel and phone take the same input. No on-screen keyboard, ever.**
16. **No blur**, now or later.
17. **The System category is parked** → Could.

## 7. Contradictions in the drop

- `settings.md` says *"the three per-service name rows are all `readonly`
  'Advertised name', Bluetooth included"*; its own `INV` has **no name rows
  at all**. George's rule settles it in favour of the literal: no name rows.
- `README.md` warns *"the meta tabs measured 42px instead of 44px"* because
  the fonts are missing **on their side**. Our device has the real faces, so
  their spacing measurements are not our baseline where the two disagree.

## 8. What this does not cover

**The mechanical sweep is incomplete and its size is unknown.** Now Playing
and Settings were compared element by element. Library (2,696 lines against
seven design screens), `WaitingServices`, `HandoffScreen` and `IdleScreen`
were sampled, and sampling missed real items — George named six in one
breath, of which the album page's Add to queue and the artist page's tag
pills are confirmed above, and `WaitingServices`' icon sizes, the artist
page's album wrapping and its Retry treatment remain unchecked.

**A full sweep was proposed and declined** (George, on cost): *"A complete
sweep now would bring maybe an additional few mechanical items at a large
expense so I wouldn't go for it."* He will judge the remainder on the panel.

**The instrument that exists and was not used:** the drop ships
`verify.html` (38 checks, six groups, including a live computed-style diff)
and `geometry.json` — landmark geometry at 1280×800, 3px tolerance,
re-measured 2026-09-20. It covers **Now Playing only**. Running it against
the port would settle that screen's layout objectively and is cheap; it was
not run here.

**Also not established:** whether the design's spacing beyond the landmarks
matches, anything about the two `.dc.html` files' interaction states, and any
screen's behaviour under null metadata.

## 9. The panel check, 2026-09-20 — five findings and what was decided

George, on the device, against 9b and 9c. Each was reproduced in the source
before it was changed; the cause is stated because four of the five were not
what the symptom suggested.

1. **The home screen flashed before the artist page.** Tapping the artist
   name opens the Library, and the Library opens at its root while two
   fetches run - the artist list, then the discography. Not a navigation bug:
   the right screen was always coming, a second late, behind the wrong one.
   **Fixed by not drawing the root while an artist is being resolved**, and
   by taking the flag from the prop rather than from an effect, which runs
   after the first paint.

2. **The Lyrics tab looked empty and nothing was highlighted.** Two causes.
   `.lyrics--synced` centres its five lines and is written after
   `.lyrics--scroll`, so at equal specificity it won there too: the whole
   song was centred *and* translated, putting the sung line off the top.
   And **a stamped LRC line with no words is timing, not a lyric** - the
   run-in, an instrumental break, the outro - so through a gap the panel
   followed the clock onto a blank line and drew nothing. **Words are now
   kept apart from timing**: the line shown is the last one sung, and it is
   highlighted only while it is actually being sung. George: *"when the song
   doesn't have any lyrics left ... the last lyric should be shown (not
   highlighted of course)."* The full-song view also drops the five-line
   distance fade, which is the window's, for the design's flat unsung ink.

3. **Artist and Release cut their text with no fade and no control.**
   **Decided: clamp, fade, More/Less, and the whole block is the tap
   target** - George, who asked for the artist page's treatment and for
   tapping the text to work there too. **This departs from the drop**, which
   scrolls both texts inside the panel with a bottom mask
   (`fadeWhenScrollable`). A scroller inside a panel that also scrolls takes
   the finger meant for the panel, which is the reason the artist page
   clamps in the first place. More/Less appears only when the text is
   actually cut.

4. **The artist page's biography did not come back to its measured height.**
   `fitAbout` measured the first album row on screen, and unfolding makes the
   column scrollable - so folding back measured from wherever the scroll had
   left it. **Now measured in the column's own content**, scroll included,
   which gives the same answer at any position.

5. **The artist tab had no genres.** Added, from the same LMS query the
   artist page uses (`genres artist_id:`), resolved through the cached artist
   list because a renderer reports a name and LMS answers by id. Fetched when
   the tab is opened, not per track. An artist this library does not hold -
   anything over Bluetooth or Spotify - simply has no pills. The design gives
   these pills three accents in rotation where the library's artist page uses
   one; both are kept as their own screen draws them.

**Two more from the 2026-09-21 pass**, both removals:

6. **The three-renderer bar belonged to the home screen only.** It was drawn
   wherever the Library was and nothing was playing, so a discography or a
   playlist carried a footer about something else. On the home screen
   "nothing is playing and here is what could be" is the whole message;
   anywhere else it is furniture. Now gated on the home grid actually being
   on screen, which is not the same test as "no page has been opened" - an
   artist page on its way from Now Playing satisfies the second and not the
   first.

7. **More/Less went.** George: *"tapping in the text works perfectly as a
   toggle and the bottom fade indicates that there is more to be read."*
   Removed from the artist page's biography and from Now Playing's Artist
   and Release panels.

   **This makes the fade the only signal, so it had to stop lying.** The mask
   was applied whenever the text was folded, including over a note short
   enough to be whole - which the control used to cover for, because a
   "More" that was absent said as much as the fade did. Both panels and the
   artist page now measure whether anything is under the fold and draw the
   mask only then.

**Three more, 2026-09-21 — and two of them had one cause:**

8. **Press feedback on a list row was wrong twice over.** The design gives a
   row none — only the action buttons inside one carry `style-active` — and
   adding it produced both of the symptoms George reported separately.

   *The track title flashed on tap.* `.track__hit:active { opacity: 0.62 }`
   dims the whole row, title included, on the way to revealing the actions.

   *Tapping a radio category lit a different one.* The list is replaced under
   the finger, and the browser keeps `:active` on whatever element is there
   now — so the row that took the tapped one's place stayed highlighted for
   as long as the finger was down. Removed from the four rows that are
   replaced or revealed **in place**: browse rows, playlist and radio rows,
   album tracks, radio cards. The buttons keep theirs.

   **Not what it looked like.** The first guess was that `openRadio` set the
   page before it pushed the path; it does not — both land in one batch. The
   second was a daemon fault: a sub-level fetch appeared to return the root.
   It did not. **The route's query parameter is `at`, and the test used
   `handle`** — `docs/LESSONS.md`'s standing point about instruments, on a
   two-minute scale.

9. **The radio cards were not the design's.** The grid carried no padding, so
   the cards ran to the screen edge while every list below them sat 40 px in.
   Card padding 20→26 px, gap 16→18, grid gap 14→16, the disc pulled back
   8 px, and **the label and the count share a line** — the design puts the
   label at `flex:1` with the meta beside it, where the port stacked them.
   Label 19→22 px, meta 13→16 px mono.

10. **Every list now opens at the top.** A scroller keeps its offset when its
    contents are replaced, so walking into a radio category landed halfway
    down a list nobody had seen. One action on every scroller, resetting on
    the page's identity; the two hand-written `toTop` calls the browse panes
    had are gone, so there is one mechanism rather than two.

11. **The mini strip's renderer is no longer a pill** — mark and word only,
    mono 21 px/600 at 0.16 em with the mark at 28 px, which is what the
    design draws. 9b did this to Now Playing's source mark and stopped
    there; one renderer wearing two different treatments on two surfaces is
    the kind of thing only a diff notices.

