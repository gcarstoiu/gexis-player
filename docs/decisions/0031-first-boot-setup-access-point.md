# ADR-0031 — First-boot setup over a temporary access point

**Status:** Accepted; **amended 2026-09-28** with George's answers to the open questions, before Phase 13's build
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

## Amended 2026-09-28: George's answers, before the build

Planned against the design (`design/source/Setup.dc.html`, `design/screens.md`
§13). Every answer below is George's, 2026-09-28. Five gaps were found reading
the design against the hardware, and the answers close them.

### Security and joining

1. **WPA2.** A player **with a panel** makes up its own password and shows it on
   the panel. A player **without one** uses the fixed password **`gexis-setup`**,
   the same as the network's name. The first idea was `gexis`, but WPA2 needs 8
   to 63 characters. Whether a panel is attached is read from the display
   connector, not assumed.
2. **QR codes, no captive portal.** The panel shows a QR code that joins the
   setup network, with the password written under it, and a second one that
   opens the setup page, with its address under it.
3. **The phone drives setup, and only the phone.** The panel, when there is
   one, shows helping information (how to join, the address, progress). It does
   not run the steps.

### The steps

4. **Music:** no server discovery during setup. Over the setup network the
   device cannot see the home network, so a scan would always come back empty.
   An empty, optional Lyrion address field stays, with the Spotify Connect and
   Bluetooth switches. Discovery works as it does today once the device is on
   the home network.
5. **A wrong Wi-Fi password:** with one radio the join can only be tested after
   the setup network is down, so the phone has already lost the page. The
   device returns to setup mode within about a minute, **keeping every other
   answer**, and the panel and the page say it could not join and why.
6. **Wi-Fi country:** taken from the time zone. The setup network needs a
   country before anything can be asked, so it starts on the image's default
   and switches to the chosen one when the answers are applied.
7. **Re-entry** (criterion 8's threshold):
   - at boot, if there is no Ethernet link and no configured Wi-Fi is joined
     within **90 s**, the setup network opens;
   - while it is open **and no client is connected to it**, the device looks for
     its configured networks every **5 minutes** and rejoins one that is back.

   So a router reboot does not strand the device, and nobody's setup is cut off
   mid-way.
8. **First boot on Ethernet** runs the same setup over the ordinary network.
   The Network step shows the Ethernet connection, and offers Wi-Fi as well
   for anyone who wants it.

### Testing (George: no Ethernet on gexis)

Raising the setup network on gexis takes down the Wi-Fi Claude reaches it
through. So every test runs as a **timed script on the device**:
- it raises the setup network for a set time and logs to the card (Debug logs,
  ADR-0103);
- then it tears the network down and rejoins the home Wi-Fi. That happens
  whatever the script did, through a timer that does not depend on it.

George joins from his phone during the window, and Claude reads the logs
afterwards. The full test is a card flashed with nothing pre-seeded.

