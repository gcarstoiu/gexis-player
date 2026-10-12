# ADR-0139 — No passwordless sudo in the public image; test cards get it by provisioning

**Status:** **Accepted** — 2026-10-12, on George's standing direction
(2026-10-11: *"Remove passwordless sudo, last of all"*, and *"how will you
still test and debug after this?"* - answered here). Confirmed by the final
code review of 2026-10-12, which found it a real exposure.
**Amends:** the image's first-boot stage (`image/stage-gexis/01-firstboot`).

## Context

The image installs `/etc/sudoers.d/010_pi-nopasswd` (`pi ALL=(ALL)
NOPASSWD:ALL`). It was added when a provisioned card was found with no way
to become root at all (image/README.md), and every test since has relied on
it: installing previews over SSH, reading the journal, restarting services.

`pi` is also the user the kiosk browser, Squeezelite and the panel's
compositor run as, and two of those face the network. With passwordless
sudo, a flaw in any of them is a flaw as root. The review of 2026-10-12
confirmed nothing in the player itself calls `sudo`: the core runs as root
under systemd, and every privileged action goes through it.

## Decision

1. **The public image installs no sudoers rule for `pi`.** `pi` keeps no
   password, so on a card nobody provisioned there is no login and no way
   to root but the core's own API.
2. **A card provisioned for testing gets it back** with a new provisioning
   option, `DEV_SUDO="yes"` in `image/provision.local.env`: `make
   provision` writes it into the card's `firstrun.sh`, which installs the
   same rule on first boot, checked with `visudo` as the image step did.
   Without it, provisioning works exactly as before.
3. **Cards already flashed keep the rule they were flashed with.** An
   update cannot tell a test card from anyone else's, and every card flashed
   so far (images 0.9.x-0.10.x, all on the Testing channel) is a test card:
   sofapi and the bar keep theirs. The first public image is the first
   without it.

## Consequences

- `image/verify-image.sh` checks the rule is **absent** from the image.
- `image/README.md`'s first-boot notes and the technical guide say how a test
  card gets sudo.
- Debugging a user's player is through the problem report, as designed
  (ADR-0125), never through a login.
