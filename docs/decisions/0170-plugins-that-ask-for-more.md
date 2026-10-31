# ADR-0170 — Plugins that ask for more

**Status:** **Accepted** 2026-10-30 (George: three permissions from the
start; the first check by reading; the loopback fix before 1.10.0). Phase 24
(`ph-plugin-catalogue`), step 7, before 1.10.0 (George). George decided the
direction the same day (a stricter first check, then more permissive; a CEC
plugin first, ADR-0168, *Changed*); the rest is Claude's proposal. Amends [ADR-0106](0106-plugins-you-install-and-update.md)
(the sandbox) and [ADR-0168](0168-a-plugin-catalogue.md) (the checks and the
notice); the tiles and the notice are drawn in
[ADR-0169](0169-one-store-for-every-plugin.md)'s canvas.

## Context

Every plugin the player did not ship runs in one sandbox (ADR-0106): its own
temporary user, the system read-only, no devices (`PrivateDevices=yes`; a
renderer gets the sound devices only). That stops a whole kind of plugin -
a TV remote over HDMI-CEC, an IR receiver or knob on GPIO, a USB remote -
and would leave each to us (George, 2026-10-30: the community should be able
to extend the player; check more first, then allow more).

What such a plugin needs, found on 2026-10-30:
- **The player's controls are already in reach.** The core's HTTP API takes
  D-pad presses (`POST /panel/key`, ADR-0161, built for Home Assistant),
  transport commands and volume from any client on the network, a plugin
  included. A TV remote needs no new message for them.
- **Only the device is missing.** sofapi (Pi 4, 1.9.1) has `/dev/cec0` and
  `/dev/cec1`, `root:video 0660`, under the KMS driver, and `cec-ctl` in the
  image; the service sandbox hides them.
- **Opening one device is a pattern we already use**: the renderer's unit
  has `PrivateDevices=no`, `DevicePolicy=closed`, `DeviceAllow=char-alsa rw`
  and the group `audio`.

## Proposed (Claude)

1. **A plugin declares what it needs** in its manifest:
   `"permissions": ["cec"]`, from a fixed list the player knows. An unknown
   name is refused by the upload check, so by the catalogue's check too.
2. **The player grants exactly that** with a drop-in for the plugin's unit,
   written by the core under `/run/systemd/system/<unit>.d/` at every start
   from the installed manifest and the user's consent, never kept on its
   own: `cec` = `PrivateDevices=no`, `DevicePolicy=closed`,
   `DeviceAllow=/dev/cec0 rw`, `DeviceAllow=/dev/cec1 rw`, the group
   `video`. Nothing else of the sandbox changes.
3. **The user is asked**: the notice before adding lists each permission in
   plain words (the canvas's *A plugin that asks for more*), from the
   uploaded file's manifest or the catalogue entry. A catalogue entry's
   version carries its `permissions`, which the listing check compares with
   the archive's manifest; the player refuses an archive whose manifest asks
   for other than what was shown. **An update that asks for more asks
   again**, listing what is new; one that asks for the same or less goes
   straight on, as updates do (ADR-0168, *Changed*).
4. **The stricter first check** (gexis-plugins), by reading (George): for
   the first listing of a plugin, and any version that adds a permission,
   the review note says what each permission is used for and where in the
   code, and that nothing else uses it. Later versions are read as today.
5. **The CEC plugin first**, written as an outside author would: its own
   public repository, listed through the catalogue, asking for `cec` alone.
   It joins the TV as a playback device on the HDMI port the TV is on; the
   TV remote's arrows, OK and Back go to `POST /panel/key`; play, pause,
   next and previous to the transport routes; the TV switching off or on to
   the screen's standby. Tried first by hand (`cec-ctl` on a test player
   with a TV), since nothing of it has been tried on a Pi.
6. **Ours may declare permissions the same way later**, so that a plugin is
   a plugin underneath too; nothing of ours moves in this phase.

## Decided (George, 2026-10-30)

7. **Three permissions from the start**, so that an author need not wait for
   a release: each granted as (2) says, with the devices' own groups.
   - `cec`: `/dev/cec*` (`video`).
   - `gpio`: `/dev/gpiochip*`, `/dev/gpiomem` (`gpio`), and I²C, SPI and IR
     receivers (`i2c`, `spi`, `/dev/lirc*`) once their buses are on. The
     player switches none of those buses on today: a plugin that needs one
     says so, and switching them on is a later decision.
   - `usb`: USB devices and HID (`/dev/bus/usb`, `/dev/hidraw*`), and USB
     serial ports (`dialout`). Raw USB and HID are root's only on the image:
     a udev rule of ours gives them to a group the grant adds.
8. **The first check by reading** (4), not by running it on a test player.
9. **The loopback fix before 1.10.0**, on its own branch (below).

## Found on the way, fixed apart

**A plugin can pass for the panel.** A few routes trust a caller on
`127.0.0.1` as the panel (`/touch`, `/panel/shown`, `/network/keep`,
`/renderers/park`), and a sandboxed plugin calls the core from `127.0.0.1`
too. True of every uploaded plugin since ADR-0106. A fix of its own, before
1.10.0 (George): the panel proves itself with a token only the kiosk can
read.

## Built (2026-10-30)

On `ph-plugin-catalogue`: `plugin_permissions.py` (`cec`, `gpio`, `usb`, the
drop-in, written at every core start, a unit whose grant changed restarted),
the manifest's `permissions`, consent kept as `granted` in the plugin's
record, the `409` round for an upload and a catalogue install, an update
asking again for what is new, a restore granting nothing new, the udev rule
for USB and HID; `gexis-plugins`, locally: a version's `permissions` and an
entry's `area`, each compared with the manifest. The loopback fix on
`fix-panel-loopback`, merged into the phase branch. Shown on sofapi with a
test plugin uploaded from a phone-sized remote: without the permission it
could open no device; its next version asking for `cec` was asked about
first, then opened `/dev/cec0` and `/dev/cec1` and was refused the GPU and
the GPIO chip; started without its grant, as at boot, it was restarted with
it four seconds after the core; removed, nothing of it was left. The kiosk
proves itself (its panel requests all answered), and a call on loopback
without the token is refused. Not yet: CEC with a TV; the plugin.

## CEC on a test player (2026-10-30)

George connected sofapi's second HDMI port to a receiver (input 6) that
feeds a TV. Tried by hand with `cec-ctl` and `cec-follower`:
- **The bus works through the chain.** The port reads physical address
  `2.6.0.0`; claimed as a playback device it got logical address 8 (another
  player on the bus had 4) and saw the TV (0), the receiver (3, 5) and that
  player, with their vendors and power states.
- **The player can wake the TV and take the input.** *Image View On* woke
  the TV, which then asked for the player's vendor, power status and name;
  waking it reset HDMI, so the player was unregistered for a moment and an
  *Active Source* sent then was lost. Sent again once registered, the
  receiver switched to it (*Routing Change* to `2.6.0.0`).
- **The kernel answers some messages itself** (physical address, vendor,
  name) but not *Give Device Power Status*: with no follower it is refused,
  so the plugin must answer the bus as a device does.
- **Not yet seen: the remote's keys** (George was called away); asked again
  when he is back.

**The plugin, 0.1.0** (local, `~/projects/gexis-tv-remote`, not yet
published): standard-library Python on the kernel's CEC device; a playback
device that answers power, menu and deck status and the active source, and
sends the remote's keys to `/panel/key`, `/panel/go/home` and the transport
routes; nothing switched on or taken by itself; the kernel's own key
passthrough off, so a key reaches the player once. 9 tests without a TV.
Installed on sofapi from a phone-sized remote (asked about `cec` first): its
first run joined the wrong port - sofapi's panel reports an HDMI address too -
so it now joins each port with an address and keeps the one where a TV or a
receiver answers a poll; it gives a vendor ID (the HDMI placeholder, as
`cec-ctl` does), since the TV kept asking. Seen on the bus: it joined as
playback device 8 on the TV's port and answered the TV's questions.

**George's key test** (2026-10-31, the TV's remote through a Harmony): Back
did nothing and Exit worked as Back; he raised nothing else about the keys.
The plugin then said nothing of a key it does not use, so what Back sent is
not known. Its log showed something else: at boot it started before the
player's plugin socket was there, and its hello thread ended. **0.1.1**
(local): the hello is tried again until the socket is there, and again after
the core restarts; a key the plugin does not use is written to its log once.
Installed on sofapi the same morning as an update from a phone-sized remote:
not asked about `cec` again, and connected to the player at once.
Open: Back, pressed again with 0.1.1, and whether the receiver passes its own
remote's keys on over the bus (the plugin takes keys from any device on it).

## Settings (ADR-0022)

None: a permission is granted by adding the plugin, and taken back by
removing it.

## Measured before it is called done

- `cec-ctl` on a test player with a TV: the player seen as a playback
  device, the remote's keys received, the TV's standby seen.
- The CEC plugin under its drop-in: `/dev/cec0` opened, `/dev/dri` and the
  rest of `/dev` still refused; without the grant, refused.
- An upload and a catalogue install that ask for `cec`: the notice lists it;
  an archive asking for more than was shown is refused; an update adding a
  permission asks again.
