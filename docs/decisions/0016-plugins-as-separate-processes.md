# ADR-0016 — Plugins are separate processes with an IPC contract

**Status:** Accepted
**Date:** 2026-09-04

## Context

Functionality is extended by plugins: additional renderers, idle screens,
meters, themes. Two structures were available — in-process modules loaded by the
core, or separate processes speaking a defined protocol.

## Decision

**Separate processes with an IPC contract.**

## Rationale

**Fault isolation.** A crashing plugin cannot take down playback or the UI. With
in-process modules it can. For a device whose primary job is to keep playing
music, this is the stronger argument.

**Language independence.** Plugins can be written in anything. The core is
Python (ADR-0017); in-process modules would bind every future renderer adapter
to that choice.

**Repository independence.** The Qobuz Connect plugin is planned for a private
repository. Qobuz Connect launched in May 2025 developed with StreamUnlimited,
and the official integration route is partnership, a proprietary SDK, and a
certification self-test — incompatible with a public repository. moOde reached
the same conclusion in May 2025 and found no FOSS-licensed code to integrate;
Volumio has it via partnership.

The unofficial route is reverse-engineered clients. `ahcm/qconnect` exists, and
roderickvd — maintainer of librespot and pleezer — has been reverse-engineering
the protocol since May 2025.

A plugin in a different repository makes the contract real rather than a
convention inside one codebase.

## Consequences

- Costs an IPC layer that in-process modules would not need.
- Plugin lifecycle becomes the supervisor's problem: start, stop, health, and
  what happens when a plugin stops responding.
- The contract must be versioned, because plugins in other repositories will lag
  the core.
- Qobuz Connect is delivered as an **optional plugin the user installs**, not
  something the base image ships.

## Note

Qobuz Connect does not replace Plexamp as the ADR-0008 reversal test.
`qconnect` is open source and writes to ALSA, so it is cooperative and will not
stress the PipeWire question at all. Plexamp keeps that role.
