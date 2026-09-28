# Finding 099 — The setup access point on one radio

**Date:** 2026-09-28
**Question:** Before Phase 13 builds ADR-0031's setup network: on gexis's one
radio, how fast does NetworkManager raise it and give the home Wi-Fi back, can a
phone join it and reach the core's page, and can the device scan for networks
while hosting one?

**Scope:** `gexis`, image v0.2.1-730-g66d931e, provisioned onto the home Wi-Fi
(5 GHz, channel 116), George's backup restored, nothing playing. Two runs of
`image/tools/ap-trial.sh` (180 s each, 17:34:43 and 17:44:41), which raise
`gexis-setup` with `nmcli device wifi hotspot`, WPA2, password `gexis-setup`,
regulatory domain DE from provisioning. **One phone**, George's Pixel 10 Pro
(Android, Chrome 154). Times are the script's, from its own start; the core's
log for the page. **Not tested:** a card with no Wi-Fi provisioned, an iPhone, a
second client, a wrong password, 5 GHz for the setup network, or anything at
boot — Phase 13 has not built the boot path.

## Result

| | Trial 1 | Trial 2 |
|---|---|---|
| Scan before the AP | 3.2 s, 7 networks | 3.3 s, 7 networks |
| AP up after `nmcli` | 1.22 s | 0.70 s |
| Radio | channel 6, 2.4 GHz, 20 MHz | same |
| Phone associated (when George joined) | +75-80 s | +24-29 s |
| Address leased | within 5 s of association | reused the lease from trial 1 |
| Scan while hosting | 3.67 s, fresh results | 3.69 s, fresh results |
| Phone still associated after that scan | yes | yes |
| Home Wi-Fi back after the AP came down | 6.01 s, same address | 6.10 s, same address |
| Guard timer needed | no | no |

- **NetworkManager moves the radio to 2.4 GHz channel 6** for the hotspot
  whatever band the home Wi-Fi is on; asked for no band, that is its choice.
- **A scan while hosting keeps the client.** Both scans returned signal levels
  different from the pre-AP scan, so they were not the cache. **The scan lists
  `gexis-setup` itself** (signal 0).
- **`ip neigh` trails association.** In trial 1 the phone was in `iw`'s station
  list 5 s before it appeared in the neighbour table, which only sees a client
  once it has sent traffic. The script counts with `iw` since 429b4b0.
- **Android warned the network had no internet** (George). He stayed connected
  and the page loaded; ADR-0031 now has the panel say to.

### The page over the setup network (trial 2)

The core listens on `0.0.0.0:8090` and gexis has no firewall, so no change was
needed. At 17:45:22, 12-17 s after association, the phone fetched `/`, the bundle,
fonts and icons, and `/settings`, and opened the `/state` WebSocket.

- **The WebSocket dropped after 10 s and reconnected 7 s later**, then held to
  the end. Nothing on gexis says why. It came at about the time Android
  checks a new network's internet; that is a guess, not a measurement.
- `/library/counts` and `/library/strip` answered **502**: LMS is not reachable
  from the setup network, which is why ADR-0031 leaves discovery out of setup.
- **The core noticed LMS was gone 45 s after the AP came up** (17:45:30) and
  had it back 3 s after the home Wi-Fi returned.

## What it bears on

- **Phase 13 can keep a live network list on the setup page**, scanned while
  hosting, with the device's own network filtered out. One phone, two scans.
- **The setup page must survive its WebSocket dropping** without losing what
  was typed, since one did in the first minute on the only phone tried.
- **ADR-0031 §5's "back to setup within about a minute"** has room: raising
  takes about a second and rejoining about six.
