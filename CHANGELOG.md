# Changelog

<!-- Generated from core/src/gexis_core/release_notes.json by
     `python -m gexis_core.changelog`: edit that file, not this one. -->

Every release of Gexis Player and its notes, newest first. The player
shows the last 10 under Settings → System → Change logs.

## 1.7.0 — 27 October 2026

### New

- An equaliser for everything the player plays: ten bands, ten presets and up to ten saved settings, each output with its own. In Settings → Audio, with a quick change in the volume drawer and on the phone.
- The phone page is now a remote: a trackpad or D-pad for the player's screen, quick actions, the volume and the equaliser, and a switch to Settings. For a player without a screen: a large cover and a bar to move through the track.
- With Fixed volume, mute works where the output has a volume control of its own.

### Fixed

- On the phone, a character the player's screen cannot type is now said in a note.
- The Beszel hub has two security fixes (Beszel 0.21.1).

### Good to know

- Off, the equaliser leaves the sound bit-perfect; switching it on or off stops what is playing.
- The phone's mini player is gone; shuffle and repeat are on the player's own screen.

## 1.6.0 — 25 October 2026

### New

- The screen can be used without touching it. With the D-pad of the Gexis Player integration in Home Assistant, or a USB keyboard plugged into the player, the arrows move a ring from control to control, OK opens what it is on, and Back goes back a step or closes what is open - on Home, in the library, on Now Playing and in Settings, on the panels and the bars.
- The first press shows the ring and a touch hides it. In the volume drawer and on a Settings slider, Left and Right change the value. While the screen is in standby, on the idle screen or showing the visualiser, a press only wakes it.
- Home Assistant learns whether the idle screen is switched on, so the integration's card offers it only then.

### Fixed

- Settings → Display → Attached screen names the screen by maker and model, and breaks lines between words rather than in the middle of one.

### Good to know

- Over the Home Assistant dashboard, the arrows and OK go to Home Assistant's own page as they are; Back takes the dashboard down.
- Setup, updates and the factory reset are left to touch and the phone; the D-pad does not act on them.
- The D-pad and the card for dashboards come with the Gexis Player integration 0.4.0 or later, installed in Home Assistant through HACS.

## 1.5.0 — 24 October 2026

### New

- DSI screens: touch screens on the Pi's own display connector, leaving both HDMI ports free for a receiver, a sound bar or a TV. The Raspberry Pi Touch Display and panels built like it are found by themselves; another DSI model is chosen in Settings → Display → Attached screen, and the player restarts and asks Keep this screen?, going back by itself if the screen stays dark.
- On a DSI screen, Screen brightness sets its backlight, and display standby turns the backlight off.
- The player in Home Assistant: with the Gexis Player integration, installed in Home Assistant through HACS, each player shows there as a media player - what plays with its artwork, play, pause, next, previous, volume and the source - with switches for the screen, the dashboard and the visualiser. The player changes nothing in Home Assistant.
- The volume drawer and the bar's pull-down controls stay open when opened on the screen, until they are closed, the visualiser takes over or Home opens. One opened by a change from elsewhere still closes by itself.

### Fixed

- On the bars, the buttons in the pull-down controls work on the first tap right after pulling them down.
- On the bars, every settings panel fits the screen: a number's value sits beside its slider, and Close is no longer cut off.
- Artist pictures and covers that failed to load once are tried again, rather than staying as initials until the screen restarts.
- A Lyrion server chosen in Settings is used at once.
- On the bars, the background pictures vary again; one picture had been shown over and over.

### Good to know

- A four-lane DSI model needs a Pi 5 or a Compute Module; on a Pi 4 the list leaves those models out.
- Tested on the hardware: the Hosyond 7" and the Waveshare 10.1" DSI-TOUCH-A. The other DSI models are listed but untested.
- The Home Assistant integration needs 1.5.0 or later.

## 1.4.0 — 22 October 2026

### New

- A Home Assistant dashboard on the screen. Set its address in Settings → Display → Home Assistant dashboard, then put it up with the house button on Now Playing, in the bar's pull-down controls or on the phone page. It stays until it is dismissed with the tab on its right edge or from the phone, and the music goes on underneath. It can also come up in place of the idle screen at set times.
- From the phone, the touchpad and keyboard work inside the dashboard as well: taps and typing reach Home Assistant's own page, for example to sign in.
- The phone page's mini player is redesigned: the screen's views in one row of round buttons with the current one marked, Screen off beside the Panel heading, and the touchpad between the track and the views.
- Album pages show a track's own artist under its title when it differs from the album's, for example a featured artist.
- Turntable and tape skins use noticeably less processor time.

### Fixed

- The visualiser no longer stops when the screen it is on changes, for example after display standby on a player with two screens.
- Opening the visualiser no longer shows a brief black flash, and its first seconds no longer flicker.
- The visualiser opens over the Home Assistant dashboard when asked for, or when it starts by itself.
- Asking for the visualiser while the screen is in standby no longer leaves it unable to start afterwards.
- With software volume (as on HDMI), the meters show the music again: at a low volume the needles barely moved or not at all.
- After a change of visualiser skin, part of the picture is no longer left black.
- On the bars, previous, next, shuffle and repeat are shown dimmed when they cannot be used for the current track, rather than hidden.
- Tapping a row in the library and Lyrion lists no longer flashes.
- With the phone's keyboard open, the mini player sits directly on the keyboard.
- The browser's offer to save a password no longer appears on the screen.

### Good to know

- Home Assistant has to allow its pages to be shown inside another page before the dashboard can appear. The manual says where to set it; the player changes nothing in Home Assistant.

## 1.3.1 — 20 October 2026

### New

- Two more screens are tested and recognised by themselves: the HMTECH 7" HDMI Monitor (800 × 480) and the HMTECH 10.1" HDMI Monitor (1024 × 600), both without touch.

### Fixed

- The idle screen comes back as it should after the visualiser has been up with nothing playing. Before, it could stay away until the screen was touched.
- On the bars, a tap wakes the screen from standby again, and a screen in standby when the player restarts (for example during an update) is no longer left dark with nothing to wake it.
- After a change to a screen of a different size, the player no longer comes up in a small box in a corner of the screen.

### Good to know

- Some screens take a few seconds to show a picture after waking from standby. The 11.9" bar takes about three.

## 1.3.0 — 20 October 2026

### New

- Between sunset and sunrise, the idle screen's current weather shows the moon in tonight's phase, lit on the side it is lit where the player is.
- Four more styles for Settings → Display → Weather icons: Modern, Futuristic, Photographic (the real Sun and Moon, from NASA photographs) and Atmospheric.
- A USB-to-optical adapter, the Realtek "USB SPDIF Adapter", is marked Tested under Output and starts on Fixed volume, for a DAC or receiver that sets the level itself.
- Through Lyrion, tracks at 88.2 or 176.4 kHz now play on a sound card that lacks those rates, converted to the card's highest rate. Before, they played silence. Every rate the card takes still goes out untouched.

### Fixed

- With Weather icon motion set to Static, the idle screen now stops moving entirely. Before, screens hidden behind it kept animating, and the setting saved almost no processor time.
- The visualiser no longer comes back partly drawn after being hidden while tracks change: no more page showing through, white areas or stepped meter edges.
- The player's web server is updated with three security fixes.

### Good to know

- A converted track is no longer bit-perfect, and plays about 1 dB quieter to leave room for the conversion.

## 1.2.0 — 19 October 2026

### New

- The player's API is documented. Everything its screen and phone page do goes through one HTTP API, now described in full as an OpenAPI file. With Settings → System → API explorer switched on, the player shows it at http://<player>.local:8090/api, where every call can be read and tried. A read-only copy for each release is on GitHub.
- Settings → Library has the Lyrion server's own On switch. Off, the server stops; its library, folders and shares are kept for when it is on again.
- Settings → Sources → Lyrion Client → Navigation is one choice, Simple, Extended or Off, in place of two switches.
- When first use's second part is run again, it lists every Lyrion server found on the network, even with one already chosen, so moving to another server needs no address.

### Fixed

- The waiting and idle screens show a calm picture while their first picture cannot be loaded, for example just after an update, instead of plain grey. A real picture follows as soon as one loads; a black background stays black.
- While the Lyrion server gets ready, the waiting screen's step no longer shows a general sentence before the server names what it is doing.
- Apps calling the player get a clear error, instead of a general fault, when Lyrion's radio is not answering or a control is sent to a source that cannot take it.

### Good to know

- Settings lists its categories as Library, Sources, Handoff, Audio, Display, Enrichment, Plugins, System.
- API explorer is off by default. While it is on, anyone on the home network can try every call from that page, restart and factory reset included. The API itself is open to the home network either way, as the settings are.

## 1.1.1 — 19 October 2026

### New

- In first use, the visualiser starts off. Switching it on starts the download of its skins straight away, and the download carries on while the rest is answered.
- While a new player's Lyrion server gets ready, the waiting screen shows the step it is on, Step 3 of 5 for example, from its download to reading the music, with its progress. This works on standard screens and on bars, and stays until the first read of the music has finished.

### Fixed

- Network shares and USB folders ticked in first use reach the Lyrion server even when the step is left without pressing its Add button.
- The Lyrion server reads the music once, after its add-ons are in, instead of during their install and again afterwards.
- The Lyrion server's own page shows the Material design as soon as its add-ons step is done.
- The player's screen no longer shows the library for a moment before Make it yours.
- In Settings → Library, the links to the Lyrion apps no longer squeeze the tile on a wide screen.

### Good to know

- After first use, the dialog on the player's screen lists only the downloads still running. The Lyrion server's steps are on the waiting screen.

## 1.1.0 — 19 October 2026

### New

- First use comes in two parts. Setup, on a phone, asks only what the player needs to run: the network, a name, the time, the output with its volume type, and the screen. Then, once the player is on the home network, a second part makes it its owner's: how music is listened to, the phone as a touchpad, the visualiser, the waiting and idle screens and standby. It can be put off and done later from Settings → Display → Personalise.
- The Lyrion server on the player reads only the music locations chosen, none at first: its Music folder, folders on USB drives and network shares, ticked at any depth, several at once.
- A Library category in Settings holds the Lyrion server: what it is doing - starting, adding its add-ons, reading the music with its progress - how many songs and albums it holds, and links to its own page and to the Squeezer, Lyrion and LyrPlay apps.
- While a new player reads its library for the first time, the panel says so in large on the waiting screen; the other sources play meanwhile.
- Getting ready, at the end of setup, follows every download and install as it happens, and the Lyrion server's first start as a numbered checklist with its progress.
- Restoring a backup in setup lists everything it brings back, grouped by Settings section.
- The Music share stops taking new files while less than 4 GB is free on the card, so the player keeps room for itself; the Music folder's row shows the free space.
- Screens and sound cards are marked Tested when they have been, and otherwise not marked.
- The waiting screen shows each source as a mark with its name, pulsing on the picture.
- With nothing playing, the library has a colourful picture behind it instead of plain grey.
- The setup network's password is always gexis-setup, and password fields can show what is typed.

### Fixed

- The visualiser opened from the phone fills the screen; it was sometimes drawn shifted.
- An update no longer resets the visualiser's choice of skins.
- The panel no longer opens an empty Now Playing, and the Lyrion player no longer takes over by itself when its server starts with nothing to play.
- Settings' switches move as soon as they are tapped.
- The panel no longer selects text or opens a menu on a long press.
- A Bluetooth device's "Not Provided" is no longer shown as a title.
- The sources on the waiting screen are centred, however many are on.

### Good to know

- A player that already runs the Lyrion server keeps reading its Music folder and USB disks as before.
- Taking a location away from the Lyrion server makes it read the whole library again, which for a large library takes hours; the settings say so.

## 1.0.6 — 17 October 2026

### New

- In Settings → System → Restore, on a phone or computer, Add a backup puts a backup file from that device in the list. The player checks it first and restores nothing until it is chosen.

### Fixed

- A backup downloaded from Restore keeps its name when saved, and one a browser saved with an extra ".gz" at the end is listed in Restore too.
- A backup cut short by a power cut is no longer listed as one that can be restored; an empty or damaged backup says so and offers only Forget.
- Small backups show their size in KB instead of "0.0 MB".
- At the top of Settings, the player's address moves to the next line on a narrow screen instead of being cut off.

## 1.0.5 — 16 October 2026

### New

- In file managers that browse the local network, players appear by their name instead of their address.

### Fixed

- The switch to other players, at the top of Settings on the phone, shows again: one player that did not answer on the network hid all the others.
- With Headless on, Settings no longer shows the screen in use, its ports or its rotation.
- In Settings, ticking and unticking an option shows at once, without the row staying lit after the tap.
- In lists from Lyrion's apps, a tapped track shows only its selection, without lighting up first.

### Good to know

- In lists from Lyrion's apps and in their search, a second tap on a selected track puts its actions away. Only Play plays it.

## 1.0.4 — 16 October 2026

### Fixed

- When looking for a Lyrion server, each one is shown by its machine's name, or by the name it was given in Lyrion, rather than by its address.
- When scanning the network for shares, a machine announced under two names is listed once, by its name.
- In lists with several choices, such as wallpaper topics, a tap shows at once, and a quick second tap no longer undoes the first.
- Settings opens and refreshes faster, and the rest of the player waits less while it does.

## 1.0.3 — 16 October 2026

### Fixed

- On the player's own screen, Update goes straight to the full-screen update view, without the small window first.
- On a bar, the apps from Lyrion fill the screen's width instead of gathering on one side.
- On a bar, a playlist from one of Lyrion's apps no longer shows an empty column with a line beside its tracks.
- In lists from Lyrion's apps, a tapped track lights up instead of shrinking and growing back.

## 1.0.2 — 15 October 2026

### New

- If no phone has joined the setup network within two minutes, it moves to the next Wi-Fi channel, and again every two minutes until one does. The setup screen shows the channel and counts down to the next.

### Fixed

- With HDMI as the output, the headphone jack takes over when the HDMI device (a TV or receiver) is switched off, and hands back when it is on again. In 1.0.0 and 1.0.1 this never happened.
- An output that is not connected, such as an unplugged USB DAC, is no longer noted in the player's log every three seconds.

## 1.0.1 — 15 October 2026

### Fixed

- The setup network, gexis-setup, can be joined on every screen: it now uses the Wi-Fi channel least disturbed by the player's own screen. On the 11.9" bar the screen's cable drowned out the channel it used, and phones saw the network come and go but could not connect.

### Good to know

- Gexis Player 1.0.1 is the first release on the Stable channel, with the image to install it from.

## 1.0.0 — 14 October 2026

### New

- Gexis Player 1.0.0 is the first release on the Stable channel: players set to Stable receive it, and the image to install it from is published with it.

### Fixed

- Restoring a backup never writes through a link already on the card, and backups taken while a plugin's folder holds links or pipes can be restored. Plugins installed by hand are stopped while their data is put back.
- Keep this screen? shows its buttons on every listed touch screen; where the player cannot tell that a screen's touch works, it can also be answered from the phone page.
- A TV chosen as the screen keeps its port after a change of rotation or model, and a screen chosen before 0.12.0 keeps its touch.
- A change of output is made once, not twice.
- An update cut short by a power cut is finished safely: Check for updates repairs it without installing anything newer, never while music plays, and the player restarts once it is done.
- The visualiser's skins no longer stop downloading part-way.
- Setup over a network cable can add a Wi-Fi network as well.
- Back from a similar artist's page returns to the artist before it, and Home on the phone after opening an album from Now Playing goes to the library.
- A streaming album with a guest artist on one track is no longer called a playlist.
- Text size reaches every piece of text on the screen.
- A touch on the screen while the visualiser rises lowers it again.
- Artist photos and backgrounds from before a library rescan are no longer shown for another artist.

## 0.15.0 — 14 October 2026

### New

- Settings → Display → Text size makes the writing on the player's screen larger or smaller, from 90 % to 130 %. Home's tiles grow with larger text.
- Attached screen and Screen port are two tiles again. Screen port shows what is plugged into each HDMI port; Change on Attached screen opens the list of makers.
- An artist's name, a similar artist and a release title open their page in the library.
- A streaming service's playlist shows each track's artist under its title, and its button says Play playlist.
- The phone's sheet opens and closes with a swipe up or down.

### Fixed

- The touchpad pointer moves more smoothly, and the touchpad reconnects within about a second when the phone has been idle. Wi-Fi power saving is now off on the player, which caused delays.
- The pointer outlines everything that can be pressed, in its own shape, and only the part that shows; its dot shrinks inside the outline. A track's Play, Queue and Add buttons each keep their outline, and Now Playing's tabs are underlined instead.
- Home's top row scrolls with the touchpad.
- A touchpad tap on the visualiser only closes it, without pressing what lies underneath.
- An artist's Popular tracks show Play, Queue and Add on the first tap, like every other track list, and a row turns teal while its actions show.
- A service's Search opens straight on its field, with the phone's keyboard up.
- The queue shows the covers of streaming tracks not played yet.
- Album Artists keeps its photos when the Lyrion server rescans its library.
- A TV turned off and on again comes back at its full size.
- After a name clash on the network, the player takes its own name.local back within a few minutes.
- Keep this screen? counts its two minutes from when it appears.

### Good to know

- The first library rescan after this update still clears the artist photos once; they are kept from then on.

## 0.14.0 — 13 October 2026

### New

- Settings → Display → Screen is one tile: the display in use and its HDMI port. Tap it to choose which port is the screen; Change picks the screen's model from the list.

### Fixed

- A TV chosen as the screen runs at 1920 × 1080, taken from the sizes it offers, and stays there. Behind an AV receiver it could come up at 640 × 480, or at 1280 × 720 with everything too large.
- Display standby no longer silences the music when the screen's HDMI port also carries the sound: the picture goes black and the sound goes on.
- While a TV is the screen, a touch panel on the other HDMI port is switched off, and touching it does nothing.
- A screen port chosen stays chosen when an AV receiver names the TV differently at a start.
- With two screens connected, the start no longer shows a cut-off logo or console text on one of them.
- The backup before an update no longer fails when a plugin removes one of its files while the backup runs. A backup that does fail stops the update at once and says so.

### Good to know

- If a TV cuts off the edges of the picture, set its picture size to Just Scan or Original.

## 0.13.0 — 13 October 2026

### New

- A TV can be the screen: connect it to either HDMI port and choose that port under Settings → Display → Screen port. The port chosen stays the screen, even with a touch panel on the other port. A 4K TV runs at 1920 × 1080 and scales it to its full screen.
- A TV has no touch, so Keep this screen? is answered on the phone page. Not answered in time, the player goes back to the screen before.
- Under each HDMI port, the Output picker shows what is connected and the sound it takes, for example "LG TV · up to 192 kHz / 24-bit", or "takes no sound".

### Fixed

- An update cut short by a power cut is finished when the player starts again. Before, it could be left half-installed while Settings said the player was up to date.
- Update… checks again before offering a release, so it offers what the channel holds now, with its notes. Before, it could show a release from the last nightly check.
- When there is nothing on the chosen update channel, or no network, Could not check for updates says so in words instead of a web address and an error code.

### Good to know

- While a TV is the screen, a touch panel on the other HDMI port shows black and ignores touches.

## 0.12.0 — 13 October 2026

### New

- Multichannel files (5.1, 7.1) from Lyrion play complete, folded down to stereo: FLAC, WAV, AIFF, DSD and Opus. Before, a multichannel FLAC lost its centre and surround channels, and a multichannel WAV did not play.
- The screen's HDMI port is one tile under Settings → Display. With something on both ports, it chooses which one the screen is on and says what is connected to each. On a board with one HDMI port it is information only.
- Visualiser tweaks has two new rows. Needles follow the volume is either Half the drop or Like a real amplifier. Gain raises or lowers the needles and bars together, from −10 to +20 dB.

### Fixed

- The spectrum's right-hand bars show the treble at its real level. On most music they used to be the tallest bars on the screen.
- The needles and bars follow the volume visibly, from the moment the player starts. On Fixed they show the recording, on every output.
- A screen confirmed in setup is kept. Before, it could stay unconfirmed, and the player kept the setup network's fixed password.

### Good to know

- An HDMI port used only for sound, such as an AV receiver, shows a black picture.
- If the HDMI output chosen for sound has nothing connected, the headphone jack plays instead, at its own volume. Sound goes back to HDMI by itself when the cable is back. Either switch stops what is playing.
- A folded-down multichannel file plays about 8 dB quieter than a stereo one, so nothing clips. Ogg Vorbis and ALAC files with more than two channels still do not play.
- The spectrum no longer lifts the treble: on most music the right-hand bars are now shorter than the middle ones.

## 0.11.0 — 12 October 2026

### New

- USB DACs are shown by their maker, with a line saying what each reports it can play, for example "USB 2.0 · up to 768 kHz / 32-bit · native DSD".
- Native DSD: on a DAC that takes DSD, with the volume on Fixed, DSD files from Lyrion play unconverted.
- Each plugin in Settings → Plugins shows its version.
- The screen works on either HDMI port; a bar screen moved to the other port asks "Keep this screen?" at the next start.

### Fixed

- A DAC that accepts only 32-bit audio (as many USB DACs do) now plays Bluetooth and other 16- and 24-bit sources, every sample kept as it was.
- On a DAC that goes above 384 kHz, Lyrion files above that rate no longer play at the wrong speed.
- Screen rotation works on a screen that is not in the player's list.
- The player switcher shows each player once.
- Uploaded plugins that are switched on start with the player, and one restored without its package no longer retries endlessly.
- Why an option cannot be chosen now shows on its own line across the tile, in amber.

### Good to know

- Uploaded plugins can no longer announce themselves on the network; the player announces them, so the player keeps its own network name.
- The visualiser stays still while DSD plays.

## 0.10.2 — 12 October 2026

### Fixed

- On the Raspberry Pi's own headphone output, mute and volume 0 are silent; they had played at full volume.
- The volume keeps its level across a change of output or volume type, and Software volume no longer starts loud after a power cut.
- Changing the output stops playback, as a change of volume type does, and no longer starts sources that were switched off.
- Bluetooth follows each phone's volume, and a pairing request wakes the screen from standby.
- A player on a cable leaves the setup network by itself, and setup over a cable no longer restarts before Finish.
- Restoring a backup can no longer place files outside the player's settings.
- An update cut short by a power cut is finished or undone at the next start.
- The problem report takes out more personal details, and the player keeps responding while it is prepared.
- A network share that does not answer no longer holds up the others or Settings.
- The phone's volume slider moves only on a tap or a sideways drag.
- The screen no longer stays on "Updating…" when an update stops without finishing.

### Good to know

- Only the three newest backups made before updates are kept; backups made by hand are never deleted.
- A factory reset also clears the screen's browser data and the settings chosen when the card was flashed.
- Artist and lyrics information stays within what the card can spare.
- A device name is one line of text.

## 0.10.1 — 11 October 2026

### New

- Switching between players on the phone: with more than one Gexis Player on the network, the button at the right of the Settings title lists them, each with what it is playing and through which source; choosing one opens its page.
- Settings → System → Problem report works in three steps: what happened and how often; a checklist showing what the player gathers and what it takes out; then sending it - on GitHub, already filled in with what happened and the log's last errors, or as a file to send by e-mail.
- Hardware feedback ends on the same choice: on GitHub, filled in, or a text file to send by e-mail. The last one prepared stays under its row, with Send again and Start over, until the sound card or screen changes.
- With Volume on Fixed, Plexamp stays at full level: its app's volume slider goes straight back to 100, and the amplifier sets the volume.

### Fixed

- Changing the volume type stops playback at once and reconnects the sources on the new type, Fixed included.
- Leaving Fixed, the volume returns to where it was before, and Spotify starts no louder than its starting volume.
- The Space topic shows pictures of outer space.
- Hardware feedback: its answers reach the GitHub form; the test pattern shows over the visualiser and wakes a dark screen; the tones wait while a paused source holds the sound card; only touch screens are asked for taps; long notes no longer push out what the player read.
- The visualiser starts after a fresh setup without first being asked for, and asking for it no longer reports an error.
- A choice in Settings is marked the moment it is tapped.
- The phone page reconnects as soon as it is brought back to the front.
- Copy works on the phone page.
- During the first start, a skin pack being installed shows Installing… with a moving bar instead of standing at 100 %.

### Good to know

- Setup asks "Keep this screen?" only when the screen chosen changes what the player applies.
- Problem reports and hardware feedback still need a GitHub account to send through GitHub; the e-mail route needs none.

## 0.10.0 — 11 October 2026

### New

- Display standby. The Screen button in the phone's mini player turns the panel's screen off; a touch, music starting or the button again turns it back on, and the player keeps playing. Settings → Display → Display standby → Scheduled standby turns it off at up to six standby times, each with its own days. Woken during one, it goes dark again after 2 minutes unused (adjustable up to 30).
- The home screen and the idle screen each have their own background. With the Lyrion client off, the home screen's is set under Settings → Display → Home screen.
- The idle screen can be switched off. It is off on a new player; a player already in use keeps it on.
- Weather icon motion: Animated or Static. Static icons use far less of the processor while the idle screen is up.
- Online wallpapers gain Space and Calm among the topics. On New Year, Christmas and Easter, Holidays shows that day's pictures in their place.

### Fixed

- A player that loses its network while running now opens its setup network after two minutes, as it does at start, and goes back to its saved network when that returns.
- A phone page open while the player rejoined its network could switch to the setup page and stay there.

### Good to know

- Settings → Display is arranged in sections: Panel, Display standby, Touchpad, Volume, Photo service and location, Home screen, Idle screen, Visualiser.
- Settings explain each option beside it instead of above the list, and such sheets stay open until closed. In Volume, only Fixed asks to confirm.
- The Space pictures background is removed. A player that used it shows Gexis wallpapers instead, and space photos are available as a topic of online wallpapers.
- Seasons applies to Gexis wallpapers only.
- The player's own wallpapers are 89 pictures, all public domain or CC0.

## 0.9.9 — 10 October 2026

### New

- The screen after setup that shows the downloads can be put away at any time with Use the player now. The downloads go on, and Settings shows how far they are. A download that does not finish brings the screen back, saying which one and where to try again.
- Setup's Screen step lists screen makers as buttons, each with its number of models. Tapping one opens its models, so the list is much shorter on a phone.

### Fixed

- A restore switches on only the plugins that were on when the backup was made. In 0.9.8 a plugin that had never been switched on came back on, and the screen after setup waited for its download.
- Setup recognises the Waveshare 11.9" bar screen straight away, as it does the 10.1" and 13.3" screens, instead of asking for it from the list.

## 0.9.8 — 10 October 2026

### New

- Reset to factory settings, under Settings → System: hold the button for 3 seconds to confirm. Every setting, network, pairing, sign-in, skin and plugin is cleared and setup starts again. The music folder, its playlists and the Pictures share stay.
- Two new backgrounds for the idle screen. Gexis wallpapers are public-domain photographs in three styles (Calm, Colourful, Psychedelic) that can follow the time of day, the seasons, and New Year, Christmas and Easter for the player's country. Space pictures shows new pictures from NASA and ESA.
- With the Lyrion client off, the waiting screen shows the clock, the date and the player's name over the background, with a tile for each source.
- Settings: Device is now part of System, grouped under This player, Network, Updates, Backup and reset, Help, About and Power.
- The browser tab shows the player's name.

### Fixed

- Setup's own Wi-Fi uses WPA2 only: a phone preferring WPA3 could not join it.
- Lyrion plays to this player even when another player on the server has the same name.
- A restore in setup no longer stops on setup's last screen; the skins download after the restart, with their progress shown.
- A restore brings Lyrion, Spotify, Bluetooth and the plugins back on or off as they were. Setup's Plugins step lists only plugins.
- After setup the screen no longer blinks when the downloads finish, and a skin pack shows its progress.
- Choosing Fixed volume while music plays now says that it starts at the next pause or stop, instead of looking already on.
- On a bar screen, the boot screen's background is one colour on both sides of the logo.

### Good to know

- The Lyrion client is now called Lyrion on every screen.
- On a bar screen, Minimise on Now Playing has the size and place of the library's Back button.
- A player already in use keeps its background; a new player starts on Gexis wallpapers.
- The player's own wallpapers make this update about 26 MB larger.

## 0.9.7 — 9 October 2026

### Fixed

- An install or update cut short - by a power cut, for instance - is finished by the player itself the next time it installs anything. Until now a skin pack could stay missing, retried every few minutes, with the screen saying its download had stopped.
- With no visualiser skins installed yet, the visualiser waits for them quietly instead of showing as failed.
- On a bar screen, the Minimise button on Now Playing points right, to the mini strip, and a tap near its top no longer opens the tray.

### Good to know

- Plexamp's plugin is at 0.4.4: while Plexamp is not answering, its log says so once instead of every second.

## 0.9.6 — 9 October 2026

### New

- Settings → Device → Cable shows a network cable's speed and address, and its address can be set Automatic or Manual. A manual address is kept only once it is confirmed from the new address within 60 seconds; otherwise the old one comes back. The connected Wi-Fi network has the same choice under its details.
- While a network cable is plugged in, the Wi-Fi steps aside; unplug it and the Wi-Fi connects again.
- Settings → System → Restore offers Download beside each backup on a phone or computer, to keep a copy off the player for a newly flashed card.
- Hardware feedback comes in three steps - the screen, the sound, then room for notes beside what the player adds to the feedback itself.

### Fixed

- Restoring a backup during setup applies its name, time zone and other answers, and asks for this player's own output and screen. Restored as a second player, it leaves the first one's Beszel connection - the hub's address and keys - and Plexamp's claim behind.
- A Plexamp claim that does not work leaves nothing behind and says why on its row, and Plexamp is offered as a source only once it is installed and answering.
- Download and Forget on a backup press only the button, not the whole row.
- On a bar screen, a confirmation such as Reboot takes its own height instead of the whole screen.

### Good to know

- Plexamp's plugin is at 0.4.3.

## 0.9.5 — 8 October 2026

### New

- First-time setup can restore a backup: after the Wi-Fi, choose Restore a backup and the backup file on the phone. The review shows what it brings, and anything setup asks - the name, for instance - can be changed there, so one player's backup can start another. Given another name, the new player leaves the first one's Beszel identity, Plexamp claim, Spotify sign-in and Bluetooth pairings behind.
- The spectrum covers 50 Hz to 16 kHz at every sample rate, with more bars for the bass and the higher bars lifted a little, so the bars on the right move with the music. Each spectrum skin draws as many bars as its panel holds.
- Settings → System → Beszel says whether the agent has reached its hub: Connected, Connecting or Not connected.

### Fixed

- A Beszel Hub public key that is not a key is refused when it is saved, and a plugin that cannot start says so beside its switch.
- On a phone, Settings no longer slides sideways.

### Good to know

- Spotify Connect (go-librespot 0.10.3) starts the first skip at once, and the Beszel agent and hub are at 0.21.0.

## 0.9.4 — 8 October 2026

### New

- Settings → Audio → Volume is one setting: Hardware (the sound card's own control), Software (the player sets the level itself, on any output) or Fixed. On an output with no control of its own, such as HDMI, Software takes Hardware's place, and the visualiser works over HDMI too.
- Settings → System → Hardware feedback: a short check of the screen and the sound - a test pattern with four taps, and test tones at 44.1, 96 and 192 kHz - then feedback on GitHub, filled in with what the player reads of its hardware. Sound cards and screens owners report as working are marked Reported.
- First-time setup offers the plugins - Plexamp, the Lyrion Server, Beszel - and the first start shows each download arriving until the player is ready.
- The IQaudIO Pi-DAC PRO is tested.

### Fixed

- Changing the output or the volume mode, or a phone connecting over Bluetooth, no longer makes the volume jump.
- The volume follows the output after switching between the sound card and HDMI.
- Spotify keeps to the starting volume even when it takes a moment to connect.
- Bluetooth takes the player again when the phone plays after a pause.
- The visualiser comes back if it stopped, and a skin that cannot be shown is skipped.
- The Lyrics tab shows five lines, without a heading of its own.
- Maximum volume shows 100 % on a new card.
- Find portraits and covers shows its progress from the start, and tapping it lights only its button.

### Good to know

- Bluetooth is discoverable by default.
- Online wallpapers come from Pixabay only: Pexels no longer issues keys.
- From this release on, an update that does not come back properly returns to the release that was there, also after a restart of the device, and nothing can start playing while one installs.

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
