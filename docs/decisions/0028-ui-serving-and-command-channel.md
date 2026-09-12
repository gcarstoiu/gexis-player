# ADR-0028 — The core daemon serves the UI; commands go over REST

**Status:** Accepted
**Date:** 2026-09-12
**Raised by:** Phase 4 criteria 1, 5 and 7
**Relates to:** [0023](0023-svelte-ui.md) (which chose Svelte and left both of
these open), [0020](0020-library-browse-tree.md) (unusable controls),
[0022](0022-settings.md) (no authentication on a trusted LAN),
[0027](0027-lms-power-as-arbitration-mechanism.md) (why an activate control
has to exist at all)

## Context

ADR-0023 settled that the UI is Svelte, compiled ahead of time to static
files, and said those files are "served from our own HTTP server" without
saying which server. It also settled the *read* direction — "reactivity for
the playback model is a store fed by the WebSocket; views subscribe; nothing
reads the socket directly" — and says nothing at all about the write
direction, because at the time nothing wrote.

Phase 4 needs both answered:

- Something must serve the built UI to Chromium on the panel and to any
  remote browser (criteria 1 and 5).
- The UI must be able to **activate LMS** (criterion 7) and **set volume**
  (added 2026-09-12, George's decision). ADR-0027 never re-activates LMS
  silently, so without a write path the phone app stays the only route back
  to LMS.

Phase 3's WebSocket at `/state` is publish-only by construction —
`wsserver.py` drains and ignores anything a client sends.

## Decision

**1. `gexis-core`'s existing `aiohttp` application serves the built UI** as
static files, in the same process and on the same origin as the state
WebSocket.

**2. Client-to-server actions are REST POSTs on that same application.** The
WebSocket stays publish-only; it is never used as a command channel.

The initial command surface, which will grow:

| route | body | effect |
|---|---|---|
| `POST /renderer/{id}/activate` | none | that renderer takes the device — LMS's `power 1` today |
| `POST /volume` | `{"percent": <0-100>}` | sets the shared hardware mixer |

## Rationale

**Errors have somewhere to go.** An activation can fail for reasons the user
must be told about — LMS unreachable being the obvious one. HTTP carries that
in a status and a body, to the caller that asked. A WebSocket back-channel
would need correlation IDs, or a "last command result" field grafted onto the
published state, to say the same thing: new machinery for a problem HTTP has
already solved. Both ADR-0020's rule ("if it exists but cannot be operated
here, show it and say where it can be") and ADR-0010's accountability rule
require a failure to be *reportable*, not swallowed.

**The verified payload shape stays untouched.** `/state`'s shape was
hardware-verified in Phase 3 criterion 1. Accepting inbound messages invites a
`{type, ...}` envelope, and an envelope on one side invites symmetry on the
other — changing a contract that is already confirmed working, for no gain.

**It is testable the way this project actually tests.** Every part of Phase 3
was verified with `curl` and small scripts over SSH. A WebSocket is not
curl-able, and on this project that is not a minor inconvenience: it is the
debugging method of record.

**One process, one origin.** No CORS, no second service to install and
supervise, no new dependency — `aiohttp` is already pinned for the LMS and
Spotify adapters' HTTP clients and already serving `/state`.

## Consequences

- **The core daemon gains a presentation responsibility** it did not have:
  serving static files. Accepted deliberately. The alternative is a second
  process to install, supervise, configure and keep in sync with the daemon's
  own port, for no functional gain over `add_static`.
- **Commands are unauthenticated**, consistent with ADR-0022's already-accepted
  risk ("settings are not protected... trusted LAN is the assumption, as it is
  for moOde and Volumio") rather than a new exposure. Worth noting what is
  actually reachable: activating LMS and moving the volume are both immediately
  visible and trivially undoable. Nothing destructive is exposed here. If a
  future command is not undoable, that is the point to revisit this, not now.
- **Chromium loads from localhost and remote browsers from the same port**, so
  criterion 5 ("same page served to a remote browser") is the default rather
  than something built twice.
- Phase 5's visualisation transport and Phase 7's library proxy will most
  likely ride the same application. **Not decided here** — neither has been
  designed, and this record should not pre-empt them.

## Rejected

**A WebSocket back-channel.** See the first two rationale points: no natural
home for errors, and it puts a verified payload contract back in play. The
tidiness of "everything over one socket" is not worth either.

**A separate static server (nginx, lighttpd).** A second package, a second
systemd unit, a second config file and a split origin, to serve a handful of
files the daemon serves in one line. It would also make the "never restarting"
requirement of criterion 1 span two processes instead of one.

**Commands as WebSocket messages with HTTP only for errors.** Two transports
for one operation, and the UI would still need the HTTP path — so it is the
REST decision plus complexity.

## Unverified

- Whether Svelte's compiled output loads cleanly under Chromium's kiosk
  configuration served this way. This is ADR-0023's own open item, unchanged
  and now due in Phase 4.
- `aiohttp`'s static-file serving under the asset load Phase 5's skin renderer
  will put on it (full-screen JPEGs swapped per track, ADR-0019). Phase 4's own
  four screens are trivial by comparison; this is flagged because Phase 5 is
  where it would first matter.
