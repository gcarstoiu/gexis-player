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
| [0010](0010-arbitration-slot-model.md) | Arbitration: base slot, connection acquisition, uniform disconnect | Accepted, amended |
| [0011](0011-meter-data-three-transports.md) | Meter data on three transports from one service | Accepted |
| [0012](0012-enrichment-additive-only.md) | Enrichment is renderer-agnostic and additive only | Accepted |
| [0013](0013-defaults-implement-public-contract.md) | Default renderers implement the public plugin contract | Accepted |
| [0014](0014-nowplaying-and-peppy-are-distinct.md) | Now playing and the Peppy screen are distinct screens | Accepted |
| [0015](0015-skin-renderer-peppymeter-format.md) | Skin renderer targets the PeppyMeter/Volumio extended format | Accepted, one item deferred to a spike |
| [0016](0016-plugins-as-separate-processes.md) | Plugins are separate processes with an IPC contract | Accepted |
| [0017](0017-core-daemon-in-python.md) | The core daemon is Python | Accepted |
| [0018](0018-volume-and-output-modes.md) | Volume and output modes | Accepted |
| [0019](0019-peppy-screen-lifecycle.md) | Peppy screen: entry, exit and lifecycle | Accepted |
| [0020](0020-library-browse-tree.md) | Library browse as a normalised tree | Accepted |
| [0021](0021-deployment-flashable-image.md) | Deployment as a flashable image | Accepted, distribution channel deferred |
| [0022](0022-settings.md) | Settings | Accepted |
| [0024](0024-bluetooth-pairing-no-pin.md) | Bluetooth pairing: no PIN, for this installation | Accepted |

## Cross-cutting rules

Rules established in one record that bind the others.

**Unusable controls** — established in [0020](0020-library-browse-tree.md):

> If the capability does not exist, hide it. If it exists but cannot be operated
> here, show it and say where it can be.

Volume in fixed output is hidden (0018); settings text and search on the panel
are shown but not editable (0022, 0020). ADR-0014's "hidden or greyed" should be
read through this rule.

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
| Qobuz navigation model | 0020 | Adopting SlimBrowse means Qobuz menus need an adapter into SlimBrowse form or a second browse path. The architecture's claim that a normalised model makes this cheap is weaker than written. |
| Image distribution channel | 0021 | Plain `.img`, self-hosted Imager repository, or application to Imager's community categories. Does not block anything yet. |
| `steps.per.degree` quantisation | 0015 | Not decidable from configuration. Spike defined; outcome to be recorded as an amendment. |
| Apt repository infrastructure | 0021 | In-place updates require a signed, hosted repository. Not specified anywhere. |
| Maximum volume ceiling | 0018 | Listed as "to be recorded"; still undecided. |
| Empty base slot behaviour | 0010 | Valid state if run headless with no LMS. Undefined. |
| Factory reset | 0021 | Implied by configuration persistence, specified nowhere. |
| Plugin settings pages | 0022 | Whether plugins can add their own settings belongs to the plugin contract (0016). |
| Pairing mode as a per-installation setting | 0024 | PIN-free is right for this installation, wrong as a shipping default (different threat model elsewhere). Needs the settings infrastructure (0022) before it can be anything but hardcoded. |

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
