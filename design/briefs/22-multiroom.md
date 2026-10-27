# Brief for Claude Design — Multiroom (Phase 22)

Written 2026-10-27 for George to hand to Claude Design. Background, if you
want it: [ADR-0166](../../docs/decisions/0166-multiroom-for-every-source.md)
(multiroom, George's decisions of 2026-10-27). What is built and differs from
the earlier designs is in
[`IMPLEMENTED-DIFFERENTLY.md`](../IMPLEMENTED-DIFFERENTLY.md).

---

**Gexis Player** is a music player for the Raspberry Pi 4. It usually has its
own touchscreen (the "panel": 7" to 13.3", most often a 10.1" 1280 x 800, or a
wide *bar*, 11.9" 1480 x 320 or 7.9" 1280 x 400), and every player has a phone
remote (your *Phone Remote v3*, built as drawn). It plays from a **Lyrion
Music Server** and is also a **Spotify Connect** speaker, a **Plexamp**
player, a **Bluetooth** speaker, and whatever source plugins add. A home can
have several players.

Please use the existing design (its tokens, type and components: the phone
remote's player menu and volume row, the panel's Now Playing and volume
drawer, the bar's tray) and export as before: the artboard HTML/CSS, a PNG
per state, new tokens as CSS custom properties, and component boundaries.

## What multiroom is

- **Several players play the same music in sync**, whatever the source.
- **A group is made by joining players to one**, and lasts until it is
  undone, a restart included. There are no saved or named groups.
- **The whole group follows the music**: music started on any player of the
  group plays on all of them, and that player leads.
- **A grouped player plays nothing of its own**: to play alone, it leaves the
  group.
- **Volume**: each player keeps its own level, and a group slider moves them
  all together, keeping their balance. A player on *Fixed* volume (an
  amplifier sets its level) stays fixed.
- **Every player of the group shows the group's Now Playing**, and play,
  pause, skip and the group volume work from any of them.
- **A command in a group is heard a moment later** (about a third of a
  second).
- **The leading player gone** (switched off): the others fall silent and stay
  grouped, until music starts on one of them.

## 1. The phone: the player list

The remote's player picker opens *Gexis players*, which today switches to
another player's remote. It needs:
- joining another player to this one's group, and taking it out; leaving the
  group; undoing the whole group;
- the group at a glance in the picker itself (which players, what plays);
- each player's state in the list: in this group, in another group, playing
  alone, idle, unreachable.

## 2. The panel and the bars

The panel has no player list today. Where grouping lives on the panel
(1280 x 800 and its family) and on the bars (1480 x 320, 1280 x 400, laid
out at 1850 x 400 CSS px, drawn at 0.8) is yours to propose - from Now
Playing, the volume drawer or Home - with the same actions as the phone.

## 3. Grouped, everywhere

- **The grouped mark** on Now Playing (the panel, the bars, the phone
  remote): the other players named (*with Kitchen, Study*).
- **The group volume** in the panel's volume drawer, the bar's tray and the
  phone's volume row: the group slider and each player's own, a Fixed
  player's as the locked row.

## States

- Not grouped; the list with other players playing, idle, unreachable, or in
  another group.
- Grouped, seen from the leading player and from another member.
- A player joining (it catches up for a moment), leaving, the group undone.
- The leading player gone: members silent, still grouped.
- A Fixed-volume player in the group volume; a player without a screen in
  the group (the phone only).
- A group of two, and of five or more with long names.
- Lyrion and the other sources look the same in a group.

Not needed: saved or named groups; the Home Assistant card, which follows
the phone in the integration's next release.
