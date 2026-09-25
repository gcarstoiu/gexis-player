# ADR-0077 — A source that is off is not running

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0013](0013-defaults-implement-public-contract.md)
(the three defaults are plugins, and a plugin does not need to know it can be
switched off), [ADR-0010](0010-arbitration-slot-model.md) /
[ADR-0027](0027-lms-power-as-arbitration-mechanism.md) (arbitration), ADR-0022's inventory
(`lms_enabled`, `spotify_enabled`, `bt_enabled`, `headless`),
[Finding 068](../findings/068-what-is-left-unwired-in-settings.md) (these four
are what is left of Phase 9 criterion 1)

## Context

Four rows in Settings claim to switch something off and switch nothing off.
Three of them are the `Enabled` toggle under LMS, Spotify Connect and
Bluetooth; the fourth is `headless`, which says *"Disables the local screen
entirely"* and does not.

They are the last unwired rows with a mark of `R` — recorded in the design —
and they are the four that need a decision rather than a callback, because
"off" has more than one plausible meaning. A toggle could mean:

- the panel stops offering it, and everything keeps running behind that;
- the daemon stops arbitrating it, and the renderer keeps running;
- the renderer is not running, and comes back when the row comes back.

The first is a lie with a switch on it. A phone that is still advertised as a
Spotify Connect target still takes the device when somebody presses play on
it, and the panel then shows a source the user turned off. The second is
quieter and still wrong: squeezelite is still a player on the LMS server, so
the device is still in the app's list, and a track sent to it plays into an
arbiter that has been told to ignore it.

## Decision

**Off means the renderer is not running, and the row survives a reboot.**

A source that is off, in full:

1. **Its unit is stopped and disabled** — `systemctl disable --now`. Disabled,
   not merely stopped: a row whose effect ends at the next boot is a row that
   lies the second time you look at it. On is `enable --now`, and both are
   idempotent.
2. **Its adapter is not watching.** The core stops running the adapter rather
   than asking the adapter to stop — see *The gate is in the core* below.
3. **The published state reports it unavailable**, so nothing in the panel or
   on a phone offers it.
4. **Arbitration refuses it.** `Supervisor.acquire` takes an `enabled`
   predicate and declines a renderer that is off, which covers every path into
   arbitration rather than the ones known today.

**Bluetooth is the radio, not just the audio path.** `bt_enabled` off powers
the adapter down (`Powered = false`) as well as stopping `bluealsa-aplay`, and
disables `gexis-bluetooth-setup.service` so a reboot does not unblock rfkill
and power it back on. A radio that is still discoverable while Bluetooth is
off is the worst of the three failures above: the phone pairs, connects, and
gets silence.

**`headless` turns off three units, not one.** `gexis-kiosk.service` is the
screen; `gexis-panel-warmup.service` exists only to read the kiosk's binaries
into the page cache and is pure boot cost without it; `gexis-peppy.service`
draws the visualiser, which has nowhere to draw. The core, the phone UI and
audio are untouched — headless is a device without a screen, not a device
without a player.

The kiosk unit's own `ExecStopPost` puts the console back out of graphics
mode, so nothing is left holding the framebuffer. **What is on that console
differs between a live change and a boot**, measured on the device 2026-09-25:
the kiosk's `Conflicts=getty@tty1.service` stops the getty when the kiosk
starts and systemd does not start it again when the kiosk stops, so turning
`headless` on mid-session leaves tty1 blank. `getty@tty1` stays *enabled*, so
a boot with `headless` already on reaches a login prompt normally.

## Rationale

### The gate is in the core

The obvious place for "don't run while off" is inside each adapter's retry
loop, and it is the wrong one. ADR-0013 says the three defaults implement the
public plugin contract and are not special-cased; a plugin that had to read a
settings row named after itself to know whether to run would put that row in
the contract. Whether a renderer runs at all is the core's business.

So the three `adapter.run(...)` coroutines are no longer gathered directly.
Each is wrapped in a supervising task that starts the adapter's run while the
row is on and cancels it when the row goes off. All three `run()` methods
catch `Exception` and not `BaseException`, so cancellation propagates through
their retry loops rather than being swallowed and retried, and each holds its
connection in an `async with` that closes on the way out.

Cancelling also settles a smaller thing that would otherwise be permanent
noise: with `go-librespot` stopped, the Spotify adapter's watch retries every
five seconds and logs a warning each time — about seventeen thousand a day
saying the renderer the user switched off is not answering.

### Disabled, not masked

`systemctl mask` is the stronger tool and would also stop a dependency pulling
the unit in. It is rejected here because masking is what an operator does to a
unit that must never run, and it leaves a symlink to `/dev/null` that a later
image update has to reason about. `disable` is the reversible form of the same
statement, and nothing in this image pulls these units in as a dependency.

### Rejected: hide it in the panel and leave it running

Considered because it is a one-line change in the UI and because a row that
only affects what is offered can never break audio. Rejected: the sources are
reachable without the panel. Spotify Connect is advertised on the network,
squeezelite is a player in the LMS app, and a Bluetooth device is in a phone's
settings screen. A switch that only the panel honours is not a switch.

### Rejected: stop the unit and leave it enabled

Considered for `headless` in particular, on the grounds that a device that
cannot be reached is less bad if a reboot brings the screen back. Rejected for
the same reason as above and one more: the row is reversible from a phone
without a reboot, so there is a way back that does not involve the row
un-setting itself. Measured on the device 2026-09-25: **12 s from the write to
the panel gone, 20 s to the panel back.**

### The unit calls are off the event loop

`systemctl disable --now go-librespot.service` took **7.0 s** on the device,
all of it stopping the unit. Run inline that is seven seconds in which the
daemon answers nothing - no state pushes, no panel, no phone - for the one
call whose whole purpose is to take time. So `set_unit_enabled` goes through
`asyncio.to_thread`. Measured after: the row's own `PUT` returns in **18 ms**
and the next request is answered in **5 ms** while the unit is still stopping.

## Consequences

- Turning `headless` on from the panel closes the panel. That is the row doing
  what it says. It is reversible from a phone, and only from a phone.
- Turning a renderer off while it is the active one stops its audio. The
  release path is the ordinary one; nothing special-cases the source of the
  stop.
- A renderer that is off reports unavailable, which is the same signal the
  panel already uses for a renderer that cannot be reached. Off and broken
  look alike in the state payload. The row is what distinguishes them, and it
  is on the same screen.

## What this does not settle

- **Whether the Library, Browse and Radio screens go with `lms_enabled`.**
  They are LMS's screens and they read the server directly rather than through
  the renderer, so they keep working with LMS off — a library you can browse
  and cannot play to. **A product decision for George**, raised separately,
  not guessed at here.
- **Whether turning `headless` on should hand tty1 back to a getty.** Today
  the screen goes blank until the next boot, which then shows a login prompt
  (above). Starting the getty would make the two agree, and it is a keyboard
  on an appliance - **George's call**, not made here.
- **Whether the rows should warn before acting.** `headless` in particular is
  a toggle that removes the surface it was pressed on. Left as it is, on the
  grounds that the note under the row says what it does.

## Reversal conditions

If an image update ever pulls one of these units in as a dependency of
something else, `disable` stops being sufficient and the decision above
becomes `mask`.
