# Finding 148 — systemd drops the uploaded plugins' port-5353 block at every reload; a plugin's own responder then renames the Pi `name-2`

**Date:** 2026-11-14. **For:** [ADR-0142](../decisions/0142-the-player-announces-for-its-plugins.md)
(amended the same day) and the name repair (`gexis-mdns-name.timer`). Found
after George could not open sofapi from his phone that afternoon and asked
for the mDNS side first.

## Scope

- **Devices:** sofapi (the `ph-radio` preview), bedroompi, guestpi and the bar
  (ShelvesPi), all at `gexis-core 1.16.2`; Raspberry Pi 4, Debian 13, systemd
  257.13-1~deb13u1, kernel 6.18.60+rpt-rpi-v8, avahi 0.8-16. bedroompi had
  started 25 minutes before; the others had run for three to eight days.
- **Plugins:** each player's uploaded plugins (two to five); one of them, an
  uploaded test renderer on sofapi, bedroompi and guestpi only, runs its own
  mDNS responder.
- **Read:** avahi's name (D-Bus `GetHostName`); avahi's, the core's and the
  plugins' logs; what holds UDP port 5353 (`ss`); the BPF programs attached
  to each plugin unit's cgroup, read from the kernel (`BPF_PROG_QUERY`,
  effective, read-only); on bedroompi, every mDNS packet about its own name
  (IPv4 and IPv6) while avahi was asked for the name once. Addresses were
  read only as labels (the player's own, another player's, another device's).
- **Changed, on the players:** systemd reloaded on bedroompi seven times; the
  block set again at runtime on its plugins and guestpi's; the test renderer
  restarted on both, then updated; both names claimed back once.
- **Not tested:** `daemon-reexec`; the fix from a package after a fresh boot
  (the new module was run by hand on bedroompi); another systemd version;
  which device on the network answers from a cache (not a player; left
  alone).

## Results

### 1. Three players of four announced as `name-2`

| Player | avahi's name | Repair tries left | Test renderer with its own responder | Clash |
|---|---|---|---|---|
| sofapi | `sofapi-2` | none of 5 | yes | 3 s after boot, three days before |
| bedroompi | `bedroompi-2` | none of 5 | yes | 6 min after boot |
| guestpi | `guestpi-2` | none of 5 | yes | at boot, four days before |
| the bar | `shelvespi` | 5 (none needed) | no | - |

The players list each other at the `-2` names. The usual names went on
resolving, answered by something else (§2).

### 2. The plugin's responder answers for the Pi's own name

- **Caught on bedroompi.** avahi was asked for `bedroompi.local` (as the repair
  timer does). Within 0.1 s of avahi's probe came an answer from bedroompi's
  own addresses, not avahi's, naming `bedroompi.local` with two IPv6
  addresses: the local-network one avahi announces and the link-local one it
  does not. avahi took it for another device's claim and went back to
  `bedroompi-2` a second later. avahi does not set aside answers that come
  from its own host.
- **Why the two differ:** at boot avahi first announced the link-local
  address, then, 3 s later, the local-network one the router advertised, and
  withdrew the first. The responder goes on giving the link-local one.
- **bedroompi's own clash** came while it held its name, in the second two
  browsers opened its page: their lookup was answered by the plugin.
- **A device on the network that is not a player** answers lookups for every
  player's name from a cache, even for names their players had given up,
  with the IPv4 address and, for two, the link-local IPv6 one. No clash was
  seen from it: the bar kept its name, and bedroompi's claim (§4) held while
  it answered.
- **A name pointing at the wrong address.** One lookup of `guestpi.local` from
  the development computer returned only the link-local address, where the
  page is not served; the connection was refused, and the next lookups
  returned the IPv4 one. This fits George's sofapi not opening that
  afternoon, but it was not shown to be the cause.

### 3. The block is in the units, not on the running plugins

- Both uploaded-plugin templates carry `SocketBindDeny=ipv4:udp:5353` and
  `ipv6:udp:5353`, and a throwaway unit with them was refused all three binds
  tried (`EPERM`). Yet the test renderer held port 5353 on bedroompi and
  guestpi.
- **Attached programs, all 13 running plugin units on the four players:** the
  units started after systemd's last reload had the bind programs; every unit
  started before it had none. The units' IP-address filters
  (`IPAddressDeny=`) were attached on all of them.
- **A reload removes it.** On bedroompi, `systemctl daemon-reload` with three
  plugins running: the bind programs were gone afterwards in 13 checks of 14
  (five reloads; once one unit kept them); the IP-address filters stayed, the
  processes were not restarted.
- **The core reloads at every start**, when it writes the plugins'
  permissions (`plugin_permissions.apply`): on bedroompi 11 s after the
  plugins had started at boot. Every plugin started at boot runs unblocked
  from then on. Other reloads come too: guestpi's and the bar's last were at
  about 3 a.m. two nights before, sofapi's at a package install that
  morning.
- **Setting the property again puts it back:** `systemctl set-property
  --runtime <unit> SocketBindDeny= SocketBindDeny=ipv4:udp:5353
  SocketBindDeny=ipv6:udp:5353` attached the programs to the running unit,
  same process, with no reload.
- systemd sends `Reloading` (true, then false) to every listener on the
  system bus, with no subscription.
- One search found no report of this upstream.

### 4. The repair timer spent its tries while the plugin answered

Five tries, 2 min apart from 2 min after boot, each refused in the same
second, then none until the next start. sofapi stayed `sofapi-2` for three
days, the last hours of them with its plugin blocked by a restart.

## Fixed (`fix-mdns-block`)

- **The core sets the block again** on every running uploaded plugin after
  each reload systemd reports, and once when it starts listening
  (`mdns_block.py`). Run by hand on bedroompi with the core's Python, through
  two reloads: the programs were back on all three plugins by the time the
  check after each reload ran.
- **The repair timer** tries five times in a row, then once every 30 min.
- **On the players:** bedroompi's and guestpi's test renderer restarted and the
  block set again on their other plugins; both names claimed back, and both
  held while another player looked them up. sofapi was playing and was left
  `sofapi-2`; its plugins are blocked.

## What it means

- ADR-0142's block held until the first reload after a plugin started; the
  core now keeps it. Its test (2026-10-12) looked only right after a start
  (Lesson 96).
- The bar's `shelvespi-2` for a day (2026-10-14), put down then to a cache of
  its previous start, came while it ran the same test renderer: most likely
  the same cause, not shown.
- Nothing changes for plugin authors: port 5353 is closed, and `announce`
  is how a plugin is found.
