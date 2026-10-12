# Finding 119 — The final code review before the first public release: 77 confirmed defects, all addressed

**Date:** 2026-10-12. **For:** the first public release's "final thorough
code check" (George, 2026-10-12: a multi-agent review, then *"Go on with all
of them"*).

## Scope

- **What was reviewed:** the whole repository on `phase-13d` at 0.10.1 -
  the core (`core/src/gexis_core`, about 31,000 lines), the updater, the
  image stages and packaging, and the UI (`ui/src`, about 30,000 lines).
- **Method:** ten reviewers, one per area (volume and output; arbitration
  and the adapters; the core's wiring; the HTTP server; setup and network;
  updates, backups and the image; settings and content; two UI areas; and
  security across everything), each reading its area and running the test
  suite or throwaway scripts. **Every finding was then checked by a second,
  independent agent told to refute it**, end to end against the code, often
  by running it. 78 were reported; 77 were confirmed and one refuted.
- **Fixes:** six agents in separate worktrees, one per group of files, each
  writing a test that failed before its fix; merged one branch at a time
  with the full suite after each. Core changes that needed the wiring in
  `__main__.py` were made after the merges.
- **Checked on devices:** the merged core and UI installed on sofapi
  (10.1") and the bar (11.9"): both start without an error; a Lyrion level
  maps to the DAC as before (45/100 -> 204/240); every main read route
  answers; `/touch` and `/panel/shown` refuse requests from the network
  (403); a problem report prepared on the bar keeps the core answering
  within 0.35 s and takes out the weather town and coordinates.
- **Not run on a device:** the headphone-jack output (fixed and tested in
  code only - neither player uses the jack); output and volume-type switches
  after the carry-through-dB change; a factory reset; an update cut short by
  power loss; a malicious backup on a device (tested with crafted archives);
  BlueZ restarting; setup over Ethernet. Most of the core's wiring cannot run
  in the test harness and is covered by tests that read the source.

## Results

Two critical: **a crafted backup could write anywhere on the device as
root** on restore (members with `..` passed the prefix check), and **on the
Pi's headphone jack, Mute, 0 % and a source at 0 wrote 0 dB - full scale**
(the code took raw 0 for silence; the jack's range is -10239 to 400). Seven
high: levels replayed on a different scale after an output or volume-type
change; renderers the user had switched off restarted by an output change;
Bluetooth volume tracking ending after the first phone; a device name
injecting lines into configuration files; a player on Ethernet keeping the
setup network up for good; setup over Ethernet restarting before Finish;
and passwordless sudo for the user that runs the kiosk and Squeezelite.

| # | Severity | Finding | Status |
|---|---|---|---|
| updates-1 | critical | A crafted backup can write anywhere on the device as root: the prefix check lets '..' through | fixed |
| volume-main-1 | critical | On the Pi headphone jack, volume 0, the slider's 0% and Mute all write 0 dB (full scale) | fixed |
| setup-server-1 | high | A configured Ethernet player keeps the setup network up for good once its network comes back | fixed |
| setup-server-2 | high | Setup over Ethernet reboots part-way through Finish when a screen is chosen | fixed |
| setup-server-3 | high | Device name is written unescaped into an EnvironmentFile and a YAML config, so a newline injects extra lines | fixed |
| updates-2 | high | Backup restore extracts archive members containing '..' anywhere under / as root | fixed |
| volume-main-2 | high | A raw level outlives a change of scale (output switch, Software<->Hardware) and is replayed on the new scale, up to full scale | fixed |
| volume-main-3 | high | Bluetooth volume tracking stops for good after the first phone disconnects | fixed |
| volume-main-4 | high | Changing the output, the volume type or a visualiser setting restarts renderers the user switched off | fixed |
| arbitration-1 | medium | The incoming renderer's volume reports reach the DAC during the outgoing renderer's release, before the starting-volume guard is armed | fixed |
| arbitration-2 | medium | An LMS return seeks a different track to the old track's position when the user picked another track from the same queue | fixed |
| arbitration-3 | medium | A plugin that closes after `hello` but before `welcome` stays in `sessions` permanently and can never reconnect | fixed |
| arbitration-4 | medium | If LMS's release does not complete, the player stays powered on and LMS can no longer be acquired | fixed; a power-off owed while connected needs George |
| arbitration-5 | medium | Bluetooth derives the device path from the MediaTransport1 path with rsplit, which is wrong for BlueZ's `devX/sepN/fdM` layout | fixed |
| content-1 | medium | Preparing a problem report freezes the whole core (volume, arbitration, WebSocket) while the scrubber's regexes run | fixed |
| content-2 | medium | Fanart frame: an LMS outage or a missing plugin is recorded as 'this artist has no photos' for good | fixed; clearing existing empty answers needs George |
| content-3 | medium | One unreachable NFS share stops every share after it from mounting | fixed |
| content-4 | medium | Artist photo URLs are persisted with the LMS host baked in and are never invalidated | fixed; LMS answers after a rescan need George |
| content-5 | medium | The problem-report scrubber misses the geocoded town and artist names logged without quotes; they reach the zip and the public GitHub issue URL | fixed |
| deferred-1 | medium | Passwordless sudo for pi makes every pi-run, network-facing service root-equivalent | fixed (ADR-0139) |
| setup-server-4 | medium | GET /settings stats every network-share mount point on the event loop, so a NAS that is switched off can freeze the whole core | fixed |
| setup-server-5 | medium | Screen stays dark with no way to wake it if the core restarts during standby | fixed |
| setup-server-6 | medium | A failed Wi-Fi join during Ethernet setup opens the setup network with no retry, and Finish without Wi-Fi is then refused | fixed |
| setup-server-7 | medium | A Bluetooth pairing request is invisible while the screen is in standby and expires | fixed |
| setup-server-8 | medium | Some device names break go-librespot's YAML config, and a backslash crashes the rename | fixed |
| setup-server-9 | medium | A backslash in the device name raises re.error, so the rename half-applies and the request fails with a 500 | fixed |
| ui-1 | medium | Panel stays locked on 'Updating… Don't switch off' for ever when the updater stops without writing done or failed | fixed |
| ui-2 | medium | Setup's last page on the phone gives the backup's name and address, not the name the player restarts with | fixed |
| ui-3 | medium | Phone's update modal compares the player's clock with the phone's clock, so a lagging player clock reads as 'did not answer' | fixed |
| ui-4 | medium | Bar strip: lifting the screen away mid-pull leaves pull.offset set, and a full-screen scrim then blocks every touch until the page reloads | fixed |
| updates-3 | medium | An install cut short by a power loss is never repaired or rolled back unless a newer release is installed by hand | fixed |
| updates-4 | medium | publish.sh resets the channel serial to 1 when fetching the published channel file fails for any reason | fixed |
| updates-5 | medium | An empty serial file left by a power cut breaks every update check permanently | fixed |
| updates-6 | medium | The updater's private apt cache and the update backups are never pruned, so the card slowly fills | cache fixed; pruning update backups needs George |
| updates-7 | medium | A backup copies, and a restore overwrites, live SQLite WAL databases such as the Beszel hub's while their service runs | fixed |
| volume-main-10 | medium | A plugin's `queue` event is stored as a raw list, so the next broadcast crashes and the takeover stops before the outgoing renderer is released | fixed |
| volume-main-11 | medium | An adapter's watch task that dies is never restarted or logged; LMS and Spotify catch only narrow exception types | fixed |
| volume-main-12 | medium | Software volume: renderers start before the core sets the software level, so after a power cut LMS can resume at 0 dB | open - needs George (boot ordering of the software level) |
| volume-main-13 | medium | Leaving Fixed after Software→Fixed writes a software-scale raw value to the card, up to full scale | fixed |
| volume-main-14 | medium | Fixed→Software on a player that never used Software sets the software stage to 0 dB | fixed |
| volume-main-15 | medium | Fixed's full-scale write goes to the start-up control name, not the current output's | fixed |
| volume-main-16 | medium | Source switches (lms/spotify/bt_enabled) are not serialised; a quick off→on can leave the source stopped or the radio off under a switch that says on | fixed |
| volume-main-17 | medium | An output change leaves a plugin renderer (Plexamp) playing to the old card while volume moves to the new one | fixed |
| volume-main-5 | medium | write_hardware raises CancelledError into its caller when a newer write supersedes it before its ramp starts | fixed |
| volume-main-6 | medium | The max_ceiling backstop in _capped converts a percentage as if it were dB, so it never caps | fixed |
| volume-main-7 | medium | Entering Fixed writes full scale to `config.mixer_name`, which is stale after an output or Software switch, so Fixed is not at full scale | fixed |
| volume-main-8 | medium | Monitor restarts recurse (`return await self.run()`), so a missing card crashes the daemon after about 80 minutes | fixed |
| volume-main-9 | medium | get_raw cannot read a mono control, so the headphone jack's level is never read or monitored | fixed |
| arbitration-6 | low | A plugin line over 64 KiB disconnects the plugin, although MAX_LINE allows 1 MiB | fixed |
| arbitration-7 | low | A plugin that sends `acquire` right after `hello`, without waiting for `welcome`, loses the acquisition | fixed |
| arbitration-8 | low | After go-librespot restarts mid-play, the core keeps Spotify active with stale metadata | fixed |
| content-10 | low | Covers sweep stores 'no cover' for every album of an artist when the MusicBrainz release-group lookup fails | fixed |
| content-11 | low | enrichment.db grows without bound | expired 'nothing found' answers pruned; size limit needs George |
| content-12 | low | A flash-time seed for output_device or skin is always rejected | fixed |
| content-13 | low | Share address beginning with '-' is passed to mount as an option | fixed |
| content-6 | low | The USB-seen record is rewritten non-atomically every 20 s; a truncated file makes Lyrion wipe and rescan the whole library | fixed |
| content-7 | low | PeppyMeter's config is rewritten in place, so a power cut can leave it truncated for good | fixed |
| content-8 | low | Raising or lowering the visualiser blocks the asyncio loop (a 0.25 s sleep plus a wlrctl call of up to 5 s) | fixed |
| content-9 | low | Browsing an unresponsive SMB/NFS server's shares returns HTTP 500 instead of a message | fixed |
| setup-server-10 | low | An address change can slip past the 'another change is waiting' check, and the automatic revert then goes back to the wrong address | fixed |
| setup-server-11 | low | Asking for the visualiser again while a restart is in progress restarts it again and kills the half-loaded one | fixed |
| setup-server-12 | low | Several POST routes answer 500 for a wrongly typed body or a failure they do not expect | fixed |
| setup-server-13 | low | Any phone on the setup network stops the player rejoining its home Wi-Fi, even one that only auto-joined | open - needs George (a phone on the setup network) |
| setup-server-14 | low | cmdline.txt is rewritten in place, so a power cut can leave it empty and the player unbootable | fixed |
| setup-server-15 | low | The pairing agent is not registered again after bluetoothd restarts | fixed |
| ui-10 | low | Library: a double tap, or Back while an artist is loading, pushes extra or stale history entries | fixed |
| ui-11 | low | Queue rail rebuilds the whole queue on every state frame, including volume-only frames | fixed |
| ui-5 | low | Settings are not re-read after a core restart when the new settings_revision equals the last one seen | fixed |
| ui-6 | low | Network-level failures leave Settings spinners and progress cards with no way to finish | fixed |
| ui-7 | low | A phone whose /surface request fails renders and behaves as the panel | fixed |
| ui-8 | low | Phone mini-player volume slider sets the level on first contact, so a scroll that starts on it jumps the volume | fixed |
| ui-9 | low | Volume drawer opened by a phone change takes a panel touch meant for the screen underneath and sets the level at that point | fixed |
| updates-10 | low | Factory reset deletes the backups share directory itself, and it comes back root-owned so the share cannot be written | fixed |
| updates-11 | low | A step marked 'TEMPORARY - remove before the first public release' is still in the factory reset | fixed |
| updates-8 | low | Factory reset leaves the kiosk browser profile and the provisioned idle URL behind | kiosk profile fixed; flash-time settings need George |
| updates-9 | low | 'Check for updates' runs without the apt-turn lock and overwrites status.json during an install | fixed |
| volume-main-18 | low | No playback output at start-up crashes the daemon (NameError meters_available) | fixed |

**Open, for George:** the boot order of the software volume (a power cut in
Software mode can play the first second at the software stage's 0 dB before
the saved level is set - fixing it needs a boot step and an ADR), and how
long a phone merely connected to the setup network may keep the player from
rejoining its home Wi-Fi.

## Run on a device afterwards (2026-10-12, the bar, 0.10.1+git122 preview)

George allowed device tests (*"You can test. As much as possibly independent
of me"*). Driven through the player's own API, the mixer controls read over SSH
after each step; nothing played; the bar put back exactly as found (Hardware,
DAC at -18 dB).

- **The headphone jack (critical, volume-main-1): fixed on the device.** Output
  to *Headphones (3.5 mm)*: 0 % wrote -10239 (silence, where it had written
  0 dB); Mute wrote -10239; unmute put back -20.23 dB.
- **Levels carried through dB across an output change** (volume-main-2): DAC
  at -20.00 dB -> jack -20.00 dB -> DAC -20.00 dB.
- **Volume types** Hardware -> Software -> Fixed -> Hardware -> Fixed ->
  Software -> Hardware: the level kept at -20 dB throughout; Fixed sets the DAC
  to full scale and takes the software stage out of the chain (read in
  `output.conf`); leaving Fixed puts back the level before it.
- **The boot step in Software (ADR-0140)**: across a reboot, the software
  level (-20 dB) was written at boot +0.8 s before bluealsa-aplay, +8.6 s
  before go-librespot, +10.4 s before squeezelite and the core.
- **Not run:** an update cut short by a power cut (an immediate reboot during
  an install was refused by Claude's command safety check as destructive; it
  needs George's go-ahead or his hand), and a factory reset (it also needs a
  phone on the setup network afterwards).
