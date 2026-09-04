# Decision records

## Numbering gap — read this first

**ADRs 0001–0007 do not exist in this repository.** They were drafted in
conversation before the repo was created and were never committed. Several are
referenced by the records below as superseded.

They are **not** being reconstructed here. Writing them from summaries and
presenting them as the historical record would be fabrication. What is known
about each is listed below, and that is all that is known.

The numbering starts at 0008 to preserve the references rather than silently
renumbering, which would make the supersession lines meaningless.

| # | Subject | Status |
|---|---|---|
| 0001 | Base OS: Raspberry Pi OS Lite vs DietPi | **Still open.** Blocked on whether DietPi supports a reproducible, CI-drivable image build comparable to Volumio's `build.sh` or moOde's pi-gen wrapper. To be written properly when resolved. |
| 0002 | PipeWire as routing and arbitration layer | Superseded by 0008 |
| 0003 | Two playback modes: passthrough and arbitrated | Void. Both were PipeWire constructs; independently void because DSD and >24-bit are unreachable on the DAC2 HD. See 0008. |
| 0004 | One active renderer | Answered by 0010 |
| 0005 | VU metering via PipeWire monitor ports | Superseded by 0011 |
| 0006 | Bluetooth on BlueZ + bluez-alsa | Still stands. Reversed to PipeWire-native mid-design and reversed back when PipeWire was dropped. Net effect: unchanged. |
| 0007 | Local AI division of labour | Constrained by 0012. The API-lookup half is adopted; the audio-embedding half needs a local library, which is out of scope, so it is a separate product operating on the LMS library. |

## Records

| # | Title | Status |
|---|---|---|
| [0008](0008-direct-alsa-over-pipewire.md) | Direct ALSA, not PipeWire | Accepted |
| [0009](0009-logical-output-device.md) | The logical `output` device | Accepted |
| [0010](0010-arbitration-slot-model.md) | Arbitration: base slot, connection acquisition, uniform disconnect | Accepted |
| [0011](0011-meter-data-three-transports.md) | Meter data on three transports from one service | Accepted |
| [0012](0012-enrichment-additive-only.md) | Enrichment is renderer-agnostic and additive only | Accepted |
| [0013](0013-defaults-implement-public-contract.md) | Default renderers implement the public plugin contract | Accepted |
| [0014](0014-nowplaying-and-peppy-are-distinct.md) | Now playing and the Peppy screen are distinct screens | Accepted |
| 0015 | Skin renderer and the PeppyMeter format | **Not written.** Blocked on skin assets. |
| [0016](0016-plugins-as-separate-processes.md) | Plugins are separate processes with an IPC contract | Accepted |
| [0017](0017-core-daemon-in-python.md) | The core daemon is Python | Accepted |
| 0018 | Volume and output modes | **Not written.** Open questions remain. |
| 0019 | Peppy screen entry and exit | **Not written.** Open questions remain. |
| 0020 | Library browse as a normalised tree | **Not written.** Open questions remain. |
| 0021 | Deployment as a flashable image | **Not written.** Overlaps 0001. |

## Conventions

- One decision per record. Numbered, never renumbered.
- A superseded record keeps its number and gains a header pointing forward.
- **Rejected alternatives are recorded with the reason they were rejected.**
  Rejected designs look reasonable again later and the reasons stop being
  obvious. ADR-0010 is the clearest example: three arbitration models were
  designed and dropped, and each would be re-proposed without that section.
- **Reversal conditions are stated where they are known.** ADR-0008 names the
  condition that would bring PipeWire back.
- Claims sourced from measurement cite the finding in `docs/findings/`.
  Unverified claims are marked as such inline.
