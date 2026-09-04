# ADR-0013 — Default renderers implement the public plugin contract

**Status:** Accepted
**Date:** 2026-09-04

## Context

squeezelite, go-librespot and Bluetooth ship in the base image. Everything else
is a plugin. The temptation is to wire the three defaults directly into the core
because they are known quantities, and define the plugin contract later for
third parties.

## Decision

**The three default renderers are implemented against the public plugin
contract, not special-cased.**

## Rationale

If the built-ins are privileged, the contract will be incomplete and the first
external plugin will discover it — at the point where fixing it is most
expensive.

Deriving the contract from three working implementations is the right order. The
error is skipping the derivation, not doing it late.

The Qobuz Connect plugin is planned for a separate private repository
(ADR-0016), which makes the boundary physical rather than a convention inside
one codebase. Any implicit coupling surfaces immediately.

## Contract fields

Minimum, as derived so far:

- **audio connection method** — always `output` (ADR-0009)
- **acquisition events** — one or more (ADR-0010)
- **release behaviour** — disconnect or pause (ADR-0010)
- **pause/disconnect capability**, with success and failure reporting
- **metadata capability declaration** — drives now-playing control rendering and
  skin field blanking
- **control surface** — what transport commands the renderer accepts

This list is expected to grow. It is derived, not designed.

## Consequences

- More work up front for the three defaults.
- The contract is exercised from day one rather than validated on paper.
- A renderer that cannot declare its capabilities cannot be added, which is a
  feature: the now-playing screen renders controls from the declaration, so an
  undeclared renderer would produce buttons that silently do nothing.
