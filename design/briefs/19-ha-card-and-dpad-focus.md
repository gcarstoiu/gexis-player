# Brief for Claude Design — A card for Home Assistant, and the D-pad's focus (Phase 19)

Written 2026-10-25 for George to hand to Claude Design. Background, if you
want it: [ADR-0160](../../docs/decisions/0160-the-player-in-home-assistant.md)
(the player in Home Assistant, with George's findings after trying it) and
[ADR-0161](../../docs/decisions/0161-a-d-pad-on-the-panel.md) (the D-pad,
proposed). What is built and differs from the earlier designs is in
[`IMPLEMENTED-DIFFERENTLY.md`](../IMPLEMENTED-DIFFERENTLY.md). Whether the
card follows Home Assistant's look (as below) or the player's is settled in
the design (George, 2026-10-25).

---

**Gexis Player** is a music player for the Raspberry Pi 4. It usually has its
own touchscreen (the "panel": 7" to 13.3", most often a 10.1" 1280 x 800, or a
wide *bar*, 11.9" 1480 x 320 or 7.9" 1280 x 400), and every player has a phone
page. It plays from a **Lyrion Music Server** and is also a **Spotify
Connect** speaker, a **Plexamp** player and a **Bluetooth** speaker. In Home
Assistant each player is a media player, with switches for its screen, the
dashboard and the visualiser, and buttons for Home, Now playing and Lyrics.

Two additions to the design. Please use the existing design (its tokens, type
and components) and export as before: the artboard HTML/CSS, a PNG per state,
new tokens as CSS custom properties, and component boundaries.

## 1. A Gexis Player card for Home Assistant dashboards

A card a Home Assistant user adds to a dashboard to see and control their
Gexis players. It holds:
- **A switcher between players**: the player shown, and a way to change to
  any other Gexis player in the home, each listed with its state as on the
  phone's switcher (*Playing · Spotify*, *Paused · Lyrion*, *Idle*). Hidden
  when there is only one player.
- **What plays**: artwork, title, artist, album, the source (Lyrion, Spotify,
  Bluetooth, Plexamp), and the position in the track.
- **Transport**: previous, play/pause, next; shuffle and repeat where the
  source has them.
- **Volume and mute.**
- **A D-pad** for the player's screen: up, down, left, right, OK in the
  middle, and Back.
- **Quick actions** for the player's screen: Home, Now playing, Lyrics.

It sits among Home Assistant's own cards, so it follows Home Assistant's theme
in light and dark (card background, corner radius, fonts, primary colour),
with Gexis touches where they help.

**Sizes:** a phone (about 360-430 px wide), one dashboard column (about
300-500 px), and a wall tablet. A compact form, with the D-pad hidden until
asked for, and a full one.

**States:**
- playing; paused;
- nothing playing: no track, Now playing and Lyrics greyed out;
- a player without a screen: no D-pad, no quick actions;
- a fixed output: no volume (it is set on the amplifier);
- a source with fewer controls: no shuffle or repeat, or no transport at all;
- the player unreachable;
- long titles; no artwork;
- the switcher open, with three players.

## 2. How the focus looks on the player's screen

The player's screen can now be driven with a D-pad (from Home Assistant, a
keyboard, later a TV remote). The control the D-pad is on needs a look of its
own. It appears at the first key press, a touch hides it, and it moves to the
next control in the direction pressed.

It must:
- be seen from across the room, about 3 m away;
- read on every background: the wallpapers, colours taken from the artwork,
  light and dark areas;
- work on the 320 px-tall bar displays as well as the standard screens;
- not move or resize anything around it.

**Show it on:** a Home tile (Simple navigation, and Lyrion's own menu tiles in
Extended navigation); a library row and an album in a grid; Now Playing's
play/pause, its volume button and its Lyrics tab; a Settings row, a toggle,
and a slider, both focused and while Left and Right change its value; a
button in a sheet; the volume drawer; on the bar, the rail, a tray button and
a library tile. Also how it travels from one control to the next, if it
moves rather than jumps.

**Sizes:** 1280 x 800 for the standard screens; 1480 x 320 and 1280 x 400 for
the bars.
