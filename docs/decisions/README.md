# Decision records

One line per decision: what was decided and its status. The longer summaries
this index carried until 2026-10-12 are kept word for word in
[INDEX-FULL.md](INDEX-FULL.md); search it when a line here is not enough, or
read the ADR itself. "(amended …)" means the ADR has changed since it was
accepted: open it before relying on the line.

## Numbering gap — read this first

**ADRs 0002–0007 do not exist in this repository.** They were drafted in
conversation before the repo was created and never committed, and they are
**not** being reconstructed: writing them from summaries and presenting them
as the historical record would be fabrication. What is known is below, and
that is all that is known. ADR-0001 was in the same position and has since
been written properly. **0098 has no record either.**

| # | Subject | Status |
|---|---|---|
| 0002 | PipeWire as routing and arbitration layer | Superseded by [0008](0008-direct-alsa-over-pipewire.md) |
| 0003 | Two playback modes: passthrough and arbitrated | Void: both were PipeWire constructs, and DSD and >24-bit are unreachable on the DAC2 HD. See 0008. |
| 0004 | One active renderer | Answered by [0010](0010-arbitration-slot-model.md) |
| 0005 | VU metering via PipeWire monitor ports | Superseded by [0011](0011-meter-data-three-transports.md) |
| 0006 | Bluetooth on BlueZ + bluez-alsa | Still stands (reversed and reversed back; net effect unchanged). |
| 0007 | Local AI division of labour | Constrained by [0012](0012-enrichment-additive-only.md): API lookups adopted; audio embedding out of scope, a separate product. |

## Records

| # | Title | Status and decision |
|---|---|---|
| [0001](0001-base-os.md) | Base OS: Raspberry Pi OS Lite 64-bit | Accepted 2026-09-04 |
| [0008](0008-direct-alsa-over-pipewire.md) | Direct ALSA, not PipeWire | Accepted 2026-09-04 |
| [0009](0009-logical-output-device.md) | The logical `output` device | Accepted 2026-09-04 |
| [0010](0010-arbitration-slot-model.md) | Arbitration: base slot, connection acquisition, uniform disconnect | Accepted 2026-09-04, amended; **partly superseded by [0027](0027-lms-power-as-arbitration-mechanism.md)** |
| [0011](0011-meter-data-three-transports.md) | Meter data on three transports from one service | Accepted 2026-09-04 |
| [0012](0012-enrichment-additive-only.md) | Enrichment is renderer-agnostic and additive only | Accepted 2026-09-04 |
| [0013](0013-defaults-implement-public-contract.md) | Default renderers implement the public plugin contract | Accepted 2026-09-04 (amended 2026-09-25): the defaults stay in the core, the contract's source not its consumers; `test_contract_surface.py` guards drift |
| [0014](0014-nowplaying-and-peppy-are-distinct.md) | Now playing and the Peppy screen are distinct screens | Accepted 2026-09-04 |
| [0015](0015-skin-renderer-peppymeter-format.md) | Skin renderer targets the PeppyMeter/Volumio extended format | Accepted 2026-09-04; one item deferred to a spike |
| [0016](0016-plugins-as-separate-processes.md) | Plugins are separate processes with an IPC contract | Accepted 2026-09-04 |
| [0017](0017-core-daemon-in-python.md) | The core daemon is Python | Accepted 2026-09-04 |
| [0018](0018-volume-and-output-modes.md) | Volume and output modes | Accepted 2026-09-04 |
| [0019](0019-peppy-screen-lifecycle.md) | Peppy screen: entry, exit and lifecycle | Accepted 2026-09-04 |
| [0020](0020-library-browse-tree.md) | Library browse as a normalised tree | Accepted 2026-09-04; **partly superseded by [0030](0030-library-typed-radio-slimbrowse.md)**; cross-cutting table amended by 0029 |
| [0021](0021-deployment-flashable-image.md) | Deployment as a flashable image | Accepted 2026-09-04; distribution channel deferred |
| [0022](0022-settings.md) | Settings | Accepted 2026-09-04; remote-only text entry **superseded by [0029](0029-text-entry-on-every-surface.md)**; first-boot blocker answered by 0031; rows appended as confirmed (latest 2026-10-18) |
| [0023](0023-svelte-ui.md) | The UI is Svelte | Accepted 2026-09-04 |
| [0024](0024-bluetooth-pairing-no-pin.md) | Bluetooth pairing: no PIN, for this installation | Accepted 2026-09-06; **reversed by [0045](0045-bluetooth-pairing-confirmation.md)** |
| [0025](0025-project-licence-gplv3.md) | gexis-player is licensed GPL v3 | Accepted 2026-09-08 |
| [0026](0026-peppymeter-native-process-integration.md) | Peppy screen: native PeppyMeter process, labwc-mediated screen ownership | Accepted 2026-09-08 (amended 2026-09-16): vendor the engines, not the Volumio wrapper; compositor mechanism verified (Finding 025) |
| [0027](0027-lms-power-as-arbitration-mechanism.md) | LMS power is the arbitration mechanism; no permanent base slot | Accepted 2026-09-12; supersedes parts of 0010 |
| [0028](0028-ui-serving-and-command-channel.md) | The core daemon serves the UI; commands go over REST | Accepted 2026-09-12; answers what 0023 left open |
| [0029](0029-text-entry-on-every-surface.md) | Text fields are editable on the panel too; no on-screen keyboard | Accepted 2026-09-13; supersedes 0022's remote-only rule, amends 0020 |
| [0030](0030-library-typed-radio-slimbrowse.md) | Library by typed query and our own screens; SlimBrowse only for radio, rooted at `radios` | Accepted 2026-09-14; supersedes 0020's pass-through; amended by 0038 |
| [0031](0031-first-boot-setup-access-point.md) | First boot with no network raises a setup access point; typing happens on the user's phone | Accepted 2026-09-14 (amended 2026-09-28, 2026-10-07, 2026-10-12, 2026-10-15): WPA2 per-device password or open `gexis-setup`, QR codes, no captive portal, the phone drives setup; the channel away from the screen's interference, the next one every 2 min until a phone joins |
| [0032](0032-one-page-two-surfaces.md) | One page, two surfaces: the panel renders everything, a remote browser renders only settings | Accepted 2026-09-15; only the settings screen is responsive |
| [0033](0033-idle-and-home.md) | Idle is "not playing and not touched"; Home is the no-renderer screen | Accepted 2026-09-15; amends 0019 |
| [0034](0034-panel-volume-travel-and-mute.md) | Panel volume: slider over −45…0 dB, shown as slider position; mute restores the prior level | Accepted 2026-09-15; amends Phase 4 criterion 8 |
| [0035](0035-settings-api.md) | Settings: one registry in the daemon, a generic API, wired one setting at a time | Accepted 2026-09-15; the API 0032 deferred |
| [0036](0036-peppy-entry-and-no-rate-or-codec.md) | Peppy screen entry: the button, or five minutes of unattended playback; no sample rate or codec anywhere | Accepted 2026-09-16; amends 0019 (§2 amended 2026-10-02: LMS's rate shown on the visualiser) |
| [0037](0037-transport-commands.md) | Transport commands: one route to the active renderer; a control the renderer has is visible, disabled when it cannot work now | Accepted 2026-09-16; amends 0020's unusable-controls rule |
| [0038](0038-library-and-radio-on-the-panel.md) | Library and radio on the panel: the designed screens only, read through the core, played on LMS | Accepted 2026-09-17; amends 0030 (screens, no Podcasts, Radio Now Playing); §7 artwork ladder corrected 2026-09-18 |
| [0039](0039-cpu-governor-performance.md) | The CPU governor is `performance`, set by a unit in the image | **Reverted 2026-09-17**: ~10 °C hotter for no visible gain. Kept for the measurements |
| [0040](0040-enrichment-providers.md) | Enrichment providers: LMS's artist-information plugin first where it answers, a key-free set (MusicBrainz, Cover Art Archive, Wikipedia, ListenBrainz, LRCLIB) behind it | Accepted 2026-09-18 (amended 2026-10-07): providers asked at once, merged per field; fanart.tv and TheAudioDB before LMS for pictures. Amends 0012 |
| [0041](0041-scrims-dim-but-do-not-blur.md) | Scrims dim but do not blur: no `backdrop-filter` anywhere in the panel | Accepted 2026-09-18; overrides the designs' blurred sheets (Finding 037) |
| [0042](0042-a-local-cache-for-vendored-downloads.md) | A content-addressed local cache for the build's vendored downloads, network only on a miss | Accepted 2026-09-19; not the backup asked for: a mirror we control is deferred |
| [0043](0043-boot-animation-and-a-silent-boot.md) | A boot animation over a silent boot: every source of text quieted, Plymouth from the initramfs, torn down when the UI paints | Accepted 2026-09-19, built the same day, **never booted** (Finding 038) |
| [0044](0044-settings-row-vocabulary.md) | The settings row vocabulary grows six mechanics: `list`, `warn`, `onlyWhen`, `optionsFrom`, `picker`, `surfaced` — and text rows take real input on both surfaces | Accepted 2026-09-20; amends 0035 and 0022; never an on-screen keyboard |
| [0045](0045-bluetooth-pairing-confirmation.md) | Bluetooth pairing is confirmed on the panel, on a device's first pair only | Accepted 2026-09-20; **reverses 0024**; needs our own BlueZ `Agent1` |
| [0046](0046-fixed-output-hides-the-slider.md) | Fixed output hides the volume control everywhere, with a padlock and a reason, rather than disabling it | Accepted 2026-09-20, built 2026-09-23; implements 0018's unbuilt half |
| [0047](0047-the-idle-screen-gains-backgrounds-and-weather.md) | The idle screen gains four backgrounds and a weather stack, both keyed and both optional | Accepted 2026-09-21: Pixabay wallpapers, Open-Meteo weather; the external page becomes one option. Amends 0033 |
| [0048](0048-how-the-device-name-reaches-four-services.md) | How the one device name reaches squeezelite, go-librespot, BlueZ and the hostname | **Proposed** 2026-09-20: nothing applied while the device runs, not even the hostname |
| [0049](0049-the-pictures-folder-is-a-share.md) | The on-device pictures folder is an SMB share | Accepted 2026-09-21: one guest-writable directory; Debian's default shares off. Amended 2026-10-16: `nmbd` on, answering names only (never master browser) |
| [0050](0050-skin-previews-are-the-skins-own-picture.md) | A skin's preview is the skin's own picture | Accepted 2026-09-21: each skin's 1280x800 `screen.bgr`; no generated thumbnails or cache |
| [0051](0051-the-visualiser-reads-its-selection-from-a-file.md) | The visualiser reads its skin selection from a file | Accepted 2026-09-22: `/run/gexis/visualisation.json`, polled; corpus spans both template directories. Amends 0019, 0026, 0050 |
| [0052](0052-the-volume-path.md) | The volume path: what moves the level, how fast, and how loud it may get on its own | Accepted 2026-09-22, amended the same day: a ramp to each target, no restore ceiling; `max_ceiling` tops every scale |
| [0053](0053-the-panel-is-a-remote-control.md) | The panel is a remote control for what is playing, not a second volume | Accepted 2026-09-22: a panel change goes to the renderer, reaching the DAC through the mirror |
| [0054](0054-one-curve-and-the-renderers-own-number.md) | One volume curve, ours, applied to each renderer's own number | Accepted 2026-09-23 (§5 amended 2026-09-26, 2026-09-28): linear in dB over 60 dB, zero silent; Spotify is told the level |
| [0055](0055-which-output-the-device-plays-to.md) | Which output the device plays to | Accepted and built 2026-09-23: all four outputs offered via `output.conf`; the two without volume are fixed output |
| [0056](0056-the-spectrum-frame-follows-its-reader.md) | The spectrum frame is the size its reader expects | **Proposed** 2026-09-23, built and running: the relay folds 30 bands to the engine's count, peak per group |
| [0057](0057-the-meters-follow-the-volume.md) | The meters show what comes out, not what went in | Accepted and built 2026-09-23: the daemon publishes its dB cut; the relay applies it to meters and spectrum |
| [0058](0058-the-visualisations-ballistics-are-settings.md) | How the visualisation moves is three settings | Accepted and built 2026-09-23: spectrum smoothing, needle fall time, needle smoothing, under Display |
| [0059](0059-artist-portraits-in-the-list.md) | Where the artist list's portraits come from | Accepted 2026-09-24: a button in Enrichment, not a background sweep; fanart first, LMS fallback |
| [0060](0060-the-panel-background-gets-a-layer-of-its-own.md) | The panel's background gets a compositor layer of its own | Accepted 2026-09-24: `.bg { will-change: transform }`, so the blur is rastered once |
| [0061](0061-the-kiosk-does-not-render-subpixel-text.md) | The kiosk does not render subpixel text | Accepted 2026-09-24: `--disable-lcd-text`; every scroll 57–59 fps, none dropped |
| [0062](0062-the-queue-removes-by-swipe.md) | A queue row is removed by swiping it | Accepted 2026-09-24: left swipe past 96 px removes; the X goes; a visible hint is George's call |
| [0063](0063-the-queue-is-as-long-as-lms-says.md) | The queue is as long as LMS says it may be | Accepted 2026-09-24: LMS's `maxPlaylistLength`; `0` becomes 2500; no answer keeps 100 |
| [0064](0064-queue-rows-have-identities.md) | A queue row is identified by its track, not its position | Accepted 2026-09-24: keyed `<track_id>#<nth>` from LMS |
| [0065](0065-long-lists-are-built-a-screenful-at-a-time.md) | A long list is built a screenful at a time | Accepted and built 2026-09-24: 140 rows, then 160 per frame |
| [0066](0066-a-home-card-says-it-was-pressed.md) | A home card says it was pressed | Accepted and built 2026-09-24: `is-pressed` on pointerdown, navigation after the paint |
| [0067](0067-only-what-is-on-screen-is-built.md) | The long lists build only what is on screen | Accepted and built 2026-09-24: artist grid windowed by letter group; browse pane and queue rail by row |
| [0068](0068-the-sweeps-portrait-is-asked-for-first.md) | The sweep's portrait is asked for first, and the whole list at once | Accepted and built 2026-09-24: the sweep before LMS; every portrait URL fetched up front in batches of 50 |
| [0069](0069-what-a-lookup-cost-is-remembered.md) | What a lookup cost is remembered, though its answer is not | Accepted and built 2026-09-25: a lookup's cost stored for a day; its answer still not |
| [0070](0070-a-cover-at-the-size-it-is-drawn.md) | A cover is published at the size it is drawn | Accepted and built 2026-09-25: the cover also published at 100 px for rows, strip and release tab |
| [0071](0071-a-queue-we-changed-is-read-at-once.md) | A queue this daemon changed is read at once | Accepted and built 2026-09-25: re-read by the daemon, not awaited from LMS's push |
| [0072](0072-a-toggle-reads-its-own-state-back.md) | A toggle reads its own state back | Accepted and built 2026-09-25: shuffle and repeat read status back at once; not the skips |
| [0073](0073-an-artist-page-does-not-wait-for-its-covers.md) | An artist page does not wait for its covers, and the grid keeps its place | Accepted and built 2026-09-25: covers load after the page; the grid returns where it was left |
| [0074](0074-the-artist-page-holds-its-place.md) | The artist page holds the discography's place while About loads | Accepted and built 2026-09-25: About gets its final height up front; the discography does not move |
| [0075](0075-the-sweeps-portraits-serve-every-renderer.md) | The sweep's portraits serve every renderer | Accepted and built 2026-09-25: one lookup keyed on the folded name serves grid, artist page and any renderer |
| [0076](0076-criterion-0-closes-with-the-opens-below-the-floor.md) | Criterion 0 closes with the screen opens below the floor | Accepted 2026-09-25: closed on lived judgement; **revisit before Phase 13** |
| [0077](0077-a-source-that-is-off-is-not-running.md) | A source that is off is not running | Accepted 2026-09-25 (amended 2026-09-26): off is stopped, disabled and refused by arbitration; at startup the switch wins |
| [0078](0078-the-transition-screen-waits-for-the-threshold.md) | The transition screen waits for the threshold | **Superseded 2026-09-26 by [0094](0094-every-takeover-shows-the-transition-screen.md)**. Was: shown after `handoff_threshold` (0–3 s) |
| [0079](0079-with-lms-off-the-panel-is-two-screens.md) | With LMS off, the panel is two screens | Accepted 2026-09-25: library, browse and radio go with LMS; the settings row decides, not availability |
| [0080](0080-a-cover-is-matched-on-a-title-both-catalogues-agree-on.md) | A cover is matched on a title both catalogues agree on | Accepted 2026-09-25, amended the same day: asked with the title's own characters; trimmed matches verified both ways |
| [0081](0081-the-daemon-owns-the-cover-it-found.md) | The daemon owns the cover it found | Accepted 2026-09-25: the daemon publishes the found cover, filling the hole only, keyed on the track |
| [0082](0082-the-archive-keeps-its-dead-links.md) | The archive keeps its dead links | Accepted 2026-09-25: `HANDOFF-ARCHIVE.md` is not edited; the link test skips it |
| [0083](0083-a-backup-leaves-the-device.md) | A backup leaves the device | Accepted 2026-09-25: backup and restore through a second SMB share; a restore replaces everything and reboots. Amended 2026-10-17: upload in Settings, added to the list |
| [0084](0084-plugins-speak-json-lines-over-a-unix-socket.md) | Plugins speak JSON lines over a Unix socket | Accepted 2026-09-25: access by filesystem permission; D-Bus, loopback HTTP and binary framings rejected |
| [0085](0085-the-alsa-default-is-our-output.md) | The ALSA default is our output | Accepted 2026-09-25: `pcm.!default "output"`, a plain alias, not a `plug` |
| [0086](0086-a-plugin-declares-itself-in-a-manifest.md) | A plugin declares itself in a manifest | Accepted 2026-09-25 (amended 2026-09-30): `plugin.json`, read whether or not running; built-ins too; optional `area` |
| [0087](0087-the-beszel-agent-is-the-first-service-plugin.md) | The Beszel agent is the first service plugin | Accepted 2026-09-25: in the image, a manifest only; `--listen -1`, so no inbound port |
| [0088](0088-a-plugins-settings-reach-its-unit-as-environment.md) | A plugin's settings reach its unit as environment | Accepted and built 2026-09-25, amended the same day: rows name `env` variables in `/run/gexis/plugins/<id>.env`; restart if enabled |
| [0089](0089-arbitration-carries-a-plugin-renderer.md) | Arbitration carries a plugin renderer | Accepted and built 2026-09-25: a plugin renderer becomes an `Adapter` over its session; the manifest owns the unit name |
| [0090](0090-plexamp-ships-the-way-beszel-does.md) | Plexamp ships the way Beszel does | Accepted 2026-09-25: Plexamp plus our plugin (`gcarstoiu/gexis-plexamp`), the plugin unit `PartOf=` Plexamp's. Amended by 0100 |
| [0091](0091-a-plugin-renderer-is-taken-off-the-device.md) | A plugin renderer is taken off the device, not asked to leave | Accepted and built 2026-09-26 (amended 2026-09-26): SIGKILL, back by `Restart=on-failure`; no polite grace; no saved queue |
| [0092](0092-a-play-queue-is-an-acquisition.md) | A play queue this renderer has not seen is an acquisition | Accepted and built 2026-09-26: the play reissued on `device_freed`; no contract change |
| [0093](0093-we-do-not-build-or-patch-the-renderers.md) | We do not build or patch the renderers | **Accepted, immovable** 2026-09-26: renderers as upstream ships them; work around or report upstream |
| [0094](0094-every-takeover-shows-the-transition-screen.md) | Every takeover shows the transition screen, for the length the user sets | Accepted 2026-09-26; **supersedes 0078** and 0010's exempt pairs; `handoff_duration`, default 1.5 s |
| [0095](0095-a-renderer-waits-for-a-busy-device.md) | squeezelite waits for a busy device instead of failing | Accepted 2026-09-26, amended the same day: only squeezelite waits (`output_wait`); calls under the lock bounded to 2 s. Amends 0009 |
| [0096](0096-turntable-and-cassette-skins.md) | Turntable and cassette skins move | Accepted 2026-09-27: pinned skins from `foonerd/peppy_templates`, motion in our renderer. Amends 0026 |
| [0097](0097-what-the-visualiser-shows-beyond-the-title.md) | What the visualiser shows beyond the title, and how it moves | Accepted 2026-09-27: scrolling ticker and state fields, never actionable; smooth rotation a setting, stepped by default. Amends 0096 |
| [0099](0099-legal-and-credits-in-settings.md) | Settings carries a legal notice and credits | Accepted 2026-09-27: Legal and Credits pages under System, from one checked inventory file |
| [0100](0100-software-we-may-not-redistribute-is-fetched-on-the-device.md) | Software we may not redistribute is fetched on the device, when it is switched on | Accepted and built 2026-09-27: a pinned URL and sha256; `gexis-fetch@<name>` installs before the unit starts. Amends 0090 |
| [0101](0101-a-mini-player-on-the-phone.md) | A mini player on the phone: volume, visualiser, idle screen | Accepted and verified 2026-09-28: a phone-only bar acting on the panel |
| [0102](0102-settings-as-an-installed-web-app.md) | Settings as an app on the phone, without a URL bar | **Decided 2026-09-28: keep the bookmark**; manifest and icon kept |
| [0103](0103-debug-logs-keep-the-journal.md) | Debug logs: the journal kept across restarts, when asked | Accepted 2026-09-28: one switch in System, off by default, writes a persistent journald drop-in |
| [0104](0104-how-the-device-knows-it-needs-setup.md) | How the device knows it needs setup, and what it does about it | Accepted 2026-09-28 (amended 2026-10-07): no saved Wi-Fi and no `setup-done`; at once if new, 90 s at boot otherwise |
| [0105](0105-updates-over-the-network.md) | Updates over the network | Accepted 2026-09-29: Debian packages, a signed repository, backup and health check, rollback; Manual by default |
| [0106](0106-plugins-you-install-and-update.md) | Plugins you install and update | Accepted 2026-09-29: ours update with the release; uploaded `.tar.gz` plugins run confined; upload notice wording owed |
| [0107](0107-our-parts-as-debian-packages.md) | Our parts as Debian packages | Accepted 2026-09-30 (amended 2026-10-18: PeppyMeter's own keys kept across upgrades): one package per component, Debian's paths, no LMS address shipped |
| [0108](0108-how-a-release-is-published-and-found.md) | How a release is published and found | Accepted 2026-09-30 (amended 2026-10-07): apt repositories on GitHub Releases; signed channel files whose serial never goes down |
| [0109](0109-other-screens.md) | Other screens: two families, a known list, and the skins per size | Accepted 2026-09-30, amended the same day and 2026-10-18 (every window maximised): two families by scale factor; 197 models; skin sets become plugins |
| [0110](0110-the-update-experience.md) | The update experience: release numbers, one modal, playback stops on consent, the panel locked | Accepted 2026-10-01: `x.y.z` releases; night runs 03:00–04:00 when idle. Amends 0105, 0022 |
| [0111](0111-skin-sets-follow-the-screen.md) | Skin sets follow the screen: one pack, chosen by the screen, with consent | Accepted 2026-10-01: one `gexis-skins-<W>x<H>` pack, installed after consent; none in the image. Amends 0109, 0022 |
| [0112](0112-the-visualisers-fanart-frame-shows-the-artists-photos.md) | The visualiser's fanart frame shows the artist's photos | Accepted 2026-10-02: LMS `artistphotos` cached ahead; a 20 s crossfading slideshow |
| [0113](0113-a-skin-packs-tables-ship-apart-from-its-pictures.md) | A skin pack's tables ship apart from its pictures | Accepted 2026-10-02; **not yet built** (2026-10-07). Amends 0111 |
| [0114](0114-the-beszel-hub-as-a-plugin.md) | The Beszel hub as a plugin | Accepted 2026-10-02: `gexis-beszel-hub`, off until switched on, port 8095; no other settings |
| [0115](0115-the-lyrion-server-as-a-plugin.md) | The Lyrion server as a plugin | Accepted 2026-10-02 (amended 2026-10-03; 2026-10-18: locations chosen, folders ticked): upstream 9.1.1, off, lowest priority; never switched to by itself |
| [0116](0116-change-logs-in-settings.md) | Change logs in Settings | Accepted 2026-10-03: the last 10 releases' notes in Settings; older in `CHANGELOG.md` |
| [0117](0117-dacs-beyond-the-two-on-the-bench.md) | DACs beyond the two on the bench | Accepted 2026-10-04: the card reports its own scale and name; Tested, Known, Detected; DSD postponed. **Amended 2026-10-18**: the lists show Tested or nothing |
| [0118](0118-lyrion-s-own-menus.md) | Lyrion's own menus, plugins included | Accepted 2026-10-05: Lyrion's menus as home tiles, behind *Extended navigation*, off by default; player settings left out |
| [0119](0119-plexamp-is-claimed-from-settings.md) | Plexamp is claimed from Settings, and says when it is | Accepted 2026-10-05: claimed by `PLEXAMP_CLAIM_TOKEN`; the row reads *Claimed* with *Claim again* |
| [0120](0120-backgrounds-cropped-by-what-they-show.md) | Backgrounds cropped by what they show; Pexels and TheAudioDB | Accepted 2026-10-05 (**Pexels removed 2026-10-07**): cropped around detected subjects on the player (YOLOX-S) |
| [0121](0121-the-phone-as-the-panel-s-touchpad-and-keyboard.md) | The phone as the panel's touchpad and keyboard | Accepted 2026-10-05: a touchpad drives a panel pointer; a text field opens the phone's keyboard |
| [0122](0122-now-playing-minimised-to-where-you-were.md) | Now Playing minimised, back to where you were | Accepted 2026-10-06: a Minimise chevron keeps the library's path and scroll; Home kept |
| [0123](0123-the-network-in-settings-cable-and-wi-fi.md) | The network in Settings: cable and Wi-Fi | Accepted 2026-10-07: a Cable row; a manual address kept only once confirmed within 60 s |
| [0124](0124-software-volume.md) | Software volume, the owner's choice | Accepted 2026-10-07: off by default, after the meter tap, not bit-perfect below 100 %. Row merged by 0127 |
| [0125](0125-a-problem-report-users-can-download.md) | A problem report users can download, with the personal parts taken out | Accepted 2026-10-07: one zip, personal parts tokenised on the device, read before sending. Sending revised by 0138 |
| [0126](0126-hardware-reports-from-users.md) | Hardware reports from users | Accepted 2026-10-07: a guided check to a pre-filled GitHub issue; a Reported state, merged by reviewed commit. **Amended 2026-10-18**: lists show Tested (here or reported working) or nothing, a problem as a line |
| [0127](0127-one-volume-row.md) | One Volume row: Hardware, Software or Fixed | Accepted 2026-10-07: default Hardware, Software where there is no control; a migration carries old choices |
| [0128](0128-setup-installs-plugins-and-settles.md) | First setup installs the plugins and waits until the player has settled | Accepted 2026-10-07: a Plugins step before Review; an unskippable settling screen |
| [0129](0129-a-service-says-whether-it-is-connected.md) | A service says whether it is connected | Accepted 2026-10-08: read from the unit user's connections, not its log; `"connection": true`; Beszel first |
| [0130](0130-the-spectrum-covers-what-is-heard.md) | The spectrum covers what is heard: 50 Hz to 16 kHz at every rate | Accepted 2026-10-08: log-spaced bands, rate-sized FFT; amended 2026-10-13: a band's level is its energy, no lift |
| [0131](0131-setup-can-restore-a-backup.md) | Setup can restore a backup | Accepted 2026-10-08 (amended 2026-10-08; 2026-10-18: the review by section): after Network, New player or Restore; every answer changeable |
| [0132](0132-reset-to-factory-settings.md) | Reset to factory settings | Accepted 2026-10-09: in System; wiped at next boot to a fresh card, backups and music included |
| [0133](0133-the-waiting-screen-and-the-players-own-wallpapers.md) | The waiting screen, and the player's own wallpapers | Accepted 2026-10-10 (amended 2026-10-11): built-in Gexis wallpapers; with LMS off, a waiting screen of clock and source tiles |
| [0134](0134-the-panel-says-when-the-player-has-no-network.md) | A network lost after boot opens the setup network | Accepted 2026-10-11: after two minutes without a network; the strip withdrawn |
| [0135](0135-display-standby.md) | Display standby: the screen off on demand and at night | Accepted 2026-10-11: HDMI off while playing; touch, music or phone wake it. Amends 0019 |
| [0136](0136-switching-between-players-on-the-phone.md) | Switching between players on the phone | Accepted 2026-10-11: players announce `_gexis._tcp`; the phone lists them and moves the tab |
| [0137](0137-plugins-are-told-when-output-is-fixed.md) | Plugins are told when the output is Fixed | Accepted 2026-10-11: an `output` message within contract 1; Plexamp held at 100 |
| [0138](0138-reports-in-steps-and-one-way-to-send.md) | Reports in steps, a visible checklist, and one way to send for both | Accepted 2026-10-11: three steps; one Send step: GitHub issue or a download to e-mail |
| [0139](0139-no-passwordless-sudo-in-the-public-image.md) | No passwordless sudo in the public image; test cards get it by provisioning | Accepted 2026-10-12: no sudoers rule for `pi`; `DEV_SUDO="yes"` for test cards |
| [0140](0140-the-software-volume-is-set-before-the-renderers-start.md) | The software volume is set before the renderers start | Accepted and built 2026-10-12: `gexis-softvol-restore.service`, a oneshot before the renderers |
| [0141](0141-picture-and-sound-on-different-hdmi-ports.md) | Picture and sound on different HDMI ports | Accepted 2026-10-12: both ports listed; Screen port when both connected; sound-only port black; jack stands in |
| [0142](0142-the-player-announces-for-its-plugins.md) | The player announces for its plugins | Accepted 2026-10-12: uploaded plugins denied port 5353; `announce` event, avahi file per plugin |
| [0143](0143-usb-dacs-widened-to-32-bits-and-lyrion-at-384-khz.md) | USB DACs: widened to 32 bits, and Lyrion at 384 kHz | Accepted 2026-10-12: `type linear` to S32 for 32-bit-only cards; Squeezelite told rates ≤384 kHz |
| [0144](0144-native-dsd-on-a-dac-that-takes-it.md) | Native DSD on a DAC that takes it | Accepted 2026-10-12: Fixed volume + card reporting DSD → Squeezelite `-D`; peppyalsa skips non-PCM |
| [0145](0145-multichannel-folded-down-to-stereo.md) | Multichannel files folded down to stereo | Accepted 2026-10-13: our own Squeezelite folds >2 channels down (ITU, LFE out, no clipping) |
| [0146](0146-the-meters-follow-the-volume-again-with-a-gain.md) | The meters follow the volume visibly, with a gain of their own | Accepted 2026-10-13: bars the whole cut, needles half, Fixed unchanged; published at every start; a Gain row −10..+20 dB; the needles' share a row (Half the drop / Like a real amplifier) |
| [0147](0147-a-tv-as-the-screen.md) | A TV as the screen, by choosing its port | Accepted 2026-10-13: the Screen port choice wins; 1080p at most; Keep from the phone; the panel's touch off. Amended 2026-10-14 (Finding 125): a listed panel shows its own Keep, and the phone answers too unless its touch is fingerprinted |
| [0148](0148-text-size.md) | Text size | Accepted 2026-10-14: 90-130 % on the player's screen; Home's tiles grow; a zoom set aside |
| [0149](0149-first-use-in-two-parts.md) | First use in two parts: set up, then make it yours | Accepted 2026-10-18: built on `ph-first-use` from Claude Design's hand-off; Claude's decisions recorded in it |
| [0150](0150-a-library-category.md) | A Library category | Accepted 2026-10-18: Lyrion Server's rows under Library; plugins may declare `area: library`; app links |

## Cross-cutting rules

Rules established in one record that bind the others. Their full history is
in [INDEX-FULL.md](INDEX-FULL.md).

**Unusable controls** — [0020](0020-library-browse-tree.md):

> If the capability does not exist, hide it. If it exists but cannot be operated
> here, show it and say where it can be.

Volume in fixed output is hidden (0018); read ADR-0014's "hidden or greyed"
through this rule. **Amended by [0037](0037-transport-commands.md):** a control
the renderer has that is not operable *right now* (Next on a radio station)
stays visible and disabled. **Amended by [0029](0029-text-entry-on-every-surface.md)
and [0030](0030-library-typed-radio-slimbrowse.md):** text fields are editable
on the panel and search is not rendered, so the second branch has no live case;
it is kept as a principle. The rule binds a *shippable* product; during
development unwired UI is marked in the code, and Phase 9 criterion 2 is the
backstop.

**Accountability** — [0010](0010-arbitration-slot-model.md), restated by
[0018](0018-volume-and-output-modes.md):

> Never show a state the user cannot account for.

Not a prohibition on silence: mute, fixed output into a powered-down amplifier
and minimum volume pass, because the user caused them. An uncommunicated
renderer takeover does not.

**Never reference an ALSA card by index** — [0009](0009-logical-output-device.md).

**Spend the hardware on responsiveness.** Footprint and flash wear are not
selection criteria. Protect the audio path with priority, not by doing less.

## Deferred, needing their own records

| Subject | Raised by | Why it is not settled |
|---|---|---|
| ~~Qobuz navigation model~~ | 0020 | Answered 2026-09-14 by [0030](0030-library-typed-radio-slimbrowse.md): not rendered. |
| Image distribution channel | 0021 | Plain `.img`, self-hosted Imager repository, or Imager's community categories. |
| `steps.per.degree` quantisation | 0015 | Not decidable from configuration; spike defined. |
| Apt repository infrastructure | 0021 | In-place updates require a signed, hosted repository. |
| Maximum volume ceiling | 0018 | Still undecided. |
| Plugin settings pages | 0022 | Belongs to the plugin contract (0016). |
| Pairing mode as a per-installation setting | 0024 | Persistence built; the settings screen remains. |

## Conventions

- One decision per record. Numbered, never renumbered.
- A superseded record keeps its number and gains a header pointing forward.
- **Rejected alternatives are recorded with the reason they were rejected.**
  Rejected designs look reasonable again later and the reasons stop being
  obvious. [0010](0010-arbitration-slot-model.md) is the clearest example: three
  arbitration models were designed and dropped, and each would be re-proposed
  without that section.
- **Reversal conditions are stated where they are known.**
  [0008](0008-direct-alsa-over-pipewire.md) names the condition that would bring
  PipeWire back.
- Claims sourced from measurement cite the finding in `docs/findings/`.
  Unverified claims are marked as such inline.
- Add a new record's row here in one line: link, title, status with date, and
  at most ~15 words saying what was decided. Longer context belongs in the ADR.
