# Installing Gexis Player

From an empty card to music, in about twenty minutes. The steps are the same
on Windows, macOS and Linux.

## What you need

- A **Raspberry Pi 4** with a **DAC** on it (a HAT such as the HiFiBerry
  DAC2 HD), or a USB DAC.
- A **microSD card**, 32 GB or more, A1 or A2 rated, from a known brand.
- The **official Raspberry Pi 5.1 V / 3 A power supply**. A phone charger is
  the most common cause of a player that restarts by itself.
- Optionally an **HDMI touch screen**. A screen that has its own power port
  is best powered from its own supply.
- A computer with a card reader, and a **phone**.

See the [hardware requirements](HARDWARE.md) for what is tested.

## 1. Download the player

Download **gexis-player.img.xz** from the
[latest release](https://github.com/gcarstoiu/gexis-player/releases/latest).
There is no need to unpack it.

## 2. Put it on the card

1. Install **Raspberry Pi Imager** from
   [raspberrypi.com/software](https://www.raspberrypi.com/software/) and open it.
2. **Device:** Raspberry Pi 4.
3. **Operating system:** scroll to the bottom, choose **Use custom**, and pick
   the `gexis-player.img.xz` you downloaded.
4. **Storage:** your microSD card. Check it is the card: everything on it is
   erased.
5. When Imager offers to **customise the settings** (Wi-Fi, user name and
   so on), **skip it**. The player is set up from your phone in step 4, and
   Imager's settings would get in its way.
6. Write, wait for Imager to verify the card, and take the card out.

## 3. Start the player

1. Put the card in the Raspberry Pi.
2. Connect the DAC to your amplifier, and the screen if you have one. A
   network cable is optional.
3. Connect the power supply last.

The first start takes a few minutes. The screen may go dark and come back
once or twice while the player prepares the card and finds the screen's
best mode. Leave it powered.

## 4. Set it up from your phone

**With a screen:** it shows two QR codes. Scan the first to join the
player's own Wi-Fi, **gexis-setup**, then the second to open the setup page.
The Wi-Fi password is on the screen.

**Without a screen:** join the Wi-Fi **gexis-setup** (password
`gexis-setup`), then open **http://10.42.0.1:8090** in the phone's browser.

**With a network cable plugged in:** setup runs over your own network
instead, at the address the screen shows, or
**http://raspberrypi.local:8090**.

The phone may say the setup Wi-Fi has no internet. That is expected: stay
connected. The page then walks you through your Wi-Fi, a name, the clock,
the sound output, your music, the screen and the extras, or restores a
backup of an earlier player.

When you finish, the player joins your Wi-Fi, restarting if its name or
screen changed. Put the phone back on your home Wi-Fi. On the first start after setup the player
downloads its visualiser skins and the extras you chose, showing each one's
progress, and is then ready to play.

## Afterwards

- Open the player's settings from any phone or computer on your network at
  `http://<name>.local:8090`, with the name you gave it.
- Updates arrive over the network: *Settings → System*. You never need to
  flash the card again.
- Before you ever re-flash, keep a backup: *Settings → System → Back up now*,
  then *Restore → Download* on a phone or computer.

Something not right? The [FAQ](FAQ.md) answers the common questions, and the
[user manual](manual/README.md) explains every screen and setting.
