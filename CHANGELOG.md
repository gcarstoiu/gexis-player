# Changelog

Every release of Gexis Player and its notes, newest first. Generated from
`core/src/gexis_core/release_notes.json` by `python -m gexis_core.changelog` -
edit that file, not this one. The player shows the last 10 under
Settings → System → Change logs.

## 0.9.3 — 7 October 2026

### New

- Settings → System → Problem report prepares one file with the player's logs, versions, hardware and settings, to attach to a report of a problem on GitHub or by e-mail. Addresses, names, networks, shares, keys and what is played are taken out on the player first. It is downloaded on a phone or computer.
- Settings → Device → Wi-Fi shows the connected network's signal, speed, band and channel. Secured networks show a lock, open where the password is already saved.
- The user manual, a FAQ, the hardware requirements and a technical guide are on GitHub, linked from the project page.

### Fixed

- Screens open faster while music plays: the visualiser no longer draws while it is hidden.
- Check for updates only checks; it no longer installs when Updates is set to Automatic.
- On a phone, the last setting is no longer hidden behind the volume bar; on a computer, the bar no longer covers a sheet's buttons.
- Setting up a new card, setup's screens fit the attached screen, and a bar screen is turned to landscape before setup starts.
- A visualiser skin download no longer holds up Spotify or Bluetooth: while the player is in use, it downloads more slowly.

### Good to know

- From the next update on, the update screen shows the notes of every release it skips, and the install step's progress moves from the start.

## 0.9.2 — 6 October 2026

### New

- Extended navigation, under Settings → Sources → Lyrion Client, brings Lyrion's own menus to the screen: My Music with every library view, Favourites, and apps. It is off by default.
- Now Playing has a Minimise button in its top-left corner, back to the screen it was opened from.
- The phone's volume sheet keeps its buttons in one row, open or closed. Now playing switches between Now Playing and the screen before it.
- Under Enrichment, one button finds artist portraits and album covers together and shows what its last run found.
- Library albums opened from My Music show track lengths and release details.

### Fixed

- Bluetooth and Spotify tracks find album art more often, including tracks by several artists.
- Search fields bring up the phone's keyboard with one tap.
- The pointer and scrolling from the phone are smoother.
- From the next update on, the update screen stays on its finished steps until Done, and its progress moves steadily.

### Good to know

- Artists on Home is now called Album Artists.

## 0.9.1 — 5 October 2026

### New

- The phone can act as a touchpad and keyboard for the screen. Open the volume sheet on the phone: one finger moves a pointer on the screen and a tap presses. Tapping a text field brings up the phone's keyboard, and what is typed appears on the screen.
- Two fingers on the touchpad scroll what is under the pointer, and a pinch zooms the screen around it. Lines along the right and bottom edges of the touchpad scroll with one finger.
- Pointer style offers two pointers, Dot and Arrow, next to Pointer speed under Settings → Display. Phone touchpad turns the touchpad off.
- The phone's volume sheet has Home, Now playing and Lyrics buttons for the screen. Lyrics opens the lyrics on Now Playing, and turns them off again.
- While the pointer rests on the volume controls, they stay open.
- Online wallpapers no longer repeat until every picture of the day has been shown, and each day brings a new set. Pictures on the device follow the same rule, and artist pictures vary between an artist's backgrounds.

### Fixed

- An update now stops whatever is playing, not only Lyrion.
- When Spotify starts playing, its starting volume holds instead of jumping to the last level.
- Starting volume is now beside Spotify's switch.
- After an update, long notes can be scrolled, and stay until Continue is pressed.
- The TheAudioDB key and Pexels API key can be saved.
- No mouse pointer is left on the screen.
- Some idle screen pictures failed to load and the previous one stayed up.

### Good to know

- The phone and the screen need to be on the same network for the touchpad, as for the rest of the phone's controls.
- Artist pictures are looked up once more after this update, to find each artist's other backgrounds.

## 0.9.0 — 5 October 2026

### New

- Plexamp can be claimed from Settings: paste a claim token from plex.tv/claim and the row shows Claimed. Claim again moves the player to another Plex account.
- Idle screen pictures are placed by what they show: faces, people and animals stay in view instead of being cut off. A picture too close to fit is shown a little narrower, or skipped.
- TheAudioDB adds artist pictures and album covers where fanart.tv has none, for the idle screen and for Update artist portraits and Update album covers. A TheAudioDB key is optional.
- Pexels can be used beside Pixabay for online wallpapers, with its own key. On a bar, the source with more wide pictures is asked first.
- With Headless on, the settings that only affect the screen are hidden, Enrichment included.
- Skin type greys out the types that have no skins for the screen in use.
- Saving a new device name restarts the device, and says where it comes back.
- Setup and Settings have shorter, plainer texts throughout, and errors are written in words.
- A sound card that is not found by itself can be chosen under Settings → Audio → Sound card board.
- Each output shows whether it is Tested, Known or Detected.
- An output whose volume control does not work in decibels plays at a fixed level.

### Fixed

- Spotify no longer lowers loud tracks, and now plays as loud as Lyrion at full volume.
- Saving a setting no longer keeps the buttons disabled for seconds.
- Restoring a backup no longer talks about joining a network.
- Lists count what they hold: backups and saved networks are no longer called paired.

### Good to know

- This update is larger than usual, about 70 MB more, for the picture recognition that places idle screen pictures.
- Without a key of your own, TheAudioDB's shared key is used, and updating album covers can take noticeably longer.
- Claiming Plexamp again registers the player as new in the Plex account; the old entry stays until it is removed there.
- Pexels is not issuing new keys at the moment.

## 0.8.9 — 4 October 2026

### New

- On a bar, Now Playing shows the album art from edge to edge, the lyrics larger and centred without the title above them, and the lyrics button beside the queue.
- On a bar, the volume tray closes with a swipe up from anywhere, including from the volume slider and the bottom of the screen.
- On a bar, while nothing plays, the side rail shows the renderers waiting to be used, sized to fit however many there are.
- On a bar, the idle screen prefers wide pictures and fills the bar with them, and the home screen's background shows the artwork's colours as Now Playing does.
- On a bar, the radio categories have their own icons and colours, and part of the next column shows when there are more.
- The update window shows how far the install step has got, as it does for the download.

### Fixed

- Flinging the queue no longer speeds up by itself and jumps to the last track.
- On a bar, the boot logo appears from the start of the boot, the right way round and whole, instead of after a long blank screen.
- Artist pictures on the artist page are sharper.
- On a bar, the handoff animation shows notes travelling between the two sources, and the pull-down handle is centred beside the album art.

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
