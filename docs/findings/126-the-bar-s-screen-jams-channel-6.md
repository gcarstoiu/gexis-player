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
