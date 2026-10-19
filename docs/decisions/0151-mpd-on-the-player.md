# ADR-0151 — MPD on the player

**Status:** **Proposed** — 2026-10-19. Phase 15 (`ph-mpd`). Decisions
recorded below as George takes them; open points at the end. Nothing is built
until it is accepted.

## Context

Lyrion's player, Squeezelite, carries two channels (Finding 121), so a 5.1 or
7.1 file reaches a receiver folded down to stereo (ADR-0145). The Pi's HDMI
takes 2 to 8 channels of PCM, and the receiver on the bench takes 8 (Finding
121). MPD decodes up to 8 channels in ALSA's order and DSD natively; it plays
on the machine it runs on, so it would run on the player, with its own
library or as a satellite of a central MPD that holds the database
(`docs/DEVELOPMENT.md`, Phase 15).

## Decided by George (2026-10-19)

1. **Both ways of holding the library**: MPD's own library on the player,
   and a satellite of a central MPD on the network.
2. **Both libraries on one player, one navigated on the panel at a time.**
   MPD sits beside the Lyrion server; the panel browses one of them at any
   moment. With MPD chosen, the panel's navigation is today's simple one,
   without Radio.
3. **Multichannel over HDMI to an AV receiver only**, measured as Finding 121
   measured stereo; USB multichannel DACs stay untested.
4. **Software volume on every channel alike; the meters show front left and
   right.**
5. **DSD**: native to a DSD DAC for stereo; multichannel DSD as PCM over HDMI
   (the Pi sends no one-bit audio over HDMI).
6. **First use**: MPD an answer to *How will you listen?*, its music on
   *Where is your music?*, as the Lyrion server's are (ADR-0149) - open to
   change as the discussion goes on.
7. **Its own entry in Settings → Library** (ADR-0150), beside the Lyrion
   server.
8. **Its own music locations**, separate from the Lyrion server's (George:
   *"separate just so as not to mix and complicate matters"*).

## Measured since (Finding 128, 2026-10-19)

George asked for a smaller phase (*"It's too much work and the benefit is
questionable"*). Idea 2 was tested: Lyrion's library and apps playing to MPD
through Lyrion's *UPnP/DLNA bridge* and upmpdcli. 5.1 and 7.1 FLAC and a 5.1
WAV reached the receiver as 6 and 8 channels, and 5.1 DSD as 6. It needs the
bridge in pass-through mode with DSD among its formats (by default it keeps
two channels and refuses DSD), and the centre and LFE channels swapped before
the HDMI port - checked by ear on a 5.1 system.

## Open

- How apps control MPD: MPD clients, UPnP/OpenHome through upmpdcli, or both;
  and upmpdcli's streaming plugins (George asked about TIDAL and Qobuz).
- Where the choice of the library the panel browses lives, and its name.
- New files on network shares: inotify does not see changes made on a NAS
  (to be verified), so shares need scheduled rescans.
- A multichannel file with a stereo output chosen: folded as ADR-0145 does
  for Lyrion.
- The satellite: what the central MPD must offer (its music at the same
  paths), and how it is found.
- Proposed settings for ADR-0022's inventory, appended once George confirms.
