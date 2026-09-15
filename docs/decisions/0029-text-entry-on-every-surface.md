# ADR-0029 — Text entry is available on every surface

**Status:** Accepted
**Date:** 2026-09-13
**Raised by:** George
**Amends:** [0022](0022-settings.md) ("Text entry is remote-browser only",
superseded), [0020](0020-library-browse-tree.md) (one row of the cross-cutting
table)

## Decision

**A text field, where one exists, appears and is editable on both the panel and
a remote browser.** Neither surface gets a different version of the control.

**No on-screen keyboard is built.** On the panel, text entry requires an
external USB keyboard.

**A focused text field with no keyboard attached does nothing, and says
nothing** — no hint, no keyboard-presence detection, no "edit this from a
browser instead" pointer. George, 2026-09-13: *"nothing, we accept it."*

## Why

ADR-0022 made text settings remote-browser-only and required the panel to show
them read-only *with a statement of where to change them*. That is two
presentations of every text setting and a component that has to know which
surface it is rendering on. The rule costs more implementation than the problem
it solves, and the escape hatch — plug in a keyboard — already exists and needs
no code.

The original rationale (*"an on-screen keyboard at 1280x800 is substantial work,
and typing a URL on a panel in a hi-fi rack is unpleasant"*) is not disputed and
is not overturned. What changes is the conclusion drawn from it: the answer to
"no on-screen keyboard" is a keyboard port, not a second UI mode.

## Scope — what this does not change

**The designs will contain no text-entry widgets** (George, 2026-09-13). So this
record removes a constraint rather than adding a surface, and no text input is
expected on the panel in the near term. Text *values* that matter — LMS address,
device name, idle URL — are still displayed on the panel; only the rule
restricting where they may be *edited* is retired.

**Library search (ADR-0020, Phase 7) is not decided here.** Its row in that
record's table still reads "shown, not editable", and how search takes input
without a text-entry widget is an open question for Phase 7. Marked `[?]`.

**The inventory in ADR-0022 is unchanged.** This adds no setting and removes
none; it changes only where an existing setting may be typed into.

## Accepted consequence

This is a knowing exception to ADR-0014's *"a next button that silently does
nothing is worse than no next button."* A text field tapped on a keyboard-less
panel is exactly that: a control that accepts focus and does nothing.

It is accepted because the case is narrow — the designs carry no text fields, so
the situation requires a field that does not currently exist plus a user who has
not attached a keyboard — and because the alternatives were each worse per the
decision above. If text fields do appear on the panel later, **re-open this**:
the cheap mitigation (a static line on the settings screen naming the keyboard
and the browser address, no detection required) was considered and declined
here, not overlooked.

## Effect on ADR-0020's cross-cutting rule

The rule itself stands:

> **If the capability does not exist, hide it. If it exists but cannot be
> operated here, show it and say where it can be.**

Its table loses one row. "Settings text field on the panel — shown, not
editable" is retired: the capability now exists on the panel, so the first
branch does not apply and the second no longer needs to. The search row keeps
the second branch alive pending Phase 7.

## Effect on ADR-0022's first-boot blocker

ADR-0022 recorded: *"Wi-Fi credentials cannot be entered remotely, because
without Wi-Fi there is no remote browser."*

This record **softens that but does not close it.** A keyboard on the panel is
in principle a route in, but nothing designed today provides a pre-network
settings surface to type into, and the designs carry no text-entry widget to
type into either. The blocker still belongs to ADR-0021, and the candidate
approaches listed in ADR-0022 (pre-seeding at flash time, a temporary access
point, a one-off local-entry exception) are still the live options. In practice
`firstrun.sh` pre-seeding is what the image does today.
