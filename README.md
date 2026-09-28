<p align="center">
  <img src="docs/assets/gexis-sound.svg" alt="gexis sound" width="240">
</p>

# Gexis Player

**A high-fidelity music player for the Raspberry Pi 4, with a touchscreen, that
plays whatever you send it — from your phone, your music server or the streaming
apps you already use — and hands the DAC cleanly from one to the next.**

🎧 Bit-perfect up to 24-bit / 192 kHz · 🔀 Spotify, Lyrion, Plexamp and
Bluetooth on one device · 🖥️ A 1280×800 touchscreen that shows what's playing,
whoever is playing it · 📈 VU meters, spectrum and turning turntables when you just
want to watch the music

> 🚧 **Work in progress.** Gexis Player is built in the open and used every day on
> its reference device, but it has no public release image yet. See the roadmap.

<!-- Screenshots / demo go here: now playing, library, visualiser, idle screen,
     settings on a phone. -->

---

## 🎵 What it does

You put a Raspberry Pi 4 with a HiFiBerry DAC and a touchscreen next to your
amplifier, flash the Gexis image, and it becomes a streamer with a face:

- **Cast to it from the apps you already have.** It appears as a speaker in the
  Spotify app, as a player in Lyrion (Logitech Media Server) and Plexamp, and as a
  Bluetooth speaker on your phone.
- **Switch sources without thinking about it.** Start playing from another app
  and it takes over: the previous source is stopped politely, a short transition
  screen shows who is taking over, and the new one plays. You never have to
  "disconnect" anything first.
- **See what's playing on the panel.** Artwork, artist, album, lyrics (synced
  where available), artist biographies and photos. It's the same screen whatever
  the source: Spotify, your own library through Lyrion, Plex, or a phone over
  Bluetooth.
- **Browse and play your library** from the panel when you use Lyrion: albums,
  artists, playlists and radio.
- **Watch it.** A visualiser with nearly 190 skins: classic needle VU meters,
  spectrum analysers, and turntables and tape decks whose records and reels turn
  as the music plays.
- **Control it from your phone's browser.** Every setting on the panel is also
  on your phone. The panel and the phone take the same input.

## ✨ Main features

| | |
|---|---|
| 🔊 **Sources** | Spotify Connect · Lyrion / Logitech Media Server (squeezelite) · Bluetooth (A2DP) · Plexamp |
| 🎚️ **Sound** | Bit-perfect to the DAC up to 24/192. One volume, applied in the DAC's own hardware attenuator. A maximum-volume limit that holds for every source, and a starting volume Spotify never exceeds when it takes over |
| 🔀 **Handover** | One source at a time, never mixed. Takeover in any direction. The previous source is released before the next one plays |
| 🖼️ **Now playing** | Artwork, track info, synced or plain lyrics, artist info and photos, queue for Lyrion |
| 📚 **Library** | Browse Lyrion by album, artist, playlist and radio, from the touchscreen |
| 📈 **Visualiser** | 189 skins: VU meters, spectrum, and animated turntables and tape decks with progress, time, volume and play-state shown in each skin's own style. Skins can rotate per track |
| 🌤️ **Idle screen** | Clock, weather and wallpapers when nothing is playing |
| 📱 **Settings anywhere** | The full settings screen on the panel and on any phone or computer on your network |
| 🔌 **Plugins** | Extra sources and services as plugins, switched on or off in Settings, with progress and retry shown in the switch itself when one downloads software. Today: Plexamp (source), Beszel monitoring (system). Remove deletes what a plugin downloaded |
| 💾 **Backup & restore** | Your settings, pairings and source logins in one archive on a network share, restored onto a freshly flashed card |
| 🙈 **Headless** | Run it without the screen; everything else keeps working |

## 🏆 Where it shines

- **Sound you can check.** Bit-perfect is a property of the whole audio chain,
  and because Gexis owns the whole system, not an app on top of someone else's,
  the chain can be inspected rather than taken on trust.
- **Handover done properly.** Most multi-source players leave you juggling apps
  when two of them want the DAC. Gexis arbitrates: the newest deliberate choice
  wins, and the others are told.
- **One face for every source.** A track from Spotify, from your own library or
  from a phone over Bluetooth looks the same on the panel, with the same
  artwork, lyrics and artist pages.
- **A visualiser worth leaving on,** from studio VU meters to a turning
  record with its tonearm tracking the song.

## ⚖️ Limitations and trade-offs

We'd rather you knew these up front:

- **One hardware setup.** Raspberry Pi 4 (4 GB), a HiFiBerry DAC2 HD and
  a 1280×800 touchscreen. Other boards, DACs and screen sizes are not
  supported.
- **Your library comes through Lyrion.** Gexis has no local music library of its
  own. Browsing your files needs a Lyrion Music Server elsewhere on your
  network.
- **One source plays at a time,** by design (no mixing). A takeover is not
  instant: the previous source has to let go of the DAC first, and some
  sources let go faster than others.
- **On a phone you get Settings, not the whole player.** Now playing, the
  library and the visualiser live on the panel; on a phone, your streaming app
  is the remote.
- **The first setup needs a network.** Setting up Wi-Fi on first boot, without
  one, is on the roadmap.
- **Plexamp's volume is its own.** Plexamp scales the sound inside its own
  engine, so the Plexamp app's slider sets Plexamp's level and the panel's sets
  the DAC's. The two are separate numbers.
- **Not a store product.** It's a hobby project, built carefully with the help
  of AI and tested on real hardware, but without a support team behind it.

## 🗺️ Roadmap

Rough, and subject to change:

- 🟢 **Now:** Legal and Credits pages in Settings. Plugins that download
  software, with progress, retry and remove. A mini player on the phone. Animated skins with scrolling tickers, smooth rotation, and progress,
  volume and play-state in each skin's own style.
- 🔜 **Next:** a first public release image. First boot without a network (the
  player offers its own Wi-Fi setup). Installing your own plugins from Settings.
  Keeping plugins up to date.
- 🎨 **Later:** themes. Artist and album information from your own Plex server.
- 💭 **Maybe:** a visual equaliser, room correction with a phone as the
  microphone, the DAC's own filter and polarity options.

## 📜 Legal

**Gexis Player is free software under the GNU General Public License, version 3
or later.** It is provided **as is, without any warranty**, without even the
implied warranty of merchantability or fitness for a particular purpose. You
use it at your own risk, including any risk to your equipment and your hearing.

It is built on the work of many open-source projects, each under its own
licence. The full list, with licences and authors, is in
[THIRD-PARTY.md](THIRD-PARTY.md) and on the device under Settings → System →
Legal and Credits.

**Some software is not part of Gexis Player** and is downloaded on your device
from its maker only when you switch it on. It is used under its maker's terms:

- **Plexamp** is Plex, Inc.'s proprietary software.

Spotify Connect is provided through go-librespot, an independent open-source
client that ships in the image. It is not made or endorsed by Spotify.

**Gexis Player is not affiliated with, endorsed or sponsored by** Spotify,
Plex, Lyrion, the Bluetooth SIG, Raspberry Pi or HiFiBerry. Their names
and logos are trademarks of their owners and are used only to name what works
with what.

## 🙏 Credits

Gexis Player stands on the shoulders of PeppyMeter and its skin artists,
squeezelite, go-librespot, bluez-alsa, Raspberry Pi OS and many more,
all listed in [THIRD-PARTY.md](THIRD-PARTY.md). Thank you.
