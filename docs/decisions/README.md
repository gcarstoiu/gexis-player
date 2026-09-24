# Decision records

## Numbering gap — read this first

**ADRs 0002–0007 do not exist in this repository.** They were drafted in
conversation before the repo was created and were never committed. Several are
referenced by the records below as superseded.

They are **not** being reconstructed. Writing them from summaries and presenting
them as the historical record would be fabrication. What is known about each is
listed below, and that is all that is known.

ADR-0001 was in the same position but has since been written properly, because
the question blocking it was answered.

| # | Subject | Status |
|---|---|---|
| 0002 | PipeWire as routing and arbitration layer | Superseded by [0008](0008-direct-alsa-over-pipewire.md) |
| 0003 | Two playback modes: passthrough and arbitrated | Void. Both were PipeWire constructs; independently void because DSD and >24-bit are unreachable on the DAC2 HD. See 0008. |
| 0004 | One active renderer | Answered by [0010](0010-arbitration-slot-model.md) |
| 0005 | VU metering via PipeWire monitor ports | Superseded by [0011](0011-meter-data-three-transports.md) |
| 0006 | Bluetooth on BlueZ + bluez-alsa | Still stands. Reversed to PipeWire-native mid-design and reversed back when PipeWire was dropped. Net effect: unchanged. |
| 0007 | Local AI division of labour | Constrained by [0012](0012-enrichment-additive-only.md). The API-lookup half is adopted; the audio-embedding half needs a local library, which is out of scope, so it is a separate product operating on the LMS library. |

## Records

| # | Title | Status |
|---|---|---|
| [0001](0001-base-os.md) | Base OS: Raspberry Pi OS Lite 64-bit | Accepted |
| [0008](0008-direct-alsa-over-pipewire.md) | Direct ALSA, not PipeWire | Accepted |
| [0009](0009-logical-output-device.md) | The logical `output` device | Accepted |
| [0010](0010-arbitration-slot-model.md) | Arbitration: base slot, connection acquisition, uniform disconnect | Accepted, amended, **partly superseded by [0027](0027-lms-power-as-arbitration-mechanism.md)** |
| [0011](0011-meter-data-three-transports.md) | Meter data on three transports from one service | Accepted |
| [0012](0012-enrichment-additive-only.md) | Enrichment is renderer-agnostic and additive only | Accepted |
| [0013](0013-defaults-implement-public-contract.md) | Default renderers implement the public plugin contract | Accepted |
| [0014](0014-nowplaying-and-peppy-are-distinct.md) | Now playing and the Peppy screen are distinct screens | Accepted |
| [0015](0015-skin-renderer-peppymeter-format.md) | Skin renderer targets the PeppyMeter/Volumio extended format | Accepted, one item deferred to a spike |
| [0016](0016-plugins-as-separate-processes.md) | Plugins are separate processes with an IPC contract | Accepted |
| [0017](0017-core-daemon-in-python.md) | The core daemon is Python | Accepted |
| [0018](0018-volume-and-output-modes.md) | Volume and output modes | Accepted |
| [0019](0019-peppy-screen-lifecycle.md) | Peppy screen: entry, exit and lifecycle | Accepted |
| [0020](0020-library-browse-tree.md) | Library browse as a normalised tree | Accepted, **partly superseded by [0030](0030-library-typed-radio-slimbrowse.md)**; cross-cutting table amended by [0029](0029-text-entry-on-every-surface.md) |
| [0021](0021-deployment-flashable-image.md) | Deployment as a flashable image | Accepted, distribution channel deferred |
| [0022](0022-settings.md) | Settings | Accepted; remote-only text entry superseded by [0029](0029-text-entry-on-every-surface.md), first-boot blocker answered by [0031](0031-first-boot-setup-access-point.md) |
| [0023](0023-svelte-ui.md) | The UI is Svelte | Accepted |
| [0024](0024-bluetooth-pairing-no-pin.md) | Bluetooth pairing: no PIN, for this installation | Accepted |
| [0025](0025-project-licence-gplv3.md) | gexis-player is licensed GPL v3 | Accepted |
| [0026](0026-peppymeter-native-process-integration.md) | Peppy screen: native PeppyMeter process, labwc-mediated screen ownership | Accepted, **amended 2026-09-16** (vendor the engines, not the Volumio wrapper); compositor mechanism **verified** (Finding 025) |
| [0027](0027-lms-power-as-arbitration-mechanism.md) | LMS power is the arbitration mechanism; no permanent base slot | Accepted — supersedes parts of [0010](0010-arbitration-slot-model.md) |
| [0028](0028-ui-serving-and-command-channel.md) | The core daemon serves the UI; commands go over REST | Accepted — answers what [0023](0023-svelte-ui.md) left open |
| [0029](0029-text-entry-on-every-surface.md) | Text fields are editable on the panel too; no on-screen keyboard | Accepted — supersedes [0022](0022-settings.md)'s remote-only rule, amends [0020](0020-library-browse-tree.md) |
| [0030](0030-library-typed-radio-slimbrowse.md) | Library by typed query and our own screens; SlimBrowse only for radio, rooted at `radios` | Accepted — supersedes [0020](0020-library-browse-tree.md)'s pass-through decision; amended by [0038](0038-library-and-radio-on-the-panel.md) |
| [0031](0031-first-boot-setup-access-point.md) | First boot with no network raises a setup access point; typing happens on the user's phone | Accepted — answers the blocker [0022](0022-settings.md) raised and [0021](0021-deployment-flashable-image.md) could not close |
| [0032](0032-one-page-two-surfaces.md) | One page, two surfaces: the panel renders everything, a remote browser renders only settings | Accepted — only the settings screen is responsive; clarifies Phase 4 criterion 5 |
| [0033](0033-idle-and-home.md) | Idle is "not playing and not touched"; Home is the no-renderer screen | Accepted — amends [0019](0019-peppy-screen-lifecycle.md) |
| [0034](0034-panel-volume-travel-and-mute.md) | Panel volume: slider over −45…0 dB, shown as slider position; mute restores the prior level | Accepted — amends Phase 4 criterion 8 |
| [0035](0035-settings-api.md) | Settings: one registry in the daemon, a generic API, wired one setting at a time | Accepted — the API ADR-0032 deferred |
| [0036](0036-peppy-entry-and-no-rate-or-codec.md) | Peppy screen entry: the button, or five minutes of unattended playback; no sample rate or codec anywhere | Accepted — amends [0019](0019-peppy-screen-lifecycle.md) |
| [0037](0037-transport-commands.md) | Transport commands: one route to the active renderer; a control the renderer has is visible, disabled when it cannot work now | Accepted — amends [0020](0020-library-browse-tree.md)'s unusable-controls rule |
| [0038](0038-library-and-radio-on-the-panel.md) | Library and radio on the panel: the designed screens only, read through the core, played on LMS | Accepted — amends [0030](0030-library-typed-radio-slimbrowse.md) (screen list, Podcasts exclusion, Radio Now Playing); §7's artwork ladder corrected 2026-09-18 |
| [0039](0039-cpu-governor-performance.md) | The CPU governor is `performance`, set by a unit in the image | **Reverted the same day** (George, 2026-09-17): ~10 °C hotter for no visible improvement; the panel's smoothness came from sharing one backdrop. Kept for the measurements |
| [0040](0040-enrichment-providers.md) | Enrichment providers: LMS's artist-information plugin first where it answers, a key-free set (MusicBrainz, Cover Art Archive, Wikipedia, ListenBrainz, LRCLIB) behind it | Accepted — amends [0012](0012-enrichment-service.md)'s Sources and its single shared bucket |
| [0041](0041-scrims-dim-but-do-not-blur.md) | Scrims dim but do not blur: no `backdrop-filter` anywhere in the panel | Accepted — amends the designs, which draw every sheet over a blurred backdrop. [Finding 037](../findings/037-why-a-blurred-scrim-costs-the-panel.md) has the mechanism |
| [0042](0042-a-local-cache-for-vendored-downloads.md) | A content-addressed local cache for the build's vendored downloads, network only on a miss | Accepted — a sha256 protects integrity, not availability. **Explicitly not the backup it was asked for**: a mirror we control is deferred |
| [0043](0043-boot-animation-and-a-silent-boot.md) | A boot animation over a silent boot: every source of text quieted, Plymouth from the initramfs, torn down when the UI paints | Accepted (George, 2026-09-19) and built the same day — **never booted**. [Finding 038](../findings/038-what-the-panel-shows-while-it-boots.md) has the budget: 19.7s, kiosk at 18.26s |
| [0044](0044-settings-row-vocabulary.md) | The settings row vocabulary grows six mechanics: `list`, `warn`, `onlyWhen`, `optionsFrom`, `picker`, `surfaced` — and text rows take real input on both surfaces | Accepted (George, 2026-09-20) — amends [0035](0035-settings-api.md) and [0022](0022-settings.md); settles [0029](0029-text-entry-on-every-surface.md)'s keyboard question: there is never an on-screen one. Phase 9 **9d**, and it gates 9e/9f/9g |
| [0045](0045-bluetooth-pairing-confirmation.md) | Bluetooth pairing is confirmed on the panel, on a device's first pair only | Accepted (George, 2026-09-20) — reverses [0024](0024-bluetooth-pairing-no-pin.md). Needs **our own** BlueZ `Agent1`: `bt-agent` answers on a console and `gexis_core` has no agent code. Phase 9 **9f** |
| [0046](0046-fixed-output-hides-the-slider.md) | Fixed output hides the volume control everywhere, with a padlock and a reason, rather than disabling it | Accepted (George, 2026-09-20) — implements [0018](0018-volume-and-output-modes.md)'s unbuilt half. Phase 9 **9i, last**: it carries the undecided boot level, **+72 dB** from today's |
| [0047](0047-the-idle-screen-gains-backgrounds-and-weather.md) | The idle screen gains four backgrounds and a weather stack, both keyed and both optional | **Proposed** — amends [0033](0033-idle-and-home.md), whose "the external page" becomes one option of several. **Two providers unchosen**, the shape [Finding 030](../findings/030-free-enrichment-providers.md) already answered once. Phase 9 **9g** |
| [0048](0048-how-the-device-name-reaches-four-services.md) | How the one device name reaches squeezelite, go-librespot, BlueZ and the hostname | **Proposed** — implements [0022](0022-settings.md) §2 and §3. **Nothing is applied while the device is running**, not even the hostname, which can be: a live change is how the phone that typed the name loses its way back. Phase 9 **9e** |
| [0049](0049-the-pictures-folder-is-a-share.md) | The on-device pictures folder is an SMB share | **Accepted** — George, 2026-09-21, choosing from four ways to get a picture onto an appliance: *"Let's go with B. Simplest for now as it should be."* One directory, guest-writable because [0028](0028-one-daemon-one-origin.md) already leaves the LAN that way, and Debian's own `[homes]`, `[printers]` and `[print$]` turned off. Closes [0047](0047-the-idle-screen-gains-backgrounds-and-weather.md)'s last open question. Phase 9 **9g** |
| [0050](0050-skin-previews-are-the-skins-own-picture.md) | A skin's preview is the skin's own picture | **Accepted** — George, 2026-09-21: *"Let's keep it simple and use what we have instead of generating thumbnails and cache and more logic."* Every skin ships a 1280x800 `screen.bgr`, so 9h's image-build render, its cache and its change detection all disappear rather than being designed. Phase 9 **9h** |
| [0051](0051-the-visualiser-reads-its-selection-from-a-file.md) | The visualiser reads its skin selection from a file | **Accepted** — `/run/gexis/visualisation.json`, polled beside `nowplaying.json`. The corpus spans the pack's *two* template directories, because the one the engine loads holds 71 meters and no spectrum at all, so two of the four `skin_corpus` words would offer nothing; `base.path` swapped around the factory built 13 of 13 (measured 2026-09-22). Amends [0019](0019-peppy-screen-lifecycle.md), [0026](0026-peppymeter-native-process-integration.md), [0050](0050-skin-previews-are-the-skins-own-picture.md). Phase 9 **9h** |
| [0052](0052-the-volume-path.md) | The volume path: what moves the level, how fast, and how loud it may get on its own | **Accepted, then amended the same day.** The boot number is not the hazard, an unattended jump is — but §1's `restore_ceiling` held the hardware down while every control still read what the renderer remembered, so the first nudge released it in one move; withdrawn, and the ramp answers the hazard instead. `max_ceiling` is redefined as *the top of every scale*, applied as a shift so every step keeps its size. Direct libasound writes (5.7 ms against 16.4) and a ramp to each new target, because a drag only ever delivers a sample of itself. `travel_curve` renamed to what it does; `max_ceiling` enforced in one place; the mirror rate-limited; Spotify stops attenuating the stream. On [Finding 045](../findings/045-the-volume-path-measured.md). Phase 9 **9i** |
| [0053](0053-the-panel-is-a-remote-control.md) | The panel is a remote control for what is playing, not a second volume | **Accepted** — George, 2026-09-22. One sound has two numbers today (LMS 25 shows 33 on the panel, measured). A panel change would be sent to the renderer — LMS's RPC, go-librespot's API, Bluetooth's own control — and reach the DAC through the mirror that already exists. Costs +6 ms on Bluetooth, +10 on Spotify, **+22–33 on LMS**. squeezelite will not carry a mixer change back to LMS, which is why it has to be the server. On [Finding 046](../findings/046-the-remote-control-path-measured.md). Phase 9 **9i** |
| [0054](0054-one-curve-and-the-renderers-own-number.md) | One volume curve, ours, applied to each renderer's own number | **Accepted** — George, 2026-09-23. A renderer's zero was -38 dB and the bottom fifth of LMS's travel spanned one decibel, because other programs derived our curve from a control's declared range. Since [0053](0053-the-panel-is-a-remote-control.md) they need not: the daemon knows each renderer's own number. Bluetooth's level leaves the mixer (`--volume=none`, bluealsa's D-Bus `Volume`), the dummy control becomes a trigger, and one curve - linear in dB over 60 dB with zero as silence - serves all three. On [Finding 047](../findings/047-where-the-volume-actually-goes.md). Phase 9 **9i** |
| [0055](0055-which-output-the-device-plays-to.md) | Which output the device plays to | **Accepted and built** — George, 2026-09-23. four playback outputs measured on the device and **two of them have no volume control at all**, so choosing one *is* [0046](0046-fixed-output-hides-the-slider.md)'s fixed output. The switch is two lines of `output.conf` because everything already goes through [0009](0009-alsa-device-indirection.md)'s `pcm.output`, and the visualiser follows for free. All four are offered and the empty socket says *nothing connected*. Phase 9 **9j** |
| [0056](0056-the-spectrum-frame-follows-its-reader.md) | The spectrum frame is the size its reader expects | **Proposed**, built and running so George can look. A FIFO carries bytes, not messages: peppyalsa measures 30 bands and a skin draws 20-22, and PeppySpectrum reads `4 x size` bytes at a time, so every bar showed a different band each refresh ([Finding 051](../findings/051-the-spectrum-pipe-and-the-bars-must-agree.md)). The relay folds its bands to the count the engine declares, peak per group; peppyalsa stays at 30 and the panel keeps all of them |
| [0057](0057-the-meters-follow-the-volume.md) | The meters show what comes out, not what went in | **Accepted and built** — George, 2026-09-23: *"Both should follow... Let's do both and see."* The meter tap is upstream of the DAC's attenuator, so the needles never moved with the volume. The daemon publishes the dB it is cutting and the relay applies it to every consumer — a multiplication for the linear VU, a subtraction for the logarithmic spectrum. Fixed output needs no special case: the DAC is at full scale, so the number is 0 |
| [0058](0058-the-visualisations-ballistics-are-settings.md) | How the visualisation moves is three settings | **Accepted and built** — George, 2026-09-23: *"Add these as settings for me to tweak as I please for both meters and spectrum."* Spectrum smoothing, needle fall time and needle smoothing, in a **Meters and spectrum tweaks** group under Display. Two are peppyalsa's and go through `output.conf`, so applying them reopens the sound card; the third is PeppyMeter's and restarts the visualiser. Each row says which |
| [0059](0059-artist-portraits-in-the-list.md) | Where the artist list's portraits come from | **Accepted** — George, 2026-09-24: a **button** in Enrichment, not a background sweep. Two of them — artist portraits and album covers — fanart first, LMS as the fallback, everything re-asked on every press, honest progress (*X of Y processed, Z found*), paced, one at a time. Keyed on the folded name, never LMS's ids, and gated on the confidence threshold. **25-30 minutes for both**: fanart returns an artist's albums in the artist call, so album art needs no per-album request ([Finding 054](../findings/054-what-lms-knows-about-artist-identity.md) §9). LMS cannot hold the MusicBrainz ids for us (§10). Phase 9 **9k** |
| [0060](0060-the-panel-background-gets-a-layer-of-its-own.md) | The panel's background gets a compositor layer of its own | **Accepted** — George, 2026-09-24: *"Go for a"*. `.bg { will-change: transform }`. The two blurs behind every screen are re-evaluated over whatever a scroll damages, so the cost is the scroller's area and nothing in it ([Finding 059](../findings/059-what-the-panel-pays-for-its-blur.md)). Promoted, the blur is rastered once: artist grid **27.8 → 52.9 fps**, as good as deleting the background, and **pixel-identical** — max difference 2 of 255 ([Finding 061](../findings/061-the-background-wants-a-layer-of-its-own.md)). Phase 9 **criterion 0** |
| [0061](0061-the-kiosk-does-not-render-subpixel-text.md) | The kiosk does not render subpixel text | **Accepted** — George, 2026-09-24, having run it: *"C works."* `--disable-lcd-text`. Chromium keeps a scroll on the main thread rather than lose subpixel text on a scroller that is not opaque, and every screen here draws over a translucent veil. With it, **every scroll reaches 57-59 frames drawn a second at 0.00 % dropped**, including the queue rail ([Finding 062](../findings/062-the-two-changes-together.md)). Subsumes Finding 060. Phase 9 **criterion 0** |
| [0062](0062-the-queue-removes-by-swipe.md) | A queue row is removed by swiping it | **Accepted** — George, 2026-09-24. The per-row X goes; a left swipe past 96 px removes, a tap still plays. Gives the titles 50 px back. **The affordance is the cost** — the accessible control stays, off screen; whether it needs a visible hint is still George's call. Phase 9 **criterion 0** |
| [0063](0063-the-queue-is-as-long-as-lms-says.md) | The queue is as long as LMS says it may be | **Accepted** — George, 2026-09-24: *"Increase the queue to whatever is set in Lms."* `maxPlaylistLength` (2500 on his server) replaces a hardcoded 100, read once per run. LMS's `0` means unlimited and becomes a 2500 ceiling; a server that will not answer keeps 100. The old window also **broke removing a track**, because it refilled from beyond itself. Phase 9 **criterion 0** |
| [0064](0064-queue-rows-have-identities.md) | A queue row is identified by its track, not its position | **Accepted** — George, 2026-09-24, after three failed attempts at the symptom. `TrackMetadata.track_id` from LMS, keyed `<id>#<nth>`. Keyed by position, one removal rewrote ~180 rows' contents and the swiped row was recycled rather than destroyed. Phase 9 **criterion 0** |
| [0065](0065-long-lists-are-built-a-screenful-at-a-time.md) | A long list is built a screenful at a time | **Accepted and built** — George, 2026-09-24: *"Do 1."* 140 rows, then 160 more per frame. The artist grid's first row goes **1939 ms → 264 ms** and a 467-track playlist's **1407 → 312**, with the rest filling behind ([Finding 063](../findings/063-the-panel-builds-every-row-before-it-draws-one.md)). The A-Z rail completes the grid before jumping. Phase 9 **criterion 0** |
| [0066](0066-a-home-card-says-it-was-pressed.md) | A home card says it was pressed | **Accepted and built** — George, 2026-09-24: *"Radio has a tapping animation. The rest do not."* Neither had one; Radio's next screen simply painted at once where the others held the panel's last frame. `is-pressed` on pointerdown, navigation in `afterPaint`: every card pressed within 8–14 ms and **painted at 25–37 ms**. Does not reverse the 2026-09-21 removal from list rows, which are replaced under the finger. Phase 9 **criterion 0** |
| [0067](0067-only-what-is-on-screen-is-built.md) | The long lists build only what is on screen | **Accepted and built** — George, 2026-09-24: *"the artists and browse should be nearly instantaneous"*. The artist grid windows by letter group, the browse pane by row. Opening the grid blocks the main thread **1255–1358 ms → 0–62 ms**, builds 69 cards instead of 918, and paints in 202–243 ms; the scrolls keep 59.7 frames a second. Chosen because nothing *in* a card accounts for its cost ([Finding 064](../findings/064-the-count-is-the-cost.md)). Phase 9 **criterion 0** |

## Cross-cutting rules

Rules established in one record that bind the others.

**Unusable controls** — established in [0020](0020-library-browse-tree.md):

> If the capability does not exist, hide it. If it exists but cannot be operated
> here, show it and say where it can be.

Volume in fixed output is hidden (0018). ADR-0014's "hidden or greyed" should be
read through this rule.

**Amended 2026-09-16 by [0037](0037-transport-commands.md)** (George): a third
case. A control the renderer has, and that is operable here but **not right
now** — Next on a radio station — stays **visible and disabled**, never
hidden. Hiding is only for a capability that does not exist.

**Amended 2026-09-13 by [0029](0029-text-entry-on-every-surface.md):** settings
text fields are no longer part of the second branch — they are editable on the
panel too, via an external keyboard. There is no on-screen keyboard, and a
focused field with no keyboard attached does nothing and says nothing, which
0029 records as a knowingly accepted exception to 0014. The designs carry no
text-entry widgets, so this removes a constraint rather than adding a surface.

**Amended 2026-09-14 by [0030](0030-library-typed-radio-slimbrowse.md):** the
search example goes too — search is no longer rendered anywhere. **The second
branch now has no live case.** It is kept as a principle, not deleted, but
nothing in the product currently exercises it; judge a future case on the
reasoning, not on the retired examples. The first branch is doing all the work:
text-input items are dropped wherever they appear, which is how the radio
subtree stays operable without an on-screen keyboard.

**Scope clarified by George, 2026-09-13: this rule binds a *shippable*
product, and is a guideline during development.** From Phase 4 the UI is
imported from complete designs while the backend is wired up a phase at a
time, so screens will legitimately carry controls that do nothing yet — a
transport row before Phase 6, a lyrics tab before Phase 8. That is
development scaffolding, not a decision to ship dead controls, and it is
validated hard before the product is shippable rather than at each step.

**Resolved 2026-09-13: the gate is Phase 9 criterion 2**, "no unwired UI
remains, or each survivor is explicitly justified". It is the **backstop, not
the mechanism** — removal is continuous, each phase clearing the markers for
whatever it wires. Unwired UI is marked in the code so checking is a generated
list rather than an audit.

**Accountability** — established in [0010](0010-arbitration-slot-model.md),
restated by [0018](0018-volume-and-output-modes.md):

> Never show a state the user cannot account for.

Not a prohibition on silence. Mute, fixed output into a powered-down amplifier,
and volume at minimum all pass, because the user caused them and can undo them.
An uncommunicated renderer takeover does not.

**Never reference an ALSA card by index** — [0009](0009-logical-output-device.md).

**Spend the hardware on responsiveness.** Footprint and flash wear are not
selection criteria. Protect the audio path with priority, not by doing less.

## Deferred, needing their own records

| Subject | Raised by | Why it is not settled |
|---|---|---|
| ~~Qobuz navigation model~~ | 0020 | **Answered 2026-09-14 by [0030](0030-library-typed-radio-slimbrowse.md):** Qobuz is not rendered. `My Apps` is unreachable because the generic browser is rooted at `radios`, not `home`. The cost named here — that a normalised model does not make plugin menus cheap — is now paid as a standing cost: adding a streaming service later is our work, not automatic. |
| Image distribution channel | 0021 | Plain `.img`, self-hosted Imager repository, or application to Imager's community categories. Does not block anything yet. |
| `steps.per.degree` quantisation | 0015 | Not decidable from configuration. Spike defined; outcome to be recorded as an amendment. |
| Apt repository infrastructure | 0021 | In-place updates require a signed, hosted repository. Not specified anywhere. |
| Maximum volume ceiling | 0018 | Listed as "to be recorded"; still undecided. |
| Factory reset | 0021 | Implied by configuration persistence, specified nowhere. Adjacent to [0031](0031-first-boot-setup-access-point.md)'s re-entry condition — a device that returns to setup mode is most of a reset — but not the same decision. |
| Plugin settings pages | 0022 | Whether plugins can add their own settings belongs to the plugin contract (0016). |
| Pairing mode as a per-installation setting | 0024 | PIN-free is right for this installation, wrong as a shipping default (different threat model elsewhere). Needs the settings infrastructure (0022) before it can be anything but hardcoded. **Half-unblocked 2026-09-13:** Phase 3 criterion 5 built the persistence (`settings.py`), so what remains is the settings *screen*, not the store. |

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
