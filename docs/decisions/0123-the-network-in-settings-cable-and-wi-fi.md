# ADR-0123 — The network in Settings: cable and Wi-Fi

**Status:** **Accepted** — George, 2026-10-07 (*"All good. Agreed with your proposal"*, the rows, the 60 s safeguard and the wording included), on what to add: *"cable network
connection setup, connection speed and signal strength in the connected WiFi
overview"*; then *"A. Let's give some flexibility and allow manual
introduction as well, not just showing. B. Agreed. See where everything fits
so as not to make everything too crowded."* Its rows are in ADR-0022's inventory.
**Builds on:** [ADR-0031](0031-first-boot-setup-access-point.md) (setup; on
a cable, Wi-Fi is optional - amendment 8), [ADR-0104](0104-how-the-device-knows-it-needs-setup.md),
[ADR-0022](0022-settings.md) (every setting inventoried).

## Context

A player on a cable already works: NetworkManager takes an address by DHCP,
and setup notices the cable and makes Wi-Fi optional. Settings shows none of
it - *Device → Wi-Fi* lists the known wireless networks, with four signal bars
each, and nothing about a cable. Nobody can see the cable's speed, the
player's address on it, or give it a fixed address; nor the connected Wi-Fi
network's real signal, speed or band.

## Decision

**Where it goes, so Device is not crowded** (George: *"see where everything
fits"*). Device has six rows today. The network gets **one row more, not
five**: details live in the sheet a row opens, not on the page.

1. **[N] Cable** - *Device*, beside *Wi-Fi*, shown only while a cable is
   plugged in (or a fixed address is set for it). The row reads its state at
   a glance: *Connected · 1000 Mb/s · 192.168.1.20*, or *No link*.
   Its sheet:
   - **Address**: *Automatic* (DHCP, the default) or *Manual*.
   - Manual: **Address** (with its prefix, e.g. `/24`), **Gateway**, **DNS**
     (one or two). Checked as typed; *Save* is refused until they make a
     working combination (address and gateway in the same network).
   - **Kept only once it is shown to work** (the same shape as ADR-0109's
     *Keep* for a new screen): applying a manual address that leaves the
     player unreachable would lock the owner out of Settings. After *Save*,
     the phone page is told the new address to open; unless the change is
     confirmed from it within **60 s**, the player goes back to the address
     it had.
2. **[N] Wi-Fi: the connected network's details** - no new row. The
   connected network's line in the *Wi-Fi* list keeps its bars and adds its
   **speed** (e.g. *390 Mb/s*); its sheet shows **signal** (dBm and %),
   **band and channel** (*5 GHz · 36*), the player's **address**, and the
   same **Address: Automatic / Manual** choice as the cable, kept the same
   way. Read while the sheet is open, every few seconds.
3. Nothing else on the page changes; other networks show as today.

## Consequences

- NetworkManager does the work for both (`nmcli connection modify … ipv4.method
  manual …`); the core already drives it for Wi-Fi.
- A manual address is saved with NetworkManager's connection, so a backup
  carries it like the Wi-Fi networks; a factory reset removes it.
- `gexis` has no cable: the cable half is tested on a second Pi or the bench
  before it ships, and said so until then.
- IPv6 stays automatic; manual applies to IPv4 only (raise if wanted).

## Built

- **2026-10-03 (0.9.3):** the connected Wi-Fi network's details - signal,
  speed, band, channel, address.
- **2026-10-08, the cable**, with a cable on guestpi (George: *"Lan cable
  connected. You can work on it being supported"*):
  - `wired.py`: the port's link and speed from the kernel, its profile's
    address, gateway and DNS from NetworkManager, and `check()` for a manual
    address (an address with its prefix; a gateway inside that network, not
    the address itself; one or two DNS servers), each refusal a sentence;
  - `Cable.change()` saves the profile's IPv4 settings, applies the new ones
    (`nmcli connection modify` and `up`), and puts the old ones back if the
    port does not take them;
  - **the safeguard:** a change waits `KEEP_S` = 60 s for *Keep*
    (`POST /network/keep`), counted only when the request arrives at the new
    address, which shows it works, or from the panel (loopback), which
    reaches the player whatever its address. Not kept, the old settings come
    back by themselves;
  - the *Cable* row is shown while the port has a link or holds a manual
    address (the registry's new `shown` providers). Its line is *Connected
    · 1000 Mb/s · address*, with *manual* or *waiting to be kept* after it;
    *No link* without a cable;
  - the sheet (`CableSheet`): the facts, *Automatic* / *Manual*, the fields,
    *Save*. `CableKeep` asks *Keep the new cable address?* on every page,
    phone and panel, while a change waits; at the old address it names the
    new one to open.
- **Tried on guestpi, 2026-10-08,** with nothing playing:
  1. a manual address (`192.0.2.230/24`, checked free by ping and ARP
     first) answered at once; *Keep* from the Wi-Fi address was refused;
     not kept, the cable went back to DHCP 60 s later to the second;
  2. set again and kept from the new address, through the page: the banner,
     the sheet and *Keep* at `.230`;
  3. back to *Automatic* through the sheet, kept at the address DHCP gave
     (`.107`). guestpi ends as it started.
- **2026-10-08, the Wi-Fi address** (decision 2; George: *"do it as well"*):
  the same `wired.Cable`, on `wlan0` and the connected network's profile;
  the same form under the connected network's details in the Wi-Fi sheet.
  It is served at `/network/wifi/address`, because `/network/wifi` was
  already the details. Only one change waits at a time, and *Keep* counts
  for whichever waits. Found while trying it: after a Wi-Fi rejoin the new
  address shows only seconds later, so the phone was told to open
  `http://None:8090`. A change now names the typed address (Manual), or waits
  up to 20 s for DHCP's (Automatic).
- **Tried on guestpi, Wi-Fi, 2026-10-08,** working over the cable: a manual
  `192.0.2.231/24`, not kept, back to DHCP after 60 s plus the rejoin;
  set again and kept from `.231`; back to *Automatic*, kept at `.21`.
- **Consequence corrected:** "a backup carries it like the Wi-Fi networks"
  above is wrong. A backup holds no NetworkManager profile (ADR-0083's
  members), so a manual address is set again after a restore.
- NetworkManager stores the cable's profile once it is changed (the profile
  it made by itself lived only in memory before). Automatic is the same as
  before it.

## Amended 2026-10-08: the cable wins

George, seeing the cable and the Wi-Fi connected at once: *"which must be an
error"*; on the choice: *"The cable should win"*.

- **While the cable carries the player, the Wi-Fi is disconnected.** Its
  networks stay saved. When the cable's link goes, the Wi-Fi connects again
  by itself, with its own address; `<name>.local` finds the player either
  way. Before, NetworkManager kept both, the cable carrying the traffic
  (its route is preferred) and the player answering at two addresses.
- **The Wi-Fi stands down only once the cable has its address**, not at the
  link: on guestpi the link came several seconds before DHCP's answer, and
  the first version left the player with no network in between.
- **The setup network is never taken down** for a cable.
- **A Wi-Fi network joined in Settings while the cable is in** is joined -
  which proves the password - then set aside; the sheet says *"Saved. The
  player uses the cable while it is plugged in; this network takes over
  when the cable is unplugged."*
- **Built** as `wired.CableFirst`, a check every 5 s in the core. **Tried on
  guestpi** with the port taken down for 30 s and brought back, twice: the
  Wi-Fi was connected within 10 s of the link going, and disconnected 5 s
  after the cable had its address again.
- **Not tried:** a real unplug, as opposed to taking the port down; and a
  player whose Wi-Fi has never been set up (it has nothing to connect to,
  and stays on no network until the cable is back).
