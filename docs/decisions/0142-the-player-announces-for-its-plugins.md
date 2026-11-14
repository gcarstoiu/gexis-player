# ADR-0142 — The player announces for its plugins

**Status:** **Accepted** — 2026-10-12. George, on the approach (*"Go with the
first approach and let's make this work to learn from it"*); the announcing
side moved from the plugin to the player after the test below. **Amended**
2026-11-14 (George, to fix it): decision 1's block is set again after every
systemd reload ([Finding 148](../findings/148-plugins-port-block-lost-at-reload.md)).
**Amends:** [ADR-0106](0106-plugins-you-install-and-update.md) (the uploaded plugins'
sandbox), the plugin contract (one event added, contract still 1).

## Context

An uploaded renderer, tested on guestpi on 2026-10-12, ran its own mDNS
responder and published its service under a host named after the device -
`GuestPi.local`. avahi saw a second claim on the Pi's own name and renamed the
Pi `guestpi-2.local`: the address in every bookmark stopped answering, and the
player switcher listed the Pi as another player. Nothing in the player stopped
a plugin from doing this, and nothing offered it a better way.

Tested the same day:

- **Denied port 5353** (`SocketBindDeny=`), the plugin's own responder could
  not answer; the plugin carried on, and avahi took `guestpi.local` back with
  no conflict.
- **A plugin cannot publish through avahi itself.** Its sandbox runs as a
  systemd dynamic user, and the system bus refused every connection from one
  (`Transport endpoint is not connected`), sandbox options or not, while a
  static user was accepted. The image also lacked `libnss-systemd`; adding it
  let the name resolve and changed nothing at the bus.
- **The same service, published by avahi from a file in
  `/etc/avahi/services` under the Pi's own host name, was found by the phone
  app that looks for it**, as before.

## Decision

1. **Uploaded plugins may not bind the mDNS port**: both uploaded-plugin
   units carry `SocketBindDeny=ipv4:udp:5353` and `ipv6:udp:5353`. Shipped
   plugins run under their own units and are not affected.
2. **A plugin asks the player to announce for it**: the event
   `{"t": "announce", "services": [{"type": "_x._tcp", "port": 1234,
   "name": "...", "txt": {"k": "v"}}]}`. Each message replaces that plugin's
   whole set; an empty list withdraws it.
3. **The player writes them as one avahi service file per plugin**,
   `/etc/avahi/services/gexis-plugin-<id>.service`, under the Pi's own host
   name. The file goes when the plugin disconnects, and every such file is
   cleared when the core starts, so a crash leaves nothing announced.
4. **What is accepted**: at most 4 services; `type` of the form
   `_name._tcp` or `_name._udp`, never one the player announces itself
   (`_gexis._tcp`, `_smb._tcp`, `_device-info._tcp`, `_workstation._tcp`,
   `_ssh._tcp`, `_sftp-ssh._tcp`); `port` 1-65535; `name` up to 63
   characters, the device's name when left out; at most 20 `txt` entries,
   keys of letters, digits, `.`, `_`, `-` and values up to 255 bytes. A
   message that breaks any of this is refused whole, with the reason logged.

## Consequences

- A plugin that runs its own responder still runs, unannounced, until it
  uses `announce`; the plugin manual says so.
- The player keeps every name on the network: no plugin can claim the host
  name, or announce one of the player's own services.
- Shipped plugins are untouched; they publish as they do today.

## Amendment, 2026-11-14 — the block kept through reloads

Finding 148: systemd 257 takes the `SocketBindDeny=` block off every running
unit at each `daemon-reload` and leaves the units' other filters in place.
The core reloads at every start, after the plugins have started, so a plugin
started at boot ran with port 5353 open, and the test renderer's own
responder had avahi rename three players `name-2` for days. The test above
looked only at a freshly started unit.

1. **The core sets the block again** on every running uploaded plugin
   (`systemctl set-property --runtime`, the list emptied first) after each
   `Reloading(false)` systemd sends on the system bus, and once when it
   starts listening (`mdns_block.py`). It does not restart the plugin.
2. **The name repair keeps trying:** `mdns-name.sh` asks for the name five
   times in a row, then once every 30 min, so a clash whose cause has gone
   clears without a restart.

Not tried: `daemon-reexec`.

## Unverified

The bus's refusal of dynamic users is measured, not explained. If it is
understood later, `announce` still stands: it keeps the names in the player's
hands either way.
