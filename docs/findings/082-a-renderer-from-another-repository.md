# Finding 082 — A renderer from another repository takes the device, and gives it back

**Date:** 2026-09-25
**Question:** Phase 10 criterion 2 — *a fourth renderer built against the
contract, in a separate repository, with no changes to the core.* Does it
actually work, on hardware, with audio?
**Scope:** `gexis`, the branch's core deployed over the installed one, and
`gcarstoiu/gexis-plexamp` at its first commit running from
`/opt/gexis-plexamp`. Plexamp headless 4.13.2, claimed by George with his own
token the same evening. One run of each leg, driven from the device. **The
panel was not watched**; every number here is from the core's journal and from
`/proc/asound`, with the DAC resolved by name (`sndrpihifiberry`) and never by
index.

## It takes the device

Plexamp was given a play queue; one second later:

```
  after 1s -> active: plexamp   card: access: MMAP_INTERLEAVED   plexamp: state="playing"
    acquire: plexamp takes the device (was lms)
    release[lms]: polite stop freed the device (0.1s)
```

**The plugin saw `playing` on Plexamp's own timeline, sent `acquire` over the
socket, and arbitration released LMS.** Nothing in that sentence has happened
before: every previous acquisition on this device came from code living in the
same repository as the thing it was talking to.

## It gives it back, and the ladder waits

LMS was then activated. Plexamp's release is the API stop at `:32500`, which
confirms **instantly** and leaves the ALSA device held for a deterministic
**14 s** ([Finding 077](077-plexamp-on-gexis.md)) — so the plugin declares a
**16 s** polite grace, and the whole question is whether the ladder honours it
rather than escalating against a renderer that was going to let go anyway.

```
    acquire: lms takes the device (was plexamp)
    state: handoff plexamp -> lms
    release[plexamp]: freed within polite grace (14.1s)
    state: handoff finished
```

**14.1 s, inside the declared grace, with no SIGTERM and no SIGKILL.** The
number matches Finding 077's measurement of the same hold to a tenth of a
second, which is the point: a renderer measured once, declaring what it
measured, and the core believing it.

## "With no changes to the core"

The core gained a great deal this week — a plugin adapter, `register`/`forget`,
state slots, a socket group. **None of it names this renderer.** Every
occurrence of the string in `core/src/` is a comment explaining why something is
the way it is:

```
state.py:      `unknown renderer 'plexamp'`, after everything else about it worked.
plugin_env.py: the Beszel agent is one, Plexamp is another, and so is
arbitration.py: to give up the device: `KeyError: 'plexamp'` from inside
```

No branch, no map, no special case. The renderer's behaviour reaches the core
entirely through what it declared in `hello` and what it says on the socket.

## Three things this found before it worked, and they are the point

Criterion 2 exists to test the contract, not Plexamp. It failed three times
first, and **no test in the core repository could have caught any of them**,
because every test there was written by the same hand as the thing it tested:

1. **The socket authorised nobody but root** — `0660` on a socket the daemon
   creates is `root:root`. The plugin ran as `pi` and the kernel refused it
   before `hello`. Now `root:gexis-plugins`
   ([ADR-0084](../decisions/0084-plugins-speak-json-lines-over-a-unix-socket.md)
   amended).
2. **Arbitration carried it and the published state did not** — `StateStore`'s
   renderer slots came from the same fixed map. `unknown renderer 'plexamp'`,
   *after* the handshake, the adapter and the registration had all worked
   ([ADR-0089](../decisions/0089-arbitration-carries-a-plugin-renderer.md)
   amended).
3. **The supervisor was given a copy of the adapter map.** I decided that
   deliberately and wrote down a reason: *"the caller's dict is its own."* It is
   not — `__main__` looks renderers up in that same dict at runtime, and one of
   those lookups is the release ladder's own `device_busy`. The first real
   takeover raised **`KeyError: 'plexamp'` from inside `_release_with_ladder`**,
   which is the worst place on this device for an exception. One map now, shared.

## What this does not show

- **Nothing about metadata.** The plugin sends position, duration and transport
  state; title, artist, album and artwork live on the Plex Media Server, not on
  the player's timeline, and are not implemented. **So the contract's metadata
  half has still never been exercised from outside.**
- **Nothing about the panel.** Whether Plexamp draws correctly as a source,
  with its mark and accent, was not looked at.
- **One run of each leg.** Finding 077 established the 14 s across three runs;
  this shows the ladder honouring it once.
- **Nothing about a phone.** Playback was started by an API call, as before.
- **Nothing about claiming.** George pasted the token into Plexamp's own setup;
  the `claim_token` row is accepted by the plugin and does nothing yet.
- **Two of my own probe mistakes**, recorded because they wasted a pass each: a
  script that read `/proc/asound/card5` by index, which this project forbids,
  and a `POST /transport/play` sent while LMS was the active renderer — which
  played LMS, opened the card, and made the next two runs meaningless until the
  journal was read unfiltered.
