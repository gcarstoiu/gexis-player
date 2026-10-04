# Changelog

Every release of Gexis Player and its notes, newest first. Generated from
`core/src/gexis_core/release_notes.json` by `python -m gexis_core.changelog` -
edit that file, not this one. The player shows the last 10 under
Settings → System → Change logs.

## 0.8.8 — 4 October 2026

### New

- A newly attached screen is used straight away at start, already in its own resolution, with Keep this screen?. A screen the player does not know is laid out from its own resolution, and a panel that stands upright, such as a bar, is turned to landscape.
- On a bar, Now Playing shows the artist, album and year larger, with the year straight after the album.
- On the Testing channel, the player's logs are kept across restarts by default, to help track down problems.

### Fixed

- Keep this screen? waits two minutes for every change, including a new screen and a rotation.
- On a bar's first start, Keep this screen? is drawn on the bar's own layout, so its Keep button can be seen.

## 0.8.7 — 4 October 2026

### New

- A newly attached screen the player recognises is used straight away at start, with Keep this screen?; if it is not kept, the player goes back to the screen before. Any other new screen is asked about, and the list of screens opens on its size.
- A USB disk stays in the Lyrion server's list for 7 days after it is unplugged.
- Setup says so when it finds no Wi-Fi network or no audio output.
- Setup's step counter counts only the steps that are shown.

### Fixed

- On an artist's page, genres are kept to two rows, so Play and Shuffle are never covered.
- After setup, Keep this screen? waits two minutes, as it says.
- When the setup network cannot start, setup says why in a sentence.
- A skin pack that failed to download is no longer reported as failed once the screen's pack is installed, and a failure is described in plain words.

## 0.8.6 — 3 October 2026

### New

- The skin picker shows each skin straight away: its pictures are made ahead, smaller, on the player.
- A Waveshare 13.3″ HDMI LCD (H) is recognised when setup offers a screen.
- After forgetting a Bluetooth device, the message says to forget the player on that device too before pairing again.

### Fixed

- Forgetting a Bluetooth device works again.
- The spectrum falls to zero when playback pauses, as the meters do.
- The boot logo is centred on every screen size.
- An update started while a skin pack is downloading waits for it instead of failing.

## 0.8.5 — 3 October 2026

### New

- Settings explanations appear once, in the window a setting opens, not also in the overview.
- On a phone, the arrow sits in the middle of each settings tile.
- A new Lyrion server says it is setting up and that this takes about 3 minutes.
- A scan the Lyrion server stopped for lack of memory is said on its row, with how many files fit.
- Plexamp and the Lyrion server move to a new version as part of the update that brings it.

### Fixed

- Adding a network share no longer scans the library twice.
- A NAS that is off when the player starts no longer makes the Lyrion server wipe and rescan its library.

### Good to know

- The Lyrion server may use the player's memory less 1 GB. On a player with less than 4 GB, a new server uses less memory for scanning.
- A player with 1 GB of memory is not offered the Lyrion server.
- The Lyrion server no longer offers its own updates; its version comes with the player's updates.

## 0.8.4 — 3 October 2026

### New

- Settings has Change logs, under Updates: what changed in the last 10 releases.
- A display sold with or without a case is listed once.

### Fixed

- A new Lyrion server installs its add-ons and opens in Material Skin once it is installed.
- Remove works for an uploaded plugin that a backup brought back without its package.

### Good to know

- Once an update is installed, its notes are under Change logs rather than Software update.

## 0.8.3 — 3 October 2026

### New

- Network shares for the Lyrion server are listed by name, each with Forget beside it.
- A share the scan does not find can be added with "Add by address".

### Fixed

- Remove works for the Lyrion server.
- The Network shares setting no longer shows a share's login details.

### Good to know

- Removing the Lyrion server also deletes its library, its settings, its add-ons and its network shares. The Music folder and its playlists stay.
- Network share passwords are no longer kept in the settings or in backups. After restoring a backup onto a new card, enter the password again.

## 0.8.2 — 3 October 2026

### New

- Network shares for the Lyrion server can be found with a scan: the servers on the network are listed, then their shares, with a login where the server asks for one.
- Lyrion Server heads Sources, with Lyrion Client beneath it.
- A new Lyrion server opens straight into Material Skin, without its setup wizard.

### Fixed

- Adding a network share for the Lyrion server no longer fails.
- Switching a plugin off and on quickly no longer leaves it stopped while its switch says on.
- Updating from 0.8.0 to this release installs correctly.

## 0.8.1 — 3 October 2026

### New

- Network shares for the Lyrion server can be found with a scan: the servers on the network are listed, then their shares, with a login where the server asks for one.
- Lyrion Server heads Sources, with Lyrion Client beneath it.
- A new Lyrion server opens straight into Material Skin, without its setup wizard.

### Fixed

- Adding a network share for the Lyrion server no longer fails.
- Switching a plugin off and on quickly no longer leaves it stopped while its switch says on.

## 0.8.0 — 2 October 2026

### New

- The Lyrion server can run on the player itself: switched on under Plugins, it is downloaded from the Lyrion community and plays music from the player's own Music folder (shared on the network), from USB disks and from network shares (SMB or NFS) added under Sources. Material Skin, Music & Artist Information and Radio Now Playing are installed with it. The player offers it in the list of servers and never switches to it by itself.
- The Beszel hub can run on the player: switched on under Plugins, its page is at port 8095 of the player.
- On a phone, long lists in Settings fill the screen, and a warning appears once an option is chosen, with Confirm.

### Good to know

- Both plugins are off until switched on.
- The Lyrion server needs internet access the first time it is switched on.

## 0.7.0 — 2 October 2026

### New

- Skins have readable names, brand first, such as "Naim · Turntable · art beside", and the skin list is sorted by name.
- The Skins setting has Fanart: the skins that show the artist's photos.
- On a phone, a swipe left or right moves to the next or previous skin; the list stays open after a skin is chosen.
- A plugin that reports the playing file's own sample rate shows it on the visualiser.

### Fixed

- Settings shows the attached screen after restoring a backup made before screens could be chosen.
- The sample rate stays within the space the skin gives it.
- The player's logo is centred on more skins.
- During an update, Updating… brings back the progress window after Hide.

### Good to know

- A skin chosen before keeps its place under its new name.

## 0.6.0 — 2 October 2026

### New

- Skins with a frame for the artist show a slideshow of the artist's photos, from the Music & Artist Information plugin on the Lyrion server; the photo changes every 20 seconds.
- Album art takes the shape the skin gives it, such as a circle or a rounded square.
- While Lyrion plays, the visualiser shows the sample rate where the skin has a place for it.
- Choosing a screen asks Keep this screen? only when the picture changes. After first-time setup the phone says so, and the screen waits two minutes for Keep.

### Fixed

- Duplicate skins are removed. The sets are smaller: 120 skins at 800 × 480, 147 at 1280 × 400, 138 at 1480 × 320, 286 at 1280 × 800 and 287 at 1920 × 1080.
- Text that could not be read is corrected in three skins.
- The player's logo is centred in its place on more skins.
- After a screen goes back to the previous one, Settings shows the screen in use.

### Good to know

- An installed skin set is updated with the release, so it gets smaller.
- The 800 × 480 tape-recorder skins are left out: their layout was made for a larger screen.

## 0.5.0 — 2 October 2026

### New

- The visualiser's skins now come in a set for each screen size: 800 × 480, 1280 × 400, 1480 × 320, 1280 × 800 and 1920 × 1080. A screen gets the set drawn for its size, or the largest set that fits it, centred on black.
- The 1280 × 800 set has 432 skins, including the 1280 × 720 designs fitted to the screen.
- First-time setup asks before installing the visualiser, and says how many skins the screen gets. They are downloaded once the player is on the home network.
- Plugins has Visualiser skins. Off removes the skins and the visualiser with them; on downloads them again.

### Fixed

- The waiting screen fits four or more sources.
- Handing over to a plugin without a logo shows its initial in the ring.

### Good to know

- A player that already has the visualiser keeps its skins as they are. Switching Visualiser skins off and on again fetches the new set for its screen.
- Settings → Display lists HDMI screens only for now: 110 models.

## 0.4.0 — 1 October 2026

### New

- Other screens: gexis lays itself out for other standard screens, such as 16:9, and for bar screens (1280 × 400 and 1480 × 320).
- Settings → Display has Attached screen (181 models, those tested with gexis marked Tested) and Screen rotation. A change restarts the player on the new screen and asks Keep this screen?. Without a touch within 30 seconds it goes back.
- First-time setup has a Screen step: it recognises a tested screen, or offers the full list, or Headless.
- A plugin without a logo shows its initial in a circle.

### Fixed

- Setup's Headless warning now says what really happens without a screen.

### Good to know

- Nothing changes on the screen in use unless another one is chosen.
- Until a screen has been kept with Keep this screen?, the setup network's password is gexis-setup.

## 0.3.3 — 1 October 2026

### Fixed

- An update no longer restarts the device just to put back a start-up setting that the first boot removes.
- Before an update starts, it says that the player restarts, and the device too if the system needs it.
- Parts of the player that did not change are no longer downloaded again.

## 0.3.2 — 1 October 2026

### New

- The update has its own tile, Software update; Release now only shows what this device runs.

### Good to know

- Installing restarts the player; the music stops. No reboot.

## 0.3.1 — 1 October 2026

### Good to know

- No visible changes: this release lets you try the new update screens.
- Release notes now show as sections with bullet points.
- Installing restarts the player; the music stops. No reboot.

## 0.3.0 — 1 October 2026

What's new: updates are clearer. The Release tile has one button that opens the update: it shows what's new, lists every step as it happens, and shows the download's progress. While updating, the panel shows the progress and can't be used. Release numbers are short now.

Changed: if music is playing, the update asks before stopping it instead of waiting, and nothing resumes afterwards. Automatic updates run between 3 and 4 at night, only when nothing is playing.

This update itself still runs the old way; the new screens apply from the next one. Installing restarts the player; the music stops. No reboot.
