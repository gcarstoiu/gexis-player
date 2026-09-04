# ADR-0022 — Settings

**Status:** Accepted
**Raises:** a first-boot blocker for ADR-0021 — see below
**Date:** 2026-09-04
**Raised by:** ADR-0019

## Context

Settings were not in the original requirement list. They accumulated: ADR-0018
produced output mode and boot volume, ADR-0019 produced skin corpus, two
timeouts and the idle URL, and the Should tier adds themes and plugin
management.

This record exists because the list is now long enough that where it lives and
how it is reached are design questions, not implementation details.

## Inventory

Assembled from the records rather than invented. Marked where a record already
constrains the behaviour.

### Audio

| Setting | Source | Notes |
|---|---|---|
| Output mode: fixed / variable | ADR-0018 | confirmation required; takes effect on next track or after stop |
| Boot volume level | ADR-0018 | fixed safe level, not restored from last session |
| Maximum volume ceiling | ADR-0018 | listed as "to be recorded"; still undecided |

### Display

| Setting | Source | Notes |
|---|---|---|
| Skin corpus: meter-only / meter+spectrum | ADR-0019 | |
| Idle timeout before Peppy screen | ADR-0019 | reset by local touch only |
| Grace period before idle screen | ADR-0019 | default five minutes |
| Idle screen URL | ADR-0019 | external, lazy loaded, needs a fallback |
| `steps.per.degree` override | ADR-0015 | deferred to a spike; may or may not survive as a user setting |
| Theme | Should tier | |
| Headless — disable the local screen | Must | |

### Renderers

| Setting | Source | Notes |
|---|---|---|
| Enable / disable each renderer | implied by ADR-0013 | |
| Bluetooth pairing and trusted device list | ADR-0010 | pairing is a settings function, and ADR-0010 requires a recently-connected list for reconnection |
| LMS server address or discovery | Must | |
| Plugin management | Should tier | |

### Identity and network

| Setting | Source | Notes |
|---|---|---|
| Device name | — | see Q4 |
| Wi-Fi configuration | — | overlaps ADR-0021; see Q2 |

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
