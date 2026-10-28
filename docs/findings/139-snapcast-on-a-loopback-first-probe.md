# Finding 139 — Snapcast on a loopback: the first probe

**Date:** 2026-10-28. **For:** Phase 22 (`ph-multiroom`): ADR-0166's
technical decisions are confirmed or changed by the phase's measurement.
This is its first, silent part: how Debian's Snapcast behaves on a loopback,
before any of it is built.

## Scope

- **Device:** guestpi (Pi 4), gexis-player 1.7.0, nothing playing, the
  equaliser off. Debian trixie's `snapserver` and `snapclient` 0.31.0-1
  (arm64), the binaries unpacked from the packages and run from `/tmp`, not
  installed; every library they need was already on the player.
- **Silent:** `snd-aloop` loaded for the test with two cards
  (`enable=1,1 id=Loopback,Group pcm_substreams=1,1`) and unloaded after (it
  was not loaded before: the player had been updated to 1.7.0 without a
  restart). Test signals went into `hw:Group,0,0` with `aplay`; the client
  played to a file, or to the other loopback. Nothing reached a card.
- **Signals:** a 440 Hz sine (S16_LE), and for the comparison a random
  signal of 32-bit samples below 2^27 in magnitude (S32_LE), at 44.1 and
  96 kHz; the client's output found in it by a 64-byte run and compared
  frame by frame.
- **One client, on the same player**, over loopback TCP: the network, the
  clock between two players and any delay heard are not measured here.
- **Not tested:** a real card; two players; Wi-Fi; the cost to the CPU;
  how long a client takes to follow a server that moves; any renderer but
  `aplay`; an hour of play (the client's corrections over time).

## Results

1. **snapserver's ALSA source keeps the capture open, and a loopback's
   capture fixes the rate for the next playback.** With the stream at
   44.1 kHz, a 48 kHz `aplay` was given 44.1 kHz (*rate is not accurate*):
   a renderer that takes the rate it is given plays at the wrong speed. The
   capture must be closed while nothing plays, as CamillaDSP's
   `stop_on_inactive` does for the equaliser.
2. **Removing an ALSA stream crashes the server.** `Stream.RemoveStream` on
   an `alsa://` stream ended snapserver at once
   (`snd_pcm_avail: Assertion 'pcm' failed`). Adding one at runtime worked.
3. **Process streams cannot be added at runtime** (*Adding 'process'
   streams is not allowed*).
4. **Pipe streams work, declared at start, one per rate.** With a pipe per
   rate in the configuration (`mode=create`), `arecord` from the loopback's
   capture into the pipe while something plays, and `Group.SetStream` to
   move the client, both rates played; stopping `arecord` closed the
   capture, and the next rate opened free.
5. **The samples arrive unchanged.** Through FLAC at 32 bits: at 96 kHz
   all 384,000 frames identical; at 44.1 kHz all but one block of 339
   frames (7.7 ms) 36 ms before the end, where the stream was cut. No frame
   was inserted or dropped in 4 s.
6. **The client closes its card after 5 s without audio** (*No chunk
   received for 5000ms. Closing ALSA*), and opens it again for the next.
7. **The server announces itself on the network** (Avahi, *Snapcast*), and
   no option turns that off.
8. **The packages enable and start their own units on install** (their
   postinst: `deb-systemd-helper enable`, then `deb-systemd-invoke start`);
   the client then plays to ALSA's `default`, which is the player's
   `output`.

## What it changes

ADR-0166 D1 as amended 2026-10-28: the server reads pipes, one per rate,
fed by `arecord` while the loopback plays; the units are the player's own,
Debian's masked; the server kept off the system bus so it announces
nothing. The bit-perfect claim holds in steady play; the client's
corrections over an hour are for the phase's measurement.
