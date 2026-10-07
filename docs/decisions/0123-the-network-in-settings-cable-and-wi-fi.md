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
