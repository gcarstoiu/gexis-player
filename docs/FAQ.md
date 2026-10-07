# Gexis Player: questions and answers

For people who use the player day to day. It describes the player as of
the release it ships with. Setting names are written as they appear in Settings, with
their place: *Settings → Audio → Maximum volume* means the Audio page, row
*Maximum volume*. Settings opens on the screen and, in the same form, on any
phone or computer on the same network.

---

## Sound and playback

**The music stutters, and Settings will not load on the phone. What is wrong?**
Most likely the player's Wi-Fi connection is poor. On one player, a large
13.3″ screen setup (the panel, its power supply or its HDMI cable) jammed the
player's Wi-Fi: a fifth to a third of the network traffic was lost, which was
heard as stuttering and seen as Settings failing to load on the phone. With
that screen unplugged, or swapped for another, the network was clean again.
Try the player with the screen unplugged for a moment; if the stutter goes,
move the screen's cable and power supply away from the Pi, try another cable,
or connect the Pi to the router with a network cable, which avoids the
problem entirely.

**Will a library scan by the Lyrion server interrupt the music?**
It should not. The Lyrion server runs at the lowest priority, and 40 minutes
of playback during a full scan of a large library had no gaps. The Pi
does get warm during a scan (close to the temperature where a Pi 4 starts
slowing itself down), so a heatsink or fan is recommended.

**There is a click at the start of some tracks. Why?**
It happens when the next track has a different sample rate from the last
(for example 44.1 kHz followed by 96 kHz). The DAC clicks when its clock
changes. It is the price of bit-perfect playback: each track is sent at its
own rate, without resampling. Tracks at the same rate play on without it.

**Is the sound bit-perfect?**
Through a DAC with its own volume control, yes, up to 24-bit / 192 kHz: the
volume is set in the DAC's own hardware, not by changing the samples. Three
exceptions: over HDMI the sound is not bit-perfect; with *Settings → Audio →
Volume* on *Software* it is not bit-perfect below 100 %; and Plexamp lowers its
volume inside its own software, so below 100 in the Plexamp app it is not
bit-perfect either.

**Why is there no volume slider?**
*Settings → Audio → Volume* is set to *Fixed*. Fixed sends the full level all
the time, for an amplifier that sets the volume itself; the screen shows a
padlock instead of a slider. To get the slider back, choose *Hardware* (the
sound card's own volume control) or *Software* (the player recalculates the
sound - not bit-perfect below 100 %). On an output with no volume control of
its own, such as HDMI, Hardware is greyed out and Software is used in its
place. Turn the amplifier down before switching to Fixed: in Fixed,
*Maximum volume* and Spotify's *Starting volume* no longer apply (both rows
are hidden), and every source plays at full level.

**Can the player be stopped from ever playing too loud?**
Yes: *Settings → Audio → Maximum volume*. Set it to 80 and the player is never
louder than the slider at 80, from any source. 100 % on the screen, in
Lyrion and on a phone then all mean that level, so no control shows a number
louder than what comes out. It does not apply with *Volume* set to
*Fixed*: then the player always sends the full level, and the amplifier is
what limits the volume.

**Spotify started much louder than the music before it. Can that be avoided?**
*Settings → Sources → Spotify Connect → Starting volume* (default 60 %) is the
loudest Spotify starts at when it takes over, whatever the Spotify app was
last set to. A lower level is kept; a higher one comes down to the setting.
For the first few seconds the player holds that level even if the phone sends
its own, higher one. (Spotify's loudness normalisation is off on the player,
so at full volume it is as loud as Lyrion.) Like *Maximum volume*, it does
not apply with *Volume* set to *Fixed*.

**The bottom of the volume slider is very quiet, or the middle is too loud.**
*Settings → Audio → Volume curve* sets how the slider's travel maps to
loudness. *Cubic*, the default, puts half travel at −15.5 dB, the way most
volume controls behave. *Linear (dB)* spreads the decibels evenly, which
makes the lower half much quieter.

**Plexamp at the same number is quieter than Spotify or Lyrion. Why?**
Plexamp keeps its own volume. The Plexamp app's slider changes Plexamp's
level inside its own software; the screen's slider changes the DAC. The two
numbers are separate, and Plexamp's level comes on top of the DAC's.

**The volume panel opens on the screen by itself. Why?**
Someone changed the volume from a phone or app, and the screen shows it.
*Settings → Display → Show volume when changed elsewhere* switches this off,
and *Volume drawer auto-hide* sets how long it stays up. Changes made on the
screen itself never open it.

**Can Spotify and Bluetooth play at the same time?**
No. One source plays at a time, never mixed. Starting music from another app
takes the player over: the previous source is stopped first, a short
transition screen shows who is taking over, and the new one plays. Nothing
needs to be disconnected first.

**Can the transition screen be shortened or turned off?**
Yes: *Settings → Handoff → Show transition screen*, and *Transition screen
length* (1 to 5 seconds) for how long it stays up. A takeover still in
progress when the time runs out keeps it up until it finishes.

**When Spotify stopped, the player went back to Lyrion on its own. Why?**
*Settings → Handoff → Reclaim LMS when a session ends* is on. When Spotify,
Bluetooth or Plexamp stops, Lyrion then takes the player back. A phone that
locks can end a Spotify session, so with this on, the player can switch to
Lyrion without warning. It is off by default.

**When Lyrion gets the player back, does it start playing again?**
That is *Settings → Handoff → Restore transport on return*: *Play only if
playing* (the default) resumes only if Lyrion was playing when it was taken
over; *Always pause* and *Always play* do what they say.

---

## Screen and touch

**The screen goes black for a moment every so often.**
Check the HDMI cable. On a 13.3″ screen, short blackouts every minute or so
were caused by the cable, even though the same cable had worked on a smaller
screen. A new cable stopped them. The player itself showed no fault at the
time, which is typical of a cable problem.

**After choosing a screen, tapping Keep does nothing.**
Check that the touch cable (the USB lead from the screen to the Pi) is
plugged in firmly; on one player a loose touch cable was the cause. If Keep
is not tapped within two minutes, the player goes back to the screen it had
before, so nothing is lost.

**What is "Keep this screen?"**
Whenever a screen change alters the picture (a new screen, another model
chosen in *Settings → Display → Attached screen*, or *Screen rotation*), the
player restarts on it and asks *Keep this screen?* (*Keep this rotation?*
after a rotation change). Without a tap on Keep
within two minutes it goes back to how it was, so a screen that shows nothing
cannot lock anyone out. A screen mounted upside down is set with *Screen
rotation*, 180°.

**I attached a different screen. Does it need setting up?**
Usually not. A screen the player recognises is used straight away at start,
and asks *Keep this screen?*. Any other screen is asked about, and the list
of screens opens on its size. The layout follows the screen: *Standard* for
ordinary screens, *Bar* for wide strip screens (such as the tested 1280 × 400 and 1480 × 320),
which are turned to landscape. On the very first start, setup's own screens
are already laid out for the attached screen; setup's Screen step then
confirms it.

**Which screens work?**
HDMI screens only. Tested on the hardware: a 10.1″ 1280 × 800 (the reference
screen), a 13.3″ at 1920 × 1080, and the 1280 × 400 and 1480 × 320 bars.
Others in *Settings → Display → Attached screen* are listed but untested;
those tested are marked *Tested*, those owners have reported working
*Reported*. DSI and DPI screens are not supported.

**Can the player run without a screen?**
Yes. *Settings → Display → Headless* turns the screen off, and every setting
that only affects the screen is hidden while it is on. Everything else,
including all sources and Settings on the phone, keeps working.

**How do I type into a text field on the screen?**
With the phone: open the volume sheet on the phone page, use the touchpad to
tap the field on the screen, and the phone's own keyboard comes up; what is
typed appears on the screen. Every text setting can also be filled in
directly from Settings on the phone.

**How do I get back from Now Playing to where I was?**
Tap the Minimise button in Now Playing's top-left corner. It returns to the
screen Now Playing was opened from. Home stays where it is, for the start of
the library.

---

## Idle screen and visualiser

**When does the idle screen appear?**
After *Settings → Display → Idle screen → Timeout* (default 5 minutes) with
nothing playing and nobody touching the screen. It shows a clock, the
weather and a background picture. A touch, or music starting, brings the
player back.

**Where do the idle screen's pictures come from?**
*Settings → Display → Idle screen → Background* chooses: *Artist pictures*
from the library; *Wallpapers online* from Pixabay (it needs a free key, entered
in the row below); *Wallpapers on device*, read
from the player's Pictures share on the network; or *Black*. Pictures are
placed by what they show, so faces, people and animals stay in view.

**The online wallpapers keep repeating.**
They no longer repeat until every picture of the day has been shown, and
each day brings a new set. *Wallpaper topics* sets which Pixabay categories
are drawn from; choosing several mixes them.

**The weather is for the wrong place, or not shown.**
Set *Settings → Display → Idle screen → Location* to a city or place name.
*Forecast* chooses today only or three days; *Weather* turns it off. The
forecast comes from Open-Meteo and needs no key.

**Can the idle screen be used as a photo frame?**
Yes: switch *Clock* and *Weather* off under *Settings → Display → Idle
screen*, and only the pictures remain. *Change the picture every* sets the
pace, and *Background brightness* how bright they are.

**When does the visualiser appear?**
After *Settings → Display → Visualiser → Timeout* (default 10 minutes) of
music playing without a tap or a skip; *Stop when nothing is playing* gives
the screen back after silence. It can also be opened from Now Playing, or
toggled from the phone page.

**There is no visualiser, or no skins to choose from.**
The skins are a separate download: *Settings → Plugins → Visualiser → Visualiser
skins*. Each screen size gets its own set (from about 50 MB to about 490 MB);
switching it off removes them. While music plays, or for 10 minutes after a
phone connects over Spotify or Bluetooth, the set downloads at no more than
3 MB/s, so the music keeps its share of the network; otherwise at full
speed. Over HDMI audio output the visualiser moves only with
*Settings → Audio → Volume* on *Software*; on *Fixed* it does not.

**How do I pick one skin and keep it?**
Under *Settings → Display → Visualiser*, choose a *Skin type*, switch off
*Rotate skin per track*, and choose a *Skin*: tapping one previews it, and
nothing changes until *Use this skin*. On the phone, swiping left or right
moves to the next or previous skin. Note that applying *Spectrum smoothing*
or *Needle fall time* under *Visualiser tweaks* stops the music for a moment
while the sound card is reopened.

**Some skins show a slideshow of the artist. Where do the photos come from?**
From the Lyrion server's Music & Artist Information plugin. They are the
*Fanart* skins; the photo changes every 20 seconds.

---

## Phone and touchpad

**How do I open the player on a phone?**
In any browser on the same network, open `http://gexis.local:8090`, with the
player's own name in place of *gexis*. It can be saved as a bookmark or added
to the phone's home screen. There is no app to install.

**What can the phone do?**
Everything in Settings, plus a mini player at the bottom: the source, the
title, the volume, and one row of buttons for the panel - Home, Now Playing,
Lyrics, Visualiser and Idle screen. Opening the sheet adds a touchpad for the
screen. Browsing the library happens on the screen, or in the
streaming app.

**How does the touchpad work?**
Open the volume sheet on the phone. One finger moves a pointer on the
screen, a tap presses, two fingers scroll, and a pinch zooms. The lines along
the right and bottom edges scroll with one finger. Tapping a text field on
the screen brings up the phone's keyboard. A touch outside the sheet closes it.

**The pointer is too slow, or hard to see.**
*Settings → Display → Pointer speed* (150–400 %) and *Pointer style* (*Dot* or
*Arrow*). *Phone touchpad* switches the touchpad off altogether.

**The touchpad or the phone page does nothing.**
The phone and the player must be on the same network. If the page loads but
is slow or drops out, see the Wi-Fi questions: a poor connection shows on the
phone first.

---

## Network and Wi-Fi

**How do I change the Wi-Fi network?**
*Settings → Device → Wi-Fi* lists the networks in range. A secured network
needs its password the first time; saved networks join in one tap. The time
zone is taken from the network; set it in *Settings → Device → Time zone*
only if that comes out wrong.

**How good is the player's Wi-Fi connection?**
Open *Settings → Device → Wi-Fi* and tap the connected network. It shows the
signal (in dBm and as a percentage), the speed the radio is using, the band
and channel, and the player's address, updated every few seconds. As a rough
guide, a signal above −67 dBm is good for music; below −75 dBm, stutter
becomes likely. A 5 GHz network is usually faster but reaches less far than
2.4 GHz.

**The player lost Wi-Fi while running and has not come back.**
Restart it. A player only checks its Wi-Fi when it starts: if it cannot reach
its network then, it opens its own setup network after 90 seconds, and keeps
looking for the saved network every few minutes.

**What is the player's name, and can it be changed?**
*Settings → Device → Device name* is one name for everything: the network
address (`name.local`), the Lyrion player, the Spotify Connect device, the
Bluetooth name and Plexamp. Changing it restarts the player, and Settings
says at which address it comes back.

---

## Setup and first boot

**How is a new player set up?**
On first start with no network, the player opens its own Wi-Fi, called
*gexis-setup*. The screen shows two QR codes: one to join that network, one
to open the setup page. The phone then walks through Wi-Fi, a name, the
clock, the output, the music and the screen.

**What is the setup network's password, and why does the phone say it has no internet?**
The password is shown on the screen; a player without a screen uses
`gexis-setup`. The phone's warning about no internet is expected: stay
connected, as the setup page is served by the player itself.

**The setup page disappeared halfway through.**
The player has one radio, so it either hosts its setup network or joins the
home Wi-Fi, never both. When setup finishes and the player moves over, the
phone loses the page. Put the phone back on the home Wi-Fi and open the
address the last setup screen showed. If a Wi-Fi password was wrong, setup
comes back with the reason and keeps everything else that was entered.

**Setup says it found no Wi-Fi, or no audio output.**
It says so when it finds none. For Wi-Fi, move closer to the router, or set
the player up over a network cable. For audio, check the DAC is seated
firmly; a board that is not found by itself can be chosen later in
*Settings → Audio → Sound card board*.

---

## Library and Lyrion

**Does the player need a Lyrion server?**
For browsing and playing your own music files, yes. It can use a Lyrion
server elsewhere on the network, or run one itself. Spotify, Bluetooth and
Plexamp work without one.

**How do I run the Lyrion server on the player itself?**
Switch on *Lyrion Server* on the Plugins page; its rows are at the top of
*Settings → Sources*. It needs internet the first time, as it is downloaded,
and takes about 3 minutes to set up. Its own pages (Material Skin) are then
at `http://gexis.local:9000`, with the player's name in place of *gexis*. The
player never switches to it by itself: choose it in *Settings → Sources →
Lyrion Client → Server*.

**Where can the player's Lyrion server find music?**
The player's own Music folder (shared on the network), USB disks, and
network shares (SMB or NFS). Under *Network shares*, a scan lists the servers
on the network and then their shares, with a login where needed; a share
that does not announce itself can be added with *Add by address*.

**How long does the first scan take?**
On a 4 GB Pi over Wi-Fi, a library of tens of thousands of files took a
couple of hours, and a rescan with nothing changed under half an hour. The first scan
starts by itself when a folder is added.

**The server's row says the scan stopped for lack of memory.**
The server may use the player's memory less 1 GB. A library too big for it
is not scanned in full, and the row says how many files fit. On a 4 GB Pi,
setting Lyrion's own *Database Memory Config* to *Normal* (on Lyrion's
Performance page) roughly doubles how many files fit. A player with 1 GB is
not offered the server.

**A USB disk or NAS was off for a while. Is the library lost?**
No. A NAS that is off when the player starts no longer makes the server wipe
its library, and an unplugged USB disk stays in the server's list for 7
days.

**What does Remove do for the Lyrion server?**
It deletes the server's library, its settings, its add-ons and its network
shares with their logins. The Music folder and its playlists stay. Switching
it on again downloads it and starts a new library.

**How do I see Lyrion's own menus and apps on the screen?**
Switch on *Settings → Sources → Lyrion Client → Extended navigation*. The
home screen then has My Music with every library view, Favourites, and Apps,
including what Lyrion's apps add. It is off by default.

---

## Streaming sources

**The player does not appear in Spotify.**
Check *Settings → Sources → Spotify Connect → Enabled*. The player appears
under its device name. The phone and the player must be on the same network.

**How do I pair a phone over Bluetooth?**
While the player is discoverable, pair from the phone's Bluetooth settings.
By default a six-digit code appears on the screen to confirm (*Settings →
Sources → Bluetooth → Pairing*), and the player is always discoverable
(*Discoverable* also offers *3 min after boot* and *Off*).

**A Bluetooth device will not pair again after being forgotten.**
Forget it on both sides: in *Settings → Sources → Bluetooth → Trusted
devices* on the player, and forget the player in the phone's Bluetooth
settings, then pair again. The same after re-flashing the player's card: the
new card has new pairing keys, and a phone still holding the old ones may say
it *can't communicate* with the player until it forgets it and pairs again.

**Bluetooth plays, but the screen says "Not provided".**
The phone is sending no track details. In the one case seen, the phone was
in battery-saving mode, which can hold back what it sends; once that was off,
the details came through. Not every app sends track details over Bluetooth.

**How do I connect Plexamp?**
Switch on *Plexamp* on the Plugins page (it is downloaded from Plex). Then, in
its *Claim token* row under *Settings → Sources*, paste a token from
plex.tv/claim; the row then shows *Claimed*. *Claim again* moves the player
to another Plex account, and registers it there as a new player.

---

## Pictures, lyrics and artist information

**Album art is missing for Bluetooth or Spotify tracks.**
With *Settings → Enrichment → Look up missing artwork* on, the player looks
the cover up when the source sends none. The match has to be at least as
sure as *Confidence threshold* (recommended 90 %); below it the player shows
nothing rather than a wrong cover. Since 0.9.2, covers are found more often,
including for tracks by several artists.

**Where do lyrics come from, and why are some not synced?**
From LRCLIB, switched on with *Settings → Enrichment → Lyrics*. Where LRCLIB
has only plain lyrics, they are shown without timing. Some tracks have none.
The Lyrics button on Now Playing, or on the phone's volume sheet, shows them.

**Where do artist pictures and biographies come from?**
Biographies from Wikipedia; album and artist details from MusicBrainz. Artist
pictures from fanart.tv with a key of your own (*fanart.tv key*), then
TheAudioDB; without a fanart.tv key, from the Lyrion server's Music & Artist
Information plugin, or initials where it is not installed.

**How do I fill in portraits and covers for the whole library?**
*Settings → Enrichment → Lyrion Client → Find portraits and covers* checks
every album artist and album on fanart.tv and TheAudioDB, keeping Lyrion's
picture where neither has one. It runs in the background without stopping
the music, and shows what its last run found. Without a TheAudioDB key of
your own it uses a shared key and can take noticeably longer.

**The artist page's Popular list is empty.**
It needs a free ListenBrainz user token, in *Settings → Enrichment →
ListenBrainz token*.

---

## Updates and maintenance

**How are updates installed?**
*Settings → System → Software update* shows a waiting release and its notes.
Installing stops the music (it asks first), restarts the player and checks
it; the device itself restarts only if the system needs it, and the update
says so before starting. If the new release fails its check - also after the
device restarts - the player goes back to the release it had. While it
installs, no phone or app can start playing on it. *Settings → System → Change logs* lists what
changed in the last 10 releases.

**The player is several releases behind. Does it install each one in turn?**
No: it goes straight to the newest release on its channel, in one update. What
the releases in between changed comes with it: settings they renamed or
retired are carried over in order, and if any of them needed a full restart,
the device restarts. Before it installs, the update shows the notes of every
release it skips, newest first, each under its number and date; afterwards
*Settings → System → Change logs* has the last 10 and points to the full list
on GitHub. In
the rare case that the newest release needs a newer updater than the device
has, the update says so, and the card is re-flashed with a current image
(after a backup).

**Can updates install by themselves?**
Set *Settings → System → Updates* to *Automatic*. A waiting release is then
installed between 3 and 4 at night, never while music plays, and one that
failed is not retried.

**What are Stable and Testing?**
*Settings → System → Update channel*. Testing gets each release first and may
have problems; Stable gets it once it has been tried. Going back to Stable
does not downgrade: the player stays where it is until Stable passes it.

**Do Plexamp and the Lyrion server update?**
Yes, with the player: a new version of either comes as part of the player
update that brings it.

**How do I back up the player before re-flashing the card?**
*Settings → System → Back up now* writes the settings, the library's
pictures, the paired devices and the player's configuration into the
player's Backups share on the network. Copy the backup off the player before
flashing. Afterwards, copy it back into the Backups share and choose it under
*Restore*; the player restarts with everything back. Network share passwords
are not kept in backups, so enter them again.

**What are Debug logs for?**
*Settings → System → Debug logs* keeps the player's logs across restarts (up
to 100 MB) to help track down a problem. It is on by default on the Testing
channel; switching it off deletes the logs kept.

**My sound card or screen is not marked Tested. Can I help?**
Yes: open *Settings → System → Hardware feedback* on a phone or computer. It
takes two short steps. First the screen: a test pattern on the player's
screen shows whether all of it is visible, and four circles to tap measure
where the touches land. Then the sound: a short test tone at 44.1, 96 and
192 kHz, and a few questions about how it plays. On a player without a
screen, or one set to Headless, it starts at the sound. The feedback is then
sent on GitHub (a GitHub account is needed), filled in with what the player
reads of the hardware itself - never a serial number or anything about you -
and it is public, so the next owner can see what works. A week after a sound
card or screen that is not Tested is first used, the System page offers this
once in a line at its top; its × puts it away for good. Once feedback is
accepted, the next release marks that card or screen *Reported* in the player
and in the project's hardware list.

**Something is wrong. How do I report it?**
Open *Settings → System → Problem report* on a phone or computer on the same
network, say in a line what happened, and tap *Download*. The player prepares
one file with its logs, versions, hardware and settings; this takes up to a
minute. Before the file is written, the player takes out addresses, network
and device names, shares, accounts, keys, the weather location and the names
of what you play, each replaced by a token such as `ip-3`. Read the file before
sharing it, then attach it to a new report on GitHub with *Report a problem*,
or e-mail it to george.carstoiu@gexis.net.
If the problem goes away at a restart, switch on *Debug logs* first, so the
logs from before the restart are kept.

---

## Hardware

**What hardware does the player need?**
A Raspberry Pi 4 Model B (4 GB tested; 2 GB untested), a 32 GB card is
recommended, a DAC (the HiFiBerry DAC2 HD and IQaudIO Pi-DAC PRO are tested), and optionally
an HDMI touch screen. Power from the official 5 V 3 A supply, and a heatsink
or fan, especially with the Lyrion server. The minimum and recommended
hardware, with what each rests on, are in the
[hardware requirements](HARDWARE.md).

**Which DACs work?**
Each output in *Settings → Audio → Output* shows *Tested*, *Reported*,
*Known* or *Detected*. The HiFiBerry DAC2 HD and the IQaudIO Pi-DAC PRO are
tested; a board owners have reported working is *Reported* (*Reported with
problems* if a report says otherwise); the other boards on the player's list
are known but untested; a class-compliant USB DAC should be detected by
itself but has not been tried. A board that is not found by itself can be
chosen in *Settings → Audio → Sound card board*. The screen's HDMI audio
can be chosen too; it is not bit-perfect, its volume is set in software
(or fixed), and the visualiser moves with it only while the volume is in
software.
