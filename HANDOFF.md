# Handoff

Last updated: 2026-09-22 (twenty-second session, on R2D2 — **Phase 9's
design sweep: 9a through 9h are done, the 2026-09-22 drop is applied, and
the image is built and verified. The volume work is split in two: 9i the
level, 9j where it goes**)

## Start here

**Phase 9's design sweep is done bar the volume work.** **9a through 9h are
built, checked on the panel and committed.** What is left is now **two**
subphases, split on George's agreement (2026-09-22):

- **9i — the volume path, measured, then the rows.** Eight rows in Audio and
  not one of them wired, ADR-0046's fixed output never built — and **three
  symptoms George found on the built panel**: the level does not move
  smoothly, it hops after a cold boot, and the maximum feels different
  between renderers. **[Finding 045](docs/findings/045-the-volume-path-measured.md)
  is the first half**, done 2026-09-22, everything that needed nobody at the
  speakers:
  - **The jumps are the drag's sampling.** A 200 ms drag delivers 6 of 12
    finger positions to the DAC, in **4 dB steps**; a 2 s drag delivers all
    60, in 0.45 dB steps. The panel sends one request at a time and keeps
    only the latest, so the hardware hears a staircase.
  - **A write costs 16.4 ms and two thirds of that is ours** — the `amixer`
    subprocess. libasound directly is 5.7 ms, of which 5.7 is the DAC's own
    I²C; the dummies take 0.021 ms. So the daemon could **ramp**: 4 dB is
    eight steps and 46 ms.
  - **The boot hop is 53 dB, at thirteen seconds.** The boot service sets
    −90 dB, squeezelite starts, LMS pushes its remembered 25%, and the
    daemon mirrors it: −37 dB. At LMS 100% that would be **+90 dB**.
    **`boot_volume` does not survive the first renderer**, which changes the
    question George owes an answer to.
  - **The meter is a pre-attenuation tap**, so "does one renderer deliver a
    quieter stream" can be answered **with the room silent**.
  - **Spotify's volume is applied twice** (§7, measured the same day with
    George's phone connected): go-librespot attenuates the stream *and* the
    daemon attenuates the DAC. At its 25 the stream is down 21 dB and the
    DAC is at −34, about −55 dB where a quarter was asked for; the same
    quarter on LMS is −37 and nothing else. **The maxima are not what
    differ** — both deliver full scale at 100% — everything below it does.
    `external_volume: true` in go-librespot's config is the fix, our config
    sets no volume keys at all, and **it makes Spotify louder at the same
    setting**, so it belongs at the gate.
  - **Connecting Spotify put the DAC at 0.00 dB by itself**, restoring
    240/240 — the loudest the device has, from the same restore-on-acquire
    that causes the boot hop.
  - **Bluetooth is the one renderer left to measure**, and it needs a phone
    connected and nothing else.
- **9j — which output.** The device has four cards and the user has never
  been offered the choice. All three renderers already play to one PCM, so
  the switch is two lines of `/etc/alsa/conf.d/output.conf` and the meter
  follows the audio — but **HDMI has no mixer control at all**, so choosing
  it *is* fixed output. Wants an ADR before implementation.

**The 2026-09-22 design drop is applied, all four parts of it.** George:
*"Please be thorough and check the designs I import — do not guess or
inferr."* The drop is vendored whole at `design/` and is the point of truth
for what it draws; **the panel stays the point of truth where the two
differ**, which the vendoring commit lists.

- **Now Playing's meta column grew** — tabs 19, title 54 at 1.06 clamped to
  two lines, artist 35, album 30, year 25 mono. **The Track tab's synced
  strip is three lines, not five**: 32px, the neighbours at 0.42, and a
  30%/70% mask on the window so they are ghosted rather than merely dimmer.
- **The idle screen has two forecast layouts**, `3 days` and `None`, and
  carries feels-like, wind, sunrise and sunset.
- **The visualisation picker is built** — a list of 380px with a preview
  pane beside it. Tapping a row previews; the 60px button writes.
- **`device_name` carries a warning**, and `warn` now has a second form: a
  string is about the row and is up the whole time the sheet is open. The
  drop's sentence says saving restarts the services and stops playback;
  [ADR-0048](docs/decisions/0048-how-the-device-name-reaches-four-services.md)
  applies the name at the next restart and stops nothing, so the row reads
  George's own line instead (ADR-0044 §2 records the deviation).

**George's five findings on the drop are in** (2026-09-22, after the first
pass): the renderer's mark stands alone at 32px with no word beside it; a
phone's taps no longer end the visualisation; the picker follows the corpus
and the fourth word is **All**, not Random; the `device_name` warning is his
sentence; and `idle_minmax` is gone, so the registry is 71 rows.

**The one that was not a design change:** *"Changing skin during playback
while being in visualization mode, stops showing the visualisation."* The
cause was the touch report. ADR-0036 counts a touch as attention and
attention takes the meter down — and the panel tells the daemon about
touches, because the daemon cannot see them. That report was wired to the
window rather than to the surface, so **a tap on a phone ended the
visualisation on a device in another room**. `/surface` already knew the
difference (ADR-0035 §6); the report is the panel's alone now.

**Two things George has to rule on:**

- **`skin` is a new settings row and needs his word for ADR-0022's
  inventory** ([N]). It is the picker's own row: a `choice` with
  `picker: true`, `optionsFrom: skin_corpus`, shown only while
  `skin_rotate` is off.
- **Two type sizes are pinned rather than grown.** `--t-title`, `--t-artist`
  and `--t-lead` moved for the Track header, and two other places used them:
  the Artist tab's name and the Release tab's title. The drop does not touch
  either panel, so both keep the size they had (25px and 22px) as literals.
  Say the word and they follow.

**9h is finished, and the last of it closed a hole that had been open since
9d.** `skin_corpus` and `skin_rotate` were in the registry with nothing
behind them — unwired, so a write was refused.
[ADR-0051](docs/decisions/0051-the-visualiser-reads-its-selection-from-a-file.md)
gives the renderer a file to read: `/run/gexis/visualisation.json`, written
by the daemon and polled in the driver's frame hook beside
`nowplaying.json`. No restart, no new channel.

**The corpus is every pack — 99 skins, 77 meters, 9 spectrum, 13 both.** The
engine reads one `meters.txt` (`gelo5/templates`, 71 skins and not one
spectrum), so two of the four corpus words would have offered nothing; the
driver loads all four template directories and swaps `base.path` around the
factory, as it already swaps `meter`. **It said 84 for a few hours** — the
stock pack was excluded on the grounds that the spectrum engine was pointed
at Gelo5's sections, which described one hardcoded line rather than the
device. George: *"there were 99 skins in total — why are you telling me now
that there are only 84?"* The engine follows the skin's pack now.

**And the visualiser was black when he tapped the button** — three faults in
a row, all introduced the same day, all fixed and this time **verified as
pixels**: the spectrum config ships root-owned while the unit runs as `pi`,
so the write that chooses a section killed `main()` after the display
existed and left a window with no loop behind it, owning every touch; a
spectrum-only skin with no engine draws nothing at all; and the engine's own
`meter = random` overwrote the chosen skin on the first frame.
`docs/LESSONS.md` case 15 is the reason it got that far: **a log line is the
process's account of itself, and on a screen only pixels are evidence.**
`grim` on the device takes the capture, and Claude can read the PNG.

**Two more he found after that, and only one of them was new.**

- **The needles shook, and had been shaking since Phase 5.** The engine's
  pipe drain reports *zero level* when a poll finds no new frame, and 47 of
  117 reads in five seconds found none while music played — each zero going
  into a four-deep smoothing buffer. The drain now holds the last frame,
  which is what our own `FifoSource` has always done with the same pipes.
  Measured before and after, frame by frame; the pre-9h driver paces the
  same, so nothing this week caused it.
- **The picker's preview was cropped on a laptop.** A 16:10 box at the full
  width of the pane, with the picture `cover`ed into it: on a wide, short
  window `max-height` beat `aspect-ratio` and the skin lost its edges. The
  picture keeps its own shape now, at four viewports checked.

**What 9h landed before that:**

- **Three kinds of skin, not two** — 77 meters, 9 spectrum, 13 both, counted
  on the device. The old two options were *directories*, and `templates/` is
  not the meter corpus. The row is **Skins**: VU meters / Spectrum / VU
  meters + spectrum / Random.
- **[ADR-0050](docs/decisions/0050-skin-previews-are-the-skins-own-picture.md):
  a preview is the skin's own `screen.bgr`** — no render, no cache, no
  change detection, and **9h needs no image build**.
- **The home strip, all three shapes**, after George corrected a finding
  that said two of them were impossible (`docs/LESSONS.md` case 14). They
  are `browselibrary` **sorts**, not fields or tags, and need no plugin.
- **`viz_stop` wired**, and `viz_timeout` moved from seconds to the minutes
  the design draws. Both read per tick.
- **`idle_clock`**, so the panel can be a picture frame (2026-09-22).

**The device is carrying deployed files, not a built image.** The daemon,
the panel and **`driver.py`** were rsynced to it for this work. The driver
is the new one: `image/stage-gexis/05-peppy/files/gexis-peppy-driver.py` is
what a build would install, and until that build the device and the image
differ.

**9g — the idle screen — is done.** Both providers chosen the way Finding
030 chose the enrichment ones ([Finding 043](docs/findings/043-the-idle-screens-two-providers.md)):
**Pixabay** on the pictures, **Open-Meteo** on George's answer to the
question that decided it — *a Gexis is not sold*, so a non-commercial free
tier is one this appliance may use.
[ADR-0047](docs/decisions/0047-the-idle-screen-gains-backgrounds-and-weather.md)
is **Accepted** and has one open question left, which is George's: whether
artist pictures should avoid the artist currently playing.

**What the panel shows now:** a drifting clock and date over one of four
backgrounds, a forecast bar across the bottom in three icon sets, and the
credits both providers require on one line along the bottom. Artist
pictures come from **fanart** with LMS behind them (six for six on George's
library); wallpapers come from Pixabay, random across the chosen categories;
on-device pictures come from an SMB share; and a picture that `cover` would
cost more than a quarter of is shown whole over a blurred copy of itself.

**One of the two things a build still owes: [ADR-0049](docs/decisions/0049-the-pictures-folder-is-a-share.md)'s
image stage has never been through one** (the other is the new `driver.py`,
above). samba is installed and the
share verified on the device — a picture written to it over SMB was drawn
on the panel — and the stage that bakes it is written with `testparm`
assertions that pass against that device. **The next rebuild is what proves
the stage**, and it is the first thing on this image that is neither ours
nor a renderer.

**Nine things the panel found that no test would have**, which is the
argument for the gate:

- **The design draws this screen and the first build did not look for it** —
  it is in `source/Now Playing.dc.html`, not a file of its own, and
  `screens.md` says so in its first paragraph.
  **[LESSONS](docs/LESSONS.md) case 13**, one day after case 12 and the same
  shape: a summary read in place of the source. The screen was rebuilt to the
  drawing.
- **A flat 4px contour reads grey at 21px** — 62% of the ink against the
  clock's 35%, measured over a controlled field. It tapers with the type now.
- **`object-fit: cover` keeps 35% of a portrait's height**, which is where
  the blurred-halo fit came from. The halo costs nothing: 16.8 ms a frame
  with it and without.
- A fixed scrim cannot keep a moving clock legible, and a radial gradient
  still opaque at its box's edge draws a rectangle over the picture.
- **Artist pictures were asked for at 300 px and drawn at 1280** — Finding
  035's defect upside down.
- **The geocoder does not take what the row asks for**: `Berlin, DE` — the
  design's own example — returns nothing from Open-Meteo, where `Berlin`
  returns five. The daemon splits the string now and ranks the answers.
- **An unreachable geocoder was reported as a place that does not exist**,
  which sends the user to fix a row that was already right.
- **Rotation was hidden for every background but Pixabay**, though the
  behaviour was common — the worst kind of gap: the feature works and
  nothing offers it.
- **Pictures in folders were invisible**, and the path guard that assumed one
  segment had to become one that resolves and checks containment.

**Known and deliberate:** an empty on-device folder shows the clock on black
with no explanation *on the idle screen* — the region blanks, never the
screen — and the settings row is where it says why.

**Two measured traps recorded there:** the Art Institute's IIIF image server
403s without an `AIC-User-Agent` header (with a browser User-Agent too — the
JSON API answers fine without it, so it fails only when an image is
fetched), and NASA's APOD carries a `copyright` field naming a photographer
on most days, so it is not the public-domain source it is assumed to be.

- **9a** — the decisions: ADR-0044, 0045, 0046 Accepted, ADR-0022 amended
  for the catalogue/surfaced split, ADR-0047 opened for the idle screen.
- **9b** — Now Playing: one header instead of two, the album year from LMS
  first, the source mark de-pilled, and the synced lyrics fixed after the
  panel check.
- **9c** — the Library sweep: Add to queue, the artist route out of a New
  Music album, radio as a tinted grid, genre pills, the About error branch.
- **9d** — the settings vocabulary and the Settings screen, **appended on
  George's instruction** to cover Wi-Fi and LMS discovery: see below.

**The diff it is all built on is
[Finding 042](docs/findings/042-the-device-against-the-new-design.md)**, and
its §9 records the five panel-check findings and what each turned out to be.
Ground truth is the device: `npm run build` on `ui/` reproduced
`/opt/gexis-ui`'s bundle byte-identically, settings came from live
`/settings`, state from a real `/state` frame, and the design's inventory
from evaluating its own `INV` literal rather than its prose — which matters,
because the two disagree.

**9d is the one to read about before touching Settings.** ADR-0044 now
carries **seven** mechanics, not six: `grouped` was counted as a fixture of
the drop's demo and is a mechanic. `visible` is computed in the registry and
published per row — the panel filters and does nothing else. A `list` with
`kind: "server"` stores a value and every other list does not. 54 rows became
56; 36 are surfaced.

**Where a list's items come from is answered for two of three.**
`core/src/gexis_core/wifi.py` (NetworkManager through `nmcli`, daemon is
root so there is no polkit agent) and `discovery.py` (UDP broadcast on 3483,
protocol verified against the real server — `IPAD` comes back absent, so the
address is the datagram's source). Generic routes `GET`/`POST
/settings/{key}/items`. **Bluetooth's trusted devices are still 9f's** and
that row opens on its own empty state.

**Two traps in `nmcli` that fail quietly**, both now tested: `-t` output
escapes colons inside values, so `split(":")` cuts a network called `2:1` in
half; and a saved connection is not named after its network — this image's is
`preconfigured` — so SSIDs are matched through `802-11-wireless.ssid`.

**What 9d taught about the plan itself.** George found four things on the
panel that no subphase owned. Two were scheduled nowhere at all (Wi-Fi, LMS
discovery); `handoff_duration` and `reboot` were design keys owed to nobody;
and `grouped` was a mechanic nobody had counted. **The list of design keys
the registry lacks is now written out in the test by its owing subphase** —
nine to 9g, four to 9h — so the next omission fails a test rather than
waiting to be found on hardware.

- **9e** — one `device_name`, written to all four and applied at the next
  restart ([ADR-0048](docs/decisions/0048-how-the-device-name-reaches-four-services.md)).
  Gate run end to end: renamed to `SofaPi`, rebooted, all four advertised
  it; renamed back, rebooted, all four followed.

**9e's gate found two defects no amount of reading would have**, and that is
the argument for having it:

- **BlueZ never read `main.conf`'s `Name =`.** Its `hostname` plugin
  overrides it — the vendor file says so two lines above the setting — and
  this image had been setting it since Phase 2. The build asserted its own
  `sed` had matched, which passed every time and meant nothing, because the
  hostname was the same string. `/etc/machine-info`'s `PRETTY_HOSTNAME` is
  the real mechanism. **[LESSONS](docs/LESSONS.md) case 9.**
- **A rename locked the panel out of its own browser.** Chromium's profile
  lock is `<hostname>-<pid>` and it refuses to start when that hostname is
  not the machine's — a two-button dialog on an appliance with no keyboard.
  `gexis-kiosk-start` clears the three Singleton entries before launching.

**And one in the deploy, worth knowing before the next one.** `rsync -a` put
the repository's `644` over the `755` the image installs, so Chromium never
started while `systemctl is-active gexis-kiosk` still said `active` — the
unit is labwc, and labwc was fine. **After any kiosk restart, check
`journalctl -u gexis-core | grep 'GET /assets/index-'`**, which cannot be
true unless Chromium started, loaded and reached the daemon, and names the
build on screen. The eight scripts installed `755` are executable in git
now. **[LESSONS](docs/LESSONS.md) case 10.**

**9f — Bluetooth pairing ([ADR-0045](docs/decisions/0045-bluetooth-pairing-confirmation.md))
— is built and on the device.** Our own `Agent1` replaced `bt-agent
--capability=NoInputNoOutput`, the request reaches the panel, accept and
reject work, and the countdown is the agent's rather than the panel's.
`bt_discoverable` is implemented for real, all three options, with
`DiscoverableTimeout=0` for Always — the "3 minutes" defect. `bt_trusted`
has its item list and `Forget`, which 9d left to it: it was the one `list`
with no source. Devices come from BlueZ's object tree, **paired only** (the
tree also carries everything the adapter has merely seen while
discoverable), and Forget is `Adapter1.RemoveDevice`, not `Trusted = false`
— clearing the flag leaves the bond and the phone reconnects.

**Checked on the panel, 2026-09-21** (George: *"Works fine"*): his Pixel is
paired and trusted, Settings › Sources › Trusted devices lists it with a
Forget, and the sheet opens instantly. **The reject and expiry paths have
not been driven since the freeze was fixed** — accept has, by the pair that
is on the device. Forgetting the phone from both ends is what sets up
driving them.

**Two panel defects found after that code was written, both fixed.** The
pairing frame froze — countdown still, Reject doing nothing — while every
server-side check passed, because an `$effect` read what it wrote and Svelte
stopped updating the whole tree ([LESSONS](docs/LESSONS.md) case 11); and a
failed answer left both buttons disabled, a `try/catch` with no `finally`.

**And the `bt_trusted` row read "None" with a phone paired** (George, on the
panel, 2026-09-21): the row's value is a count, the panel counted `row.items`
as the design does, and the design carries its items inline where ours were
fetched when the sheet opens — so the row could only ever read the empty
answer. **The row and the sheet are two surfaces, and the sheet working says
nothing about the row.**

**[ADR-0044](docs/decisions/0044-settings-row-vocabulary.md) §1 is amended
for what that turned out to be about: when a `list`'s items arrive.** George,
seeing the sheet still flash as it opened: *"Isn't the list static? It should
be instant."* It was not static — the sheet refetched on every open and began
in its searching state whatever the answer cost. Measured on the panel frame
by frame: **spinner from 27 ms to 36 ms, devices at 56 ms**, over a BlueZ read
of 22–29 ms. So:

- **`discover: true`** — LMS discovery (2.5 s) and a Wi-Fi scan (seconds) go
  looking when the sheet opens and say so while they look. `wifi` carries the
  flag now; it always searched and only the server row said so.
- **no `discover`** — `bt_trusted`'s items are one `GetManagedObjects`, so
  they arrive **with the row** in `/settings` and the sheet opens drawn, the
  refresh running behind it. The same read gives the row its count.

Re-measured after the change: **the searching block never enters the DOM at
all** (a MutationObserver over the whole body for 600 ms), and the Wi-Fi sheet
still shows its own, with its own words. The three kinds are `server`,
`network` and `device` now — the two-way branch had `device` falling through
to Wi-Fi's side of it, so the Bluetooth sheet said it was *"looking for
networks"* and *"sweeping every channel"*.

**Design Claude is owed the `device_name` restart warning text.** The note
shipped in 9e says the true thing plainly as a placeholder.

**Two settings rows still report behaviour the code does not have**, each
found by measuring rather than reading: `travel_curve` names a curve 34 dB
quieter at mid-travel than ADR-0034's slider, and `max_ceiling` is `None`,
so no ceiling is enforced. The third was `bt_discoverable`, which reported
"3 min after boot" that nothing chose (BlueZ's 180 s default reverting an
untimed `discoverable on`) — **9f implemented it**, and Always now sets
`DiscoverableTimeout=0`.

**`device_name` is refused** — `HTTP 409 "not wired yet"`. The four service
names agree only because each was set to the same literal at build time.
Nothing propagates. That is 9e.

**Finding 042 §8 says what it did not cover, and George closed the gap-hunt
on cost.** Now Playing and Settings were compared element by element; Library,
WaitingServices, Handoff and Idle were sampled, and sampling missed real
items — George named six in one breath. Two are confirmed in the finding;
three are unchecked and are expected to surface during 9c, where he judges
them on the panel. **The unused instrument:** the drop ships `verify.html`
(38 checks) and `geometry.json` (landmarks at 1280×800, 3 px tolerance) —
Now Playing only, cheap to run, not yet run.

**The boot-screen work from earlier in this session is done and paused.** The
still is on the device, the handover is 10 ms, two of three flashes are
accounted for and one is unexplained; a red-`swaybg` diagnostic is prepared
and not run. [Finding 041](docs/findings/041-the-ten-seconds-with-no-animation.md) §§8–10.

**Three build-side hazards found by the survey, none fixed:**
`49b79c6` changed `systemctl enable gexis-splash-backstop.service` → `.timer`
without a `disable` or an `rm`, and `01-run.sh` still installs the service
unit, so a warm build can keep the old symlink and quit the splash at
`multi-user.target`; `01-firstboot/files/firstrun.sh:67`'s
`sed -i 's| systemd.run.*||g'` is greedy and would strip **every** quieting
option and `splash` itself — inert today only because it targets a placeholder
path, so the obvious-looking fix is the one change that silently kills the
animation; and `02-run-chroot.sh` asserts nothing about the systemd wiring it
creates.

**ADR-0041 — scrims dim but do not blur** is the substantial result of step 1.
`backdrop-filter` costs 24.5 ms a frame in draw-and-submit against a 16.7 ms
budget with the CPU idle; the compositor reads the live screen back every
frame, which is a tile-based GPU's worst case
([Finding 037](docs/findings/037-why-a-blurred-scrim-costs-the-panel.md)). Not
the radius, not the area, and Vulkan is worse. **It does not reach the target
on its own:** the rail goes from ~15 fps to ~36 against a 55 fps floor.

**The build now caches its downloads** ([ADR-0042](docs/decisions/0042-a-local-cache-for-vendored-downloads.md)):
six artefacts, ~308 MB, content-addressed in `~/.cache/gexis-player/downloads`,
proven on the second build — zero bytes fetched. **It is explicitly not a
backup**: it protects this machine, not a fresh clone. A mirror we control is
deferred and is the only thing that answers George's actual question.

**Two pieces of Phase 9 groundwork are done and unused**, both off-device and
both waiting for the sweep:

- **The unwired-UI audit** (criterion 2). All 66 interactive elements traced.
  One real dead control, fixed then; **the latent trap it named was real and
  is now closed** — `confirmSheet()` had no path for a wired `action` row and
  `lib/settings.js` never sent `POST`, so the first action ever wired would
  have had a silently dead button. `reboot` was that first action, in 9d,
  and `runSetting` is the missing call. The audit predicted this exactly.
- **The settings wiring map** (criterion 1). Of 48 unwired rows: 14 are a read
  away, 19 need a branch, 4 need the feature built, 11 need a route or a
  sub-screen. `viz_timeout` is read by the daemon but missing from `wired`, so
  the phone cannot change a setting something actually consults.









**Phase 7a — panel responsiveness — is closed** (2026-09-18). Artwork at the
size drawn, an instrument that survives its own scrutiny, and a baseline:
[Finding 034](docs/findings/034-what-the-panel-presents.md). **The target is
three things** (George): under 2 % of frames dropped, no interaction below
55 fps, and his own go-ahead. Everything failed it when measured, which is
the point of having it. **The open question, now Phase 9 criterion 0: why is
a playing panel never idle?** 71 % of wanted frames dropped with nobody
touching it; PeppyMeter is already eliminated.

**Read Finding 034's six instrument faults before measuring anything here.**
Each produced a confident, plausible number: partial frames counted as
dropped (17.9 % on an untouched panel), fixed coordinates that scrolled
nothing (25-31 %), playback uncontrolled (57.7 % where the same control had
said 0.00 %), every frame counted twice (102 fps on a 60 Hz panel), a rail
measured with nothing below the current track to scroll, and thin runs
averaged in.

**Next: Phase 8 - enrichment and lyrics.** It needs an ADR choosing the
providers before any code;
[Finding 030](docs/findings/030-free-enrichment-providers.md) compares the
free ones and recommends a key-free combination without deciding it.

**Phase 7 — library browse — is merged (PR #19, 2026-09-18).** Every step
was built and checked by George on the panel; the last, the queue rail, on
2026-09-18. [ADR-0038](docs/decisions/0038-library-and-radio-on-the-panel.md)
is **Accepted**, `docs/DEVELOPMENT.md` Phase 7 records what each step
settled, and the step-by-step narrative is in
[the archive](docs/HANDOFF-ARCHIVE.md). What the panel has now: Home as the
library root with New Music, the album page, the artist grid and artist
page, three-pane Browse with row actions, playlists, radio, and the queue
rail with Clear and a playlist chooser. Play means in order; Shuffle all is
its own button.

**Open, deferred by George: one investigation into what makes the panel
slow.** It started as the lists (the New Music strip scrolls unevenly, the
artist grid is slow to load, open and scroll - 917 artists in one pass) and
George widened it after step 10: *with the rail built, everything is "quite
slow"*. [Finding 032](docs/findings/032-panel-frame-times-during-a-scroll.md)
says what is and is not established, and warns that the instruments lie
before they help. **One candidate is already named rather than guessed:**
the queue rail asks LMS for 500 px covers and draws them at 42 px
(`ARTWORK_SIZE` in `adapters/lms.py` serves both now playing's well and
every queue row), where the library reads already ask for the size drawn.
Candidates for the lists: rendering only what is on screen, lighter cards,
letter buckets from the core. `content-visibility: auto` was tried on the
artist grid and removed - off-screen groups are only estimated, so the jump
rail landed inside the previous letter.

**Two defects from the step 10 check are worth carrying forward as
patterns**, both fixed with a test that fails without the fix:

- **A queue that could never grow.** It was read only by the *seed* status
  query at subscribe time, and every later change arrives as a CometD push.
  All three tests over it passed, because each called the reader itself and
  none drove the push loop. *A test that exercises a function is not a test
  that anything calls it* (`docs/LESSONS.md`).
- **A Peppy screen that could not be dismissed by touch.** Whether it is up
  was known only in memory, so a daemon started *while it is on screen*
  believed it was hidden and ignored every touch, stranding the panel behind
  the meter. Any state held about something outside the process has to be
  reconciled at startup, not assumed.

**Test data on George's LMS:** playlist folder `/playlist` (George set it;
it triggered a full rescan that renumbered the library). Playlists
`gexis-test-album` (122541), `gexis-test-mixed` (122543),
`gexis-test-empty` (122544) — George removes them. Finding 029's raw replies
are at `~/gexis-findings/029-raw/` on R2D2, deliberately not in the repo
(library listing, playlist names, a TuneIn serial).

**Probing SlimBrowse can start playback.** A radio walk that followed
`base.actions.go` played a station for 45 s (Finding 029). Resolve the
command and refuse anything ending in `play` or `add` before sending.

**Corrected in this session, worth not repeating:** Claude raised "playing
from the library must power LMS on" as an open decision. It was not: LMS's
auto-power-on on play is recorded in ADR-0027 (hardware, 2026-09-12) and
Finding 019. The repo was not searched first — `docs/LESSONS.md` case 4's
corollary.

**Measured 2026-09-17 against George's LMS (read-only), now in ADR-0038:**
the `radios menu:radio` reply has no `id` on any item, so Podcasts is
excluded by its `["podcast","items"]` command; `cover_300x300` is a 173 KB
PNG where `cover_300x300_o.jpg` is a 25 KB JPEG (one album);
`ignoredarticles` is "The El La Los Las Le Les".

**Phase 8 research is recorded, ahead of time:**
[Finding 030](docs/findings/030-free-enrichment-providers.md) compares free
enrichment providers (George asked 2026-09-17). Nothing decided; the provider
choice needs an ADR when Phase 8 starts. George: API keys are a per-user
setting, so a key is not a blocker (ADR-0022 inventory row added).

**The Phase 8 image is built and verified as a file, not flashed:**
`image/deploy/2026-09-18-gexis-player-v0.2.1-272-g10fbb44-dirty.img`
(478 s, first attempt; `image/verify-image.sh` - all checks passed). **It
did not test the loop-device fix:** R2D2 had not rebooted, so the nodes
were still the ones `modprobe` made by hand (Finding 033). That test is
still a reboot followed by a build.

**The Phase 7 image:**
`image/deploy/2026-09-18-gexis-player-v0.2.1-232-g65d62e3-dirty.img`
(464 s; `image/verify-image.sh` - all checks passed, including the venv and
`/opt/gexis-ui` byte-identical to this checkout). **The device still runs the
Phase 6 image** (`2026-09-17-gexis-player-v0.2.1-202-gf3674f3-dirty.img`)
with Phase 7 hand-installed, so a reflash is what proves the image.

**The device** was flashed and provisioned 2026-09-17. Both SSH keys authorized. **After every reflash**
append C3PO's key (`provision.local.env` carries R2D2's only; George chose
not to change `provision.sh`):
`ssh pi@gexis.local 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/c3po_id_ed25519.pub`,
then `ssh-keygen -lf ~/.ssh/authorized_keys` on the device shows R2D2
`SHA256:UVfvJQXw…ci4` and C3PO `SHA256:d/pT3AST…tok`.

**Phase 6 is merged** (PR #18, 2026-09-17). George called the image checks
done without item-by-item results, so none is recorded as observed
(`docs/DEVELOPMENT.md` Phase 6 status).

**The loop-device question is answered
([Finding 033](docs/findings/033-loop-device-before-a-build.md)).** The test
HANDOFF set up was run on 2026-09-18: the state before the build was the
module autoloaded (`loop 45056 0`) and **no `/dev/loopN`**, and the build
failed at `export-image/prerun.sh` with the same
`mknod: invalid minor device number '/dev/loop0 (lost)'` as ever, in 210 s.
So **the module being loaded is not what decides it - the missing device
node is**, and `image/README.md`'s recorded root cause was wrong (now
corrected there). The failed build leaves a `/dev/loop0` behind, which is
why every rerun passes. **No durable fix is chosen: it needs George, and
`sudo`.** Candidates, none tried: create a node before the build; load the
module with `max_loop=8` so udev makes `/dev/loop0-7` at boot; or put the
reload in the build script rather than in someone's memory. Until then the
first build after a reboot fails and the second passes.

**Docker group:** after the reboot `id` shows `docker` (950) directly;
`newgrp` is no longer needed. Run builds detached so the session's memory
guard cannot kill them:
`nohup setsid bash -c "make image > ~/gexis-build.log 2>&1; echo BUILD-EXIT=\$? >> ~/gexis-build.log" >/dev/null 2>&1 </dev/null &`.
Move the previous log aside first. The submodule shows `m image/pi-gen`
afterwards: expected, leave it.

**Development moved to R2D2 on 2026-09-17** (see Machines).
`~/provision.local.env.bak-c3po-key` (holds the Wi-Fi password) can be
deleted once George is happy.

**Phases renumbered 2026-09-16:** 9 is settings wiring and UI polish (new);
10 is the plugin contract; 11 Plexamp and 12 Qobuz Connect (new); 13 is first
boot.

**Issues to look at later (Phase 6 hardware rounds, 2026-09-16):**

- **Over Bluetooth, the Plexamp app reports pauses late or not at all** — about
  6 s from its own button, 4.5 s or never for a panel command. The Spotify app
  on the same phone reports in 0.2 s (Finding 028, addendum 2). A2DP's
  stream-idle signal comes 3 s after the report, so it cannot help. With
  Plexamp the panel's icon falls back after 8 s. Next step, with the speakers
  on: does Plexamp's audio stop at the tap?
- **LMS had player `gexis` on fixed volume (`digitalVolumeControl` 0), cause
  unknown.** George found it as "phone volume does nothing while the panel is
  muted, and LMS's volume bar is frozen". Measured 2026-09-16: with 0, LMS
  moves its own number but always sends full level, so no LMS volume change
  reaches the device, muted or not. Mute then became a trap, because the one
  change that ends it never arrived. Set back to 1 with George's OK; re-tested
  while playing: LMS volume reaches the DAC again, and a change while muted
  ends mute (ADR-0034). **George never touched it,** and nothing in this repo
  sets it; it worked on 2026-09-08 (Finding 008). **Checked after the 2026-09-17 reflash: 1.**
  Still unchecked after an LMS restart. Nothing warns when it is 0; a candidate for
  Phase 9.
- **Pausing LMS moved the DAC slightly** (dummy −47 → −50 dB, DAC 152 → 150)
  during the same test. Small, unexplained, not investigated.
- **After a `gexis-core` restart, a phone already connected is not active.**
  The Bluetooth adapter seeds metadata from a `MediaPlayer1` that is already
  present but never calls `on_acquire`. It only matters when the daemon
  restarts, not at boot. **Both halves are fixed** (2026-09-18):
  George saw the library's "waiting for a service" block over a playing
  Spotify track, because go-librespot announces acquisition with events and
  events are edges - nothing is emitted for a stream that was already
  running. The adapter now reads `/status` when it connects and acquires if
  something is playing, the same shape as the LMS adapter's "player already
  powered on at startup". Measured before the fix: 66 s from connect to the
  next `will_play`. **Bluetooth is the same shape and fixed the same way:**
  acquisition there is driven by `InterfacesAdded`, and a `MediaPlayer1`
  that was already present produces no such signal, so the startup scan now
  acquires when its `Status` is playing. Neither adapter acquires for a
  *paused* session: one left paused before the daemon started cannot be told
  from one somebody abandoned, and claiming it would take the device from
  whoever has it.
- **LMS once reported a position about 5 s ahead on resume**, then corrected
  it at the next pause. Not reproduced on a second try; recheck with sound.

**Follow-ups, not blocking:**

- `viz_timeout` is read by the daemon but not wired in the settings registry,
  so the phone cannot change it (ADR-0035 says wire it with its feature).
- The stock skins are Volumio-branded; Gelo5's are the image default.
- Titles too long for their box are cut with "…"; the wrapper scrolls them.
- Fonts: DejaVu for text; DSEG7 (OFL) for time. PeppyFont not vendored.
- George once saw the spectrum overlap remaining time on `dash-spectrum`;
  not reproduced in 24 rotations or a direct start.
- **Lesson candidate:** hand-started test processes multiplied because pid
  files captured the wrong pid; George saw overlapping skins. Stop by looking
  processes up, not by trusting a pid file.

**Still open from earlier:** Claude Design owes drawn number/text editors and a
corrected `design/README.md`.

## Build environment (2026-09-13) — read this before the next build

No Phase 4 work happened this session. What changed is the build host, and it
matters because **Claude runs every build** (George, 2026-09-13), which makes
one failure mode routine rather than incidental.

**1. Docker's `data-root` moved to `/home/docker`.** It was `/var/lib/docker`,
on `/` — 62G with 9.1G free — while `image/deploy/` is in the repo on `/home`
(396G). The low-disk warnings were always about `/`; deleting zips from
`image/deploy/` frees the partition that *wasn't* full. Moved with
`rsync -aHAX --numeric-ids` (overlay2 needs hardlinks, xattrs and numeric
ids); `/` went 9.1G → 26G free. The old tree is gone. Roll back by removing
`/etc/docker/daemon.json` if this ever needs undoing.

**2. `make prune` (new), run automatically by `make image`.** Two things
accumulated in the preserved volumes, neither a cache: `work/*/export-image/`
leaked one raw ~4.5GB image *per build* (pi-gen's `prerun.sh` deletes only
`${IMG_FILENAME}${IMG_SUFFIX}.img`, and our `IMG_SUFFIX` is the git-describe
version, different every build — the leak is ours, not pi-gen's), and
`deploy/` kept every build's output, which `build-docker.sh` re-streams to the
host each run. First run reclaimed **10,194 MB**; volumes 18.89GB → 8.20GB.

**This is what to reach for instead of `make clean`.** `clean` does
`docker rm -v pigen_work`, which destroys the volumes *including* the ~8.4GB
of stage rootfs trees that make a build warm. "Clear the disk warning" and
"lose the warm build" were the same command. `clean` still exists, for forcing
a genuinely cold build.

**3. `DEPLOY_COMPRESSION=none`** — `image/deploy/` now holds a raw
`<date>-gexis-player-<version>.img`, no `image_` prefix, no zip. Settled the
open call `image/README.md` had carried since 2026-09-05, and the deciding
reason is the division of labour: **Claude builds, George flashes** (George,
2026-09-13), and a raw `.img` goes straight into Raspberry Pi Imager. Costs
4.5GB against 1.28GB zipped; `mtools` inspection and `bmaptool` support come
along with it. **Do not re-propose compression to make the copy-out cheaper**
— that optimises the build host at the cost of the one manual step in the
loop. `make prune` and `make fetch-deploy` handle both halves of the cost.

**4. `make fetch-deploy` (new) — expect to need it.** `build-docker.sh:154`
ends every build with `docker cp …/deploy - | tar -xf -`, streaming the whole
directory through a pipe. Under host memory pressure **that** is the step that
dies, with the build itself already complete. Observed twice on 2026-09-13,
both times leaving a valid image in the volume.

Two traps here, both of which cost time this session:

- **There is no kernel OOM record.** The kill comes from the process
  supervising the build, so `journalctl | grep oom-kill` finds nothing and
  proves nothing. A correct diagnosis was retracted on exactly that
  non-evidence before the failure was reproduced live.
- **A fallback inside `make image` cannot work.** The signal reaches make
  (`make: *** [Makefile:127: image] Terminated`), so no recipe is left
  running. Recovery must be a separate invocation — hence the target.

`make fetch-deploy` copies per-file (no tar pipe; 44s for 4.5GB), skips
anything already present at the right size, and appends the manifest
annotation `image` would have. Verified: recovered image byte-identical,
manifest reporting the true 749s.

**Current warm-build baseline: 12m29s** (cold ~40m), 2026-09-13, with prune
and no compression. Latest artefact:
`image/deploy/2026-09-13-gexis-player-v0.2.1-98-gfec5067-dirty.img` —
**built and verified as a file, not yet flashed.** `04-ui` (labwc, the
`PAMName=login` seat, 1280x800, the Chromium flags) is still written entirely
from documentation and has never been run on hardware.

Commits: `3c13bd1` (prune), `987e84f` (raw .img), plus the `fetch-deploy`
commit, on `phase-3-core-daemon`.

## Machines

| Name | What it is | Notes |
|---|---|---|
| `R2D2` | **dev machine from 2026-09-17** | CachyOS, 12 cores, 31 GB RAM, **fish shell**. `192.168.178.134`. Replaced C3PO because builds kept being killed for low memory. Set up per `image/README.md`'s host prerequisites: Docker with `data-root` `/home/docker`, qemu-user-static-binfmt, `~/.local/bin/qemu-aarch64`, loop autoloaded via `/etc/modules-load.d/loop.conf`. Repo at `~/projects/gexis-player`, both `*.local.env` files and Claude's project memory copied from C3PO, its key authorized on `gexis`. UI builds, 444 core tests pass. |
| `C3PO` | former dev machine | CachyOS, 8 cores, 14 GB, **fish shell** — no heredocs. Hand it script files to run with `bash`, not pasted multi-line commands. Retired for builds 2026-09-17 (out of memory). |
| `rig` | Raspberry Pi 4, 4 GB | Raspberry Pi OS Lite 64-bit, Trixie. **Reference machine** — holds the environment Findings 002-004 were measured against. Not the build/test target. |
| `gexis` | Raspberry Pi 4 | Flashed from this project's own `make image` output. User `pi`. Reachable as `pi@gexis.local` by SSH key. **The image-built target** — Phase 2 onward is built and measured here. |
| SD card 2 | moOde | Reference install. Read-only recon source. Do not modify. |
| LMS server | `192.168.178.188` | For manual testing (arbitration base slot, etc). **CI gets a containerised throwaway instead — CI must not depend on this server being up.** |

**Provisioning a freshly flashed card:** `make provision DEVICE=/dev/sdX`
fills in `firstrun.sh`'s SSH key / Wi-Fi / hostname from
`image/provision.local.env` (gitignored, copy `image/provision.env.example`
to create it) and clears the card's stale SSH host key. See
`image/README.md`.

**Builds are versioned, starting 2026-09-07** (George: "can we start
giving release numbers to the builds"). `git describe --tags --always
--dirty` at build time, appended to the `.info` manifest as "Image
version: vX.Y.Z" — same place peppyalsa's commit and go-librespot's
version already live, not a new mechanism. First tag: `v0.1.0`
(annotated, on `phase-2b-arbitration`). No bump convention decided yet
(when to cut `v0.2.0` vs. just moving the tag) — tag manually before a
build worth naming, for now.

**Filenames carry the version too, starting 2026-09-11** (George asked).
The `.info`-only note above is now out of date on this point - the
plumbing concern it named (threading the version through pi-gen's own
two-pass `image/config` sourcing, which would need git access *inside*
the container that isn't there) turned out to have a simpler answer:
pi-gen already exposes `IMG_SUFFIX`, appended to every export-image
filename with no default of its own unless a stage sets one (none of
ours do), so the `Makefile`'s `image:` target now passes
`-e IMG_SUFFIX=-$(IMAGE_VERSION)` via `PIGEN_DOCKER_OPTS` - no
`image/config` change, no submodule edit. Confirmed the env var reaches
the container intact via a standalone `docker run -e` test (a plain host
environment variable does not cross that boundary on its own - `docker
run` only forwards what's explicitly passed) and confirmed the resulting
filename shape by simulating `build.sh`'s own variable-resolution lines
directly. The `image:` target's own manifest-lookup glob was widened
(`*-gexis-player.info` → `*-gexis-player*.info`) to still find the
now-longer filename - the exact class of thing that broke silently once
already (the multi-manifest annotation bug, Phase 2c's prerequisites) -
check this first if a future build's manifest looks unannotated again.

**First real `make image` run found it didn't work at all - the
filenames came out exactly as before, no version suffix.** Root cause:
`image/stage-gexis/EXPORT_IMAGE` (this project's own file, not the pinned
submodule - the mechanism that triggers pi-gen's export-image stage at
all, adapted from upstream's stage4/5 convention) unconditionally set
`IMG_SUFFIX=""` at its own top, sourced by `build.sh` right before the
export stage runs - silently clobbering whatever the Makefile had passed
in via the container's environment, every single build, before this was
noticed. The annotated `.info` manifest's own version line still worked
(a separate, host-side mechanism, unaffected) - only the filenames
themselves were wrong. Missed originally because the isolated
verification checked the env-var-passing mechanism and simulated
`build.sh`'s own variable-resolution lines directly, but never checked
whether anything sourced *after* those lines could still overwrite the
result - `EXPORT_IMAGE` files are exactly that, and this project's own
copy of the pattern wasn't audited. Fixed (`IMG_SUFFIX="${IMG_SUFFIX:-}"`,
preserves rather than clobbers), confirmed by the same isolated-simulation
method as before (sourcing the actual fixed file with `IMG_SUFFIX`
pre-set, exactly as the container would have it). **A second `make
image` run is what actually proves this** - the one that produced today's
reverted, currently-flashed image predates this fix.

## Phase order

```
0  reproducible image                     * merged - pi-gen, ADR-0021
1  measurements                           absorbed into 2 - needs 2's own renderers
2  audio layer + arbitration              * merged
3  core state daemon                      * merged
4  UI shell + idle + display-only nowplay * merged
5  visualisation service + Peppy screen   * merged
6  now playing, full                      * merged (PR #18)
7  library browse                         * merged (PR #19) - typed queries +
                                            our screens; SlimBrowse for radio
7a panel responsiveness                   * done - artwork at the size drawn,
                                            an instrument that survives its
                                            own scrutiny, and a baseline
                                            (Finding 034). Reaching the target
                                            is Phase 9 criterion 0
8  enrichment + lyrics                    <- next. Additive only, cannot break
                                            playback.
                                            Needs an ADR choosing the providers
                                            first (Finding 030)
9  settings wiring + UI polish            <- next. Every ADR-0022 row wired or
                                            scoped out; criterion 0 is the
                                            panel reaching Phase 7a's target
10 plugin contract + themes               Qobuz is the fourth-renderer test;
                                            a Beszel agent is the test that
                                            the contract carries a non-renderer
                                            (George, 2026-09-18)
11 Plexamp as a renderer                  starts with the hardware check: does it
                                            release the device? (ADR-0008's
                                            reversal condition)
12 Qobuz Connect as a renderer            the plugin that proves 10
13 first boot without a network           setup access point; pull forward the
                                            moment a non-developer gets a device
                                            (ADR-0031)
```

Phases 9-13 were renumbered on 2026-09-16 (George). `docs/DEVELOPMENT.md`
holds each phase's acceptance criteria; this list is only the order.

## Things that will bite if forgotten

- **A reflashed card only has R2D2's SSH key.** `make provision` writes the
  one key in `image/provision.local.env`; C3PO's
  (`~/.ssh/c3po_id_ed25519.pub`) is appended by hand after first boot
  (George, 2026-09-17). Both keys are commented `desktop-to-dietpi`; compare
  fingerprints, not comments.

- **Never `docker start pigen_work`.** It re-runs pi-gen's entrypoint and
  starts a build — done accidentally on 2026-09-13 while inspecting the
  volumes, killed ~90s into stage0 (no damage: `lists/partial` and
  `dpkg/updates` were empty, `dpkg/status` untouched). To read the volumes,
  use a throwaway container, which is what `make prune` does:
  `docker run --rm --volumes-from pigen_work pi-gen:latest sh -c '…'`.
  Note the real build never starts `pigen_work` either — when it exists,
  `build-docker.sh` runs `pigen_work_cont` with `--rm --volumes-from`, so
  `pigen_work` is only a volume holder and its exit status is irrelevant.
- **`work/*/build.log` accumulates across `CONTINUE=1` runs.** Its first
  timestamp is not this build's start. Anything deriving a duration from it
  must take the *last* `Begin /pi-gen/stage0` to the *last* `Build finished`
  — a first cut of `fetch-deploy`'s annotation reported 4186s for a 749s
  build by spanning two runs.
- **An interrupted `docker cp … | tar -xf -` rewrites `deploy/`
  alphabetically** and can truncate a *previous* build's artefact, not just
  the current one. Cost a good image on 2026-09-12 (583MB of a real 1.05GB).
  `make prune` shrinks the blast radius by keeping only the current build in
  the volume; it does not remove it. Check sizes before trusting a
  `deploy/` file that a killed build touched.
- **Never reference an ALSA card by index.** 3 on `rig`, 2 on moOde, 1 on
  `gexis` — same DAC model, three different indices (Finding 005). Use
  `hw:sndrpihifiberry`.
- **`ctl.output`, not just `pcm.output`, in `output.conf`.** Mixer access
  (`squeezelite -V DAC`) resolves through the control interface, not the
  PCM slave chain — ADR-0009 was itself incomplete on this until Phase 2a.
- **`squeezelite -V <control>` does not fail on a bad mixer name** —
  confirmed from its source. It logs and silently falls back to software
  volume. `squeezelite.service`'s `ExecStartPre` is the actual assertion.
  As of 2026-09-08 (B2) the target is `hw:gexislmsvol`'s `Master`, a
  private `snd-dummy` control, not the real `DAC` — same risk, different
  target; the check was updated to match, don't let it drift back.
- **`alsactl monitor <card>` needs the `hw:` prefix** — `alsactl monitor
  gexislmsvol` fails with `Invalid CTL`, `alsactl monitor
  hw:gexislmsvol` works. Not documented in `alsactl(1)`'s own SYNOPSIS.
  Found 2026-09-08 wiring up `DummyMixerBridge`.
- **`amixer sget`'s value line format differs by control** — a control
  with distinct playback/capture volumes prints `Front Left: Playback
  216 [...]`; one without (e.g. a `snd-dummy` card's `Master`) prints
  `Front Left: 30 [...]` — no "Playback" word. `volume.py`'s `get_raw()`
  parses both now; a regex written against only the real DAC's format
  will silently return `None` for a dummy control.
- **gexis-player is GPL v3 (ADR-0025, 2026-09-08).** Every file we
  author under `core/src/gexis_core/` carries `# SPDX-License-Identifier:
  GPL-3.0-or-later` as its first line — see `docs/DEVELOPMENT.md`'s
  "Licence" section. Don't add it to a vendored third-party file.
- **A `.gitignore` fix on one branch does not protect other branches**
  working off the same tree. Run `./test-gitignored-credentials.sh` on
  whatever branch you're on if you're not sure.
- **`type plug` must not appear in the `output` chain.**
- **`alsa-lib` is pinned at `1.2.14-1+rpt1+deb13u1`** (moved from
  `1.2.14-1+rpt1`, 2026-09-12, George's decision — see ADR-0021's amended
  pin bullet). Findings 002/003 measured the older version; they are left
  as the measurements they were, not rewritten. **The failure mode to
  recognise:** a pinned version can vanish from the archive index and
  then `make image` fails outright at `stage-gexis/00-alsa` with
  `E: Version '...' for 'libasound2t64' was not found`. That is the pin
  working as intended (a hard stop, not silent drift) — check
  `archive.raspberrypi.com/debian`'s own `binary-arm64` `Packages` index
  for what is actually available before touching anything, rather than
  trusting apt's "however the following packages replace it" list, which
  names armhf and `-data` packages and reads like a restructure when it
  is only a point release. ADR-0021's deferred Q3 (snapshot-pinning the
  archive) is the standing fix and is still deferred.
- **`docs/DEVELOPMENT.md` on `main` is stale** — see above.
- **Adding a user to the `docker` group needs a new login session**, not
  just relaunching Claude Code — a shell spawned before the change keeps
  its old group list until it's re-created (new terminal / re-login).
  Check with `id` before assuming `docker` commands will work.
- **A failed `make image` leaves `pigen_work` behind even after
  `make clean`** if `clean` ran before the failing attempt rather than
  after it — `clean`'s `docker rm -v pigen_work` only removes what
  exists *at the time it runs*. Run `make clean` again after any failure,
  right before retrying.
- **An interrupted `make image` can leave a *previous* image truncated in
  `image/deploy/`, looking exactly like a valid one.** Found 2026-09-13.
  The build itself finished (15m18s, warm) and was killed by `C3PO`'s own
  low-memory condition during the final `docker cp ... | tar -xf -` that
  copies results out. That copy rewrites everything in `deploy/`
  alphabetically, so it had already overwritten the previous day's `.zip`
  and got part-way: 583 MB where the real file was 1.05 GB. Nothing says
  so — the filename and timestamp look normal, and flashing it would fail
  in some interesting way much later.
  **Recovery needs no rebuild.** `PRESERVE_CONTAINER=1` means the finished
  artefacts are still in the container: `docker cp
  pigen_work:/pi-gen/deploy/. <somewhere>` retrieves them from a *stopped*
  container (`docker exec` will not work on one). Check the recovered
  sizes against `unzip -t` before trusting either file.
- **Two images in `deploy/` is ~2.3 GB and the disk is 62 GB.** With the
  pi-gen container and its volumes also resident, 85% used is a normal
  post-build state. `make clean` reclaims the container's share; the
  images themselves are only removed by hand.
- **Don't assume `C3PO`'s tooling is on the image.** `xxd`, `bc`,
  `telnet`, `nc` aren't there (Lite base doesn't have them) — `od`,
  `curl`, `ss`, `fuser` are. Reach LMS's CLI (port 9090) via bash's
  `/dev/tcp` instead of `telnet`/`nc`. More broadly, never paste command
  blocks across machines without checking which host a shell is actually
  attached to first (see the method note above).
- **`systemctl is-active` does not mean "working."** squeezelite reported
  active while go-librespot held the ALSA device out from under it,
  retrying every 5s with no way to see that from unit status alone —
  found on hardware, 2026-09-06. Check the actual symptom (audio, or in
  this case `fuser` on the PCM node), not just unit state.
- **A commanded pause does not make squeezelite release faster than its
  `-C` idle timeout** — measured ~8.5s from an LMS CLI pause to the ALSA
  device actually freeing, 2026-09-06. Arbitration cannot get a fast
  release out of squeezelite through LMS's own pause command; see the
  hardware session above for what this means for criterion 4.
- **go-librespot's `server.port` and `zeroconf_port` are ephemeral if
  left unset** — measured differing across a single `systemctl restart`.
  `server.port` is now pinned (`config.yml`); `zeroconf_port` is left
  random on purpose, since nothing on this device needs to address it by
  a fixed port and it must stay reachable from off-device (the phone
  app) regardless of which port it lands on.
- **`$EDITOR` is unset on `C3PO`.** `git merge` without `--no-edit` stops
  waiting for `vi`, which isn't installed. Use `git commit --no-edit` (or
  set an explicit editor) rather than let it hang.
- **Bluetooth is rfkill soft-blocked by default on this image** —
  nothing in the unattended boot clears it (that's normally
  `raspi-config`'s interactive country-code step). `rfkill list` and
  `/sys/class/rfkill/*/soft` show it directly; `hciconfig hci0 up`'s
  error message names it explicitly. Don't trust `bluetoothd`'s own
  "Failed to set mode: Failed (0x03)" to self-diagnose this — it's the
  same underlying block, several layers removed. `rfkill` itself is on
  the image already (`/usr/sbin/rfkill`, needs `sudo` and isn't on a
  non-root `PATH` by default) — it was never actually missing, just not
  found by an unqualified `which rfkill`.
- **A stock `alsa-restore.service` fights any "boot volume is fixed,
  never restored" requirement.** It's enabled by default on Raspberry
  Pi OS Lite and does exactly the opposite. Mask it, don't just order
  your own unit to run after it and hope you win the race.
- **A lossy bidirectional bridge over two different scales needs echo
  suppression on *both* directions, and a single write can produce more
  than one incoming event.** A boolean "skip the next one" flag missed
  both — see the volume bridge fix above for the measured consequence
  (a real ratchet to zero) and the fix (a shared time-window, not a
  one-shot flag).
- **`bluetoothctl discoverable on` does NOT mean persistently
  discoverable.** BlueZ's `DiscoverableTimeout` defaults to 180s and
  silently reverts the adapter afterwards; `Pairable` has no such default
  and does persist, so the two behave differently despite being set the
  same way two lines apart. Cost us blocker 3 and 1h36m of a live debug
  session. Read `bluetoothctl show` back after setting it, rather than
  trusting "Changing discoverable on succeeded".
- **Build filenames now carry the version (2026-09-11)** — the
  `Makefile`'s `image:` target manifest-lookup glob is
  `*-gexis-player*.info`, not `*-gexis-player.info` — if a future edit
  narrows it back, the annotation step will silently stop finding the
  manifest again, the same shape as the multi-manifest bug this project
  already hit once (Phase 2c's prerequisites, `ls -t | head -1`).

## Working agreement

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits. Does not commit to
`main` — opens PRs.

Every architectural decision becomes a numbered ADR before implementation.
Findings state their scope: what was tested, under what conditions, what was
not. `docs/LESSONS.md` (PR #5) tracks recurring verification-methodology
failures, kept distinct from findings and ADRs.
