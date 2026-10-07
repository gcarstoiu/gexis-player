# ADR-0128 — First setup installs the plugins and waits until the player has settled

**Status:** **Accepted** — George, 2026-10-07, on the list before the first
public release: *"Add step in setup for installing plugins and loading screen
on first setup for things to be downloaded and settled."* The three questions
answered the same day: *"1. All. No he can't. Leave it for settings but
inform user."*
**Builds on:** [ADR-0031](0031-first-boot-setup-access-point.md) and
[ADR-0104](0104-how-the-device-knows-it-needs-setup.md) (first-boot setup),
[ADR-0106](0106-plugins-you-install-and-update.md) (plugins installed and
updated), [ADR-0111](0111-skin-sets-follow-the-screen.md) (the skin pack for
the screen is downloaded).

## Context

Setup today has eight steps on the phone (Network, Name, Time, Output, Music,
Screen, Visualiser, Review). After Review the player joins the home network
and restarts into normal use - and then, unseen, it is still busy: the skin
pack for the screen downloads (ADR-0111), and any plugin the owner wants
(Lyrion Server, Plexamp, ...) is installed afterwards from Settings, one at a
time. On guestpi (2026-10-07) Spotify took a long time to connect right after
setup while this was going on.

## Decision

1. **A Plugins step in setup**, after Visualiser and before Review: the
   plugins this release ships, each with one line on what it is and its size,
   off unless chosen. The choice is saved like every other step.
2. **A settling screen after setup**, on the panel and on the phone while it
   is still connected: what is being downloaded and installed (the skin pack,
   each chosen plugin), each with its progress, then *Ready*. Music is offered
   only once it has settled.
3. **Nothing new to set:** the step's answer is the plugins themselves
   (ADR-0106); no ADR-0022 row.

## Decided (George, 2026-10-07)

1. **All the plugins the release ships** are offered in the step.
2. **The settling screen cannot be skipped**: music is offered once it has
   settled.
3. **A download that fails is left for Settings, and the owner is told**: the
   settling screen says which one did not finish and where to try again
   (*Settings → Plugins*), then finishes; the player does not retry on its own.

## Built (2026-10-07, on `phase-13d`)

- **The Plugins step** (`SetupPage.svelte`, `GET /setup/plugins`): every
  shipped plugin that is not a built-in source - Plexamp, the Lyrion Server,
  Beszel, the Beszel hub - each with one line from its manifest's new
  `summary` (or where it downloads from); a plugin with a notice shows it on
  the first tap and switches on at the second. No download size is shown:
  the pins do not carry one.
- **After the join** every offered plugin is switched on or off as chosen,
  explicitly - a plugin switch's default is on, which is not a choice - and
  `settling.json` records what to wait for.
- **The settling screen** (`SettlingScreen.svelte`, `settling.py`,
  `/state`'s `settling`): each download's progress; *Ready* for 4 s; a
  failure - or a download that has not started 10 minutes after setup - named
  with *Settings → Plugins*, then OK (`POST /settling/done`).
- **Music is not blocked** while it settles: the screen covers the panel (and
  shows on a phone), but a source can still take the device. Not yet seen on a
  freshly set-up device.
