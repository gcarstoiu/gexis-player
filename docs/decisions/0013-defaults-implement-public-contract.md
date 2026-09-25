# ADR-0013 — Default renderers implement the public plugin contract

**Status:** Accepted, **amended 2026-09-25** — the defaults stay in the core
process, so they are the contract's *source* rather than its *consumers*. See
*Amendment* below.
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

## Amendment, 2026-09-25 — the defaults are the contract's source, not its consumers

**George's decision**, taken when Phase 10 was planned: LMS, Spotify and
Bluetooth **stay in the core process**, against `adapters/base.py`'s abstract
class, and are not ported to the IPC contract ADR-0016 defines for plugins.

**That makes the sentence above literally untrue**, and saying so is the point
of this amendment. *"The three default renderers are implemented against the
public plugin contract, not special-cased"* described an intent that the
implementation has not followed: the defaults are Python classes in one
process; plugins will be separate processes speaking a wire protocol. The
defaults are privileged.

**Why it is still the right call.** Porting a working renderer out of process
puts playback in the path of a contract experiment, and buys coverage that a
new plugin gives for free. Spotify was the candidate — it exercises nearly the
whole surface — and the answer was no: the thing being tested is the contract,
and testing it on the renderer that currently works is a trade of real risk
for a rehearsal.

**What the record now claims instead:**

> The three default renderers are the contract's **source**. Every field in it
> is derived from their actual behaviour, and nothing enters it that none of
> them needed. They are not its consumers, and no claim is made that they
> exercise it.

**And the guard that replaces the exercise.** With the defaults not using the
contract, the two can drift silently — the wire protocol gains a field the
adapters never grow, or `Capabilities` grows one the protocol never carries,
and nothing fails. So:

- **The wire schema is derived from `Capabilities` and `Adapter`**, not written
  beside them.
- **A test asserts the surface**, so a change to either side is a deliberate,
  visible act rather than a divergence nobody sees
  (`core/tests/test_contract_surface.py`, added with this amendment; it pins
  the surface today and becomes the derivation's check when the wire schema
  exists).

This is weaker than the original claim and it is honest about being weaker.
**The original argument still stands as the reason to watch for this**: if the
built-ins are privileged, the contract will be incomplete and the first
external plugin will discover it. The first external plugin is now a Beszel
agent, deliberately chosen because it is *not* a renderer
([Finding 075](../findings/075-what-moode-learned-about-plexamp.md) is why the
second one is a risk of its own).

## Consequences

- More work up front for the three defaults.
- The contract is exercised from day one rather than validated on paper.
- A renderer that cannot declare its capabilities cannot be added, which is a
  feature: the now-playing screen renders controls from the declaration, so an
  undeclared renderer would produce buttons that silently do nothing.
