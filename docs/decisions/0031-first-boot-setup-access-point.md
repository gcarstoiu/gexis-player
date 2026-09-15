# ADR-0031 — First-boot setup over a temporary access point

**Status:** Accepted
**Date:** 2026-09-14
**Raised by:** George — give credentials a phase, *"with an initial hotspot
creation upon the first boot for setting up the device — so basically not only
the credentials but also things like hostname"*
**Answers:** [0022](0022-settings.md)'s first-boot blocker, and the first-boot
problem [0021](0021-deployment-flashable-image.md) could not close
**Phase:** 10 — see `docs/DEVELOPMENT.md`

## The problem this closes

ADR-0022 recorded it plainly: *"Wi-Fi credentials cannot be entered remotely,
because without Wi-Fi there is no remote browser."* ADR-0021 could not close it
either — Imager cannot customise a custom image file, and the supported routes
(a self-hosted Imager repository, or applying to Imager's community categories)
tie the first-boot mechanism to the distribution channel.

Both records listed "a temporary access point" as a candidate and neither chose
it. This record chooses it.

## Decision

**On first boot, when no network configuration exists, the device raises its own
Wi-Fi access point and serves a setup page over it.** The user connects a phone
or laptop, fills the form, and the device joins their network.

### Why this resolves the text-entry problem rather than reopening it

Setup is the one moment that genuinely requires typing — an SSID, a password, a
device name — and it happens **on the user's own phone, which has a keyboard**.

The panel's role is display-only: it shows the network name, the password and
the address to open. That is exactly what [0029](0029-text-entry-on-every-surface.md)
leaves the panel able to do, and it is why the panel still needs no on-screen
keyboard. The hardest text entry on the device is handled by never asking the
device to take it.

### Mechanism

**NetworkManager's own AP mode.** Verified on `gexis`, 2026-09-14: NetworkManager
1.52.1 active, and `nmcli -f WIFI-PROPERTIES.AP device show wlan0` reports
`yes` — the radio supports AP mode. NM's `ipv4.method=shared` runs its own
dnsmasq for DHCP, so **no `hostapd` and no `dnsmasq` package is added to the
image**.

**The setup page is served by `gexis-core`**, which already serves the UI and
the command endpoints ([0028](0028-ui-serving-and-command-channel.md)). No
second web server, no second origin.

### What setup collects

- **Wi-Fi SSID and password** — the blocker itself
- **Device name** — [0022](0022-settings.md)'s *one* name, propagated to the
  mDNS hostname, the Spotify Connect name and the Bluetooth name. Setting it
  here means the device is reachable at the user's chosen `<name>.local` from
  the first successful boot, rather than at a default that must be changed later
- **LMS server address** — optional; discovery is tried first

### This does not replace `firstrun.sh`

`firstrun.sh` pre-seeding ([0021](0021-deployment-flashable-image.md)) stays,
and stays the route for development and for `make provision`. The two compose:
**pre-seeded configuration wins; the access point is what happens when there is
none.** A developer flashing a card keeps the current workflow untouched.

## Constraints that shape it

**One radio.** `wlan0` cannot reliably serve an access point and a client
connection at once, so the AP is torn down when credentials are applied. Setup
is a mode the device leaves, not a service it runs.

**Ethernet bypasses the flow entirely.** If the device has a working network on
boot, there is nothing to set up over an AP and the AP must not appear.

**The user must be able to get back in.** A router replaced or a password
changed would otherwise lock the owner out of their own device with no input
path. The device returns to setup mode when it cannot reach any configured
network — the re-entry condition is specified with the phase criteria, because
getting it wrong in either direction is bad: too eager and the AP flaps on every
router reboot, too reluctant and the device is bricked from the user's point of
view.

## Open — decide with the phase, not now

- **Access point security.** An open AP is simpler; anyone in range can
  configure the device. A WPA2 AP with a per-device random password shown on the
  panel is better and costs a label on screen. **Recommendation: WPA2 with the
  password on the panel**, since the panel is right there and this is a one-time
  flow.
- **Captive portal.** Automatic redirect needs DNS interception plus correct
  responses to each OS's connectivity probe — real work, and fragile across
  phone vendors. **Recommendation: not in the first cut.** The panel displays
  the address, which is the affordance a screen is good at. Revisit if testing
  shows users do not type it.
- **Re-entry threshold.** How long, and how many failures, before the device
  concludes the network is gone and reopens the AP.

## Unverified

- AP mode has **not** been exercised on this hardware — only the capability bit
  was read. Whether `wlan0` raises a stable AP on a Pi 4 under this NM version,
  and how long the station↔AP transition takes, is untested.
- Whether hostname changes propagate cleanly to Spotify Connect and Bluetooth
  without a reboot. ADR-0022 requires one name; whether all three consumers pick
  it up live is unknown.
