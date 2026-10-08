# ADR-0129 — A service's switch says whether it is connected

**Status:** **Accepted** — George, 2026-10-08: *"Can you also add a status to
the beszel client? Connected or not connected or pending, with the
corresponding icons for it in green, red and orange?"*
**Builds on:** [ADR-0087](0087-the-beszel-agent-is-the-first-service-plugin.md)
(the Beszel agent, a service plugin),
[ADR-0119](0119-plexamp-is-claimed-from-settings.md) (a row's `status`, which a
plugin reports).

## Context

The Beszel agent's switch said only that it was on. On guestpi on 2026-10-08 a
pasted Hub public key kept the agent from connecting, and nothing on the
device said so: the owner had to look at the hub. The day before, a row
message was added for a unit that has *failed*
(`"{name} could not start. Check its settings."`). But an agent that runs and
keeps retrying never fails, so that message doesn't cover it.

## Decision

1. **Beside the switch of a switched-on service that connects somewhere**:
   - **Connected**: green, with a tick;
   - **Connecting**: orange, a dot that pulses;
   - **Not connected**: red, with a cross.

   Nothing is shown while the service is switched off.
2. **The core reads it; the plugin does not report it.** A service holding an
   established TCP connection off this device, by the user its unit runs as,
   is *Connected*. A running service without one is *Connecting* for 60 s
   (since it was switched on, started, or last connected), then *Not
   connected*. A failed unit is *Not connected* at once.
   - It is read from the kernel's table (`/proc/net/tcp`, `tcp6`), not from
     the service's log. Upstream's log wording can change with any version:
     Beszel went from 0.20 to 0.21 the same day.
3. **A manifest asks for it with `"connection": true`.** It is honoured only
   on a `service` plugin, and only on the player's own plugins. An uploaded
   plugin runs as a temporary user made for each run (ADR-0106), so the
   core has no fixed user to look for. Beszel's manifest sets it.
4. **It is the row's `indicator`, separate from its `status`** (ADR-0119):
   - `status` is what a plugin says about its own row. Plexamp's `failed`
     still says *Claimed*, so `status` can't carry a red *Not connected*
     without changing what it means for every plugin.
   - The two show side by side: a failed unit has the orange *could not
     start* note under its name and the red *Not connected* beside its
     switch.
5. **No setting.** Nothing to choose; no ADR-0022 row.

## Limits

- **Coarse:** an open connection counts as connected. The hub checks the
  agent's key after the connection opens, and a refused key closes it within
  a second or two. That is shorter than the core's 10-second look, so a bad
  key reads *Not connected* after the grace, but a look could land inside
  that window and restart the 60 s.
- **One process per user:** a service whose user holds other connections off
  the device (an update check, say) would read *Connected* from those. The
  Beszel agent's user holds none.

## Built (2026-10-08, on `phase-13d`)

- `connections.py`:
  - `established(uid)` reads the kernel's table, skipping listening,
    closing and loopback entries;
  - `reading(...)` turns the unit's state into an indicator;
  - `unit_uid(unit)` comes from `systemctl show -p User`.
- `__main__._follow_service_plugins` looks every 10 s (it was 15 s) and calls
  `Settings.indicate(row, tone, text)`.
- `plugins.Plugin.connection`; the Beszel manifest sets it. Its package goes
  to `0.21.0-2`, because the manifest changed (LESSONS 53).
- `Settings.svelte`: the `.ind` indicator. `tokens.css`: `--accent-ok`
  `#7fd58e` and `--accent-bad` `#ee7b70`; orange is the existing
  `--accent-warn`.
- Checked in a browser on the panel (1280 × 800) and on a phone (412 px):
  all three states, with nothing wider than the screen.
