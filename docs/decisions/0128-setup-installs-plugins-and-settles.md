# ADR-0128 — First setup installs the plugins and waits until the player has settled

**Status:** **Proposed** — George, 2026-10-07, on the list before the first
public release: *"Add step in setup for installing plugins and loading screen
on first setup for things to be downloaded and settled."* The questions under
*Owed* are his to answer before it is built.
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

## Decision (proposed)

1. **A Plugins step in setup**, after Visualiser and before Review: the
   plugins this release ships, each with one line on what it is and its size,
   off unless chosen. The choice is saved like every other step.
2. **A settling screen after setup**, on the panel and on the phone while it
   is still connected: what is being downloaded and installed (the skin pack,
   each chosen plugin), each with its progress, then *Ready*. Music is offered
   only once it has settled.
3. **Nothing new to set:** the step's answer is the plugins themselves
   (ADR-0106); no ADR-0022 row.

## Owed (George)

1. [?] Which plugins the step offers - all of those the release ships, or a
   chosen few (Lyrion Server, Plexamp)?
2. [?] Whether the settling screen may be skipped ("Use it now, finish in the
   background"), or always waits.
3. [?] What happens when a download fails on the first boot (no network yet,
   a slow line): retry on its own with the screen saying so, or continue and
   leave it to Settings.
