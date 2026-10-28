# ADR-0166 — Multiroom for every source

**Status:** **Accepted** 2026-10-27 (George: his answers, and C1-C6
confirmed the same day; C3 he called an edge case). Amended 2026-10-28:
the design back from Claude Design (`design/source/22/`), decision 10 and
where it is measured, George's answers that day; D1 as Finding 139 found
it, and C5's wording mended. Phase 22
(`ph-multiroom`), started the same day (George: multiroom, then AirPlay 2, before room correction, which
cannot be tried yet). The experience is George's, from his answers the same
day (*Decided*); the technical decisions are proposed, and confirmed or
changed by the phase's first measurement. Builds on
[ADR-0010](0010-arbitration-slot-model.md) (arbitration),
[ADR-0013](0013-defaults-implement-public-contract.md) (renderers and the
plugin contract), [ADR-0018](0018-volume-and-output-modes.md) (volume),
[ADR-0037](0037-transport-commands.md) (transport commands),
[ADR-0136](0136-switching-between-players-on-the-phone.md) (the players on
the network), [ADR-0162](0162-a-simple-equaliser.md) (the loopback, a change
of rate) and [ADR-0164](0164-the-phone-remote.md) (the phone remote).

## Context

- Lyrion already plays in sync on several players: Squeezelite is synced by
  the Lyrion server, bit-perfect and gapless, on players that use the same
  server. Spotify, Bluetooth, Plexamp and plugin renderers play on one
  player each.
- Every renderer, the plugins included, plays to the same output path,
  `pcm.output` (or `pcm.output_wait`, Squeezelite's), and with the equaliser
  on that path already ends on `snd-aloop`'s loopback (ADR-0162 D1). Audio
  taken there is every source's, with no change to a renderer or to the
  plugin contract.
- The players already find each other: each announces `_gexis._tcp`, and
  `/players` lists them (ADR-0136).
- Snapcast (GPL-3.0) keeps players in time over the network: a server reads
  the audio, clients play it, each corrected to the server's clock. Debian's
  `snapserver` and `snapclient` 0.31.0 are in the players' own archive
  (trixie), with no download from elsewhere.

## Decided (George, 2026-10-27)

1. **It works for every source**: Lyrion, Spotify, Bluetooth, Plexamp, and
   any renderer plugin, with nothing asked of the plugin.
2. **One group, Lyrion's own sync for Lyrion.** Players are grouped once,
   in Gexis. While the group plays Lyrion, the group is Lyrion's own sync
   group (bit-perfect, gapless, seen in Lyrion's apps); the other sources go
   through Gexis's own sync. Lyrion's multiroom keeps working as it does.
3. **Join players, until undone.** From a player's remote, and from the
   panel, other players are joined to it; the group lasts until it is
   undone, a restart included.
4. **The whole group follows.** A source started on any player of the group
   plays on the whole group.
5. **Each player keeps its own volume, and a group slider** moves them all
   together, keeping their balance. A player on Fixed volume stays fixed.
6. **Every member shows the group's Now Playing**, marked as grouped, and
   play, pause, skip and the group volume work from any of them.
7. **As short a delay as possible.** Grouped, a command is heard after the
   buffer that keeps the players together; George chose the shortest, over
   about a second that rides out a weak Wi-Fi link.
8. **The source's own rate.** Grouped, a source plays at its own rate,
   unchanged; a change of rate between tracks costs a short gap, as the
   equaliser's does.
9. **Home Assistant too**: the integration offers Home Assistant's own join
   and unjoin for media players, in its release after the player's.
10. **Lyrion's syncs are Gexis groups** (George, 2026-10-28, after the
    design): Gexis players synced in a Lyrion app (Material, Lyrion's web
    page) are grouped in Gexis too, and unsynced there they leave it - one
    group, whichever side made it; every source then follows it.

## Proposed (technical)

**D1 — Snapcast for every source but Lyrion.** Each player runs
`snapserver` and `snapclient`, idle until grouped. The player where the
group's source plays is the group's **leader**: its output path ends on a
loopback, its server reads the loopback, and every member's client - the
leader's own included, so all are equally late - plays into that member's
own output chain: its equaliser, its volume control, its meters. Lossless
(FLAC or plain PCM, chosen by the measurement); bit-perfect to each
member's chain.

*As amended 2026-10-28* ([Finding 139](../findings/139-snapcast-on-a-loopback-first-probe.md),
Debian's 0.31.0 on guestpi): snapserver's own ALSA source holds the
loopback's capture, which fixes the rate for the next stream, and removing
one at runtime ends the server. So the loopback is a second card of
`snd-aloop`, **Multiroom**, beside the equaliser's; the server declares one
pipe per rate (44.1 to 384 kHz, 32 bits); while something plays into the
loopback the core runs `arecord` from its capture into that rate's pipe and
moves the clients to it, and stops it when the stream ends, so the next
opens at its own rate. `output` pads every integer format to 32 bits on the
way in, as the equaliser's chain does (float refused); FLAC at 32 bits
arrived sample-identical in the probe. The chain a grouped player plays to
alone is `gexis_group_in`, which its client plays into; a card that cannot
take 32 bits is given its widest by the client (`--sampleformat *:24:*`,
padding undone exactly). The units are the player's own,
`gexis-snapserver` and `gexis-snapclient`, started by the core only;
Debian's `snapserver` and `snapclient` units, which their packages enable
and start, are masked by `gexis-system`, which ships the masks. The server
answers its control port on loopback only, serves no web page, and is kept
off the system bus, so it announces nothing on the network; the members are
given the leader's address.

**D2 — Lyrion through Lyrion.** While the group plays Lyrion, the core syncs
the members' Squeezelite players to the leader's through the Lyrion server
(`sync`, and `sync -` to undo); Snapcast is idle. A member on a different
Lyrion server cannot be in Lyrion's sync: see C3.

**D3 — The group is the players' state, kept by each.** A new `group` in
`/state` (the leader, the members, each member's reachability) and routes
to join a player, leave, and undo the group; the player that is asked tells
the others over their HTTP API, as the phone's player list does. Each keeps
the group across a restart.

**D4 — The leader moves with the source** (decision 4). A takeover on any
member - Spotify Connect, Bluetooth, Plexamp, a plugin's `acquire`, Lyrion
starting there - makes that member the leader: the others' clients move to
its server, after a short gap. The source keeps its own arbitration
(ADR-0010) on the player it plays on.

**D5 — Commands and metadata through the leader.** A member's `/state`
carries the leader's metadata and controls; a transport command on a member
is sent to the leader (ADR-0037's one route to the active renderer).

**D6 — Volume per player; the group's as a relative move.** Each player's
own control after its client (hardware or software, ADR-0018) sets its
level; Snapcast's own volume stays at 100 % so nothing is scaled twice. The
group slider moves every Variable member by the same step, as a share of
its own travel, and leaves Fixed members alone. A source's own app volume
(Spotify's slider, a volume-handing plugin) moves the group.

**D7 — The buffer as short as measured safe** (decision 7): Snapcast's
`buffer` and each client's latency set from the phase's measurement on the
test players' Wi-Fi, aiming at about a third of a second.

**D8 — A change of rate restarts the group's stream at the new rate**
(decision 8), as CamillaDSP is restarted for the equaliser (ADR-0162 C2):
the core already sees the loopback's rate change; members' clients reopen
their outputs at the new rate.

## Claude's decisions (confirmed by George, 2026-10-27)

- **C1 — A player in a group plays nothing of its own.** Grouped, the
  player's sound is the group's; leaving the group is how it plays alone.
- **C2 — The leader gone** (switched off, off the network): the members fall
  silent and stay in the group, and the next source started on any of them
  leads; the group is never undone by a player's absence alone.
- **C3 — Players on different Lyrion servers**: Lyrion cannot sync them, so
  such a group plays Lyrion through Snapcast too (not gapless across tracks,
  as Lyrion's own sync is).
- **C4 — Native DSD in a group** comes only from Lyrion: through Lyrion's
  sync, each player plays it as its Squeezelite does today. Snapcast carries
  PCM only, so where Lyrion goes through Snapcast (C3) a DSD track plays as
  PCM or not at all - which, the measurement says.
- **C5 — Grouped, the meters and the visualiser on each player show its own
  output**, as when it plays alone. (*Wording mended 2026-10-28*: it said
  "after its own equaliser"; alone, the meter reads the music before the
  equaliser, ADR-0162 D4, and grouped it does the same.)
- **C6 — The grouping is drawn in Claude Design first**: the phone's player
  list (join, leave, the group), the panel's place for it, and the grouped
  mark on Now Playing; a brief once this record is accepted.

## The design (Claude Design, 2026-10-28)

`design/source/22/` (its `README.md` is the specification). George's picks:
**1a**, Join and Remove on each row of the phone's *Gexis players*; **2a**,
the group in the panel's volume drawer and a *Group* pill and band in the
bar's tray; **3a**, the grouped mark midway between the progress bar and the
play control. Its rules, beyond the decisions above:

- The leader cannot be removed and has no *Leave*; *Undo group* ends the
  group, asks first, and keeps the music on the leader.
- The *All* slider moves every Variable member by the same step; its value
  is their mean; its mute mutes every member. Fixed members are not moved.
  (Built as D6 words it, the same share of each one's own travel: B13.)
- Joining stops a player's own music without asking, and takes it out of
  any other group (C1).
- Each member keeps its own equaliser.
- The leader gone: the others fall silent and stay grouped (C2); its panel
  shows Home.

## Claude's decisions in the build (2026-10-28, confirmed by George the same day)

- **B1 — A change reaches the members at once**, and each player puts it in
  force after, in the order the changes were made: an undo reached the
  leader 26 s late while the asker restarted its renderers (guestpi and
  bedroompi). Of two changes made at once to one group, the later wins.
- **B2 — Forming or leaving a group restarts a renderer only when one plays
  or holds the device**, and not Squeezelite playing Lyrion when its own
  chain is unchanged (one Lyrion server). So joining a player that plays
  Spotify, Bluetooth or Plexamp to a group interrupts it a moment, as the
  equaliser's switch does; a player that was idle is not touched.
  *Amended 2026-10-28, confirmed by George the same day:* the idle renderers restart
  too, without the join or the leave waiting for them - a renderer keeps the
  ALSA configuration it read first, so out of a group sofapi's
  bluealsa-aplay went on writing every Bluetooth stream into the group's
  loopback (LESSONS 84). Nothing that plays is cut by it; a phone may see
  Spotify or Plexamp leave its list of devices for a few seconds.
- **B3 — Undo keeps the music on the leader without a cut**: it plays on
  through its own server until the stream ends, then plays alone.
  *Amended 2026-10-28, confirmed by George the same day:* until nothing holds the
  device, a pause included - going alone rewrites the chain and restarts
  whoever holds it, and a source cast to sofapi just after an undo was
  restarted mid-start and lost its session. A source taking over meanwhile
  plays on through the server too.
- **B4 — Every member runs its server**, idle (about 1.5 % of a core
  measured), so a source started on any of them leads at once.
- **B5 — The buffer is 400 ms** until the measurement (D7); the manual and
  the FAQ say *about 0.4 seconds*.
- **B6 — A member's card that cannot take the stream's rate** is given its
  highest by the client's resampler, as the equaliser and Squeezelite's
  own do; one that cannot take 32 bits, its widest (padding undone exactly).
- **B7 — Lyrion's apps set each player's own volume** in a group (Lyrion's
  sync group has its own); Spotify's and a volume-handing plugin's move the
  group (D6).
- **B8 — Lyrion's sync is kept as the group is while grouped** (one
  server), so Lyrion started on any member plays on all; the leader switches
  the members' players on while Lyrion plays there. Of a sync made in a
  Lyrion app, Lyrion's master (or the first Gexis player synced) makes the
  group here; a player unsynced there leaves (the leader hands the lead on
  first).
- **B9 — A player older than multiroom** is listed without Join, its state
  followed by *Update to join*.
- **B10 — The group is not in a backup**: a restored player plays alone; a
  reflashed member, still in the others' group, is given the group again
  when it is next seen.
- **B11 — Home Assistant's unjoin of the leader undoes its group**, as the
  design gives the leader no Leave.
- **B12 — The UI's choices where the drawing is silent or production
  differs** are listed in `design/IMPLEMENTED-DIFFERENTLY.md` (*Multiroom*):
  among them, the panel's and the bar's group controls offered only when
  another player is found; *or* in the leader-gone note; the bar's progress
  row moved up when grouped; no new way to the group from Home on a member
  whose leader is off.
- **B13 — The *All* slider moves each member the same share of its own
  way**: up, of its way to 100; down, of its way to 0, so their mean lands
  where the finger is and all reach 100 and 0 together. A source's own app
  moves the others the same share as the leader moved. The design's same
  step for all had a member at 100 hold the mean below the finger, and the
  slider jumped back (sofapi at 100, the bar at 80, 2026-10-28). Each
  slider also keeps the finger's level for 1.5 s after it lets go, until
  the members' new levels have arrived.

## Settings (ADR-0022)

None proposed. The group is the players' state, not a setting; the buffer is
fixed from the measurement. If the measurement shows that no single buffer
suits every home's Wi-Fi, a setting is proposed then.

## Measured before it is called done

- The delay heard from a command, and the buffer that gives no dropout over
  an hour on the test players' Wi-Fi.
- How far apart the players are: Snapcast's own clock figures from each
  client, and George by ear in two rooms.
- What it costs a Pi 4: the leader (server and client) and a member, with
  the equaliser and the visualiser on.
- The gap at a change of rate and at a change of leader.
- Lyrion's own sync unchanged with Gexis's grouping around it.

**Where it is measured** (George, 2026-10-28): the preview goes on all four
test players (sofapi, the bar, guestpi, bedroompi), each checked free before
every test. Lyrion's half runs on a Lyrion server of Claude's in Docker on
the development machine, with the public-domain demo library; the players
used are pointed at it for the test and given their own server back after.

## Amended 2026-10-28: D7, each client's latency is what follows it

George heard sofapi and the bar apart in one group, and in time with
sofapi's equaliser off. Snapcast keeps its clients in time at the device
each one opens. On sofapi, with the equaliser on, that device is the
loopback; CamillaDSP then holds every sample for a chunk and its target
level (1024 + 1024 frames at 44.1 kHz, about 46 ms; the card's own buffer
read 1010-2001 frames), and the bar, equaliser off, plays to its card. D7
had left every client's latency to the measurement, so each was 0.

- **A client's latency is the delay after it that Snapcast cannot see**,
  worked out by the player's own core when its client starts: with the
  equaliser in the chain, two of CamillaDSP's chunks at the rate it plays
  to the card (`equaliser.latency_ms`, 43-46 ms up to 192 kHz), else 0. A
  switch of the equaliser in a group already restarts the client, which
  takes the new value then.
- **The card's own delay** - a USB adapter, an optical or HDMI receiver, a
  DAC's filters - is not read from anywhere: it stays with the measurement
  above, by ear or with a microphone, per output.

## Not in this record

- AirPlay 2 (Phase 23) and its own multiroom from Apple's devices.
- Groups of players on more than one network.
- Saved, named groups (George chose joining until undone).

## Alternatives considered

- **Gexis's sync for Lyrion too.** One mechanism, but Lyrion's apps would
  see separate players and lose its own groups; George chose to keep them.
- **Feeding the other sources into the Lyrion server** (its line-in plugins)
  and letting Lyrion sync everything. It needs a Lyrion server in every
  home, adds Lyrion's several seconds of buffer, and transcodes.
- **RTP or PulseAudio's network sink.** No clock correction between
  players: they drift apart.
- **Groups of the renderers' own** (Spotify Connect groups, Plexamp's).
  Each covers one source, and not every source has one.
