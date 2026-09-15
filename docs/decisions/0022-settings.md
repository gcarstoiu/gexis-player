# ADR-0022 — Settings

**Status:** Accepted
**Raises:** a first-boot blocker for ADR-0021 — see below
**Date:** 2026-09-04
**Raised by:** ADR-0019
**Amended:** 2026-09-13 — **the inventory below is refreshed**, George's
request. The original list was assembled on 2026-09-04 and predates Phases
2, 3 and 4, ADRs 0024-0028, and every volume finding; it had 16 items in
four groups and now has roughly fifty in seven. **Nothing was dropped** —
all 16 survive, several with what has since been measured about them
attached. Everything this record *decided* (settings are a separate screen,
text entry is remote-browser only, no authentication, one device name,
mixed application) is unchanged.
**Amended again:** 2026-09-13 — **"text entry is remote-browser only" is
superseded** by [ADR-0029](0029-text-entry-on-every-surface.md). The
inventory is untouched: that record adds no setting and removes none, it
changes only where an existing setting may be typed into.

## Context

Settings were not in the original requirement list. They accumulated: ADR-0018
produced output mode and boot volume, ADR-0019 produced skin corpus, two
timeouts and the idle URL, and the Should tier adds themes and plugin
management.

This record exists because the list is now long enough that where it lives and
how it is reached are design questions, not implementation details.

## Inventory

Assembled from the records rather than invented — which is why it grew: most
of what follows is a consequence of something already decided or measured,
not a wish list. Refreshed 2026-09-13.

Each row is marked:

- **[R]** recorded in a decision or finding
- **[H]** exists in the running system today, but hardcoded
- **[N]** new suggestion, not in any record — the only invented rows here
- **[?]** a decision already owed, where a settings screen would otherwise
  silently ship whatever the placeholder happens to be

### Audio — level and output

| Setting | Mark | Notes |
|---|---|---|
| Output mode: fixed / variable | [R] | ADR-0018. Only variable is built and hardware-verified; fixed is design-complete but unimplemented. Confirmation required; applies on next track or after stop. In fixed mode the volume slider **disappears everywhere**, settings included |
| Boot volume level | [R][H] | ADR-0018; `boot_volume_steps`, raw 60 = −90 dB, confirmed 2026-09-06. Fixed safe level, never restored from the last session |
| Maximum volume ceiling | [R][?] | ADR-0018 listed it "to be recorded"; still undecided |
| Restore floor for a *remembered* level | [R][H][?] | `restore_volume_floor_db`, −40 dB — a **placeholder never confirmed**, and Finding 011 §4 measured it as too quiet for Bluetooth's unmanaged floor bump. Never applies to the boot default, on purpose |
| Boot default mid-session, or only at true cold boot? | [R][?] | Finding 011 §3 — a renderer's first use mid-session currently lands as quiet as a power-on |
| Per-renderer volume memory on/off | [R][H] | George's decision 2026-09-07, currently unconditional |
| Which renderers are volume-managed | [R][H] | `capabilities.volume_managed`; Bluetooth excluded pending Finding 006 |
| Volume slider travel curve | [N][?] | Left open by Phase 4 criterion 8. The control is dB-linear, so travel mapped straight to percentage puts everything usable in the top quarter — 55 % is already −54 dB, measured |

### Arbitration — who gets the device

None of this group existed in the 2026-09-04 list. It is all consequence of
Phase 2 and ADR-0027.

| Setting | Mark | Notes |
|---|---|---|
| Enable / disable each renderer | [R] | implied by ADR-0013 |
| Re-activate LMS automatically when another session ends | [N] | ADR-0027 deliberately never does this — the reason Phase 4 criterion 7 existed at all (withdrawn 2026-09-15). Plausible opt-in, but it would reintroduce the spurious-reclaim failure that record measured, so not a free toggle |
| Restore transport state on return | [R][H] | ADR-0027: play only if it was playing |
| Seek re-anchor on return | [R][?] | Deferred twice in ADR-0027's Open, which then found a second argument for it: pressing play on a deactivated player loses the position entirely |
| Timeout ladder: polite / SIGTERM / SIGKILL grace | [H] | `TimeoutLadder` defaults |
| squeezelite `-C` idle close | [R][H] | Currently 1. Drove the whole release-timing result (Finding 018) |
| Transition screen threshold, and the exempt pairs | [R][H] | ADR-0010 calls 1 s "an initial value open to revision". **Evidence-gated rather than preference** — a pair earns exemption by measurement — so exposing it as a preference may be wrong |

### Display and screens

| Setting | Mark | Notes |
|---|---|---|
| Idle screen URL | [R] | ADR-0019; external, lazy loaded, needs a fallback for unreachable and unconfigured — and for *reachable but refuses framing*, see the panel home URL below |
| Panel home URL | [H] | `GEXIS_KIOSK_URL` in `/etc/gexis/kiosk.env`, hardcoded to `http://127.0.0.1:8090/`. Proven changeable with no rebuild and no code change (2026-09-14: the panel rendered an arbitrary third-party page correctly at 1280x800). George, 2026-09-14: **keep it hardcoded, we will need it later** — recorded because it is a setting in fact, not because it should be exposed. A panel that can be pointed away from our own UI has no route back except SSH |
| Idle timeout before the Peppy screen | [R] | ADR-0019, reset by local touch only |
| Idle timeout — to the idle screen | [R][H] | ADR-0019's "grace period after playback stops", generalised by [ADR-0033](0033-idle-and-home.md): one timeout on every screen, counted while not playing and not touched. Hardcoded to 5 minutes in `ui/src/App.svelte` since Phase 4d (confirmed as a setting by George, 2026-09-15) |
| Skin corpus: meter-only / meter+spectrum | [R] | ADR-0019 |
| Skin rotation per track on/off | [N] | Rotation is unconditional in ADR-0019 |
| `steps.per.degree` override | [R] | ADR-0015, deferred to a spike; may not survive as a user setting |
| Theme | [R] | Should tier |
| Headless — disable the local screen | [R] | Must |
| Screen brightness | [N] | The panel never sleeps by decision (ADR-0019); brightness is a separate question that record does not answer |
| Elapsed vs remaining time | [N] | Both are published |
| Show the transition screen at all | [N] | |

### Renderers and sources

| Setting | Mark | Notes |
|---|---|---|
| LMS server address, or discovery | [R][H] | Must. Hardcoded to `192.168.178.188:9000` in `core.toml` today |
| LMS player name | [H] | `gexis` |
| Bluetooth pairing: PIN-free vs confirmation | [R][?] | ADR-0024, and listed in `README.md`'s deferred table as *needing this record's settings infrastructure* before it can be anything but hardcoded. **Half-unblocked as of Phase 3**: the SQLite store exists, the settings screen does not |
| Bluetooth discoverability | [R] | BlueZ's 180 s default, no change by decision (ADR-0024's amendment). "Always / 3 minutes after boot / off" is the natural triple if it becomes a setting |
| Trusted device list — view and forget | [R] | ADR-0010 requires a recently-connected list for reconnection. Clearing it is one of this record's two named accepted risks |
| Auto-trust on pair | [H] | `gexis-bluetooth-trust.service` |
| Spotify Connect device name | [R] | Follows the single device name below |
| Plugin management | [R] | Should tier, ADR-0016 |

### Identity and network

| Setting | Mark | Notes |
|---|---|---|
| Device name | [R] | One name → mDNS hostname, Spotify, Bluetooth. The sanitised hostname must be shown alongside what was typed, not silently substituted (see Q4) |
| Wi-Fi configuration | [R] | Overlaps ADR-0021; the first-boot blocker this record raises (see Q2) — **answered 2026-09-14 by [ADR-0031](0031-first-boot-setup-access-point.md)**, entered on the user's phone over a setup access point, Phase 10 |
| Time zone / NTP | [N] | Confirmed as a setting by George, 2026-09-15. The idle clock shows device time, and the image ships no time zone: `gexis` came up as Europe/London and was set to Europe/Berlin by hand on 2026-09-15 — **a reflash loses it** |
| Restrict the API to loopback | [N] | ADR-0028 binds `0.0.0.0` and is unauthenticated by decision; a lock-down toggle is cheap and consistent with the accepted-risk framing below |

### Enrichment and lyrics — Phase 8

| Setting | Mark | Notes |
|---|---|---|
| Enrichment on/off | [R] | ADR-0012 |
| Confidence threshold | [R] | ADR-0012: below it, show nothing. A confidently wrong artist biography is worse than a blank panel |
| Lyrics on/off | [R] | |
| Artwork lookup for renderers that supply none | [R] | George, 2026-09-12: Bluetooth's absent art is transient — artist/album/title are enough to find it later |

### System and maintenance

Almost entirely new. That this group barely existed is itself worth noticing.

| Setting | Mark | Notes |
|---|---|---|
| Updates: automatic / manual | [R][N] | ADR-0021's update mechanism. Not hypothetical: on 2026-09-12 a held pin plus a moving archive failed a build outright |
| Factory reset | [R] | `README.md`'s deferred table — implied by configuration persistence, specified nowhere |
| Settings backup / restore | [N] | |
| Log level / diagnostics | [N] | |
| Show image version and build info | [R][?] | The build self-identification gap: nothing on a running device says which build it is, and `DEVELOPMENT.md`'s tier-3 rule expects the runner to assert against the manifest |
| Reboot / shut down | [N] | LMS's own menu already offers "Turn Off gexis", so the panel carrying it is consistent rather than novel |

### Four decisions this inventory is waiting on

Marked **[?]** above, gathered here because a settings screen built before
they are answered will encode the placeholders as if they were choices:
`restore_volume_floor_db`, the boot-default-mid-session question, the
maximum volume ceiling, and build self-identification.

## Settled by prior records

- **Output mode switching is not instantaneous.** Confirmation dialogue, and the
  change applies on the next track or after a stop (ADR-0018). Settings that
  change audible behaviour mid-playback need this treatment generally.
- **Controls disappear rather than grey out** when inapplicable (ADR-0018,
  ADR-0014). In fixed output mode there is no volume slider and no mute control
  anywhere, including in settings.

---

## Resolved

### Settings are a separate screen

A peer of library navigation, now playing and the Peppy screen, reached from the
same navigation.

*Rationale:* the inventory above is fifteen settings and will grow — plugins,
themes and every future record add to it. A drawer or overlay does not survive
that growth, and it makes sub-pages awkward. A screen has room for structure.

The cost is a top-level destination on a device whose main job is playing music.
Accepted.

### Text entry is remote-browser only

> **Superseded 2026-09-13 by [ADR-0029](0029-text-entry-on-every-surface.md).**
> A text field, where one exists, is now editable on both the panel and a
> remote browser. There is still no on-screen keyboard — the panel's route is
> an external USB keyboard — and a focused field with no keyboard attached
> does nothing, with no hint, which ADR-0029 records as a knowingly accepted
> exception to ADR-0014. The rationale below is not disputed; only the
> conclusion drawn from it changed. What survives unchanged: **the
> touchscreen displays every setting, including text values.**

**No on-screen keyboard.** Settings requiring free text — idle screen URL, LMS
server address, device name — are editable only from a remote browser.

**The touchscreen still displays every setting**, including text values. Where a
value cannot be edited locally, the screen shows it and states where to change
it. A setting that is invisible on the panel would leave a user unable to see
how their device is configured.

*Rationale:* an on-screen keyboard at 1280x800 is substantial work, and typing a
URL on a panel in a hi-fi rack is unpleasant regardless of how good the keyboard
is. Toggles, choices and sliders — which is most of the inventory — remain fully
editable locally.

#### This creates a first-boot blocker

> **Softened, not closed, by [ADR-0029](0029-text-entry-on-every-surface.md)
> (2026-09-13).** A keyboard on the panel is in principle a route in, but
> nothing designed today provides a pre-network settings surface to type into,
> and the designs carry no text-entry widget.
>
> **Answered 2026-09-14 by
> [ADR-0031](0031-first-boot-setup-access-point.md)** — the third candidate
> below ("a one-off exception permitting local entry for network setup only"),
> in the form of a temporary access point. The device raises its own Wi-Fi,
> serves the setup page from `gexis-core`, and the typing happens **on the
> user's phone**, which has a keyboard. The panel stays display-only, so this
> closes the blocker without reopening the on-screen-keyboard question.
> Scheduled as Phase 10. `firstrun.sh` pre-seeding remains the route for
> development and wins when present.

**Wi-Fi credentials cannot be entered remotely, because without Wi-Fi there is
no remote browser.**

This record does not solve it. It belongs to ADR-0021 (deployment as a flashable
image), and that record cannot be accepted without an answer. Candidate
approaches — pre-seeding credentials at flash time, a temporary access point, or
a one-off exception permitting local entry for network setup only — are noted
here so the problem is not rediscovered.

### Settings are not protected

Consistent with the no-authentication decision for the web UI. Trusted LAN is
the assumption, as it is for moOde and Volumio.

#### Accepted risk

Two settings are reachable by anyone on the network and have consequences:

- **Output mode.** Switching variable to fixed sets the DAC to 0 dB. Into an
  amplifier whose volume was set for an attenuated source, that is very loud.
- **Bluetooth trusted devices.** Clearing them is disruptive and not obviously
  reversible to a non-technical user.

The mitigation is the one ADR-0018 already requires: confirmation, and the
change applying on the next track or after a stop rather than immediately. That
protects against accident. It does not protect against a guest experimenting,
and no protection is offered against that.

An alternative was considered and rejected: making dangerous settings
touchscreen-only, on the reasoning that someone in the room will hear the
consequence. It would have paired neatly with text entry being remote-only —
the settings hardest to type are the safe ones. Rejected because it splits the
settings surface across two devices by risk category, which is harder to explain
than either rule alone.

### One device name

A single name, propagated to the mDNS hostname, the Spotify Connect device name,
the Bluetooth device name, and any future Connect renderer.

#### Sanitising is required and the user will see it

mDNS hostnames permit a narrower character set than Spotify and Bluetooth
display names, which accept spaces and punctuation. So a single stored name must
be sanitised for the hostname while the display names use it verbatim.

**The user will therefore see a different string in one place than they typed.**
The settings screen must show both — the name as entered and the resulting
hostname — rather than silently transforming it.

### Application is mixed

| Setting type | Behaviour |
|---|---|
| Toggles, choices, sliders | applied immediately |
| Text fields | explicit commit |
| Anything changing audible behaviour mid-playback | deferred, with confirmation |

*Rationale:* immediate application lets the user see the result, which is right
for a toggle and wrong for a half-typed URL. The third row is ADR-0018's
existing requirement for output mode, generalised.

## Out of scope for this record

- Which specific settings are exposed to plugins, and whether plugins can add
  their own settings pages. That is part of the plugin contract (ADR-0016) and
  should be decided there.
- First-boot and out-of-box configuration, which belongs with the deployment
  decision (ADR-0021) even though it overlaps Q2.

## Unverified

These bear on the single-name decision and could force a rename to be treated as
a disruptive operation rather than an ordinary setting.

- Whether the mDNS hostname can be changed without a restart, and what that does
  to an open browser session — the user renaming the device from a remote
  browser may disconnect themselves.
- Whether go-librespot and bluez-alsa accept a device-name change at runtime or
  require a restart of the renderer. If a restart is needed, renaming while
  playing would interrupt playback.
