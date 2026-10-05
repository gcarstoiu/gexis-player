"""ADR-0055 — which output the device plays to.

Measured on `gexis`, 2026-09-23: four playback outputs, and **two of them
have no volume control at all**. Choosing one of those *is* ADR-0046's
fixed output, which is why 9i and 9j were one conversation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import pytest

from gexis_core import outputs
from gexis_core.outputs import Output


@pytest.fixture(autouse=True)
def _known_cards():
    """What each card takes, measured on `gexis` 2026-09-23, so the tests
    do not shell out to `aplay`."""
    outputs._needs_plug.clear()
    outputs._needs_plug.update(
        {"sndrpihifiberry": False, "Headphones": False, "vc4hdmi0": True, "vc4hdmi1": True}
    )
    yield
    outputs._needs_plug.clear()

HIFIBERRY = Output(card="sndrpihifiberry", label="HiFiBerry DAC+ HD", control="DAC")
JACK = Output(card="Headphones", label="Headphones (3.5 mm)", control="PCM")
HDMI1 = Output(card="vc4hdmi0", label="HDMI 1", control=None, connected=True)
HDMI2 = Output(card="vc4hdmi1", label="HDMI 2", control=None, connected=False)
ALL = [HDMI1, HDMI2, JACK, HIFIBERRY]


class TestTheConfigItWrites:
    def test_the_template_has_not_drifted_from_the_image(self):
        """`output.conf` stops being a static image file and becomes
        something the daemon writes, so the two copies can disagree
        silently. They are compared here rather than discovered to differ
        on a device - the same failure mode as `test_registry_wiring`,
        which this project hit twice in one afternoon."""
        shipped = (
            Path(__file__).resolve().parents[2]
            / "image" / "stage-gexis" / "00-alsa" / "files" / "output.conf"
        )
        assert outputs.render(HIFIBERRY, plug=False).rstrip() == shipped.read_text().rstrip()

    def test_the_waiting_head_follows_the_card_on_both_chains(self, tmp_path):
        """**ADR-0095.** `output_wait` is `output` with an open that waits, so
        it must follow the chosen output exactly as `output` does - metered or
        converted - and must never be what `configured()` reads back."""
        for output, plug in ((JACK, False), (HDMI1, True)):
            rendered = outputs.render(output, plug=plug)
            assert f"slave.pcm {{ type hw card {output.card} nonblock 0 }}" in rendered
            assert rendered.index("pcm.output {") < rendered.index("pcm.output_wait {")
            conf = tmp_path / f"{output.card}.conf"
            conf.write_text(rendered)
            assert outputs.configured(conf) == output.card

    def test_the_card_lands_in_both_places(self):
        """The PCM's slave *and* the ctl's card. Missing the second is the
        bug ADR-0009's own comment in this file is about: squeezelite would
        resolve its mixer against nothing and fall back to software
        volume."""
        rendered = outputs.render(JACK, plug=False)
        assert 'slave.pcm "hw:Headphones"' in rendered
        assert "card Headphones" in rendered

    def test_the_meter_scope_survives_the_switch(self):
        """ADR-0011: the visualiser taps whatever the slave becomes,
        because the scope wraps it. If a switch dropped the scope the
        meters would go dead on every output but the first."""
        for output in (HIFIBERRY, JACK):
            rendered = outputs.render(output, plug=outputs._needs_plug[output.card])
            assert "scopes.0 peppyalsa" in rendered
            assert "/run/gexis/meter.fifo" in rendered

    def test_a_converted_chain_carries_no_meter(self):
        """**George, 2026-09-23: "Spotify disconnects immediately when I get
        to play something via hdmi 1. Lms plays but I am not hearing
        anything."** Neither was what it looked like. go-librespot was
        *aborting* - `pcm_meter.c:1222: snd_pcm_scope_s16_get_channel_
        buffer: Assertion 's16->buf_areas' failed` - and squeezelite was
        logging `_write_frames:615 mmap_commit error` ten times a second
        and playing silence. ALSA's `type meter` and the peppyalsa scope
        come apart when there is a `plug` under them.

        **The cost is the visualiser's levels on that output**, which is
        cheaper than a renderer that aborts, and is stated in the row."""
        for output in (HDMI1, HDMI2):
            rendered = outputs.render(output, plug=True)
            assert "type meter" not in rendered
            assert "scopes.0 peppyalsa" not in rendered

    def test_writing_the_same_config_twice_is_not_a_change(self, tmp_path):
        """The caller restarts every renderer on a change, so 'changed' has
        to mean changed."""
        path = tmp_path / "output.conf"
        assert outputs.write(HIFIBERRY, path) is True
        assert outputs.write(HIFIBERRY, path) is False
        assert outputs.write(JACK, path) is True


class TestChoosingOne:
    def test_a_stored_choice_is_honoured(self):
        assert outputs.resolve("Headphones (3.5 mm)", ALL) is JACK

    def test_an_output_that_is_gone_falls_back_to_one_that_can_be_heard(self):
        """**ADR-0055 §3, George: "Agreed".** Pull the HAT and the stored
        value names a card that no longer exists. The answer is the first
        output *with a volume control* - never a silent one. A device that
        comes back quiet is recoverable; one that comes back mute looks
        broken."""
        assert outputs.resolve("HiFiBerry DAC+ HD", [HDMI1, HDMI2, JACK]) is JACK

    def test_with_nothing_but_silent_outputs_it_still_chooses_something(self):
        assert outputs.resolve("HiFiBerry DAC+ HD", [HDMI1, HDMI2]) is HDMI1

    def test_nothing_at_all_is_none_rather_than_a_crash(self):
        assert outputs.resolve("anything", []) is None

    def test_no_stored_choice_picks_an_audible_default(self):
        assert outputs.resolve(None, ALL) is JACK

    def test_a_card_id_is_accepted_as_well_as_a_label(self):
        assert outputs.resolve("sndrpihifiberry", ALL) is HIFIBERRY


class TestTheDisconnectedNote:
    """George, 2026-09-23: *"Offer all, but maybe it clears that the one
    that is not connected looks disabled or has a note saying that nothing
    is connected."*"""

    def test_an_unplugged_output_says_so(self):
        assert HDMI2.option == "HDMI 2 — nothing connected"
        assert HDMI1.option == "HDMI 1"

    def test_the_note_does_not_orphan_a_stored_choice(self):
        """**The suffix is display only.** Storing the option string and
        then plugging a cable in changes the label; matching on what comes
        before the suffix means the choice survives it."""
        assert outputs.resolve("HDMI 2 — nothing connected", ALL) is HDMI2
        plugged = Output(card="vc4hdmi1", label="HDMI 2", control=None, connected=True)
        assert outputs.resolve("HDMI 2 — nothing connected", [plugged]) is plugged


def test_our_own_dummy_cards_are_never_offered():
    """They have a mixer and no audio path, which is exactly the shape that
    would otherwise pass every test above."""
    assert "gexislmsvol" in outputs.OURS and "gexisbtvol" in outputs.OURS


class TestNothingStoredChangesNothing:
    """**The bug this class exists for**, caught on the device within
    seconds of deploying: with no stored choice, `resolve` fell straight
    through to "the first output with a volume control" — which on this
    device is the Pi's own headphone jack, because `aplay -l` lists card 4
    before the HiFiBerry's card 5. A daemon restart moved the device off
    the HAT and logged it afterwards.

    A rule for recovering from missing hardware must not fire when no
    hardware is missing.
    """

    def test_the_configured_card_wins_when_nothing_is_stored(self):
        assert outputs.resolve(None, ALL, current="sndrpihifiberry") is HIFIBERRY

    def test_a_stored_choice_still_beats_the_configured_one(self):
        assert outputs.resolve("HDMI 1", ALL, current="sndrpihifiberry") is HDMI1

    def test_the_fallback_is_only_for_when_both_are_gone(self):
        """Stored and configured both name the HAT; the HAT is gone."""
        assert outputs.resolve(
            "HiFiBerry DAC+ HD", [HDMI1, HDMI2, JACK], current="sndrpihifiberry"
        ) is JACK

    def test_an_unreadable_config_is_not_a_reason_to_move(self, tmp_path):
        assert outputs.configured(tmp_path / "nope.conf") is None

    def test_the_configured_card_is_read_back_out_of_what_was_written(self, tmp_path):
        path = tmp_path / "output.conf"
        outputs.write(JACK, path)
        assert outputs.configured(path) == "Headphones"


class TestTheConversionLayer:
    """**George switched to HDMI 1 and both renderers refused to play**
    (2026-09-23). squeezelite: *"unable to open audio device with any
    supported format"*, every five seconds; go-librespot: *"Device or
    resource busy"*, which was the first one's retry loop holding the card.

    `hw:vc4hdmi0` offers exactly one format, `IEC958_SUBFRAME_LE`, because
    the Pi carries HDMI audio as an IEC958 subframe. Renderers send
    `S16_LE` or wider. `hw:` can never open it.
    """

    def test_hdmi_gets_a_conversion_layer(self):
        rendered = outputs.render(HDMI1, plug=True)
        assert "type plug" in rendered
        assert 'slave.pcm "hw:vc4hdmi0"' in rendered

    def test_the_dac_does_not(self):
        """**ADR-0009: `type plug` must not appear in this chain** - it
        converts silently and would defeat the bit-perfect claim without
        any error. The prohibition is kept where it means something."""
        rendered = outputs.render(HIFIBERRY, plug=False)
        assert 'slave.pcm "hw:sndrpihifiberry"' in rendered
        assert "plug" not in rendered

    def test_the_headphone_jack_does_not_either(self):
        assert "plug" not in outputs.render(JACK, plug=False)

    def test_a_card_that_cannot_be_asked_keeps_hw(self, monkeypatch):
        """ADR-0009 would rather fail loudly than convert quietly, so an
        unanswered question is not a licence to insert a converter."""
        outputs._needs_plug.clear()

        def boom(*a, **k):
            raise OSError("no aplay here")

        monkeypatch.setattr(outputs.subprocess, "run", boom)
        assert outputs.needs_plug("whatever") is None

    def test_the_answer_is_asked_for_once(self, monkeypatch):
        outputs._needs_plug.clear()
        calls = []

        class Result:
            stderr = "FORMAT:  IEC958_SUBFRAME_LE\n"

        monkeypatch.setattr(outputs.subprocess, "run", lambda *a, **k: (calls.append(a), Result())[1])
        assert outputs.needs_plug("vc4hdmi9") is True
        assert outputs.needs_plug("vc4hdmi9") is True
        assert len(calls) == 1


class TestAnUnanswerableCard:
    """**"No answer" had been folded into "needs nothing", and it wrote
    HDMI back into the config with no conversion layer twice** (2026-09-23).

    Asking a card what formats it takes means *opening* it, and a card a
    renderer is still holding answers nothing. The first version cached
    that nothing as False; the second stopped caching it but still
    returned False, so the startup reconciliation rewrote a working config
    into a broken one.
    """

    def test_unknown_is_none_not_false(self, monkeypatch):
        outputs._needs_plug.clear()

        class Busy:
            stderr = "aplay: main:850: audio open error: Device or resource busy\n"

        monkeypatch.setattr(outputs.subprocess, "run", lambda *a, **k: Busy())
        assert outputs.needs_plug("vc4hdmi0") is None

    def test_unknown_is_not_remembered(self, monkeypatch):
        """Or one busy moment decides the card for ever."""
        outputs._needs_plug.clear()

        class Busy:
            stderr = ""

        monkeypatch.setattr(outputs.subprocess, "run", lambda *a, **k: Busy())
        outputs.needs_plug("vc4hdmi0")
        assert "vc4hdmi0" not in outputs._needs_plug

    def test_a_config_that_cannot_be_computed_is_not_written(self, tmp_path, monkeypatch):
        """The one that matters: a working file is left working."""
        outputs._needs_plug.clear()
        path = tmp_path / "output.conf"
        path.write_text("something that works\n")

        class Busy:
            stderr = ""

        monkeypatch.setattr(outputs.subprocess, "run", lambda *a, **k: Busy())

        assert outputs.write(HDMI1, path) is False
        assert path.read_text() == "something that works\n"


class TestTheBallisticsAreInTheConfig:
    """ADR-0058: two of the three numbers George asked for are peppyalsa's,
    and peppyalsa is configured in `output.conf`."""

    def test_the_defaults_are_what_the_image_ships(self):
        from gexis_core import outputs

        rendered = outputs.render(HIFIBERRY, plug=False)
        assert f"decay_ms {outputs.DECAY_MS}" in rendered
        assert f"smoothing_factor {outputs.SMOOTHING_FACTOR}" in rendered

    def test_a_tuning_reaches_the_file(self):
        from gexis_core import outputs

        rendered = outputs.render(
            HIFIBERRY, plug=False, tuning=outputs.Tuning(decay_ms=900, smoothing_factor=72)
        )
        assert "decay_ms 900" in rendered
        assert "smoothing_factor 72" in rendered
        # and nothing else moved
        assert 'slave.pcm "hw:sndrpihifiberry"' in rendered
        assert "spectrum_size 30" in rendered

    def test_a_converted_chain_defines_the_scope_but_attaches_nothing(self):
        """No meter on a `plug` chain, so the tuning reaches a scope that is
        never used. It is still written, because the block is the same text
        either way - what changes is the `scopes.0` line that hangs it on
        the PCM."""
        from gexis_core import outputs

        rendered = outputs.render(
            HIFIBERRY, plug=True, tuning=outputs.Tuning(decay_ms=900, smoothing_factor=72)
        )
        assert "scopes.0 peppyalsa" not in rendered
        assert "type meter" not in rendered
        assert "decay_ms 900" in rendered


class TestTheAlsaDefault:
    """**ADR-0085: the ALSA default is our output.**

    It exists for software that enumerates its own device list and cannot be
    told about `pcm.output` - Plexamp is the case that found it
    (Finding 077). The risk is that it quietly stops being installed, or that
    somebody "tidies" it into `output.conf`, which is regenerated on every
    output change and would drop it.
    """

    @staticmethod
    def _repo():
        from pathlib import Path
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def _conf():
        return (TestTheAlsaDefault._repo() / "image" / "stage-gexis" / "00-alsa"
                / "files" / "zz-gexis-default.conf")

    def test_the_default_points_at_our_output_by_name(self):
        text = self._conf().read_text()
        assert 'pcm.!default "output"' in text

    def test_it_adds_no_plug_anywhere(self):
        """A `plug` on top would silently convert rather than let the card
        refuse, on a device whose point is not converting - and a `plug`
        *under* the meter breaks the peppyalsa scope outright."""
        body = [
            line.split("#")[0]
            for line in self._conf().read_text().splitlines()
        ]
        assert not any("plug" in line for line in body)

    def test_it_never_names_a_card(self):
        """ADR-0009. The whole point is that software which cannot be told
        about `output` stops needing to know an index."""
        body = "\n".join(
            line.split("#")[0] for line in self._conf().read_text().splitlines()
        )
        assert "hw:" not in body

    def test_the_image_installs_it_separately_from_output_conf(self):
        # ADR-0107: gexis-system installs it, as its own file - output.conf
        # is only a default placed once, because an output change rewrites it.
        build = (self._repo() / "packaging" / "system" / "build.sh").read_text()
        assert 'zz-gexis-default.conf" /etc/alsa/conf.d/zz-gexis-default.conf' in build
        assert '"$DEF/output.conf"' in build

    def test_the_regenerated_output_conf_does_not_carry_it(self):
        """If this ever moves into the template, an output change silently
        deletes it - `outputs.write` rewrites that whole file."""
        from gexis_core.outputs import Output, render
        rendered = render(Output(card="sndrpihifiberry", label="DAC", control="Master"), plug=False)
        assert "!default" not in rendered


def test_the_outputs_are_worked_out_again_only_when_something_changed(tmp_path, monkeypatch):
    """2026-10-05: every GET /settings listed the outputs - `aplay` and an
    `amixer` per card, 50 ms on the player. Asked again when the cards,
    an HDMI connection or the chosen board change, so a cable plugged in
    still shows without a restart."""
    from gexis_core import boards, outputs

    cards = tmp_path / "cards"
    cards.write_text(" 0 [vc4hdmi0       ]: vc4-hdmi\n")
    ran = []

    def run(*args):
        ran.append(args[0])
        if args[0] == "aplay":
            return "card 0: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]\n"
        return ""

    monkeypatch.setattr(outputs, "CARDS", cards)
    monkeypatch.setattr(outputs, "_run", run)
    monkeypatch.setattr(outputs, "DRM", tmp_path / "drm")
    monkeypatch.setattr(outputs, "_DISCOVERED", {})
    monkeypatch.setattr(boards, "hat_product", lambda: None)
    first = outputs.discover(chosen_board="none")
    again = outputs.discover(chosen_board="none")
    assert [o.card for o in again] == [o.card for o in first] == ["vc4hdmi0"]
    assert ran.count("aplay") == 1
    outputs.discover(chosen_board="iqaudio-dacplus")  # a board chosen
    assert ran.count("aplay") == 2
    cards.write_text(cards.read_text() + " 1 [sndrpihifiberry]: RPi-simple\n")  # a card arrives
    outputs.discover(chosen_board="iqaudio-dacplus")
    assert ran.count("aplay") == 3
