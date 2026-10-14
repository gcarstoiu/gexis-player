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

**With Fixed, Bluetooth goes silent when the phone's slider is at 0.**
That is the phone: with the slider at the bottom it sends silence. Anywhere
above 0, Bluetooth plays at full level in Fixed, as every source does; set
the loudness on the amplifier.

**What happens when I change the volume type while music plays?**
Playback stops and the sources reconnect on the new type at once - Hardware,
Software or Fixed alike - so the level never jumps to full in the middle of a
track. Start the music again when ready; the source that comes back starts no
louder than its *Starting volume*. Leaving *Fixed*, the volume goes back to
where it was before *Fixed* was chosen (or to the *Starting volume*, on a
player that started in *Fixed*) rather than staying at full.

**What happens when I change the output while music plays?**
The same as for the volume type: playback stops, the sources reconnect on the
new output, and the screen says so. Start the music again when ready; the
source starts afresh on the new output, no louder than its *Starting volume*.

**Does the music come back loud after a power cut?**
No. With *Volume* on *Software* (HDMI, for instance), the player sets the
volume it was left at before any source can start playing, so a source that
picks up where it was after a power cut starts at that level, not at full.

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
*Settings → Handoff → Reclaim Lyrion when a session ends* is on. When Spotify,
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
chosen with *Change* on *Settings → Display → Attached screen*, or *Screen rotation*), the
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

**My sound goes to a receiver over HDMI. What if the receiver is off?**
When the HDMI port the sound goes to has nothing connected any more, the
player plays through the headphone jack until the receiver is back, then
returns to HDMI by itself. While the jack stands in it uses its own volume,
never *Fixed*, so headphones are never at full level. *Settings → Audio →
Output* says when this is happening.

**Does the player play DSD?**
Yes. DSD files from Lyrion play natively, unconverted, on a DAC that takes
DSD itself (some USB DACs; tested with an SMSL), with *Settings → Audio →
Volume* on *Fixed*, so the amplifier sets the level. In every other case
(other volume types, DAC HATs, HDMI) they are converted to PCM and play as
usual. The visualiser stays still while DSD plays.

**Does the player play 5.1 and 7.1 files?**
Yes, as stereo. Through Lyrion, a FLAC, WAV, AIFF, DSD or AAC file with more
than two channels is folded down to two: the centre and the surrounds are
mixed into left and right, the low-frequency (LFE) channel is left out, and
the result is turned down so that nothing can clip - so such a file plays
quieter than a stereo one. A multichannel DSD file is converted to PCM for
this, even where DSD otherwise plays natively; Opus is folded by its own
decoder. Ogg Vorbis and ALAC files with more than two channels are not
folded and may not play. Surround playback, all channels to an AV receiver,
is planned.

**Which screens work?**
HDMI screens only. Tested on the hardware: a 10.1″ 1280 × 800 (the reference
screen), a 13.3″ at 1920 × 1080, and the 1280 × 400 and 1480 × 320 bars.
Others under *Change* on *Settings → Display → Attached screen* are listed but untested;
those tested are marked *Tested*, those owners have reported working
*Reported*. DSI and DPI screens are not supported. The screen can be on
either of the Pi's HDMI ports; a bar screen moved from one port to the other
is set up again at the next start and asks *Keep this screen?*. With
something connected to both ports (a screen on one, a sound bar on the
other), *Settings → Display → Screen port* shows what is on each and lets
you choose which is the screen.

**Can a TV be the screen?**
Yes: connect it to either HDMI port and choose that port under *Settings →
Display → Screen port*. The player restarts on the TV at 1920 x 1080, taken from the sizes the TV
offers (a 4K TV scales it to full screen). A TV has no touch, so *Keep this
screen?* appears on the phone page - answer it there, or the player goes back
to the screen before. A touch panel left on the other port is switched off;
choose its port again to go back to it. If the edges of the picture are cut
off, set the TV's picture size to *Just Scan* or *Original*: TVs crop HDMI
pictures otherwise.

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

**I have more than one player. Do I need a tab for each?**
No. On the phone page, tap the switch button at the right of the *Settings*
title - there when another player is on the network. It lists
every player with what it is playing and through which source; choosing one
opens its page in the same tab. A player is listed once it runs this release
or later and is on the same network.

**Can the screen turn off, at night or on demand?**
Yes. The *Screen* button in the phone's mini player darkens it until a
touch, music starting or the button again wakes it; the player keeps playing meanwhile.
*Settings → Display → Display standby → Scheduled standby* does it at the
*Standby times* you set - several,
each with its own days. Woken during one, the screen goes dark again after
*Back to standby after* (2 minutes unless changed) if nobody uses it.

**When does the idle screen appear?**
Only with *Settings → Display → Idle screen* switched on - it is off on a new
player, and the panel then stays on what it shows. On, it appears after
*Timeout* (default 5 minutes) with nothing playing and nobody touching the
screen. It shows a clock, the
weather and a background picture. A touch, or music starting, brings the
player back.

**Where do the idle screen's pictures come from?**
*Settings → Display → Idle screen → Background* chooses: *Gexis wallpapers*,
the player's own public-domain photographs, built in (the default on a new
player); *Artist pictures* from the
library (while the Lyrion client is off they show the player's own instead);
*Wallpapers online* from Pixabay (it needs a free key, entered under
*Photo service and location*); *Wallpapers on device*, read from the player's Pictures share on the
network; or *Black*. Pictures are
placed by what they show, so faces, people and animals stay in view. The
waiting screen (with the Lyrion client off) has its own *Background* under
*Home screen*, chosen apart from the idle screen's.

**How do the player's own wallpapers change through the day and the year?**
With *Gexis wallpapers*, each picture comes from one of the *Wallpaper
styles* you chose (Calm, Colourful, Psychedelic), from pictures for the
time of day (dawn, day, dusk, night) or from the season's, by hemisphere.
On New Year, and on Christmas and Easter where they are public holidays,
only those days' pictures show, with the online wallpapers too; *Holidays* turns
that off. The country comes
from the weather location, or from the time zone until a location is set,
and decides whether Easter follows the Western or the Orthodox date. Every
picture is public domain or CC0, and its author is shown in the corner.

Space photos come from Pixabay: choose *Space* among the *Wallpaper topics*
of *Wallpapers online*. It asks for galaxies, nebulae and astronomy photos,
not for the word *space*, which also matches empty rooms and the like.

**The online wallpapers keep repeating.**
They no longer repeat until every picture of the day has been shown, and
each day brings a new set. *Wallpaper topics* sets what is drawn from:
*Space* and *Calm* search Pixabay's selected photos and the rest are Pixabay's
own categories; choosing several mixes them. *Holidays* shows a holiday's
pictures in their place on its days.

**The weather is for the wrong place, or not shown.**
Set *Settings → Display → Photo service and location → Location* to a city or
place name.
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

**What do a spectrum's bars show?**
The music's loudness from 50 Hz on the left to 16 kHz on the right, spaced the
way pitch is heard, so the bass has several bars of its own. It is the same
at every sample rate. Each bar is the music's own level in its range, as an
audio analyser measures it: most recordings carry less in the treble than in
the middle, so the bars on the right are usually shorter, and a recording with
almost nothing up there leaves them nearly still.

**How do I pick one skin and keep it?**
Under *Settings → Display → Visualiser*, choose a *Skin type*, switch off
*Rotate skin per track*, and choose a *Skin*: tapping one previews it, and
nothing changes until *Use this skin*. On the phone, swiping left or right
moves to the next or previous skin. Note that applying *Spectrum smoothing*
or *Needle fall time* under *Visualiser tweaks* stops the music for a moment
while the sound card is reopened.

**Do the needles and bars follow the volume?**
Yes, with *Volume type* on *Software* or *Hardware*: they show what comes
out, so they fall as the volume comes down - the bars by the whole drop, the
needles by half of it, so they still move when listening low. *Needles
follow the volume* set to *Like a real amplifier* makes the needles follow
all of it, as an amplifier's meters do. On *Fixed* the
player does not change the level, so they show the recording. *Gain* under
*Settings → Display → Visualiser → Visualiser tweaks* raises or lowers both,
from −10 to +20 dB, for a quiet recording or a low listening level.

**Some skins show a slideshow of the artist. Where do the photos come from?**
From the Lyrion server's Music & Artist Information plugin. They are the
*Fanart* skins; the photo changes every 20 seconds. An artist the plugin had
no photos for is asked about again after 30 days, since the plugin finds more
over time; an artist whose photos were found is not asked again.

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
Open the volume sheet on the phone - tap it, or swipe it up; swipe down to
close it. One finger moves a pointer on the screen, a tap presses, two
fingers scroll, and a pinch zooms. What the pointer is over is outlined when
it can be pressed. If the touchpad stops answering, it reconnects by itself:
within about a second of touching it again, or about five seconds on its own. The lines along
the right and bottom edges scroll with one finger. Tapping a text field on
the screen brings up the phone's keyboard. A touch outside the sheet closes it.

**The pointer is too slow, or hard to see.**
*Settings → Display → Pointer speed* (150–400 %) and *Pointer style* (*Dot* or
*Arrow*). *Phone touchpad* switches the touchpad off altogether.

**The touchpad or the phone page does nothing.**
The phone and the player must be on the same network. If the page loads but
is slow or drops out, see the Wi-Fi questions: a poor connection shows on the
phone first.

**Settings says "The player did not answer. Check the connection and try again."**
A change in *Settings* that gets no answer is given up rather than left
spinning: after 20 seconds, or 2 minutes for what is slow on purpose (joining
a Wi-Fi network, a Wi-Fi scan, network shares, making a backup, changing an
address, uploading or removing a plugin, starting a problem report), or 15
minutes for restoring a backup. Usually the phone went to sleep or lost the
network on the way. Check that it is on the same network as the player, then
try again; the change may have been made, so look before repeating it.

---

## Network and Wi-Fi

**How do I change the Wi-Fi network?**
*Settings → System → Wi-Fi* lists the networks in range. A secured network
needs its password the first time; saved networks join in one tap. The time
zone is taken from the network; set it in *Settings → System → Time zone*
only if that comes out wrong.

**How good is the player's Wi-Fi connection?**
Open *Settings → System → Wi-Fi* and tap the connected network. It shows the
signal (in dBm and as a percentage), the speed the radio is using, the band
and channel, and the player's address, updated every few seconds. As a rough
guide, a signal above −67 dBm is good for music; below −75 dBm, stutter
becomes likely. A 5 GHz network is usually faster but reaches less far than
2.4 GHz.

**The player lost Wi-Fi while running.**
After two minutes without a network, the player opens its own setup network
and the screen shows how to join it, as at start (after 90 seconds there). It
keeps looking for its saved network every five minutes and goes back to it
when it is in range; or choose a network from the setup screen. A phone on
the setup network keeps the player there only while someone is using the
setup page (in the last ten minutes) or the phone has only just joined; a
phone that joined by itself and was left there does not. This counts
a network that gave the player no address as no network. A player on a
network cable leaves the setup network by itself once the cable has an
address again.

**What is the player's name, and can it be changed?**
*Settings → System → Device name* is one name for everything: the network
address (`name.local`), the Lyrion player, the Spotify Connect device, the
Bluetooth name and Plexamp. Changing it restarts the player, and Settings
says at which address it comes back.

---

**What happens with a cable and Wi-Fi at the same time?**
The cable wins. While a cable is plugged in, the Wi-Fi is off and its
networks stay saved; unplug the cable and the Wi-Fi connects again by itself
within about 10 seconds, at its own address. `gexis.local` (the player's name)
finds it either way.

**Can the player have a fixed address on the cable?**
Yes: *Settings → System → Cable* (shown while a cable is plugged in), then
*Manual*, with the address and its prefix (for example `192.168.1.20/24`), the
gateway and one or two DNS servers. After *Save*, open the player at the new
address and tap *Keep* within 60 seconds. If the new address does not work,
the old one comes back by itself, so a mistake cannot lock you out. On Wi-Fi,
the same choice is under the connected network's details in *Settings →
System → Wi-Fi*. A backup does not hold a fixed address: set it again after
restoring one.

## Setup and first boot

**How is a new player set up?**
On first start with no network, the player opens its own Wi-Fi, called
*gexis-setup*. The screen shows two QR codes: one to join that network, one
to open the setup page. The phone then walks through Wi-Fi, then asks
whether this is a new player or a backup to restore. A new player goes on to
a name, the clock, the output, the music, the screen, the visualiser and the
plugins to install (Plexamp, the Lyrion Server, Beszel); a backup asks only
for this player's output and screen and answers the rest, and the phone shows
what it brings before the player restarts. Step by step, from flashing the
card: the [installation guide](INSTALL.md). Once the player is on your
network it shows what it is downloading and installing, each with its
progress (a skin pack's install says *Installing*: minutes, with nothing to
count), until it is
ready. *Use the player now* puts that screen away at any time: the downloads
go on, Settings shows how far they are, and music may be slow to start until
they finish. A download that does not finish brings the screen back, named,
with *Settings → Plugins* as the place to try it again.

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
to another Plex account, and registers it there as a new player. A token
lasts only a few minutes, so paste it soon after making it. If the row says
*The claim did not work* or *Plex signed this player out*, get a new token and
paste it again; a claim that fails leaves the player as it was.

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

**Does artist and lyrics information fill the card?**
No. The player stores what it looks up (lyrics, biographies, album and
artist details) so it need not ask again, but this store never takes more
than a tenth of the card, nor so much that less than 2 GB of the card is
left free. Past either, it deletes what was used longest ago - never what
belongs to the track playing - and gives the space back. It looks when it
starts and then every hour.

**The artist page's Popular list is empty.**
It needs a free ListenBrainz user token, in *Settings → Enrichment →
ListenBrainz token*.

---

## Updates and maintenance

**How are updates installed?**
*Settings → System → Software update* shows a waiting release and its notes,
from the last check (every night); *Update…* checks again before offering it,
so a newer release published since is the one offered. Installing stops the music (it asks first), restarts the player and checks
it; the device itself restarts only if the system needs it, and the update
says so before starting. If the new release fails its check - also after the
device restarts - the player goes back to the release it had; after a power
cut during the install, it finishes the install or goes back when it starts
again. The updater keeps only the downloads of what is installed, so old
releases do not fill the card. While it
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
flashing: on a phone or computer, *Settings → System → Restore* has *Download*
beside each backup, or copy it from the share. After flashing, setup offers *Restore a backup* right after the
Wi-Fi: choose the file on the phone, choose the output and the screen this
player has, check what the backup brings, and the player restarts with
everything back. Sources and plugins come back on or off as they were when the
backup was made. Anything else setup asks (the name, for instance) can be
changed in that review, so one player's backup can start another. With a new
name, the review offers *A second player*: on, the first player keeps its
Beszel connection (the hub's address and keys too), Plexamp's claim, Spotify
sign-in and Bluetooth pairings, so the two never share them. A backup from an older version works. A
backup can also be restored later: copy it into the Backups share and choose
it under *Settings → System → Restore*. Network share passwords are not kept
in backups, so enter them again.

**Do the backups fill the card?**
Each update makes a backup before it installs. *Settings → System → Restore*
marks those *before an update*, and the player keeps only the newest three of
them. Backups made with *Back up now*, copied into the Backups share, or left
by an update of an earlier release are never deleted by the player; remove
those that are no longer needed with *Forget* beside them under *Restore*. A backup carries the
artist and lyrics information the player has stored, so it can be larger than
the settings alone suggest.

**How do I start the player over, without re-flashing the card?**
*Settings → System → Reset to factory settings*, on the screen or a phone.
Hold the button for 3 seconds, until its bar fills; the screen and the phone
say the player is resetting, and the phone says how to reach setup. The
player restarts, clears everything and comes up in setup, as on a freshly
flashed card. It
removes every setting and the name, the settings and idle page chosen when
the card was flashed, the saved Wi-Fi networks, paired devices
and sign-ins, the skins, the plugins, the Lyrion Server's library, the
screen's browser data, and the backups kept on the player (the Backups share
itself stays, empty), so download a backup first (*Restore →
Download* on a phone or computer). The music folder, its playlists and the
Pictures share stay, and the Lyrion Server scans the music again. The
installed version stays, so there is nothing to download again except the
skins and plugins setup chooses.

**What are Debug logs for?**
*Settings → System → Debug logs* keeps the player's logs across restarts (up
to 100 MB) to help track down a problem. It is on by default on the Testing
channel; switching it off deletes the logs kept.

**Is Beszel reaching its hub?**
Its heading in *Settings → System*, above the hub address, token and key,
says so while it is on: **Connected** in
green, **Connecting** in orange for its first minute, then **Not connected**
in red. Not connected usually means the hub address, token or Hub public key
does not match the hub's *Add System* dialog. A Hub public key that is not one
is refused when it is saved, and an agent that cannot start at all says
*Beszel could not start. Check its settings.*

**My sound card or screen is not marked Tested. Can I help?**
Yes: open *Settings → System → Hardware feedback* on a phone or computer. It
takes three short steps. First the screen: a test pattern on the player's
screen shows whether all of it is visible, and four circles to tap measure
where the touches land. Then the sound: a short test tone at 44.1, 96 and
192 kHz, and a few questions about how it plays. Last, room for your own
notes, beside what the player adds for you. On a player without a screen,
or one set to Headless, it starts at the sound. The feedback is then
sent on GitHub (a GitHub account is needed), filled in with what the player
reads of the hardware itself - never a serial number or anything about you -
and it is public, so the next owner can see what works. A week after a sound
card or screen that is not Tested is first used, the System page offers this
once in a line at its top; its × puts it away for good. The last step
offers the same two ways as the problem report: *On GitHub* opens the feedback
there, and *Create* on GitHub sends it; *By e-mail* downloads it as a text file. The
player keeps it: the *Hardware feedback* row then shows *Send again* and
*Start over*, until the sound card or screen is changed, when it is
forgotten. Once feedback is accepted, the next release marks that card or screen *Reported* in the player
and in the project's hardware list.

**Something is wrong. How do I report it?**
Open *Settings → System → Problem report* on a phone or computer on the same
network. Say what happened and how often, then *Next*: the player prepares
one file with its logs, versions, hardware and settings, ticking off each step
as it goes; this takes up to a minute. Before the file is written, the player
takes out addresses, network and device names, shares, accounts, keys, the
weather location and the names of what you play, each replaced by a token such
as `ip-3`. Then choose how to send it: *On GitHub* opens a report already
filled in with what happened and the log's last errors (the file itself can be
dragged onto it too - a link cannot attach it), or *By e-mail* downloads the
file to send to george.carstoiu@gexis.net. Read the file before sharing it.
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

**The player restarts by itself, or the screen keeps going dark and coming back. Why?**
Almost always the power supply. A Raspberry Pi 4 needs a steady 5.1 V at up
to 3 A; a phone charger, or a long or thin cable, sags when the player is
busy - starting up, installing, or a touch screen lighting up - and the Pi
resets. A screen that takes its power from the Pi's USB port adds its draw
to the Pi's own. One player showed it both ways: on a phone charger it
restarted over and over within seconds of starting; on a better supply it
stopped restarting, but still dipped several times in a few minutes while
its bar screen, powered from the Pi, was in use. Use the official 5.1 V / 3 A
supply, and give a screen its own supply where it has a port for one. A
problem report (*Settings → System → Problem report*) carries the Pi's own
record under *Throttling*: `0x0` means the power has been fine since the
last start. A power cut during an install or update is repaired by the
player itself the next time it installs anything.

**Which DACs work?**
Each output in *Settings → Audio → Output* shows *Tested*, *Reported*,
*Known* or *Detected*. The HiFiBerry DAC2 HD and the IQaudIO Pi-DAC PRO are
tested; a board owners have reported working is *Reported* (*Reported with
problems* if a report says otherwise); the other boards on the player's list
are known but untested; a class-compliant USB DAC is detected by itself
and shown by its maker, with a line under it saying what it reports it can
take - its USB generation, its highest rate and sample size, and native DSD
(tried with an SMSL; most USB DACs have no volume
control of their own, so their volume is Software or Fixed). A board that is not found by itself can be
chosen in *Settings → Audio → Sound card board*. The screen's HDMI audio
can be chosen too; it is not bit-perfect, its volume is set in software
(or fixed), and the visualiser moves with it only while the volume is in
software.
