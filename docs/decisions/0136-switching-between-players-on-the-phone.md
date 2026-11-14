# ADR-0136 — Switching between players on the phone

**Status:** **Accepted** — George, 2026-10-11: *"The switcher on the phone we
can do now. Simple switch with status and renderer connected."*
**Amended** 2026-11-14 (George): every list of players in alphabetical order,
a list asks for a fresh answer when it opens, and a player reached only
through another is listed through it (below).

## Context

Each player serves its own phone page at its own address
(`name.local:8090`). A browser keeps each address apart, so with two players
on one network the owner keeps two tabs open. Players already resolve by name
over mDNS (avahi), and avahi already advertises each player's share
(ADR-0049 §4).

## Decision

1. **Each player announces itself**: `_gexis._tcp` on port 8090, an avahi
   service file in `gexis-system`, beside the share's.
2. **Each core finds the others** with `avahi-browse` (installed with avahi),
   every 30 s at most, and asks each for `GET /player/status`: its name,
   address, whether it plays, and the renderer connected. The phone reads
   `GET /players` from the player it is on; the core asks the others, so the
   browser never reaches across addresses.
3. **On the phone, a switch button at the right end of the *Settings*
   line** (amended the same day, George: larger, in line with the title;
   first drawn as the line under it) when another player is found. It opens a list of every player,
   this one marked, each with its status - *Playing · Spotify*, *Paused ·
   Lyrion*, *Idle* - and choosing another opens that player's page **in the
   same tab**.
4. **The panel has no switcher**: a panel belongs to its own player.

## Consequences

- A home-screen bookmark still opens the player it was made on; the switcher
  moves on from there.
- A player that is off, or on another network, is simply not listed.
- Players older than this release announce nothing and are not listed until
  updated.

## Built (2026-10-11, on `phase-13d`)

As decided. Tried on sofapi and the bar player, both on the preview: each
lists the other with its status (*Stopped · Lyrion*), and the phone's list
opens from the header line.

## Amended 2026-11-14: alphabetical, and fresh when opened

George, 2026-11-14, after bedroompi's menu showed a group he had undone on
sofapi a minute before, and the menu's order changed with the player it was
opened on:

1. **Every list of players is in alphabetical order** - the phone's menu
   (ADR-0164), the panel's *Add players*, the bar's band (ADR-0166) and the
   switcher - so a player keeps its place whichever player a list is opened
   on. This player sits in its place with its check, not first.
2. **A group's players stay together**, alphabetical within it, the leader
   tagged where it falls, and **the group goes where its first player
   falls** (George chose this over groups at the top). Names in a sentence
   (*with Kitchen, Study*, *Undo group*'s) follow the same order, and so do
   the group volume's members on the panel, the bar and the phone (George,
   the same evening: the leader changes whenever another player starts
   music, and a leader-first list reshuffled with it).
3. **A list opening asks `/players?fresh=1`**: if what the player found is
   older than 5 s, it asks the players already found for their status again,
   without the network search (up to 5 s); the list kept on the phone shows
   meanwhile. The background search every 30 s is unchanged.
4. **A group change is told to every player** (George, the same evening,
   after the bar's list still showed a group undone on sofapi: the bar ran
   1.16.2, without item 3). When what a player says of its group changes,
   it tells every player found (`POST /players/changed`); each asks the
   others again 0.3 s later and its open lists read `/players` again. A
   player older than this answers 404 and waits for its next look.
5. **A player reached only through another is listed through it** (George,
   the same evening, choosing this over leaving it out or listing it without
   a word: bedroompi and guestpi could not reach each other on the home
   network, while each reached the other two and the phone reached all
   four). When a player the search found does not answer, the core asks the
   players that did for their own lists (`GET /players`) and adds each
   player one of them reached directly and it did not, with `via` naming the
   player it came through - one hop: never one that player had itself
   through a third. Its row shows its status and opens its page like any
   other, as the phone reaches it itself. It cannot be grouped from here -
   a group's music goes straight from its leader to each member - so it has
   no Join, its status ends *Can't group from here* as one older than
   multiroom ends *Update to join*, and a group it leads has no *Join this
   group*. A group change is not told to it, and a group does not follow
   it. Everything else is as before when every player found answers.

Items 1-4 built on `fix-players-order`, checked with invented players on the phone,
the panel and the bar, and the manual's three group pictures retaken with the
demo library (the switcher, reached only on a narrow standalone Settings, not
seen).

Item 5 built on `fix-players-order` the same evening: checked with invented
players on the phone (at 390 and 320 px), the panel and the bar; on the four
players, bedroompi and guestpi each list the other through ShelvesPi, the
other two list all three directly. Found there and fixed: after its core
restarted, bedroompi listed itself through ShelvesPi for one look, as
ShelvesPi's list still held its status from before the restart; the check
for this player now also takes the board's id and the player's name. On
either of the two, a list opening waits 2 s, up to 4 s behind a background
look, for its fresh answer; the kept list shows meanwhile.
