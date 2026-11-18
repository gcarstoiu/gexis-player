# Finding 154 — Gaps in a group's music: the core's own Wi-Fi read started a full scan every 43 s

**Date:** 2026-11-18. **For:** George's report (2026-11-18) that a group of
sofapi and shelvespi playing Spotify stopped for a few seconds, several
times. Read from the players' logs and the radio's own events; no network
name, address or MAC was printed or kept.

## Scope

- **Devices:** sofapi (leader, gexis-core preview 1.17.0+git49) and
  shelvespi (member, 1.17.0), both Raspberry Pi 4 Model B on Wi-Fi
  (5 GHz, power save off), NetworkManager 1.52.1, wpa_supplicant 2.10,
  Snapcast 0.31.0 with `buffer = 1000`, `chunk_ms = 26`, FLAC.
- **Read:** both players' Snapcast logs since 2026-11-12 (sofapi's journal
  begins 2026-11-17); for 100 s while the group played, `iw event` and a
  ping each way five times a second; for 95 s, the D-Bus calls that ask
  for a scan, with their callers; for 55 s, every `nmcli` run, with its
  parent.
- **Not tested:** the fix in a playing group (its preview comes next); the
  earlier groups' members, whose logs are gone; why shelvespi's scan stalls
  its traffic longer than sofapi's; a wired player; other Wi-Fi chips.

## Results

- **In the group made at 18:45, shelvespi's client dropped 20 times in 15
  minutes**, 42-44 s apart (twice 85 s, one skipped). Each time: an XRUN
  (its 1 s buffer empty), about a second later *Time sync request failed:
  Connection timed out*, then a reconnect a second after that. sofapi's own
  client, playing from 127.0.0.1, logged nothing.
- **Both players scanned every channel, 2.4 and 5 GHz, every ~43 s**, each
  scan ~3 s. During shelvespi's scans its pings to sofapi took up to 2.8 s,
  with losses; during sofapi's, up to 0.3 s. shelvespi's drops fell on its
  own scans.
- **The scans were asked for by `nmcli`, run by the core**:
  `wifi.refresh_connected()` reads `nmcli -t -f ACTIVE,SSID device wifi`
  every 20 s (`CONNECTED_EVERY_S`, since 2026-09-21) for the Wi-Fi row's
  value. nmcli's default, `--rescan auto`, rescans when the last scan is
  over 30 s old: every other read, so 2 × 20 s plus the 3 s scan.
- **The fix, checked on shelvespi:** `device wifi list --rescan no` gave the
  connected network (the same as `iw dev wlan0 link`, compared, not printed)
  and started no scan in five calls. `connected_details()` already read it
  this way.
- **NetworkManager also has a background scan** set on these players:
  wpa_supplicant's `bgscan` is `simple:30:-65:300`, every 300 s while the
  signal is above -65 dBm, every 30 s below it. sofapi read -58 dBm and
  shelvespi -61 dBm; no such scan was seen in the 100 s watched.

## After the fix (2026-11-18, muted)

George asked for a test without him by the speakers. Both players on the
fix (shelvespi core git65, sofapi git76), the group muted, a popular
directory station (128 kbps MP3) on sofapi from 20:42 for 16 minutes:

- **No scan on either player** except the one asked for at 8 minutes;
  before, one every ~43 s on each.
- **No Snapcast line at all on either player**: no XRUN, sync timeout,
  reconnect or dropped chunk; every 30 s both cards were playing.
- **The positive control did not fail**: the scan asked for on shelvespi,
  and four more after the test (two with the core's old command), took
  2.8 s each while its pings to sofapi stayed under 130 ms, nothing lost,
  nothing in Snapcast's log. At 19:15 the access point had steered
  shelvespi (*WNM: Preferred List Available*) to another one, on 5220 MHz;
  the stalls had been on 5580 MHz. **So this test shows the cause gone, not
  the gaps gone on the link that had them**: on shelvespi's link today a
  scan costs no audio. Whether it returns to that access point is the
  network's choice.

## What this means

- Reading the connected network no longer scans (branch
  `fix-wifi-no-rescan`); only the Wi-Fi sheet scans, when it is opened. On
  a grouped member that is one gap, asked for.
- A player whose signal falls below -65 dBm would still scan every 30 s, by
  NetworkManager's own choice. Whether that is heard, and whether a group's
  1 s buffer should be longer (a longer delay on pause and skip), is for
  after the fix has been listened to.
- Finding 139 left the group's gaps for the phase's measurement; this is
  the first of them measured.
