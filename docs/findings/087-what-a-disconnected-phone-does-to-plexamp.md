# Finding 087 — What disconnecting the phone does to Plexamp

**Date:** 2026-09-26
**Question:** George: *"If I manually disconnect the phone from plexamp, the
panel still shows as if it's connected."* Is that a defect?
**Scope:** `gexis`, one disconnect, recorded once a second for 93 seconds
across the event: Plexamp's own timeline, the DAC's `hw_params` (card resolved
by name), the core's `active` and published `transport`, and the count of
established connections to `:32500`. George's own phone, his own disconnect.

## What happens

```
08:57:55  plexamp=playing  track=91795  card=open  core.active=plexamp  transport=playing  tcp=2
08:58:44  plexamp=playing  track=91795  card=open  core.active=plexamp  transport=playing  tcp=0
   … 45 s later, unchanged …
09:00:00  relinquish: plexamp gave up the device, nobody holds it now
```

**One thing changes at the disconnect and only one: the controller count, 2 → 0.**
Plexamp keeps playing, the position keeps advancing, the DAC stays open, and the
core keeps reporting `plexamp` / `playing`. George confirmed it out loud:
*"Music still playing."*

At **09:00:00** the track ended, Plexamp stopped, the plugin reported it, and
the core relinquished the device. **That path works.**

## So the panel is not lying

It says a renderer is playing, and a renderer *is* playing. **There is no defect
here.** What there is, is a difference between this renderer and the other two:

| | disconnecting the phone |
|---|---|
| Spotify | ends the session — go-librespot says so, and the device is released |
| Bluetooth | ends the session — the MediaPlayer1 interface disappears |
| **Plexamp** | **nothing.** It is a player, not a slave; the controller is a remote |

That is Plexamp's own design, and it is why George noticed: on this device, two
of three renderers treat a disconnect as the end.

## The TCP count looks better than Finding 077 found

[Finding 077](077-plexamp-on-gexis.md) rejected the connection count as a
release signal, having measured **0 at +7 s, +12 s and +13 s while audio was
playing and the phone was connected** — an instantaneous count is "is a poll in
flight this instant".

**This session did not reproduce that.** 48 consecutive samples while connected,
**all reading 2**; after the disconnect, 73 of 74 samples reading 0, with a
single 1 in the middle.

**Both can be true.** Finding 077 sampled while a phone was actively controlling
and polling; here two connections were held open throughout. What this
establishes is narrower than it looks: **a sustained zero over tens of seconds
distinguished "the controller left" cleanly on this occasion.** One session, one
phone, one app state. An instantaneous zero remains untrustworthy.

## The decision, which is George's

**Should disconnecting the controller stop Plexamp?**

| | what it costs |
|---|---|
| **Leave it** | nothing. The music keeps playing when the phone leaves the room, which is what a standalone player does — and what Plexamp itself intends |
| **Release on a sustained disconnect** | a window of N seconds at zero, then a commanded stop. Plausible on this evidence; **carries Finding 077's warning** that the count is noisy under other conditions, so a false positive would stop the music while somebody is listening |
| **Surface it instead of acting** | the panel could say the controller has gone without changing what plays. Nothing in the model carries "a controller is attached" today, and adding it is a contract change — v2 |

**Nothing has been built.** The middle option is the one that matches George's
expectation; the risk is that its failure mode is stopping music that somebody
is enjoying, which is worse than the thing it fixes.

## What this does not establish

- **One disconnect.** Not repeated, not with a second controller attached, not
  with the app backgrounded rather than disconnected — which Finding 075 says
  are byte-identical at the HTTP endpoints and may differ here.
- **Nothing about what "disconnect" meant.** George used the Plex app's own
  control; whether force-quitting the app, locking the phone, or leaving the
  network look the same to this count is unmeasured.
- **Nothing about the 14 s.** He also said *"takeover is instant after the 14
  seconds"*, which is the measured hold behaving exactly as
  [Finding 085](085-the-takeover-gaps-and-the-controls.md) describes.
