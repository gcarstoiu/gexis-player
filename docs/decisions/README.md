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
| [0026](0026-peppymeter-native-process-integration.md) | Peppy screen: native PeppyMeter process, labwc-mediated screen ownership | Accepted, compositor mechanism unverified |
| [0027](0027-lms-power-as-arbitration-mechanism.md) | LMS power is the arbitration mechanism; no permanent base slot | Accepted — supersedes parts of [0010](0010-arbitration-slot-model.md) |
| [0028](0028-ui-serving-and-command-channel.md) | The core daemon serves the UI; commands go over REST | Accepted — answers what [0023](0023-svelte-ui.md) left open |
| [0029](0029-text-entry-on-every-surface.md) | Text fields are editable on the panel too; no on-screen keyboard | Accepted — supersedes [0022](0022-settings.md)'s remote-only rule, amends [0020](0020-library-browse-tree.md) |
| [0030](0030-library-typed-radio-slimbrowse.md) | Library by typed query and our own screens; SlimBrowse only for radio, rooted at `radios` | Accepted — supersedes [0020](0020-library-browse-tree.md)'s pass-through decision |
| [0031](0031-first-boot-setup-access-point.md) | First boot with no network raises a setup access point; typing happens on the user's phone | Accepted — answers the blocker [0022](0022-settings.md) raised and [0021](0021-deployment-flashable-image.md) could not close |
| [0032](0032-one-page-two-surfaces.md) | One page, two surfaces: the panel renders everything, a remote browser renders only settings | Accepted — only the settings screen is responsive; clarifies Phase 4 criterion 5 |

## Cross-cutting rules

Rules established in one record that bind the others.

**Unusable controls** — established in [0020](0020-library-browse-tree.md):

> If the capability does not exist, hide it. If it exists but cannot be operated
> here, show it and say where it can be.

Volume in fixed output is hidden (0018). ADR-0014's "hidden or greyed" should be
read through this rule.

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

**Resolved 2026-09-13: the gate is Phase 9 criterion 4**, "no unwired UI
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
