# Finding 093 — Qobuz Connect, as it stands in September 2026

**Date:** 2026-09-27
**Question:** George, opening Phase 12: *"Look at the current connect client
available on GitHub and check the licence and provide me with some
recommendations."* He also said the Qobuz work might be public after all,
where the records planned a private repository.

**Scope:** desk research only. GitHub repositories were read through the API
and their LICENSE files, and Qobuz's terms and the vendors' pages were fetched,
on 2026-09-27. **Nothing was installed or run**: no client has been tried on
`gexis`, and no audio claim below is measured. Two load-bearing facts were
re-checked first-hand after the survey: the QBZ shutdown notice, and Pibuz's
licence and release.

## The records are out of date

[ADR-0016](../decisions/0016-plugins-as-separate-processes.md) and
ARCHITECTURE §9 describe May 2025. They say moOde "found no FOSS-licensed code",
name `ahcm/qconnect` and roderickvd's reverse engineering as the leads, and plan
a **private** repository because the official route is a proprietary SDK. Since
then:

- **QBZ, the codebase almost every working open-source receiver descends from,
  was shut down at Qobuz's request** in September 2026. The maintainer:
  *"Any realistic future for QBZ as a Qobuz client would … require some form of
  formal access to the platform"* ([vicrodh/qbz](https://github.com/vicrodh/qbz)
  README, read 2026-09-27). The mirrors and forks are still up.
- **moOde integrates a Connect receiver**, Pibuz, a QBZ descendant. Its 10.3.5
  notes say *"Pibuz: TBD (user install)"*: the receiver is not bundled
  ([moode PR #805](https://github.com/moode-player/moode/pull/805) and the develop
  branch's `www/relnotes.txt`).
- **Volumio** has Connect through the official partnership, on its own hardware,
  as a paid feature.
- **roderickvd** has published nothing.

## The clients

| Client | What it is | State | Licence |
|---|---|---|---|
| [PhilipVinc/pibuz](https://github.com/PhilipVinc/pibuz) | Rust headless receiver for the Pi (QBZ lineage); ALSA `hw:` direct, up to 24/192; MPRIS, JSON events, hook scripts; pairing on the LAN without a login | active; v2.5.0 on 2026-09-26; what moOde points at | **MIT** |
| [yet-another-quentin/qbzd](https://github.com/yet-another-quentin/qbzd) | Rust headless receiver (QBZ fork) | nightly only; last push 2026-08-29 | MIT |
| [ahcm/qconnect](https://github.com/ahcm/qconnect) | Rust CLI with a `serve` receiver (QBZ crates) | last push 2026-05-25 | EUPL-1.2 |
| [bufadu/gobz-connect](https://github.com/bufadu/gobz-connect) | Go receiver; own ALSA, 24/192 | one week old | MIT |
| [SofusA/qobine](https://github.com/SofusA/qobine) | Player (270★) with an *experimental* Connect mode | active | GPL-3.0 |
| [ciaens/qobuz-connect](https://github.com/ciaens/qobuz-connect) | The protocol only, no audio | v0.1.1 | MIT |
| [leolobato/qobuz-proxy](https://github.com/leolobato/qobuz-proxy) | Virtual Connect device that forwards to DLNA | active | MIT |
| [delleceste/qobuzconnect2mpd](https://github.com/delleceste/qobuzconnect2mpd) | Receiver that drives MPD | young | no LICENSE file (README says LGPL-2.1+) |

**Every licence here allows a public repository, and so does ours.** MIT and
EUPL-1.2 both sit with GPL-3.0. The case for "private" was the official SDK's
confidentiality, not any of these.

**None of them is authorised.** Each one scrapes the web player's app id and
secrets from its `bundle.js`, or hardcodes a pair (qobuz-proxy). Qobuz's terms
forbid reverse engineering its applications and bypassing its protection
measures, and allow deleting an account that does
([qobuz.com legal terms](https://www.qobuz.com/us-en/legal/terms), section 12).
The QBZ shutdown shows Qobuz enforces this.

## The official route

Qobuz Connect for device makers goes through SDK vendors: StreamUnlimited's
StreamSDK includes it and runs Qobuz's self-test for its partners. Qobuz's own
page says only "Contact us to join our Qobuz Society program". **No terms, fees
or NDA text are public.** Whether a one-person DIY project can get access at
all is unknown.

## Not verified

- Any client's real behaviour on a Pi 4 with the HiFiBerry: bit-perfect output,
  24/192, and what the device does when another renderer holds it.
- Whether Qobuz has acted against the forks.
- Official terms, and whether a small maker can reach Qobuz directly.
- Whose app id qobuz-proxy hardcodes.
