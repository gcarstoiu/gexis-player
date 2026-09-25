# SPDX-License-Identifier: GPL-3.0-or-later
"""The plugin contract's surface, pinned.

**[ADR-0013](../../docs/decisions/0013-defaults-implement-public-contract.md)
as amended 2026-09-25.** The three default renderers stay in the core process,
so they are the contract's *source* and not its *consumers*: nothing about
them exercises the wire protocol a plugin will speak. That leaves the two free
to drift - the protocol grows a field the adapters never grow, or
`Capabilities` grows one the protocol never carries, and nothing fails.

**So the surface is written down once, here, and both sides derive from it.**
This file is the drift guard's first half: it pins what the contract is made
of *today*, from the defaults, before any of it is put on a wire. When the
wire schema exists (Phase 10) it is generated from these same objects and
checked against this list, so a change on either side is a deliberate act with
a failing test behind it rather than a divergence nobody sees.

**A failure here is not a bug.** It means the contract's surface changed. The
right response is to decide whether the wire protocol changes with it - and,
if the protocol is already versioned, whether that is a new version
(ADR-0016: *"the contract must be versioned, because plugins in other
repositories will lag the core"*).
"""
from __future__ import annotations

import dataclasses

from gexis_core.adapters.base import Adapter, Capabilities

#: Every field a renderer declares about itself. ADR-0013's "contract fields",
#: as actually derived from LMS, Spotify and Bluetooth - the record's own list
#: is the prose version of this and is explicitly "expected to grow".
DECLARED = {
    "audio_connection",
    "acquisition_events",
    "supports_artwork",
    "supports_sample_rate",
    "volume_managed",
    "volume_mechanism",
    "dummy_mixer_card",
    "volume_over_bluealsa",
    "controls",
}

#: What an adapter must implement. `run` carries both acquisition edges, so a
#: renderer that cannot raise `on_release` cannot satisfy this one - which is
#: not hypothetical: see Finding 075 on Plexamp.
REQUIRED = {"run", "release", "signal_stop"}

#: Implemented by the base class, overridden only where a renderer needs it.
#: Both exist because of a measured race, not a design (Finding 014 for
#: `device_freed`, Finding 013 §1 for `restart_after_release`).
OPTIONAL = {"device_freed", "restart_after_release"}

#: Set per adapter rather than declared in `Capabilities`, and part of the
#: contract all the same - a plugin has to supply every one of these.
ATTRIBUTES = {"renderer_id", "release_action", "capabilities", "unit_name",
              "release_ladder"}


def test_the_declaration_is_exactly_these_fields():
    assert {f.name for f in dataclasses.fields(Capabilities)} == DECLARED


def test_an_adapter_must_implement_exactly_these():
    assert set(Adapter.__abstractmethods__) == REQUIRED


def test_and_may_override_exactly_these():
    concrete = {
        name for name, value in vars(Adapter).items()
        if callable(value) and not name.startswith("_")
    }
    assert concrete - REQUIRED == OPTIONAL


def test_and_must_carry_exactly_these_attributes():
    assert set(Adapter.__annotations__) == ATTRIBUTES


def test_every_default_renderer_satisfies_it():
    """The claim the amendment keeps: the defaults are where the contract came
    from. If one of them stopped declaring a field, the field would have no
    source and should not be in the contract either."""
    from gexis_core.adapters.bluetooth import BluetoothAdapter
    from gexis_core.adapters.lms import LmsAdapter
    from gexis_core.adapters.spotify import SpotifyAdapter

    for adapter in (LmsAdapter, SpotifyAdapter, BluetoothAdapter):
        assert REQUIRED <= set(vars(adapter)), adapter.__name__
        for name in ("renderer_id", "release_action", "capabilities", "unit_name"):
            assert getattr(adapter, name, None) is not None, f"{adapter.__name__}.{name}"
        assert {f.name for f in dataclasses.fields(adapter.capabilities)} == DECLARED
