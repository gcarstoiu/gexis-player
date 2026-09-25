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


# ---------------------------------------------------------------------------
# The document, against the objects it is derived from.
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "PLUGIN-CONTRACT.md"


def test_the_contract_document_exists():
    """Phase 10 criterion 1 is "contract documented and versioned". Without
    the file, every assertion below passes by checking nothing."""
    assert CONTRACT.is_file()
    assert "**Version:** `1`" in CONTRACT.read_text()


def test_it_names_every_declared_field():
    """**The drift guard's other half** (ADR-0013 as amended). The defaults do
    not speak this protocol, so nothing exercises the two together; if
    `Capabilities` grows a field the document never mentions, a plugin author
    cannot know it exists."""
    text = CONTRACT.read_text()
    missing = [name for name in DECLARED if name not in text]
    assert not missing, f"the contract document never mentions: {missing}"


def test_it_names_every_method_a_plugin_has_to_answer():
    text = CONTRACT.read_text()
    missing = [name for name in REQUIRED | OPTIONAL if name not in text]
    assert not missing, f"the contract document never mentions: {missing}"


#: Two attributes are shorter on the wire than in Python. Written out rather
#: than derived, so a rename on either side has to be made deliberately here.
WIRE_NAME = {"renderer_id": "id", "unit_name": "unit"}


def test_it_names_every_attribute():
    text = CONTRACT.read_text()
    missing = [
        name for name in ATTRIBUTES
        if f"`{WIRE_NAME.get(name, name)}`" not in text
    ]
    assert not missing, f"the contract document never mentions: {missing}"


def test_it_carries_the_transport_decision_rather_than_restating_it():
    """A specification that re-argues its own transport is one that will
    disagree with the record. It cites ADR-0084 instead."""
    text = CONTRACT.read_text()
    assert "0084-plugins-speak-json-lines-over-a-unix-socket.md" in text
    assert "/run/gexis/plugins.sock" in text


def test_it_is_frozen_and_says_what_that_cost():
    """**This assertion replaced its own tripwire on 2026-09-25**, which read
    `"draft, not frozen" in text` and said changing it should be a deliberate
    act with the Beszel agent already written. It was: both plugins exist, and
    George said *"Freeze now and do metadata. If we need to adapt it's v2."*

    What is asserted now is the thing that matters going forward - that the
    document states a version discipline, because within v1 fields may be added
    and never removed or repurposed, and a plugin in another repository is
    entitled to rely on that.
    """
    text = CONTRACT.read_text()
    assert "frozen 2026-09-25" in text.lower()
    assert "draft, not frozen" not in text
    # The rule a frozen version is worth nothing without.
    assert "added and never removed or repurposed" in text


def test_a_service_plugin_is_expressible():
    """`docs/DEVELOPMENT.md`: "If the contract cannot express that, it is a
    renderer API wearing a plugin's name." The `kind` split is what makes a
    non-renderer sayable, so it is asserted rather than assumed."""
    text = CONTRACT.read_text()
    assert '`service`' in text
    assert '`renderer`' in text
