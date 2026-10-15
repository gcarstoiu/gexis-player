# Finding 126 — The bar's screen jams the setup network on channel 6

**Date:** 2026-10-15. **With:** George, on the 11.9" bar's Pi (a Pi 4 Rev 1.4,
running test cards as "bedroompi"), sofapi (Rev 1.5, the 10.1" panel) and
R2D2 as a second receiver.

## The failure

On 0.15.0 and 1.0.0 cards in the bar's Pi, **gexis-setup could not be joined**:
after the cable was pulled (ADR-0134's fallback), and on a fresh 1.0.0 card's
first start. The phone saw the network come and go and could not connect
("Saved / Connection failure", "Can't connect"). The core logged the network
open, WPA2 only, on channel 6 (`key_mgmt WPA-PSK WPA-PSK-SHA256`,
`ieee80211w 0`), and nothing from the phone ever reached it. 1.0.0 was pulled
from Stable for it the same night. George had set this Pi up through its setup
network several times before, in the same place.

## What it was

**The HDMI link to the bar's panel radiates at multiples of its pixel clock**,
read from the panel's EDID (first detailed timing):

| Screen | Pixel clock | Nearest multiple to channel 1 / 6 / 11 |
|---|---|---|
| 11.9" bar, 1480 x 320 | 59.40 MHz | 23.4 / **1.6** / 26.6 MHz away |
| 10.1" panel (sofapi), 1280 x 800 | 77.00 MHz | 25.0 / 27.0 / **2.0** MHz away |
| A TV at 1280 x 720 | 74.25 MHz | 36.0 / 13.2 / 11.8 MHz away |

The bar's 41st multiple, 2435.4 MHz, sits 1.6 MHz from channel 6's 2437 MHz.

## How it was shown (George's phone, the same `nmcli` hotspot each time)

| Pi | Display | Channel | Phone |
|---|---|---|---|
| sofapi | on | 6 | joined in 20 s, page opened |
| bar | on | 6 | network seen on and off; "connecting", then gone |
| bar | **off** | 6 | joined in 29 s |
| bar | on | **1** | joined in 29 s |
| bar, setup's own network with the fix (channel 11 chosen) | on | 11 | joined (George) |

## Measured again, 2026-10-15 morning

The same Pi and panel through the adapter fitted the night before (the
earlier adapter no longer gives a picture), on the cable; R2D2 about 3 m
away joining a `gexis-setup` hotspot set up as the player's (WPA2, PMF off),
two tries of 25 s per run, then 300 pings of 1,200 bytes:

| Run | Channel | Display | Join | Ping loss | Average delay |
|---|---|---|---|---|---|
| 1 | 6 | on | failed twice; the Pi never saw a station | - | - |
| 2 | 1 | on | 3.4 s | 0 % | 12.4 ms |
| 3 | 11 | on | 8.3 s | 0 % | 4.6 ms |
| 4 | 6 | **off** | 8.1 s | 0 % | 4.4 ms |
| 5 | 6 | on | failed twice; the Pi never saw a station | - | - |

The PC heard the Pi on every run (signal -37 to -41 dBm); on channel 6
with the display on, the Pi never heard the PC. Channel 6 failed twice in
two, with other runs between, and worked the moment the display was off.

**Why it worked before.** Not the software: the setup network has been
`gexis-setup` since 2026-09-28, and NetworkManager (1.52.1,
`ensure_hotspot_frequency`) takes a hotspot's channel from a fixed hash of
its name - for `gexis-setup` the order is 6, 11, 13, 1, and 6 is always
allowed - so every earlier setup was on channel 6 too. The bar runs the
panel's own mode (320 x 1480, 59.4 MHz) as it has since 2026-10-01. The
change was physical; the adapter swapped that night is the one known, and
the old one can no longer be tested.

## sofapi, the same test (2026-10-15 morning)

sofapi on Wi-Fi only (its side timed, the core stopped meanwhile), R2D2
6-7 m away; the panel at 77.0 MHz, whose multiple is 2 MHz from channel 11;
a second port on throughout, at 640 x 480 (25.2 MHz, a multiple 5.3-5.6 MHz
from each of channels 1, 6 and 11 alike):

| Run | Channel | Panel | Join | Ping loss | Average delay | PC retries / packets |
|---|---|---|---|---|---|---|
| 1 | 11 | on | failed twice | - | - | - |
| 2 | 6 | on | 9.2 s | 6.3 % | 215 ms | 1,313 / 671 |
| 3 | 1 | on | failed twice | - | - | - |
| 4 | 11 | **off** | 3.6 s | 0.3 % | 23 ms | 348 / 533 |
| 5 | 11 | on | failed twice (the Pi saw a station associate; the join never completed) | - | - | - |

- **The panel is the cause on a second device**: channel 11 failed twice in
  two with it on, and joined in 3.6 s with it off.
- **The rule chose the working channel on both devices** (11 on the bar, 6
  on sofapi), **but its model is too simple**: channel 1, 25 MHz from any
  multiple of sofapi's panel, failed as well, and 6 worked only poorly. The
  interference is broader than the multiples; at this distance (signal
  -61 to -64 dBm, against -37 to -41 at 3 m) there is little margin left on
  any channel with the panel on.

Not separated: the second port's share; distance against channel; one run
per channel except 11.

## Software or the HDMI signal? Separated (2026-10-15, 09:09-09:23)

George held that this was something we introduced. Three read-only reviews
(our history v0.14.0 -> v1.0.1, public reports, and how Volumio, moOde,
piCorePlayer, comitup, wifi-connect and RaspiWiFi run their setup networks)
found no software change that fits: kernel, Wi-Fi and Bluetooth firmware,
NetworkManager, wpa_supplicant, regulatory database, `config.txt` and
`cmdline.txt` are the same from the 0.9.1 image to 1.0.1; the only radio
change in the window is Wi-Fi power saving forced off (3ca9185d, first in
0.15.0), which NetworkManager does not apply to an access point anyway. The
others' setup networks use a fixed channel or NetworkManager's hash, none
looks at the screen. Public reports of the same symptom with screens sold
for the Pi exist (a Waveshare 7" HDMI (C): "can identify the SSID, but
cannot connect"; a Pi access point whose devices "do not connect with
channel 3 when screen is on"); none names these two panels.

Then the bar on the cable, R2D2 3 m away as before, one thing changed per
run:

| Run | Channel | Changed | Join |
|---|---|---|---|
| 1 | 6 | nothing | failed |
| 2 | 6 | power saving on (as before 0.15.0) | failed |
| 3 | 6 | kiosk stopped: no compositor, browser or GPU work; the HDMI link still at 59.4 MHz | failed |
| 4 | 6 | panel off, all four cores busy | joined, 6.7 s, 0 % loss |
| 5 | 6 | Bluetooth off | failed |
| 6 | 6 | **only the HDMI clock changed**: 320 x 1480 at 54 Hz, 35.5 MHz | **joined, 3.4 s, 0 % loss** |
| 7 | 1 | the same 35.5 MHz | joined, 3.5 s |
| 8 | 1 | nothing | joined, 11.1 s |
| 9 | 6 | panel off | joined, 3.5 s |
| 10 | 6 | power saving on | failed |
| 11 | 6 | nothing | failed |

**The cause is the HDMI signal at 59.4 MHz.** With the same software,
content, load, Bluetooth and power saving, moving the clock from 59.4 to
35.5 MHz alone made channel 6 work; stopping all software drawing to the
screen, with the link still at 59.4 MHz, did not. CPU load with the panel
off did not break it; power saving and Bluetooth made no difference.

Not as predicted: at 35.5 MHz channel 1 still joined, although a multiple
(2414 MHz, the 68th) is 2 MHz from it - a higher multiple, presumably
weaker. Whether the panel shows a picture at 54 Hz was not looked at.

## sofapi with its second port off (2026-10-15, 09:33-09:39)

The same set-up as sofapi's first test (R2D2 6-7 m away, signal -62 to
-66 dBm):

| Run | Channel | Second port | Join | Ping loss | Average delay |
|---|---|---|---|---|---|
| 1 | 1 | off | 22.2 s | **81 %** | 5,146 ms |
| 2 | 11 | off | failed twice | - | - |
| 3 | 6 | off | 14.0 s | 0 % | 133 ms (438 retries / 465 packets) |
| 4 | 1 | on | failed twice | - | - |
| 5 | 1 | off | failed twice | - | - |

- Channel 11 fails with the panel on, the second port off: the panel's own
  multiple, as predicted.
- **Channel 1 is bad on sofapi with or without the second port**, although
  25 MHz from the panel's multiples: one join in two, and that one unusable.
  The second port does not explain it. What the bar's Pi heard on channel 1
  the same morning: four neighbouring networks at -56 to -70 dBm, against one
  each on 6, 11 and 13 (-74 to -79). Crowding plus a weak link at this
  distance is the likelier reason; not separated (no panel-off run on
  channel 1 here).
- At this distance only channel 6 joined reliably, and slowly.

So the pixel-clock rule avoids the screen's channel, but it knows nothing of
neighbours: on sofapi it would choose 6, the only usable channel here, by
luck as much as by design.

## A cable instead of the adapter (2026-10-15, 10:13-10:20)

George replaced the bar's adapter with a micro-HDMI cable; the panel ran at
the same 59.4 MHz. The bar on Wi-Fi only (its side timed, the core stopped
meanwhile), R2D2 3 m away as in the morning:

| Run | Channel | Panel | Join |
|---|---|---|---|
| 1 | 6 | on | failed twice |
| 2 | 1 | on | 3.6 s, 0 % loss |
| 3 | 11 | on | 3.6 s, 0.7 % loss |
| 4 | 6 | off | 3.5 s, 0 % loss |
| 5 | 6 | on | failed twice |

**The cable changed nothing.** So the adapter alone is not the radiator, and
"the adapter swapped on 2026-10-14" no longer explains why setup worked
before: the radiator may be the panel itself, its touch cable, the Pi's own
connector, or the layout. What else changed physically before 2026-10-14
evening is not on record.

## The fix (`setup_network.quiet_channel`)

The setup network takes the 2.4 GHz channel - 1, 6 or 11 - farthest from any
multiple of a connected screen's pixel clock; 6, NetworkManager's own choice,
when no screen's EDID can be read. The bar gets 11, sofapi keeps 6. No one
fixed channel suits both: 11 would put sofapi's panel 2 MHz away.

## How the investigation itself went wrong (LESSONS 72)

- **Tests on the cable were void.** `CableFirst` (ADR-0123) disconnects every
  Wi-Fi connection but one named exactly `gexis-setup` within 5 s while the
  cable has a link. The test access points were named otherwise, so the core
  took each down; the conclusions drawn from them about the hardware were
  wrong.
- **A second receiver was used before it was shown to see a working one.**
  R2D2's scan list also keeps stale entries (it showed a network on channel 6
  that had restarted on 11).
- **"The device is at fault" was said on that evidence.** George held it was
  software; it was the software's choice of channel against the software's
  display mode.

## Not tested

Other screens' channels on a device beyond the bar and sofapi; a TV's (its
clock comes from the mode the TV is run at, and the EDID's first timing may
differ); interference on 5 GHz (the setup network never uses it).
