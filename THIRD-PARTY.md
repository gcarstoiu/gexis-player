# Third-party components

Generated from `core/src/gexis_core/notices.json` by
`python -m gexis_core.notices` - edit that file, not this one. The same
list is on the player, under Settings → System → Legal and Credits.

| Component | What it does | Licence | Author | How it arrives |
|---|---|---|---|---|
| [Raspberry Pi OS Lite (Debian trixie)](https://www.raspberrypi.com/software/) | The operating system: kernel, firmware, drivers, networking, Bluetooth. | Many; each package's own, in /usr/share/doc/<package>/copyright | Raspberry Pi Ltd and the Debian project | The base of the image, built by pi-gen |
| [ALSA utilities and library](https://www.alsa-project.org) | The sound system's tools and library; volume control. | See /usr/share/doc/alsa-utils/copyright on the device | The ALSA project | Debian package |
| [bluez-alsa](https://github.com/arkq/bluez-alsa) | Plays music sent from a phone over Bluetooth. | See /usr/share/doc/bluez-alsa-utils/copyright on the device | Arkadiusz Bokowy and contributors | Debian package |
| [BlueZ tools and rfkill](https://www.bluez.org) | Bluetooth pairing and radio control. | See /usr/share/doc/bluez-tools/copyright on the device | The BlueZ project and util-linux | Debian packages |
| [Samba](https://www.samba.org) | Shares the pictures folder on the network. | See /usr/share/doc/samba/copyright on the device | The Samba Team | Debian package |
| [labwc](https://labwc.github.io) | The window compositor behind the panel. | See /usr/share/doc/labwc/copyright on the device | Johan Malm and contributors | Debian package |
| [swaybg and wlrctl](https://github.com/swaywm/swaybg) | The panel's background, and window control for the visualiser. | See /usr/share/doc/swaybg/copyright on the device | The Sway project; Aleksei Bavshin | Debian packages |
| [Chromium](https://www.chromium.org) | Draws the panel's screens. | See /usr/share/doc/chromium/copyright on the device | The Chromium authors | Raspberry Pi OS package |
| [Plymouth](https://www.freedesktop.org/wiki/Software/Plymouth/) | The boot screen. | See /usr/share/doc/plymouth/copyright on the device | The Plymouth authors | Debian packages |
| [Node.js](https://nodejs.org) | Runs Plexamp. | See /usr/share/doc/nodejs/copyright on the device | The Node.js project | Debian package |
| [Build tools left in the image](https://www.debian.org) | Compile peppyalsa on the device image: GCC, make, autotools, git, ALSA and FFTW headers. | Each package's own, in /usr/share/doc/<package>/copyright | The GNU project, FFTW and others | Debian packages |
| [squeezelite](https://github.com/ralph-irving/squeezelite) | Plays what Lyrion Music Server sends. | See /usr/share/doc/squeezelite/copyright on the device | Adrian Smith, Ralph Irving and contributors | Debian package |
| [go-librespot](https://github.com/devgianlu/go-librespot) | Makes the player a Spotify Connect device. | GPL-3.0 | devgianlu and contributors | Fetched from its release when the image is built, checked against a pinned checksum |
| [gexis-plexamp](https://github.com/gcarstoiu/gexis-plexamp) | Connects Plexamp to the player. | GPL-3.0-or-later | George Carstoiu | Fetched from its release when the image is built, checked against a pinned checksum |
| [Beszel agent](https://github.com/henrygd/beszel) | Optional system monitoring, off unless you switch it on. | MIT | henrygd | Fetched from its release when the image is built, checked against a pinned checksum |
| [PeppyMeter](https://github.com/foonerd/PeppyMeter) | The needle meters of the visualiser. | GPL-3.0-or-later | project-owner (Peppy), with the foonerd fork | Fetched at a pinned commit when the image is built |
| [PeppySpectrum](https://github.com/foonerd/PeppySpectrum) | The spectrum bars of the visualiser. | GPL-3.0 | project-owner (Peppy), with the foonerd fork | Fetched at a pinned commit when the image is built |
| [peppyalsa](https://github.com/project-owner/peppyalsa) | Feeds the music's levels to the visualiser. Modified here: one write per frame. | GPL-3.0 (modified by Gexis Player; the change is in image/stage-gexis/00-alsa/files) | project-owner (Peppy) | Built from a pinned commit with our patch when the image is built |
| [PeppyMeter screensaver for Volumio](https://github.com/foonerd/peppy_screensaver) | The turntable, tape, progress and icon behaviour our visualiser reimplements, and the stock skins. | MIT (2aCD's original ISC) | foonerd; originally 2aCD; with Wheaten | Fetched at a pinned commit when the image is built; its designs reimplemented in our own code |
| [Gelo5 skins](https://github.com/project-owner/PeppyMeter.doc) | The 84 meter and spectrum skins. | No terms of their own; distributed under their hosting repository's GPL-3.0 | Gelo5 | Fetched from a pinned release when the image is built |
| [Turntable, tape and cassette skins](https://github.com/foonerd/peppy_templates) | The 90 animated skins. | No terms of their own; distributed under their hosting repository's MIT licence | Gelo5 and Pakit S, collected by foonerd | Fetched at a pinned commit when the image is built, letterboxed to the panel |
| [DSEG7](https://github.com/keshikan/DSEG) | The seven-segment digits of the visualiser's clocks. | OFL-1.1 | keshikan | Fetched from its release when the image is built |
| [Nunito Sans](https://fonts.google.com/specimen/Nunito+Sans) | The panel's text. | OFL-1.1 | The Nunito Sans Project Authors | Bundled into the panel's screens |
| [IBM Plex Mono](https://github.com/IBM/plex) | The panel's figures and labels. | OFL-1.1 | IBM Corp. | Bundled into the panel's screens |
| [DejaVu fonts](https://dejavu-fonts.github.io) | The visualiser's titles. | See /usr/share/doc/fonts-dejavu-core/copyright on the device | The DejaVu fonts team | Debian package |
| [Bricolage Grotesque and DM Mono](https://fonts.google.com) | Drawn into the boot screen. | OFL-1.1 | The Bricolage Grotesque Project Authors; Colophon Foundry | Rendered into a picture when the boot screen was made |
| [Spotify icon](https://developer.spotify.com/documentation/design) | Shows that Spotify is playing. | Trademark of Spotify AB; the official icon, used to name Spotify | Spotify AB | Included in the player |
| [Lyrion logo](https://github.com/LMS-Community/lms-community.github.io) | Shows that Lyrion Music Server is playing. | Lyrion's brand asset, used in combination with its software (lyrion.org/terms, section 6b) | The Lyrion Music Server community | Included in the player |
| [Bluetooth mark](https://www.bluetooth.com/develop-with-bluetooth/marketing-branding/) | Shows that a phone is playing over Bluetooth. | The Bluetooth word mark and logos are registered trademarks owned by Bluetooth SIG, Inc. | Bluetooth SIG, Inc. | Included in the player |
| [Plex chevron](https://commons.wikimedia.org/wiki/File:Plex_logo_2022.svg) | Shows that Plexamp is playing. | Trademark of Plex, Inc.; the drawing is public domain as a text logo | Plex, Inc.; drawn from the Wikimedia Commons file 'Plex logo 2022.svg' | Included in gexis-plexamp |
| [Svelte](https://svelte.dev) | The framework the panel's screens are written in. | MIT | The Svelte contributors | Bundled into the panel's screens |
| [Vite](https://vite.dev) | Builds the panel's screens. | MIT | Evan You and the Vite contributors | Used to build; a small part is bundled |
| [aiohttp](https://github.com/aio-libs/aiohttp) | The player's web server and its connections to services. | Apache-2.0 and MIT (llhttp); with yarl, multidict, frozenlist, aiosignal and propcache (Apache-2.0), aiohappyeyeballs (PSF-2.0), attrs (MIT) and idna (BSD-3-Clause) | The aio-libs team | Installed from PyPI when the image is built |
| [dbus-next](https://github.com/altdesktop/python-dbus-next) | Talks to Bluetooth. | MIT | Tony Crisci | Installed from PyPI when the image is built |
| [Pygame and Pillow](https://www.pygame.org) | Draw the visualiser. | See /usr/share/doc/python3-pygame/copyright on the device | The pygame community; Jeffrey A. Clark and the Pillow contributors | Debian packages |
| [pi-gen](https://github.com/RPi-Distro/pi-gen) | Builds the image. | BSD-3-Clause | Raspberry Pi Ltd | Used to build |
| [Claude](https://www.anthropic.com/claude) | Designed the screens with George, and wrote much of the code. | Output owned by the project | Anthropic | Used to design and build |
| [Plexamp](https://www.plex.tv/plexamp/) | Plays Plex and Plexamp music. | Proprietary; Plex's terms. Includes BASS audio libraries by Un4seen Developments | Plex, Inc. | Not in the image. Downloaded from Plex on the device when you switch Plexamp on, checked against a pinned checksum |
| [Pibuz](https://github.com/PhilipVinc/pibuz) | Qobuz Connect, only if you install it from Settings. | MIT | Filippo Vicentini, from QBZ by vicrodh | Not included. Downloaded from its author's release when you choose to install it |
| [MusicBrainz and the Cover Art Archive](https://musicbrainz.org) | Album, artist and cover information. | Core data CC0; covers belong to their owners | The MetaBrainz Foundation | Contacted at run time |
| [ListenBrainz](https://listenbrainz.org) | What is popular in your library. | Its terms | The MetaBrainz Foundation | Contacted at run time |
| [Wikipedia and Wikidata](https://www.wikipedia.org) | Artist biographies. | Text CC BY-SA; Wikidata CC0 | Wikipedia's editors | Contacted at run time |
| [LRCLIB](https://lrclib.net) | Lyrics. | No licence stated for the lyrics | The LRCLIB contributors | Contacted at run time |
| [fanart.tv](https://fanart.tv) | Artist portraits and album covers, with your own key. | Its terms | The fanart.tv community | Contacted at run time |
| [Open-Meteo](https://open-meteo.com) | The weather on the idle screen. | CC BY 4.0 | Open-Meteo.com | Contacted at run time |
| [Pixabay](https://pixabay.com) | Wallpapers, with your own key. | Its content licence | Pixabay and its photographers | Contacted at run time |
| [Lyrion Music Server](https://lyrion.org) | Your music library, on your own server. | GPL-2.0, not included | The Lyrion community | Contacted at run time |
