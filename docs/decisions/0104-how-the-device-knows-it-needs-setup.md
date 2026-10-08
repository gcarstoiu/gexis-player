# ADR-0104 — How the device knows it needs setup, and what it does about it

**Status:** Accepted, 2026-09-28 (George's answers below)
**Date:** 2026-09-28
**Implements:** [0031](0031-first-boot-setup-access-point.md) and its 2026-09-28
amendment — Phase 13, criteria 1, 5-8
**Measured against:** [Finding 099](../findings/099-the-setup-access-point-on-one-radio.md)

ADR-0031 decides *that* the device raises a setup network and *what* setup asks.
It does not say how the core tells a new device from a configured one, when the
setup network opens and closes, or how the answers survive the phone losing the
page. This record does, so the build has one place to be checked against.

## 1. Two questions, kept apart

- **Does the device need setup?** A fact about its configuration. Answered once
  at startup, and changed only by finishing setup.
- **Does it need the setup network?** A fact about the radio right now. A
  configured device that cannot reach its Wi-Fi needs the network but not setup;
  a new device on Ethernet needs setup but not the network.

## 2. Needs setup

**Yes when there is no `/var/lib/gexis/setup-done` and NetworkManager holds no
saved Wi-Fi connection.** Either one means someone already configured it.

- A card from `make provision` or Imager has `preconfigured`, so it never sees
  setup (criterion 7). Nothing in `firstrun.sh` changes.
- A device flashed before Phase 13 is the same case: it has a saved Wi-Fi.
- Finishing setup writes the marker, so a device set up on Ethernet only does
  not ask again.

## 3. The setup network

**Opens:**
- **needs setup, no Ethernet carrier** after 15 s from the core starting (time
  for a cable's link to come up): at once, because there is nothing to wait for;
- **configured, and neither Ethernet nor a saved Wi-Fi has an address within
  90 s of boot** (George, 2026-09-28).

**Never opens** while Ethernet has an address (criterion 6). A new device on
Ethernet serves setup over it (ADR-0031 amendment 8).

**While open:** every 5 minutes, *if no phone is associated* (`iw` station
dump, Finding 099), the device scans while hosting. If a saved network is in
range it takes the setup network down and joins it; if the join fails, the
setup network comes back. A scan keeps a connected phone (Finding 099), but the
rule does not scan with one connected anyway: nobody's setup is interrupted.

**The connection itself:** a NetworkManager profile `gexis-setup`, WPA2, shared
IPv4 on `10.42.0.1`, **`autoconnect no`**, deleted when the device leaves setup.
A profile left behind by a crash must never bring itself up at boot in place of
the home Wi-Fi.

**The password** (ADR-0031 amendment 1): with a panel, eight characters made
once and kept in `/var/lib/gexis/setup-password` so it stays the same across
reboots. The alphabet leaves out `0 O 1 l I`, because it is read off a screen
and typed. Without a panel, `gexis-setup`. **A panel** is the HDMI connector
reporting `connected` (`/sys/class/drm/card*-HDMI-A-*/status`); gexis's panel is
on `HDMI-A-1`.

## 4. Answers outlive the page

The phone loses the page the moment the device leaves the setup network, and
Finding 099 saw the page's connection drop once without that. So **the answers
are held by the core, not the page**: each step is saved to
`/var/lib/gexis/setup-answers.json` as it is completed (the Wi-Fi password is
kept only there, `0600`, and deleted with the file). Reopening the page resumes
where the answers stop.

**Applying:** the non-network answers are written to their settings first (name,
time zone, output, Spotify and Bluetooth, the Lyrion address). Then the Wi-Fi
country is set from the time zone — the country tzdata's `zone.tab` gives the
zone, so no table of our own. Not `zone1970.tab`, which gives several:
`Europe/Berlin` is `DE,DK,NO,SE,SJ` there and `DE` in `zone.tab` (read on gexis).
Then the Wi-Fi is saved, the setup network comes down
and the join starts. **Success** writes `setup-done` and deletes the answers
file. **Failure** within 60 s brings the setup network back with the reason,
and the answers still there except the password (amendment 5).

## 5. What the panel shows

A screen of its own while setup is needed or the setup network is open: the
network's name, the password and the join QR code, and the page's address and
its QR code. Once the phone has the page, the steps' progress. It takes no
input (ADR-0029).

## George's answers, 2026-09-28

1. **Setup is for the phone only** (*"It is meant only for phone as the setting
   up device"*). The design draws the phone and nothing else. The panel's
   screen in §5 is not a second setup surface. It shows how to reach the phone
   page and follows its progress, and it is drawn from the design's parts (the
   gexis mark, the step accents, its type) because nothing draws it.
2. **Headless** (*"A headless setup means also stopping some services that are
   not needed right?"*). Yes, and that already exists: the **Headless** row
   (ADR-0077, wired 2026-09-25) stops `gexis-kiosk`, `gexis-panel-warmup` and
   `gexis-peppy`, and leaves the core, the phone page and audio alone. The
   design's Display step sets that row; nothing new is built for it. The step
   is preselected from the connector. *(A first draft of this answer said the
   list was still owed, and put a duplicate [?] row in ADR-0022. It was not
   searched for first; corrected the same day.)*
3. **A running device that loses its Wi-Fi: restarting is the way back** (*"Restarting is
   the way"*). The setup network opens at boot only, as §3 says.
4. **Settings inventory:** agreed, and appended to ADR-0022. The Wi-Fi country
   is not shown.

## Not in this record

- **The phone's steps and their look** — the design and ADR-0031 cover them.
- **Whether the name reaches Spotify Connect and Bluetooth live** (criterion 4)
  is measured at the end of the phase. ADR-0048 already writes it to all four
  places.
- **Wi-Fi on a fresh card before any country is set.** The image carries no
  `wlan` rfkill state and `firstrun.sh` sets a country only with an SSID. Whether
  the radio is usable on an unprovisioned first boot is measured by the full
  test, not assumed.

## Answered 2026-09-29, on the first blank card: the radio is off

The full test answered the last bullet above: **no**. The panel showed *"The
setup network did not start: … Connection 'gexis-setup' is not available on
device wlan0 because device is not available"*. Read from the card afterwards,
read-only: `/var/lib/systemd/rfkill/platform-fe300000.mmcnr:wlan` = `1`
(blocked; every Bluetooth entry `0`), and the image ships
`/var/lib/NetworkManager/NetworkManager.state` with `WirelessEnabled=false`.
Both are Raspberry Pi OS's by design: `raspberrypi-sys-mods` sets
`rfkill.default_state=0` and pi-gen's `stage2/02-net-tweaks` keeps NetworkManager
from lifting it when the build sets no country, *"to prevent radiating on 5GHz
bands until the WLAN regulatory domain is set"*.

**So the image has no default country, and ADR-0031 amendment 6's "starts on
the image's default" means the world regulatory domain.** The setup network
lifts the block for itself only (`rfkill unblock wifi`, `nmcli radio wifi on`)
and is pinned to **2.4 GHz** (`band bg`; the world domain allows channels 1-11),
so nothing radiates on 5 GHz before a country is known. Finish sets the country
from the time zone with `raspi-config`, as §4 says, which lifts the block for
good. The alternative, a country built into the image, was offered to George on
2026-09-29, and he chose the world domain: *"world domain for sure"* (a
built-in country would declare one country for a device used anywhere).
LESSONS 46.

**Then a race (same day, second blank card, image 755-g6eb6439).** With the
radio switched on first, the panel still showed *"device is not available"*;
**five minutes later, at the retry, the QR codes appeared** (George). So the
unblock worked and the hotspot was asked for before `wlan0` was ready. Image
759-g3d38d11 waits up to 20 s for NetworkManager to call `wlan0` usable,
retries a failed start in 15 s, and puts the radio's state beside any reason
on the panel. Its first-try start is still to be seen on hardware.

## Amended 2026-10-07 (brought into line with the code)

- **§3, "Opens", the 90 s:** counted from the core's setup task starting,
  not from boot (`_wait_for_network` in
  `core/src/gexis_core/setup_network.py`).
- **§3, the password:** made up only once a screen has been kept on the
  panel ([ADR-0109](0109-other-screens.md) decision 5); until then
  `gexis-setup`, as without a panel. Its alphabet is lowercase letters and
  digits, leaving out `0 o 1 l` (`PASSWORD_ALPHABET`); there are no capitals
  to confuse.
- **§4, "Applying":** setup also applies the clock format, Headless, the
  screen and the visualiser's skins (`SETTINGS` in
  `core/src/gexis_core/setup_flow.py`), and sets `lms_enabled` by the Music
  step's choice: off for *off*, on for an address, and on for *find* when
  one server is found. *Find* searches once, after the join and before
  setup ends (`_library`; [ADR-0031](0031-first-boot-setup-access-point.md),
  amended the same day).
- **§5, "What the panel shows":** not everything on one screen. The panel
  shows setup one step at a time, one QR code each: the join code, then the
  page's code once a phone is on the setup network, then the progress
  (George, 2026-09-29; `ui/src/screens/SetupScreen.svelte`).
