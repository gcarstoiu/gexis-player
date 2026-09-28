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

**Repository independence.** A plugin in a different repository makes the
contract real rather than a convention inside one codebase.

## Consequences

- Costs an IPC layer that in-process modules would not need.
- Plugin lifecycle becomes the supervisor's problem: start, stop, health, and
  what happens when a plugin stops responding.
- The contract must be versioned, because plugins in other repositories will lag
  the core.
