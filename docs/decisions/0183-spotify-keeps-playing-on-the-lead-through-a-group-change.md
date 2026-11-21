# ADR-0183 — Spotify keeps playing on the lead through a group change

**Status:** **Accepted** 2026-11-18 (George: keep Spotify playing), as
recommended: **A**, pause, rewrite, resume. Proposed 2026-11-15; George, the
same day: Spotify should normally keep playing on the lead when the group
changes. **Checked on sofapi** 2026-11-21 (with shelvespi; the phone's part
by George): a join paused the music 1.77 s, the track, position and volume
kept, no fallback; a leave, no gap (B3); George found the phone right and
the pause acceptable, so A stays.
**Amends:** [ADR-0166](0166-multiroom-for-every-source.md) B2 for
go-librespot. **Relates to:** Finding 014 (`/player/resume` without
Spotify's handshake), LESSONS 21, 81 and 84.

## Context

A player joining or leaving a group changes the chain under the lead's
renderers (`_group_rechain` → `_rewrite_output_conf`). Every renderer stops
first, since `outputs.write` opens the card to ask its rates and a held card
answers nothing (LESSONS 21), and restarts after, since a renderer keeps the
ALSA configuration it read when it opened (LESSONS 81, 84). Stopping
go-librespot ends the Spotify Connect session: the phone loses the player
and the music stops, where B2 says it is interrupted a moment. Lyrion has
its own way round (`_rechain_around_squeezelite`); Spotify has none.

go-librespot can reopen its output without its session ending, in 0.10.5
and in the build we ship (read in the source, `output/driver-alsa.go`,
`player/player.go`):
- **pause** closes the ALSA device; **resume** opens it again, after
  `snd_config_update_free_global()`, so the configuration is read afresh;
- **`POST /player/output`** (empty device: the configured `output`) drops
  and closes the device and opens it again, the same way, keeping the track,
  position, paused state and volume, with a gap under a second by its own
  account.

## Options

- **A. Pause, rewrite, resume.** While Spotify plays on the lead, the core
  pauses it through the API, stops the other renderers, writes, and resumes
  it. The phone shows a pause for the time the rewrite takes (a second or
  two, to be measured). Pause and resume are what the phone's own buttons
  send.
- **B. Rewrite around it, then reopen.** go-librespot keeps the card while
  the file is written, with the card's rates taken from the last time it was
  asked (the card does not change with the group); then `/player/output`
  moves it onto the new chain. Nothing reaches the phone; the gap is the
  reopen's. Needs the rates kept per card, and the probe skipped only for a
  card that did not change.
- **C. As today**, and B2 and the manual say Spotify must be picked again
  after a group change on its player.

## Recommendation

**A**, built so B can replace it if the pause shows too much. A changes one
step and uses what the phone itself sends; B touches how every chain is
written. On a player, before it is accepted as built:
- a join and a leave while Spotify plays on the lead: the music back, the
  phone still showing the player and its track, the position kept, the gap
  timed;
- Finding 014's failure looked for: after the resume, the phone's own
  Pause and Next reach the player (not the phone);
- the follower hearing the lead at the same moment as before;
- the equaliser on at the lead (CamillaDSP restarts with the chain).

Only Spotify: Bluetooth and Plexamp on the lead restart as now (B2).
