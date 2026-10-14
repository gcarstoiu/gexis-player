# Finding 125 — The review of everything since 0.10.1: 26 confirmed defects

**Date:** 2026-10-14. **For:** George, while 0.15.0 was published (*"run another full multi agent thorough check since we introduced a lot of things since the last one"*).

## Scope

- **What was reviewed:** every change from the last full review ([Finding 119](119-the-final-code-review.md), commit `323b0f34`, 0.10.1) to `v0.15.0`: 103 code files, +7,512 / -766 lines - the core, the updater, the image stages, packaging and the UI.
- **Method:** eight reviewers, one per area (the audio chain; updates and backups; screens; the core's wiring and server; library and enrichment; the touchpad and pointer; the UI screens; security across everything), each reading the diff and the code around it, running the test suite or throwaway scripts. **Every finding was then given to a second, independent agent told to refute it** against the code, often by running it. 26 were reported; all 26 were confirmed (none refuted, none left uncertain).
- **Not done:** nothing was run on a device; nothing was fixed yet. Severities are the verifiers'.

## The findings

| # | Severity | Area | Where | What |
|---|---|---|---|---|
| 1 | high | security | `core/src/gexis_core/backups.py:461` | Backup restore still writes as root through symlinks already on the disk, so a sandboxed plugin or a compromised pi service can get root |
| 2 | high | security | `core/src/gexis_core/backups.py:241` | Root writes into the pi-owned Backups folder through symlinks pi can plant there (new failure mark, and the existing .part file) |
| 3 | medium | updates | `core/updater/gexis-update:816` | finish_cut_short runs a whole release repair inside 'Check for updates', whose unit kills it after 300 s, with no panel lock and no inhibit |
| 4 | medium | updates | `core/src/gexis_core/backups.py:132` | Restoring a backup under a running uploaded plugin is undone, or corrupted, by the plugin's own SQLite WAL |
| 5 | medium | updates | `core/src/gexis_core/backups.py:386` | Backups store FIFOs and symlinks that restore then refuses, so the whole archive cannot be restored |
| 6 | medium | updates | `core/updater/gexis-update:1113` | postboot finishes a cut-short install but never restarts services or the device, so old code keeps running and reboot-required is ignored |
| 7 | medium | screens | `core/src/gexis_core/__main__.py:2207` | A rotation or model change on a chosen TV drops the 'chosen' mark; at the next start the TV's settings move onto the panel's port |
| 8 | medium | screens | `core/src/gexis_core/screen_detect.py:158` | has_touch() checks the raw stored id against the fingerprint table: on a legacy '-case' id the panel's own touch is disabled at every boot |
| 9 | medium | screens | `core/src/gexis_core/screen_detect.py:154` | The tested 7.9" bar is treated as a screen without touch: Keep buttons are hidden on it, and the known panels' touch ids are ignored while it is in use |
| 10 | medium | wiring | `core/src/gexis_core/__main__.py:1839` | Every user change of output is switched a second time, concurrently and outside the volume_change lock, by the new stand-in watcher |
| 11 | medium | ui-pointer | `ui/src/screens/KeepScreen.svelte:113` | Keep this screen? hides the panel's own Keep/Go back on almost every listed touch panel |
| 12 | medium | ui-screens | `ui/src/screens/Library.svelte:2042` | Back from a similar artist's page shows that artist's page under the previous artist's place in the path |
| 13 | medium | ui-screens | `ui/src/App.svelte:298` | Phone's Home after opening an album from Now Playing reopens that album instead of the library root |
| 14 | low | audio | `core/src/gexis_core/peppy.py:326` | A touch or a change of source during the visualiser's raise is lost, and the meter then covers the panel |
| 15 | low | audio | `core/src/gexis_core/outputs.py:207` | What a card takes is cached by card id for the life of the core, and the cache now also drives widening, Squeezelite's rates and native DSD |
| 16 | low | updates | `core/updater/gexis-update:816` | A cut-short skin pack makes 'Check for updates', or the nightly check in any update mode, reboot the device in the middle of playback |
| 17 | low | screens | `core/src/gexis_core/standby.py:222` | Scheduled standby can blank the screen while Keep this screen? is still counting down |
| 18 | low | wiring | `core/src/gexis_core/announce.py:96` | announce with services [] leaves a plugin's second and later services announced |
| 19 | low | wiring | `core/src/gexis_core/setup_network.py:835` | Setup network: _phone_since is never reset when the network reopens, so a newly joined phone loses its 10-minute grace |
| 20 | low | wiring | `core/src/gexis_core/announce.py:56` | announce refuses every service by default when the device name is over 63 characters, and the 63-character check is not avahi's 63-byte limit |
| 21 | low | library | `core/src/gexis_core/artistinfo.py:370` | Rescan revalidation only checks ids that are in the names snapshot, so stored photos for any other id survive renumbering, and a failed snapshot leaves the old one in place |
| 22 | low | library | `core/src/gexis_core/fanart.py:145` | Fanart frame's on-disk photos are keyed by LMS artist id and never invalidated on a rescan or server change |
| 23 | low | library | `core/src/gexis_core/artistinfo.py:286` | check_scope's 60 s gate is set before its awaits, so concurrent callers serve stale photos and stale LMS enrichment answers while a rescan is being revalidated |
| 24 | low | ui-pointer | `ui/src/lib/PanelPointer.svelte:134` | Outline heuristic `revealed()` drops the outline on always-visible action rows and on Lyrion search actions |
| 25 | low | ui-pointer | `ui/vite.config.js:13` | Text size leaves some pixel font sizes unscaled: font shorthand, --wait-name, inline style font sizes |
| 26 | low | ui-screens | `ui/src/screens/LyrionLevel.svelte:213` | Streaming albums with more than one track artist are labelled 'Play playlist'; the album exclusion never applies to them |

## Each finding, with its failure and the verifier's fix hint

### 1. Backup restore still writes as root through symlinks already on the disk, so a sandboxed plugin or a compromised pi service can get root

**high**, `core/src/gexis_core/backups.py:461`.

- **Failure:** 1. An uploaded plugin, which has network access (RestrictAddressFamilies allows AF_INET), creates the symlink `/var/lib/gexis-uploaded/<id>/link -> /etc/cron.d` in its own data folder.
2. It drops `gexis-x-20261014-000000.tgz`, containing member `var/lib/private/gexis-uploaded/<id>/link/evil` with a cron line, into the Backups share. That share is guest-writable over SMB.
3. It calls the restore action on the core's HTTP API, or waits for the owner to restore that backup.
4. The core, running as root, writes `/etc/cron.d/evil`, and the reboot after the restore runs it as root.

The same steps work from a compromised Plexamp (pi) through `home/pi/.local/share/Plexamp`.
- **Verifier:** I tried to refute this and could not. `_checked` (backups.py:369-398) looks only at member names and types. It refuses link members, `..`, `.`, empty parts and leading `/`, but it never checks what already exists on disk. `_put_back` (line 461) calls `extractall(root, ..., filter="tar")`. The `tar` filter rejects a member only when `realpath(join(root, name))` falls outside `root`. On the device `root` is `/`, so nothing can fall outside it and the filter blocks nothing. The code comment calls the filter "a second guard", and that claim is wrong.

Two MEMBERS folders can be written by principals that are meant to be less trusted than root:
- `home/pi/.local/share/Plexamp`, written by Plexamp running as pi. squeezelite also runs as `User=pi`.
- `var/lib/private/gexis-uploaded/<id>`, the plugin's `StateDirectory=gexis-uploaded/%i`. The plugin runs under `DynamicUser=yes` and owns that fold…
- **Fix hint:** Before extracting, walk each member's parent path under `root` with `os.lstat` and refuse the archive if any component that already exists is not a real directory (`S_ISDIR`, not a symlink). Also refuse when the final path is an existing symlink. Better still, extract each file with openat/O_NOFOLLOW relative to a directory fd. Then fix the "second guard" comment on `filter="tar"`, because that filter does nothing when `root` is `/`.

### 2. Root writes into the pi-owned Backups folder through symlinks pi can plant there (new failure mark, and the existing .part file)

**high**, `core/src/gexis_core/backups.py:241`.

- **Failure:** 1. pi runs `ln -s /boot/firmware/cmdline.txt /var/lib/gexis-core/backups/.gexis-den.before-update-20261015-030001.tgz.part` (or many such names covering the night's update window).
2. The nightly Automatic update asks the core for its backup.
3. Root opens the `.part` path and writes a gzip stream into cmdline.txt, then renames the symlink over the final name.
4. The Pi does not boot again; `/etc/shadow` or a sudoers.d file can be destroyed the same way.

The new mark gives the same overwrite whenever a backup fails: `.before-update-failed -> /etc/<anything>` gets the exception text written into it.
- **Verifier:** I could not refute this. `/var/lib/gexis-core/backups` belongs to pi with mode 2775 (packaging/core/build.sh:98). The setgid bit is set but the sticky bit is not, so the kernel's `fs.protected_symlinks` does not apply there. Root will follow any symlink pi leaves in that folder.

The core runs as root (gexis-core.service:21 `User=root`). ADR-0139 removes passwordless sudo from the public image precisely so that a flaw in Chromium, Squeezelite or Plexamp, which run as pi, is not a flaw as root. So pi to root is a real trust boundary here.

Both writes follow symlinks:
- `update_backup_failed` writes the mark with `mark.write_text`.
- `create` opens the predictable `.part` name with `tarfile.open(partial, "w:gz")`.

It is worse than reported. After `partial.replace(final)`, the renamed entry is still pi's symlink, and `create` then runs `chown pi:pi <final>`. `chown` dereferences symlinks …
- **Fix hint:** Create the partial with `os.open(..., O_CREAT|O_EXCL|O_NOFOLLOW, 0o644)` (or `tempfile.mkstemp(dir=directory)`) and hand the file object to `tarfile.open(fileobj=...)`. chown through the open descriptor (`os.fchown`) or with `os.chown(..., follow_symlinks=False)` instead of `chown(1)`. Write the failure mark the same way (unlink, then O_EXCL|O_NOFOLLOW), and have the updater open it with O_NOFOLLOW.

### 3. finish_cut_short runs a whole release repair inside 'Check for updates', whose unit kills it after 300 s, with no panel lock and no inhibit

**medium**, `core/updater/gexis-update:816`.

- **Failure:** An earlier repair failed and dpkg is still dirty. For example, postboot's heal raised CUT_SHORT because the network was not up at boot, or a skin-pack install was cut short. The user presses Check for updates. finish_cut_short starts reinstalling gexis-core (75 MB) and then dist-upgrades the remaining OS packages. After 300 s systemd sends SIGTERM to the unit's control group, apt and dpkg included. The install is cut short again, possibly with gexis-core half installed, and no note is left for the boot because finish_cut_short writes it only just before rebooting. The next attempt runs under the same 300 s limit. Meanwhile the panel stays unlocked and playback continues while packages are swapped underneath.
- **Verifier:** The code at v0.15.0 matches the finding. check() calls finish_cut_short() before it does anything else (gexis-update ~line 816). check() also runs when the Settings button starts gexis-update-checknow.service (__main__.py:2581 → updates.start(CHECK_UNIT)). That unit is the only updater unit with TimeoutStartSec=300; install, check (scheduled) and postboot all use infinity, and their comments say "an install is never cut short". finish_cut_short runs apt update, then heal() (dpkg --configure -a plus apt install --reinstall of the half-installed packages), then complete_release() (a full dist-upgrade and the gexis-player=target install, downloading archives as needed), then verify(). None of these apt calls passes prefix=INHIBIT.

The case this function was written for is a power cut that left no note, so postboot is skipped. The first thing to run after it is either the night's scheduled …
- **Fix hint:** When finish_cut_short finds work to do from the checknow unit, have it start gexis-update-install.service (or a dedicated infinity-timeout repair unit) and return, rather than running the repair inside the 300 s unit. Alternatively, add CHECK_UNIT to the running test in updates.view() and wrap the repair's apt calls in INHIBIT.

### 4. Restoring a backup under a running uploaded plugin is undone, or corrupted, by the plugin's own SQLite WAL

**medium**, `core/src/gexis_core/backups.py:132`.

- **Failure:** An uploaded plugin has a WAL database. A backup is taken, the plugin keeps writing, and the backup is restored from Settings. At the reboot the plugin's last connection checkpoints its post-backup pages into the restored file. The restore is silently reverted for that plugin, or, if the page layout changed in between, the database is corrupted.
- **Verifier:** I could not refute it. At v0.15.0 `restore_file` stops only the units listed in `STOPPED_FOR_RESTORE`, and that list holds only beszel-hub (backups.py:132). `var/lib/private/gexis-uploaded` is in `MEMBERS` (line 88). It is not in `REPLACED`, so it goes through `extractall`, which rewrites each file in place and keeps the same inode.

After that, `_put_back` unlinks the -wal and -shm beside every file it extracted (lines 509-514), including the WAL that a still-running uploaded plugin has open. The Settings restore path (wsserver.py:2579 `backups.restore(name)`, then `self._restore()`, which reboots) and the setup path (setup_flow.py:451) do not stop uploaded units either. The unit template gexis-uploaded-service@.service runs the plugin with `StateDirectory=gexis-uploaded/%i`, and nothing in the restore path stops it.

Any connection that stays open across the restore will later checkpoi…
- **Fix hint:** When the archive contains var/lib/private/gexis-uploaded, stop the uploaded-plugin units before extracting, for example `systemctl stop 'gexis-uploaded-service@*' 'gexis-uploaded-renderer@*'`, by extending `_stop_for_restore` to take glob units. Alternatively, put the files back through the write-beside-and-rename path `REPLACED` already uses, so an open connection keeps its old inode.

### 5. Backups store FIFOs and symlinks that restore then refuses, so the whole archive cannot be restored

**medium**, `core/src/gexis_core/backups.py:386`.

- **Failure:** An uploaded renderer plugin creates a FIFO in its StateDirectory (a pipe backend), or keeps a Python venv there (lib64 -> lib). A backup is created successfully and so is the update's .before-update backup. Later the user restores it, either because the update went wrong or on a new card via setup. restore_file raises ValueError before extracting anything, and no backup on the share can be restored.
- **Verifier:** I could not refute this. create() walks every entry under MEMBERS with _add(), which calls archive.add(recursive=False) and passes non-files through the live_databases filter unchanged (`if not info.isfile(): return info`). Symlinks therefore go into the archive as SYMTYPE and FIFOs as FIFOTYPE. Sockets are the one exception: tarfile's gettarinfo returns None for them and skips them. _checked() then raises on the first link and, new in this range, on any member that is not a plain file or a directory. That aborts restore_file before anything is extracted, so the whole archive fails because of one entry.

var/lib/private/gexis-uploaded is in MEMBERS and is the StateDirectory of the uploaded-plugin units (gexis-uploaded-renderer@.service: StateDirectory=gexis-uploaded/%i). Anything a third-party plugin creates there ends up in every backup, including the updater's .before-update one. creat…
- **Fix hint:** Leave symlinks, FIFOs and devices out at create time: in _add or in the filter, return None unless info.isfile() or info.isdir(), and log what was left out. Optionally have _checked skip such members in older archives with a log line instead of refusing the whole archive.

### 6. postboot finishes a cut-short install but never restarts services or the device, so old code keeps running and reboot-required is ignored

**medium**, `core/updater/gexis-update:1113`.

- **Failure:** The power is cut during the dist-upgrade before gexis-core and gexis-ui are unpacked. At boot the old gexis-core starts. postboot sees how=cut-short, and complete_release installs the new gexis-core, UI and system packages, possibly including raspi-firmware or systemd, whose postinst sets /var/lib/gexis/reboot-required. postboot reports '<target> installed (reboot)'. The device keeps running the previous core with the new UI and files until some unrelated reboot. The reboot marker stays behind and turns the next unrelated update into a reboot.
- **Verifier:** I read postboot(), complete_release(), heal(), finish_cut_short(), install(), restart(), the gexis-core postinst (packaging/core/build.sh) and gexis-update-postboot.service. Here is the path. install() writes the note with how=CUT_SHORT_HOW before dpkg starts (around line 1027). If the power is cut during the dist-upgrade, the device boots on whatever was unpacked by then. gexis-update-postboot.service runs After=gexis-core.service, so the core is already running from those files. postboot sees how==CUT_SHORT_HOW (or a dirty dpkg) and runs heal() and complete_release(), which dist-upgrade the remaining packages and install gexis-player=target. It then goes straight to verify(target), which only checks package versions, and to core_answers(), which only GETs /settings from whatever core is running. Then it reports done. Nothing on this path calls restart(), reads REBOOT_MARKER or matches …
- **Fix hint:** In postboot, after complete_release (only when it ran), do what finish_cut_short does: leave a how='reboot' note and `systemctl reboot`. The cheaper alternative is to compute the changes and call restart(changes), rebooting when it returns 'reboot', before verify and core_answers.

### 7. A rotation or model change on a chosen TV drops the 'chosen' mark; at the next start the TV's settings move onto the panel's port

**medium**, `core/src/gexis_core/__main__.py:2207`.

- **Failure:** sofapi setup: the 10.1" panel on HDMI 1 and the LG TV chosen on HDMI 2 (current = other-1920x1080-capped, HDMI-A-2, chosen) and kept. The user changes Screen rotation to 180°, or picks another model for the TV under Attached screen → Change. That restart is fine. On the next start, seen() returns the panel on HDMI-A-1, and at_start → moved() applies the TV model on HDMI-A-1. cmdline becomes 'video=HDMI-A-1:1920x1080,panel_orientation=upside_down' and the device restarts. The 1280x800 panel is forced to 1080p with the TV's scale. The question is marked phone-only, and touch_rules still ignores the panel's touch because the screen in use (the TV id) has no touch. The TV choice is lost.
- **Verifier:** _choose_screen (__main__.py:2207) builds Applied(model.id, turn, connector_now()), so chosen is False. connector_now() still returns HDMI-A-2, because seen() holds the chosen port while the old state is there. screen_apply.choose then writes current through to_json(), which drops "chosen" when it is False. Nothing else sets the mark again: the only chosen=True is in the Screen port handler (__main__.py:2293), and kept(), moved() and refresh() do not add it. At the next start, seen() no longer has a chosen connector. It falls back to prefer = the applied connector (HDMI-A-2), but the TV is not a known panel and the 10.1" panel on HDMI-A-1 is, so seen() returns the panel on HDMI-A-1. at_start's chosen guard fails, question() gives None and moved() re-applies the TV model on HDMI-A-1. That writes video=HDMI-A-1:1920x1080 and restarts. Before that start the restart from the rotation stops at…
- **Fix hint:** In _choose_screen, read current from read_state(). When current.chosen is set and its connector equals connector_now(), build the Applied with chosen=True so a rotation or model change keeps the mark.

### 8. has_touch() checks the raw stored id against the fingerprint table: on a legacy '-case' id the panel's own touch is disabled at every boot

**medium**, `core/src/gexis_core/screen_detect.py:158`.

- **Failure:** A player whose 10.1" (B) was kept under the cased preset before the merge, so screen.json has current.screen = 'waveshare-10.1-hdmi-b-case'. It updates to v0.15.0 and restarts. touch_rules() ignores 0712:000a, 0712:0010 and 222a:0001, and the panel no longer responds to touch at any start. Only the phone can drive it. Any later Keep question shows 'This screen has no touch: answer on the phone page' with no buttons.
- **Verifier:** I could not refute this. The code at v0.15.0 behaves exactly as the finding says. `has_touch()` (screen_detect.py:159) is a plain `FINGERPRINTS.get(screen_id)`. `FINGERPRINTS` has only the bare ids, such as 'waveshare-10.1-hdmi-b'. Every caller passes the raw stored id: `touch_rules` (screen_watch.py:296-299), `panels_off` (screen_apply.py:127) and `screen_question` (`__main__.py:445`). Nothing on the way rewrites a '-case' id to its bare form. `screens.by_id` (screens.py:199-200) still accepts the old cased id on purpose, so `refresh()` and screen_watch:263 treat the state as valid and keep it.

The cased id can really be on a device. `git grep` finds 'waveshare-10.1-hdmi-b-case' in v0.8.3's display_presets.json. Released tags v0.7.0 to v0.8.3 come before d93eb0f1, the commit that merged the cased presets into their panels. v0.8.3's screen_apply already wrote `current.screen` to /var/li…
- **Fix hint:** In `has_touch`, resolve the id first: `model = screens.by_id(screen_id); fp = FINGERPRINTS.get(model.id if model else screen_id)`. Alternatively, rewrite the stored `current.screen` to `by_id(...).id` in `read_state` or `refresh`.

### 9. The tested 7.9" bar is treated as a screen without touch: Keep buttons are hidden on it, and the known panels' touch ids are ignored while it is in use

**medium**, `core/src/gexis_core/screen_detect.py:154`.

- **Failure:** The 7.9" bar is in use and the user changes Screen rotation. After the restart, the bar shows Keep this screen? with no buttons and says to use the phone. Nobody at the panel can keep it; with no phone page open it reverts after 120 s. If the 7.9" bar's touch controller uses one of WaveShare's shared ids (0712:000a is the 11.9" bar's), the udev rule written at every boot also kills its touch entirely.
- **Verifier:** I confirmed this by running the code at v0.15.0. `has_touch()` (screen_detect.py:159) is true only when the model has a `FINGERPRINTS` entry that names a USB device. `FINGERPRINTS` covers the 10.1" (B), the 13.3" and the 11.9" bar. It has no entry for `waveshare-7.9-hdmi`, although that model is in `screens.TESTED`. HARDWARE.md lists the 7.9" bar as a tested touch screen. The rotation keep timeout was set to 2 minutes while George was "testing the bars" at the panel (2026-10-04), so the bar was being answered by touch before ADR-0147.

What happens when the 7.9" bar is in use:
1. `screen_question()` (`__main__.py:445`) returns `phone: True`.
2. `KeepScreen.svelte:113` then replaces the Keep / Go back buttons with "This screen has no touch: answer on the phone page".
3. `wsserver.py:2162` starts accepting non-local (phone) answers.
4. `touch_rules()` (`screen_watch.py:298`) writes the `LI…
- **Fix hint:** Treat the screen as touch-less only when it is a TV / `screens.OTHER` (or not in the presets list), not just when it lacks a fingerprint. Alternatively, have `has_touch()` return true for any listed touch panel, and add the 7.9" bar's fingerprint once its USB id has been read.

### 10. Every user change of output is switched a second time, concurrently and outside the volume_change lock, by the new stand-in watcher

**medium**, `core/src/gexis_core/__main__.py:1839`.

- **Failure:** Output is the DAC2 HD and Spotify is playing. The user selects 'Headphones' (or an HDMI port). `_change_output` stops Spotify, stops the renderers, writes output.conf and restarts them. Up to 3 s later the watcher sees ('sndrpihifiberry', False) become ('Headphones', False) and starts a second `_switch_output` while the first is usually still inside `systemctl stop`/`_start_software_volume`. It runs `supervisor.stop_active()`, `systemctl stop` (renderers plus plugin renderers), `outputs.write`, the level writes and `_restart_renderers` a second time. The renderers are restarted twice, and a source the user starts just after the first switch finishes is stopped by the second. The log also claims an HDMI port came back when none did. The same happens when the user picks an HDMI port with nothing on it, because the jack then stands in.
- **Verifier:** I read the code at v0.15.0 and the finding holds. `_watch_standin` (__main__.py 1839-1861) keeps `last` as a local variable and updates it only inside its own loop. Every 3 s it computes `outputs.in_force(settings_store.get("output_device"))`, which reads the stored choice: in_force returns `resolve(stored)`, or the jack when that choice is an unconnected HDMI port. So when the user changes the output, the card the watcher sees changes too: DAC2 HD to Headphones gives ('Headphones', False), and DAC to an empty HDMI port gives (JACK, True). Nothing filters out changes the user made, and `_switch_output` never updates the watcher's `last`. So within 3 s of a user change the watcher logs a stand-in or "HDMI is back" message that is false, calls `bump_settings_revision`, and runs `await _switch_output()` directly, without taking `volume_change`. The user's own path, the output_device row (25…
- **Fix hint:** Keep the watcher's last-seen (card, standing) in shared state that `_switch_output` sets to whatever it switched to, so a change the user made is already "seen". Have the watcher switch through `_change_output()`, or take `volume_change` and re-check under the lock before switching.

### 11. Keep this screen? hides the panel's own Keep/Go back on almost every listed touch panel

**medium**, `ui/src/screens/KeepScreen.svelte:113`.

- **Failure:** Someone chooses one of the listed touch panels, for example `btt-hdmi7-v1.2` or `geeekpi-7-hdmi`, under Attached screen on the panel itself. The player restarts on it and the panel says the screen has no touch, with no buttons to press, although it does have touch. Unless a phone happens to have the player's page open, nobody answers within the 30 s countdown (2 min after setup), and the player reverts. The new screen can never be kept from the screen itself.
- **Verifier:** I read the code end to end and it does what the finding says. `screen_question` (__main__.py:445) sets `phone = not screen_detect.has_touch(current["screen"])`. `has_touch` (screen_detect.py:159) is true only when a FINGERPRINTS entry has a usb id, and FINGERPRINTS holds just 3 models. I ran a script over `screens.all_screens()`: of the 106 listed screens, only waveshare-10.1-hdmi-b, waveshare-11.9-hdmi and waveshare-13.3-hdmi-h get has_touch=True. That includes waveshare-7.9-hdmi, which is marked tested. Every other model gets `phone: true`, and the presets describe many of them as touch panels; for example btt-hdmi7-v1.2 says "7 inch IPS capacitive touch, 5-point touch via USB".

In the non-bar branch, KeepScreen.svelte:113-117 then hides Keep and Go back and says "This screen has no touch". Nothing on the server side makes up for it. wsserver `_handle_screen_answer` still accepts a lo…
- **Fix hint:** Decide `phone` as "known to have no touch" rather than "not known to have touch". Treat any listed panel model, which is touch hardware, as having touch, and send the question to the phone only for `other-*` screens (TVs, screens in no list). Alternatively, keep Keep/Go back on the panel even when `phone` is true and add the phone note beside them.

### 12. Back from a similar artist's page shows that artist's page under the previous artist's place in the path

**medium**, `ui/src/screens/Library.svelte:2042`.

- **Failure:** Open artist A from the grid. On A's page, tap a similar-artist chip for B, which is in the library. B's page opens. Press Back: the path is now [A], but the screen still shows B's name, photo, discography and Popular list. Tapping an album there opens B's album with A's entry behind it. A's page only comes back by leaving and reopening it.
- **Verifier:** I read the code at v0.15.0 and did not run it. The chip at Library.svelte:2041-2042 is only a button when `knownArtists` has the name, so the scenario needs B to be in the library, which is the normal case. Tapping it calls openArtistByName(B). That calls openArtist(match) (732-772), which overwrites the single `artist`, `discography`, `genres` and `artistInfo` state with B's and appends {kind:'artist', id:B} to the path, giving [A, B]. back() (1202-1241) slices the path to [A]. It then reloads only when the new top is `menu`, `radio` or an artist entry carrying `byName`. A's entry came from openArtist and has no byName, so nothing reloads. The page branch at 1846 tests only `here?.kind === 'artist' && artist`. `artist` is still B, so B's page is drawn while the path says A. I found no $effect or other code that re-syncs `artist` with `here.id`. artistInfo's guard (`for !== entry.id`) on…
- **Fix hint:** In back(), when the new top is {kind:'artist'} and `artist?.id !== top.id`, reload that artist's page in place. Do it the way the radio branch does: pop the entry and call openArtist({id: top.id, name: top.label}), or add a no-push variant of openArtist.

### 13. Phone's Home after opening an album from Now Playing reopens that album instead of the library root

**medium**, `ui/src/App.svelte:298`.

- **Failure:** On the panel, tap the release title in Now Playing: the album page opens (libraryAlbum set). Go back to Now Playing, or anywhere else, then press Home on the phone remote. App bumps libraryHome, Library remounts with openAlbumNamed still set, and it navigates to that album page instead of the home grid. This repeats on every phone Home until the panel's own Home button or an artist link clears it. Turning LMS off and on again (libraryKept reset) remounts the same way.
- **Verifier:** I read the code at v0.15.0 and did not run it. The stale album request is real.

1. `openLibraryAlbum` (App.svelte:377-382) sets `libraryAlbum = {title, artist, n}` and bumps `libraryHome`.
2. Only `openLibraryHome` and `openLibraryArtist` ever set `libraryAlbum` back to null.
3. The phone's view_request effect (App.svelte:298-302) clears `libraryArtist`, sets `libraryRequested` and bumps `libraryHome` for 'home'. It never touches `libraryAlbum`.
4. `{#key libraryHome}` (line 749) therefore remounts `Library` with `openAlbumNamed={libraryAlbum}` still holding the old album.
5. Library.svelte:660-663 is an `$effect` that calls `openAlbumByName(wanted.title, wanted.artist)` whenever `wanted?.title` is set. It runs on that fresh mount, resolves the artist, then the album, and calls `openAlbum`. So the phone's Home ends on the album page instead of the root that ADR-0101 as amended promises …
- **Fix hint:** Set `libraryAlbum = null` wherever `libraryArtist` is reset: in the view_request handler (App.svelte:298) and in both `onclose` handlers. Or clear it once Library has consumed the request.

### 14. A touch or a change of source during the visualiser's raise is lost, and the meter then covers the panel

**low**, `core/src/gexis_core/peppy.py:326`.

- **Failure:** Unattended playback reaches its timer and run() calls show_async(). Within the next ~0.25 s or more, the user touches the panel (POST /touch goes to on_touch), or a phone takes over (on_active_change). visible is still False, so nothing is lowered. focus completes and the meter stays up over the panel the user just touched, or over the new source. The user has to dismiss it again.
- **Verifier:** I read peppy.py from end to end at v0.15.0. PeppyScreen.show_async takes the `_turn` lock and calls _tell(True). It then awaits asyncio.sleep(settle_s) (0.25 s) and awaits asyncio.to_thread(_run, "focus"). Only after both awaits does _shown() set visible=True. PeppyController.on_touch and on_active_change still decide synchronously with `if self._screen.visible: self._lower()`. Nothing records that a raise is under way, so a call that lands during those awaits sees visible=False and starts no hide_async. The raise then finishes and leaves the meter up.

Several callers can land in that window, because the event loop is free during the awaits:
- POST /touch from the panel (wsserver._handle_touch)
- the phone's idle toggle and view requests (_handle_idle_request and _handle_view_request, which both call on_touch)
- arbitration's on_active_change

Before a88a0e19, run() called the blocking …
- **Fix hint:** Set a `raising` flag in show_async before its first await and clear it in a finally. In on_touch and on_active_change, lower when `visible or raising`: the queued hide_async waits on `_turn` and so runs after the raise completes. Alternatively, keep a "lower requested" flag that show_async checks before its focus call and again after it.

### 15. What a card takes is cached by card id for the life of the core, and the cache now also drives widening, Squeezelite's rates and native DSD

**low**, `core/src/gexis_core/outputs.py:207`.

- **Failure:** DAC A (32-bit only, e.g. the SMSL, which takes DSD_U32_BE) is chosen, so its formats are cached under id X. It is unplugged and DAC B, which takes S16/S24 but not S32 and has the same id X, is plugged in and picked in Output. write() renders `type linear ... format S32_LE` over hw:X, and with Fixed it also writes `-D :u32be`. Every renderer fails to open the chain (B refuses S32_LE), or Squeezelite sends DSD_U32_BE to a card without it. Nothing plays until gexis-core restarts.
- **Verifier:** I couldn't refute this one. needs_plug() returns early once a card id is in _needs_plug (outputs.py:207-208). _formats and _rates are written only on that first answer (lines 243-246). I found no other writer, and nothing clears the caches on hotplug: no udev hook restarts gexis-core when a USB card changes, and __main__.py restarts gexis-core only from its own restart path (line 3756). widens(), native_dsd() and squeezelite_options() read only these caches, and write() (lines 812-827) takes widen and dsd from them.

So if a second card shows up under the same ALSA id, it inherits the first card's formats and rates until gexis-core restarts. That could be a different USB DAC with the same product-derived id, plugged in after the first was removed, or a firmware change on the same DAC. The old _needs_plug cache already had this problem for the plug decision. What v0.15.0 adds is that the …
- **Fix hint:** Clear the card's entries in _needs_plug, _formats and _rates when the output list shows the card was unplugged or replaced (or re-query on every output switch/write when the card isn't busy). Keep the cached answer only as a fallback for when the card is busy.

### 16. A cut-short skin pack makes 'Check for updates', or the nightly check in any update mode, reboot the device in the middle of playback

**low**, `core/updater/gexis-update:816`.

- **Failure:** The power is cut while a skin pack is installing. Music is playing when the user presses Check for updates, or the 03:00 timer fires before the core's pack retry has run heal. The check fixes dpkg and then runs `systemctl reboot`. Playback stops and the device restarts, though nothing was installed and nothing was asked for.
- **Verifier:** finish_cut_short() (core/updater/gexis-update:396-436) reboots whenever dpkg is dirty and dpkg_busy() is false. It never looks at which packages are broken, so a cut-short skin pack counts as an interrupted release install. Its target is the gexis-player already installed, and complete_release() reinstalls that same version. It then writes a pending note and runs `systemctl reboot`. Nothing on that path calls playing() or stop_playback().

check() calls it first, at line 816. The manual "check" action reaches check() through main() (line 1410). scheduled() calls check() at line 1140, before it reads setting("updates") or playing(). So the reboot happens even when Updates is not Automatic and music is playing.

I looked for guards that would stop this in practice:
- postboot is skipped on an ordinary boot. Its unit has ConditionPathExists=pending-check.json, and an interrupted pack instal…
- **Fix hint:** In finish_cut_short, when every broken package is a skin pack (PACK/gexis-skins) and gexis-player itself is not half-installed, run heal(opts) and return False without calling complete_release or rebooting. Otherwise check playing(), and if it is true, leave the repair to postboot or the install path rather than rebooting in the middle of playback.

### 17. Scheduled standby can blank the screen while Keep this screen? is still counting down

**low**, `core/src/gexis_core/standby.py:222`.

- **Failure:** Standby schedule on, 23:00-07:00, Back to standby after = 1 or 2 min. At 23:30 the owner chooses a new screen or rotation, and the player restarts. The question appears about 20 s after the core starts. At 60 or 120 s after core start the schedule calls standby.sleep('schedule'): the cover goes on and the output goes off, or stays on black if it carries the sound. The remaining seconds pass unseen and the change reverts.
- **Verifier:** I couldn't refute this one. Schedule.tick() (standby.py 222-237) only checks the on/headless settings, in_standby_time, standby.off, whether music is playing, and the time since standby.last_use. It never looks at state_store.state.screen_confirm.

Standby is created early in main() (__main__.py about line 3035), so last_use is the core's start time. The Keep countdown is always KEEP_S = 120 s and only starts at /screen/shown (_screen_shown, about line 3679), which is some seconds after the core starts. Neither the 'shown' path nor any other part of the Keep path calls standby.used(). Only a touch, the screen check and pairing do. Pairing already got this exact protection after the 2026-10-12 review ("A request in standby was drawn under the black cover ... and expired unseen"). The screen question did not.

In App.svelte the standby cover (z-index 2000) is drawn over the KeepScreen ques…
- **Fix hint:** In Schedule.tick, before sleeping, return early while a screen question is pending (pass Schedule a blocked=lambda: state_store.state.screen_confirm is not None, or screen_new/screen_check too). Also call standby.used() and wake in _screen_shown, the same way pairing does.

### 18. announce with services [] leaves a plugin's second and later services announced

**low**, `core/src/gexis_core/announce.py:96`.

- **Failure:** A connected plugin announces 3 services (for example _raop._tcp, _airplay._tcp and _spotify-connect._tcp), then sends {"t":"announce","services":[]} because the user turned that feature off inside the plugin. avahi keeps advertising services 2 and 3 on the LAN until the plugin disconnects or the core restarts, so phones list a target that no longer answers.
- **Verifier:** The path from the message handler to the file write has no guard that would stop this. In `__main__.py` (lines 4073-4085), the `announce` message goes through `announce.checked()`, which accepts `[]` and returns `[]`. It then calls `announce.write(session.id, [])`. In `announce.py` (lines 95-97), `write()` unlinks only the plain `gexis-plugin-<id>.service` file and returns early. The loop that would remove the numbered `.N.service` files (lines 109-112) never runs.

`withdraw()` does remove the numbered files, but it runs only when the plugin disconnects, and `clear()` runs only when the core starts. Until one of those happens, avahi keeps advertising services 2 to 4. This breaks what PLUGIN-CONTRACT.md line 212 promises ("`[]` withdraws them").

Severity stays low:
- it only hits a plugin that announced more than one service and then sends an empty list while still connected;
- the stal…
- **Fix hint:** In `write()`, when `services` is empty, call `withdraw(plugin_id, directory)` and return. Alternatively, drop the early return so the stale-file loop runs with `len(groups) == 0`.

### 19. Setup network: _phone_since is never reset when the network reopens, so a newly joined phone loses its 10-minute grace

**low**, `core/src/gexis_core/setup_network.py:835`.

- **Failure:** Session 1: a phone sits on the setup network without opening the page, and the player rejoins its home Wi-Fi after about 10 minutes, so `_phone_since` stays set. Hours later the Wi-Fi drops and watch() opens the setup network again. Someone joins it to fix the Wi-Fi but has not loaded the page yet. At the first 5-minute retry `joined_lately` is false because of the stale timestamp, so the player takes the radio back to the saved network and cuts the phone off, instead of granting the documented SETUP_ACTIVE_S.
- **Verifier:** In setup_network.py, `_phone_since` is set at line 839 only when it is None, and cleared at line 837 only when a retry counts zero stations. Neither `open()` (lines 483-552), the successful-join return in `_hold`, nor `_cable_back` (782-799) resets it. When a configured player leaves the setup network while a phone is still associated, which is exactly what the "nobody has used the page" branch at line 848 allows, the timestamp from that session survives. On the next `watch()` → `open()` → `_hold(RETRY_S)`, the first retry finds a station. `_phone_since` is not None, so it keeps the old value, `joined_lately` at line 844 is False, and `_page_in_use()` is also False because `_page_used_at` is just as stale. For a configured player (`_needed` False) the code falls through to the saved-network check and leaves at the first 300 s retry. It should instead give the newly joined phone the SETUP…
- **Fix hint:** In open(), when the state goes to "open" (or at the start of _hold), reset `self._phone_since = None`, and preferably `self._page_used_at = None` too, so each setup-network session starts its grace from scratch.

### 20. announce refuses every service by default when the device name is over 63 characters, and the 63-character check is not avahi's 63-byte limit

**low**, `core/src/gexis_core/announce.py:56`.

- **Failure:** Device name 'Wohnzimmer Regal links neben dem Fernseher und der großen Standuhr' (more than 63 characters): every plugin announce that leaves out `name` is refused with 'name is not text of at most 63 characters', so the plugin is never findable. Device name in Cyrillic or Greek of about 40 characters (about 80 bytes in UTF-8): the check passes, the file is written, avahi fails to add the service group, and the only trace is in avahi's log.
- **Verifier:** Both halves of the finding reproduce at v0.15.0.

1. In __main__.py (lines 4077-4078) the default name passed to `announce.checked` is the raw `settings.value("device_name")`. The device_name registry row has only a character-class `pattern` and no length limit, and the UI input has no maxlength. Only the derived hostname is capped, by `device_name.sanitise` with HOSTNAME_MAX=63. So when the name is longer than 63 characters, every plugin service that leaves out `name` is refused, and the whole announce message with it.

2. The check uses `len(str)`. avahi limits a service instance name to a 63-byte DNS label (AVAHI_LABEL_MAX 64 including the NUL). A non-ASCII name of 32-63 characters can exceed 63 bytes, pass the check and be written to /etc/avahi/services, and avahi then fails to register that group. The only trace is in avahi's log. Core logs nothing because the write succeeded.

Miti…
- **Fix hint:** Check bytes, not characters: `len(name.encode()) > 63`. When the name is the device-name default and it is too long, truncate it to 63 bytes at a character boundary instead of refusing, or fall back to `device_name.hostname()`.

### 21. Rescan revalidation only checks ids that are in the names snapshot, so stored photos for any other id survive renumbering, and a failed snapshot leaves the old one in place

**low**, `core/src/gexis_core/artistinfo.py:370`.

- **Failure:** First case: a composer (id 50000, not in the unfiltered `artists` list) has a Discogs photo stored. A full rescan gives id 50000 to someone else, and the grid or artist page then shows the old composer's photo (or initials from a stored None) for the new artist, indefinitely. Second case: the player moves to another server, the names fetch times out, server A's snapshot {1:'A'} is kept, photo for id 7 is stored, the server rescans and id 7 now names someone else, and the old photo is still served.
- **Verifier:** The logic holds at v0.15.0. In _revalidate (artistinfo.py:370), `moved = [i for i, name in before.items() if now.get(i) != name]` only looks at ids that are in the old snapshot, so a stored photo or slow marker for an id outside it is never compared and stays. check_scope (around lines 305-317) calls `_snapshot_names(None)` after forget(). That re-fetches the names, and when the fetch fails, `_snapshot_names` returns without writing (lines 349-354). forget() (lines 481-495) clears NAMESPACE and SLOW_NAMESPACE but not NAMES_NAMESPACE. So a stale snapshot, from the previous scan or from a different server, survives. Photos stored afterwards under the new numbering are then checked at the next rescan against that stale map, and any of their ids missing from it are kept.

Whether the wrong photo actually shows depends on what was stored. `_url` (line 269) wraps an absolute plugin URL (Discog…
- **Fix hint:** In _revalidate, drop every stored photo or slow key whose id is not unchanged in both maps (with `now.get(i) == before.get(i)` and both present). Also clear NAMES_NAMESPACE in forget(), or whenever the snapshot fetch fails, so that a missing snapshot makes the next rescan drop everything.

### 22. Fanart frame's on-disk photos are keyed by LMS artist id and never invalidated on a rescan or server change

**low**, `core/src/gexis_core/fanart.py:145`.

- **Failure:** Artist A (id 123) is played and 10 of A's photos are written to fanart/123/.done. 'Clear library and rescan' gives id 123 to artist B. Playing B on LMS calls for_artist(name, 123), sees fanart/123/.done with jpgs, and the visualiser's fanart frame shows A's photos during B's tracks until the folder falls out of the 60-artist LRU.
- **Verifier:** I could not refute this. Fanart's on-disk cache (/var/cache/gexis-core/fanart/<artist_id>/) is keyed only by the LMS artist id. The base URL is passed in but never recorded with the cache, there is no lastscan or server scope, and __main__.py (around line 3149) registers on_forget only for the enrichment-cache providers, not for fanart. A folder that has a .done marker and jpgs is returned without asking LMS again, because _empty_aged applies only to empty folders. The only thing that removes a folder is the 60-artist LRU trim.

The rescan half of the scenario is weaker than the finding says. Finding 029 §4 shows a full rescan giving every artist a new, higher id (Holograf 2681 -> 9974). That points to ids that keep counting up and are not reused, so old folders are mostly just orphaned, not hit. A collision after a rescan cannot be ruled out, but there is no evidence for one. Stale name…
- **Fix hint:** Scope the fanart cache the way LmsArtistInfo is scoped. Either key the directory by server and lastscan, or register `artistinfo.on_forget(lambda: shutil.rmtree(fanart dir) + fanart._ids.clear())`.

### 23. check_scope's 60 s gate is set before its awaits, so concurrent callers serve stale photos and stale LMS enrichment answers while a rescan is being revalidated

**low**, `core/src/gexis_core/artistinfo.py:286`.

- **Failure:** A rescan renumbers id 5 from 'Old' to 'New', and the grid sends two artist-photo batches together. The first runs the check, which spends time fetching 8400 names. The second skips the check and returns Old's Discogs photo for id 5. The tile shows the wrong artist until it is asked again.
- **Verifier:** In check_scope (artistinfo.py:283-286), `self._scope_checked = now` is set before the awaited `serverstatus` and `_artist_names()` RPCs, and there is no lock or shared future. A second caller (photos() at line 400, or the providers.py:303/344 enrichment paths) that arrives during those awaits passes the 60 s gate, returns at once, and reads `_photos` or the store before `_revalidate`/`forget` has run. The 60 s gate already accepts some staleness on purpose: a rescan that happens within 60 s of the previous check also goes unseen until the next check. So this race only adds the length of the in-flight check to a window that is already open. The case that matters most is the first check after start-up, when `_scope_checked` is None. If the library was rescanned while the player was off and the grid then asks for several photo batches at once, every caller except the first reads the old sto…
- **Fix hint:** Hold the check in a shared in-flight asyncio.Task or an asyncio.Lock so that concurrent callers await the same check. Set _scope_checked only once the check has finished, or keep setting it early but make later callers await the pending task while it runs.

### 24. Outline heuristic `revealed()` drops the outline on always-visible action rows and on Lyrion search actions

**low**, `ui/src/lib/PanelPointer.svelte:134`.

- **Failure:** On the panel, the phone touchpad pointer passes over any playlist in Library → Playlists or any radio station row: the dot shrinks to 'press' but no outline is drawn. In a Lyrion search with a result selected, the pointer over its Play / Play next / Add shows no outline either.
- **Verifier:** I checked this against HEAD, which is v0.15.0 (a4778232). Both parts of the finding hold.

1) Lyrion search. In LyrionSearch.svelte:121-124 the actions are `<span class="act" role="presentation">`, placed inside `<span class="acts">`, which sits inside `<button class="row">`. None of those spans matches PRESSABLE (PanelPointer.svelte:56), so `target.closest(PRESSABLE)` climbs up to button.row. revealed(button.row) then works like this:
- the button does not have the class `act`;
- `button.closest('.row__actions, .acts')` is null, because the button is the ancestor of `.acts`, not inside it;
- `el.querySelector('.act')` finds the span, so revealed() returns true.

As a result, line 106 draws no ring while the pointer is over Play, Play next or Add on a selected search result. Commit 0a64dda2 ("the reveal's action buttons keep their outline") added the `.acts` guard. That guard only works …
- **Fix hint:** Add `[role=presentation].act` (or `.act`) to PRESSABLE, or resolve the pressable to `target.closest('.act')` first. Make revealed() require an explicit marker such as `.is-revealed` on the row, rather than the mere presence of `.act`, so that rows with always-visible actions (Playlists, stations) keep their outline.

### 25. Text size leaves some pixel font sizes unscaled: font shorthand, --wait-name, inline style font sizes

**low**, `ui/vite.config.js:13`.

- **Failure:** Text size is set to 130 % on the panel. The update screen's 22 px title, the waiting-services names and the source-mark letters keep their 100 % size while the text around them grows.
- **Verifier:** The finding holds for its two CSS cases. The PostCSS plugin in ui/vite.config.js:13 rewrites only `font-size` declarations and `--t-*` custom properties. So:

1. `font: 700 22px var(--font-ui)` at UpdateScreen.svelte:123 (the .lock__continue button label) is skipped.
2. `--wait-name: 16px/27px/24px` in WaitingServices.svelte is skipped, and its consumer `font-size: var(--wait-name)` has no px for the plugin to find.

Both stay at their 100 % size while App.svelte:499 sets `--text-scale` to 0.9–1.3 on the panel. Neither screen sets the variable itself, so the mismatch shows whenever Text size is not 100 % and one of those screens is up. ADR-0148 says "Every font size scales … no screen is edited by hand and a new one is included without thinking about it", so the code falls short of its own ADR.

The inline cases are weaker:
- SourceMark's letter is drawn inside a fixed-size ring. That is…
- **Fix hint:** Two ways: have the plugin also rewrite the px size inside a `font` shorthand and in `--wait-*` (or any font-size custom property), or change UpdateScreen to use `font-size: 22px` and rename `--wait-name` to a `--t-*` name. The inline sizes in SourceMark and fit.js can stay as they are, or be multiplied by `--text-scale` if that is wanted.

### 26. Streaming albums with more than one track artist are labelled 'Play playlist'; the album exclusion never applies to them

**low**, `ui/src/screens/LyrionLevel.svelte:213`.

- **Failure:** Open a Spotify album through Spotty where one track has a featured artist: that track's subtitle is 'Artist, Guest • Album' and the rest are 'Artist • Album'. The Set has 2 entries, so mixed is true, hint is null, and the album page's main button reads 'Play playlist' instead of 'Play album', with artist lines under every track. The same happens with a Qobuz compilation or soundtrack album.
- **Verifier:** I read the code end to end and the logic does what the finding says. `_hint` (core/src/gexis_core/menus.py:517-537) returns 'playlist' only for a Spotty `:playlist:` link, a `/playlist/` link or a Qobuz `/images/playlists/` cover. It returns 'album' only when commonParams or params hold `album_id`, which only Lyrion's own library items carry. The tests pin this: a Spotty album (`spotify:album:16tY`) and a Qobuz album cover (`/images/covers/`) both give None (test_menus.py:390 and 392). So for any streaming album, ctx.from.hint is null and `hint !== 'album'` is true. In LyrionLevel.svelte:211-212, `playlist` then turns true as soon as `mixed` is true. `mixed` is true when the tracks' subtitle text before ' • ' (or ' - ') has more than one distinct value, which happens on a compilation, a soundtrack, or one track that credits a guest artist. The button text then follows `playlist` ('Play p…
- **Fix hint:** Have the core return 'album' for a streaming album's own markers (a favorites_url containing ':album:', or a Qobuz cover under /images/covers/) so the `hint !== 'album'` guard applies, or else make `mixed` count toward 'playlist' only when the hint is null and the item is not an app album.

