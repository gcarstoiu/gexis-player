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
    outputs._asked_of.clear()
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


# --- ADR-0124: software volume (Finding 115) ---------------------------------

def test_software_volume_puts_softvol_after_the_meter_on_a_dac():
    out = outputs.with_software_volume(outputs.Output(card="IQaudIODAC", label="IQaudIO Pi-DAC PRO", control="Digital"))
    conf = outputs.render(out, False)
    meter = conf.index("pcm.output {")
    assert 'slave.pcm { type copy slave.pcm "gexis_softvol" }' in conf[meter:conf.index("\n}", meter)], \
        "the meter sees the music as it arrives - through a copy, not the scaled samples (Finding 135)"
    assert 'type softvol\n    slave.pcm "hw:IQaudIODAC"' in conf
    assert 'control { name "Gexis Playback Volume" card IQaudIODAC }' in conf
    assert "gexis_softvol_wait" in conf and "nonblock 0" in conf, "squeezelite's waiting open has the same stage"
    assert conf.count('name "Gexis Playback Volume"') == 2, "one control for both"


def test_software_volume_goes_in_front_of_plug_on_hdmi_with_the_meter_first():
    """Finding 116: `meter → softvol → plug → card` plays, and the levels
    arrive; the meter straight over `plug` (HDMI on Fixed) still never."""
    out = outputs.with_software_volume(outputs.Output(card="vc4hdmi0", label="HDMI 1", control=None))
    conf = outputs.render(out, True)
    assert conf.startswith('pcm.output {\n    type meter\n    slave.pcm { type copy slave.pcm "gexis_softvol" }')
    assert 'slave.pcm { type copy slave.pcm "gexis_softvol_wait" }' in conf
    assert 'type softvol\n    slave.pcm { type plug slave.pcm "hw:vc4hdmi0" }' in conf
    assert 'slave.pcm { type plug slave.pcm { type hw card vc4hdmi0 nonblock 0 } }' in conf
    fixed = outputs.render(outputs.Output(card="vc4hdmi0", label="HDMI 1", control=None), True)
    assert "type meter" not in fixed.split("pcm_scope.peppyalsa")[0], "no meter straight over plug"


def test_the_software_scale_is_exact_and_tops_out_at_0_db():
    scale = outputs.SOFTVOL_SCALE
    assert (scale.raw_min, scale.raw_max, scale.db_min, scale.db_step) == (0, 360, -90.0, 0.25)
    assert scale.top == 360 and scale.db(360) == 0.0 and scale.raw(-15.5) == 298


def test_an_output_with_no_control_gains_one_and_keeps_its_card():
    hdmi = outputs.Output(card="vc4hdmi0", label="HDMI 1", control=None)
    soft = outputs.with_software_volume(hdmi)
    assert soft.control == "Gexis" and soft.software and soft.card == "vc4hdmi0" and soft.label == "HDMI 1"
    assert soft.option == hdmi.option, "offered and chosen under the same name"


def test_the_card_is_still_read_back_from_a_software_config(tmp_path):
    conf = tmp_path / "output.conf"
    conf.write_text(outputs.render(outputs.with_software_volume(
        outputs.Output(card="IQaudIODAC", label="x", control="Digital")), False))
    assert outputs.configured(conf) == "IQaudIODAC"
    conf.write_text(outputs.render(outputs.with_software_volume(
        outputs.Output(card="vc4hdmi0", label="HDMI 1", control=None)), True))
    assert outputs.configured(conf) == "vc4hdmi0", "through the plug, too"


async def test_a_change_of_output_lets_go_of_the_old_card_s_mixers():
    """George, 2026-10-07: *"Switching to hdmi and it stops working"* - the
    handle to `Gexis` stayed on the DAC, and the slider went on writing it."""
    from gexis_core import volume

    class Held:
        closed = False

        def close(self):
            self.closed = True

    held = Held()
    volume._MIXERS[("output", "Gexis")] = held
    await volume.forget_mixers()
    assert held.closed and volume._MIXERS == {}


def test_hdmi_stays_without_a_control_of_its_own_when_the_software_one_is_on_it(monkeypatch):
    """guestpi, 2026-10-07: HDMI took the software control for its own, and
    parked it at 0 dB under the level it had just been given."""
    contents = """numid=7,iface=MIXER,name='Gexis Playback Volume'
  ; type=INTEGER,access=rw---RW-,values=2,min=0,max=360,step=0
  : values=279,279
  | dBscale-min=-90.00dB,step=0.25dB,mute=0
"""
    monkeypatch.setattr(outputs, "_run", lambda *a: contents)
    assert outputs.playback_control("vc4hdmi0") == (None, None)


async def test_a_change_of_output_makes_libasound_read_its_configuration_again(monkeypatch):
    """A process keeps the ALSA configuration it loaded first; `output`
    meant the old card in the core after a switch (guestpi, 2026-10-07)."""
    import ctypes

    from gexis_core import volume

    freed = []
    monkeypatch.setattr(ctypes, "CDLL", lambda name: type("Lib", (), {
        "snd_config_update_free_global": staticmethod(lambda: freed.append(name))})())
    await volume.forget_mixers()
    assert freed == ["libasound.so.2"]


def test_hardware_gives_way_to_software_where_a_card_has_no_control():
    """ADR-0127 §2, at start-up, before the row is restricted."""
    from gexis_core.__main__ import volume_mode

    dac = outputs.Output(label="DAC", card="IQaudIODAC", control="Digital", scale=None)
    hdmi = outputs.Output(label="HDMI 1", card="vc4hdmi0", control=None, scale=None)
    assert volume_mode("Hardware", dac) == "Hardware"
    assert volume_mode("Hardware", hdmi) == "Software"
    assert volume_mode(None, hdmi) == "Software", "the default is Hardware"
    assert volume_mode("Fixed", hdmi) == "Fixed"
    assert volume_mode("Variable", dac) == "Hardware", "an unmigrated value"


def test_the_tested_optical_adapter_is_fixed_in_hardwares_place():
    """ADR-0155 decision 3: an output feeding a device with its own volume -
    the tested USB-to-optical adapter - plays at full level unless its owner
    chose Software; any other card with no control still gets Software."""
    from gexis_core.__main__ import volume_mode

    adapter = outputs.Output(label="Generic USB SPDIF Adapter", card="Adapter", control=None, usb_id="0bda:4e27")
    other = outputs.Output(label="Some USB DAC", card="AUDIO", control=None, usb_id="1234:5678")
    assert adapter.fixed_by_default and not other.fixed_by_default
    assert volume_mode("Hardware", adapter) == "Fixed"
    assert volume_mode(None, adapter) == "Fixed", "the row's default is Hardware"
    assert volume_mode("Software", adapter) == "Software", "an owner's own choice stands"
    assert volume_mode("Hardware", other) == "Software"


def test_a_usb_card_says_its_id_and_the_tested_adapter_is_marked(monkeypatch, tmp_path):
    """ADR-0155 decision 5: *Tested* by `vendor:product`, read from sysfs."""
    _plugged_dac(tmp_path, monkeypatch, card="Adapter")
    usb = tmp_path / "devices" / "usb1" / "1-1"
    (usb / "idVendor").write_text("0bda\n")
    (usb / "idProduct").write_text("4E27\n")
    assert outputs.usb_id("Adapter") == "0bda:4e27"
    assert outputs.usb_id("nothere") is None
    assert "0bda:4e27" in outputs.TESTED_USB and "0bda:4e27" in outputs.FIXED_BY_DEFAULT_USB
    assert outputs.Output(label="x", card="Adapter", control=None, state="Tested").shown_tested


# --- A USB DAC by its maker (George, 2026-10-12) ------------------------------

def _usb_card(tmp_path, number, manufacturer, product, usb=True):
    """/proc/asound/<id> -> cardN, and /sys/class/sound/cardN/device under a
    USB device holding `manufacturer` and `product`, as on sofapi."""
    proc, sound = tmp_path / "proc", tmp_path / "sound"
    proc.mkdir(exist_ok=True)
    root = tmp_path / ("usb1/1-1/1-1.1" if usb else "soc/sound")
    iface = root / "1-1.1:1.0"
    iface.mkdir(parents=True)
    (root / "manufacturer").write_text(manufacturer + "\n")
    (root / "product").write_text(product + "\n")
    (sound / f"card{number}").mkdir(parents=True)
    (sound / f"card{number}" / "device").symlink_to(iface)
    (proc / f"card{number}").mkdir()
    return proc, sound


def test_a_usb_dac_calling_itself_usb_audio_is_named_by_its_maker(tmp_path):
    """sofapi's SMSL: the driver says "USB Audio", the device "SMSL" and
    "SMSL USB AUDIO" - shown as "SMSL USB DAC"."""
    proc, sound = _usb_card(tmp_path, 6, "SMSL", "SMSL USB AUDIO")
    (proc / "AUDIO").symlink_to("card6")
    assert outputs.usb_name("AUDIO", sound, proc) == "SMSL USB DAC"


def test_a_usb_dac_with_a_model_name_keeps_it_once(tmp_path):
    proc, sound = _usb_card(tmp_path, 3, "Topping", "Topping D10s")
    (proc / "D10s").symlink_to("card3")
    assert outputs.usb_name("D10s", sound, proc) == "Topping D10s"


def test_a_card_not_on_usb_is_not_renamed(tmp_path):
    proc, sound = _usb_card(tmp_path, 5, "x", "y", usb=False)
    (proc / "sndrpihifiberry").symlink_to("card5")
    assert outputs.usb_name("sndrpihifiberry", sound, proc) is None
    assert outputs.usb_name("missing", sound, proc) is None


def test_discovery_shows_the_maker_and_still_finds_the_old_name(tmp_path, monkeypatch):
    """A choice stored as "USB Audio" before the rename still resolves."""
    from gexis_core import boards
    proc, sound = _usb_card(tmp_path, 6, "SMSL", "SMSL USB AUDIO")
    (proc / "AUDIO").symlink_to("card6")
    monkeypatch.setattr(outputs, "PROC_ASOUND", proc)
    monkeypatch.setattr(outputs, "SOUND", sound)
    monkeypatch.setattr(outputs, "_run", lambda *a: (
        "card 6: AUDIO [SMSL USB AUDIO], device 0: USB Audio [USB Audio]\n" if a[0] == "aplay" else ""))
    monkeypatch.setattr(outputs, "DRM", tmp_path / "drm")
    monkeypatch.setattr(boards, "hat_product", lambda: None)
    [usb] = outputs._discover("none", None)
    assert usb.label == "SMSL USB DAC" and usb.aka == "USB Audio"
    assert outputs.resolve("USB Audio — Detected", [usb], current=None) is usb


SMSL_STREAM = """SMSL SMSL USB AUDIO at usb-0000:01:00.0-1.1, high speed : USB Audio

Playback:
  Status: Stop
  Interface 1
    Altset 1
    Format: S32_LE
    Channels: 2
    Rates: 44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000, 705600, 768000
    Bits: 32
  Interface 1
    Altset 2
    Format: S32_LE
    Rates: 44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000, 705600, 768000
    Bits: 24
  Interface 1
    Altset 3
    Format: SPECIAL DSD_U32_BE
    Rates: 44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000, 705600, 768000
    Bits: 32
    DSD raw: DOP=0, bitrev=0
"""


def test_a_usb_dacs_details_are_what_it_reports(tmp_path):
    """sofapi's SMSL, as its sysfs and stream0 read on 2026-10-12."""
    proc, sound = _usb_card(tmp_path, 6, "SMSL", "SMSL USB AUDIO")
    (proc / "AUDIO").symlink_to("card6")
    (tmp_path / "usb1/1-1/1-1.1/speed").write_text("480\n")
    (proc / "card6" / "stream0").write_text(SMSL_STREAM)
    assert outputs.usb_details("AUDIO", sound, proc) == "USB 2.0 · up to 768 kHz / 32-bit · native DSD"


def test_a_small_usb_dac_says_less_and_capture_is_not_counted(tmp_path):
    proc, sound = _usb_card(tmp_path, 3, "C-Media", "USB Audio Device")
    (proc / "Device").symlink_to("card3")
    (tmp_path / "usb1/1-1/1-1.1/speed").write_text("12\n")
    (proc / "card3" / "stream0").write_text(
        "Playback:\n  Interface 1\n    Format: S16_LE\n    Rates: 44100, 48000\n"
        "Capture:\n  Interface 2\n    Format: S24_3LE\n    Rates: 96000\n    Bits: 24\n")
    assert outputs.usb_details("Device", sound, proc) == "USB 1.1 · up to 48 kHz / 16-bit"


def test_a_card_not_on_usb_has_no_details(tmp_path):
    proc, sound = _usb_card(tmp_path, 5, "x", "y", usb=False)
    (proc / "sndrpihifiberry").symlink_to("card5")
    assert outputs.usb_details("sndrpihifiberry", sound, proc) is None


# --- ADR-0143: a 32-bit-only DAC, and Lyrion's 384 kHz -----------------------

SMSL_DUMP = "FORMAT:  S32_LE SPECIAL DSD_U32_BE\nSAMPLE_BITS: 32\nRATE: [44100 768000]\n"
HAT_DUMP = "FORMAT:  S16_LE S24_LE S32_LE\nSAMPLE_BITS: [16 32]\nRATE: [44100 192000]\n"


def _asked(monkeypatch, dumps):
    import subprocess as sp
    monkeypatch.setattr(outputs, "_needs_plug", {})
    monkeypatch.setattr(outputs, "_formats", {})
    monkeypatch.setattr(outputs, "_rates", {})
    monkeypatch.setattr(outputs, "_asked_of", {})
    def run(args, **kw):
        return sp.CompletedProcess(args, 0, "", dumps[args[3].split(":", 1)[1]])
    monkeypatch.setattr(outputs.subprocess, "run", run)


def test_a_dac_taking_only_32_bits_is_widened_and_no_other(monkeypatch):
    _asked(monkeypatch, {"AUDIO": SMSL_DUMP, "sndrpihifiberry": HAT_DUMP})
    assert outputs.needs_plug("AUDIO") is False and outputs.widens("AUDIO") is True
    assert outputs.needs_plug("sndrpihifiberry") is False and outputs.widens("sndrpihifiberry") is False


def _plugged_dac(tmp_path, monkeypatch, card="AUDIO", devnum=5):
    """A USB card as sysfs and /proc/asound show it: the card's link, its
    device under a USB device, and that device's bus number on the bus."""
    proc, sound = tmp_path / "proc", tmp_path / "sound"
    usb = tmp_path / "devices" / "usb1" / "1-1"
    interface = usb / "1-1:1.0"
    for d in (proc, sound / "card6", interface):
        d.mkdir(parents=True, exist_ok=True)
    (proc / "card6").mkdir(exist_ok=True)
    if not (proc / card).is_symlink():
        (proc / card).symlink_to("card6")
    if not (sound / "card6" / "device").is_symlink():
        (sound / "card6" / "device").symlink_to(interface)
    (usb / "busnum").write_text("1\n")
    (usb / "devnum").write_text(f"{devnum}\n")
    monkeypatch.setattr(outputs, "SOUND", sound)
    monkeypatch.setattr(outputs, "PROC_ASOUND", proc)


S16_S24_DUMP = "FORMAT:  S16_LE S24_3LE\nSAMPLE_BITS: [16 24]\nRATE: [44100 96000]\n"


def test_a_different_dac_under_the_same_card_id_is_asked_again(monkeypatch, tmp_path):
    """Finding 125 #15 (2026-10-14): what a card takes was cached by its
    ALSA id for the life of the core. A 32-bit-only DAC unplugged and
    another with the same id plugged in inherited its widening, its rates
    and its native DSD: the chain was written S32_LE to a card refusing it,
    and nothing played until gexis-core restarted."""
    dumps = {"AUDIO": SMSL_DUMP}
    _asked(monkeypatch, dumps)
    _plugged_dac(tmp_path, monkeypatch, devnum=5)
    assert outputs.needs_plug("AUDIO") is False and outputs.widens("AUDIO") is True
    assert outputs.native_dsd("AUDIO") == "u32be"
    # Unplugged, and another DAC taking 16 and 24 bits plugged in: the bus
    # numbers it afresh.
    dumps["AUDIO"] = S16_S24_DUMP
    _plugged_dac(tmp_path, monkeypatch, devnum=6)
    assert outputs.widens("AUDIO") is False, "nothing asked yet: what the old DAC took is gone"
    assert outputs.native_dsd("AUDIO") is None
    assert outputs.squeezelite_options("AUDIO", dsd=True) == outputs.SQUEEZELITE_RESAMPLE, "no DSD: the resampler, as on any card"
    assert outputs.needs_plug("AUDIO") is False and outputs.widens("AUDIO") is False


def test_the_same_dac_is_not_asked_twice_and_a_busy_new_one_is_unknown(monkeypatch, tmp_path):
    """Asking plays a second of zeroes, so the same device keeps its answer;
    a replaced one that is busy answers nothing, which is not the old card's
    answer (Finding 125 #15)."""
    import subprocess as sp
    asked = []
    dumps = {"AUDIO": SMSL_DUMP}
    _asked(monkeypatch, dumps)
    def run(args, **kw):
        asked.append(args[3])
        return sp.CompletedProcess(args, 0, "", dumps["AUDIO"])
    monkeypatch.setattr(outputs.subprocess, "run", run)
    _plugged_dac(tmp_path, monkeypatch, devnum=5)
    assert outputs.needs_plug("AUDIO") is False and outputs.needs_plug("AUDIO") is False
    assert len(asked) == 1
    dumps["AUDIO"] = ""                                    # busy: says nothing
    _plugged_dac(tmp_path, monkeypatch, devnum=7)
    assert outputs.needs_plug("AUDIO") is None
    assert outputs.widens("AUDIO") is False and outputs.native_dsd("AUDIO") is None


def test_the_widened_chain_pads_to_32_bits_under_the_meter_and_the_card_reads_back(tmp_path):
    out = outputs.Output(card="AUDIO", label="SMSL USB DAC", control=None)
    conf = outputs.render(out, False, widen=True)
    head = conf[conf.index("pcm.output {"):conf.index("pcm.output_wait")]
    assert "type meter" in head and 'type linear slave { pcm "hw:AUDIO" format S32_LE }' in head
    assert "{ type linear slave { pcm { type hw card AUDIO nonblock 0 } format S32_LE } }" in conf
    assert "type plug" not in conf, "widening is not plug: it never changes the rate"
    soft = outputs.render(outputs.with_software_volume(out), False, widen=True)
    assert 'type linear slave { pcm "hw:AUDIO" format S32_LE }' in soft and "type softvol" in soft
    path = tmp_path / "output.conf"
    path.write_text(conf)
    assert outputs.configured(path) == "AUDIO"


def test_squeezelite_is_told_rates_only_for_a_dac_beyond_384_khz(monkeypatch, tmp_path):
    _asked(monkeypatch, {"AUDIO": SMSL_DUMP, "sndrpihifiberry": HAT_DUMP})
    outputs.needs_plug("AUDIO"); outputs.needs_plug("sndrpihifiberry")
    assert outputs.squeezelite_options("AUDIO") == "-r 44100,48000,88200,96000,176400,192000,352800,384000 " + outputs.SQUEEZELITE_RESAMPLE
    assert outputs.squeezelite_options("sndrpihifiberry") == outputs.SQUEEZELITE_RESAMPLE
    env = tmp_path / "squeezelite.env"
    assert outputs.write_squeezelite_env("AUDIO", env) is True
    assert "GEXIS_SQUEEZELITE_OPTIONS=-r 44100," in env.read_text()
    assert outputs.write_squeezelite_env("AUDIO", env) is False
    outputs.write_squeezelite_env("sndrpihifiberry", env)
    assert env.read_text().splitlines()[-1] == "GEXIS_SQUEEZELITE_OPTIONS=" + outputs.SQUEEZELITE_RESAMPLE


def test_squeezelite_converts_only_the_rates_a_card_lacks_upward(monkeypatch):
    """ADR-0155 (Finding 130): a card without 88.2 or 176.4 kHz left Lyrion
    silent on them. Squeezelite resamples only a rate the card lacks (`E`),
    to the card's highest (`X`), in soxr's very high quality (`v`) - on
    every card, since a card that takes the rate is never touched."""
    _asked(monkeypatch, {"AUDIO": SMSL_DUMP, "sndrpihifiberry": HAT_DUMP})
    outputs.needs_plug("AUDIO"); outputs.needs_plug("sndrpihifiberry")
    assert outputs.SQUEEZELITE_RESAMPLE == "-R -u vEX"
    for card in ("AUDIO", "sndrpihifiberry"):
        assert outputs.squeezelite_options(card).split()[-3:] == ["-R", "-u", "vEX"]


def test_the_squeezelite_unit_reads_the_options_unbraced():
    from pathlib import Path
    unit = (Path(__file__).resolve().parents[2] / "image/stage-gexis/02-renderers/files/squeezelite.service").read_text()
    assert "EnvironmentFile=-/etc/gexis/squeezelite.env" in unit
    assert unit.rstrip().split("ExecStart=")[1].splitlines()[0].endswith(" $GEXIS_SQUEEZELITE_OPTIONS")


def test_a_card_is_running_when_any_playback_substream_is(tmp_path):
    sub = tmp_path / "AUDIO" / "pcm0p" / "sub0"
    sub.mkdir(parents=True)
    (sub / "status").write_text("closed\n")
    assert outputs.card_running("AUDIO", tmp_path) is False
    (sub / "status").write_text("state: RUNNING\nowner_pid   : 1\n")
    assert outputs.card_running("AUDIO", tmp_path) is True
    assert outputs.card_running("missing", tmp_path) is False


# --- ADR-0144: native DSD ----------------------------------------------------

def test_native_dsd_is_the_cards_own_format_and_only_with_the_volume_fixed(monkeypatch):
    _asked(monkeypatch, {"AUDIO": SMSL_DUMP, "sndrpihifiberry": HAT_DUMP})
    outputs.needs_plug("AUDIO"); outputs.needs_plug("sndrpihifiberry")
    assert outputs.native_dsd("AUDIO") == "u32be"
    assert outputs.native_dsd("sndrpihifiberry") is None
    assert outputs.squeezelite_options("AUDIO", dsd=True).endswith(" -D :u32be")
    assert "-R" not in outputs.squeezelite_options("AUDIO", dsd=True), "a resampler would turn DSD into PCM"
    assert "-D" not in outputs.squeezelite_options("AUDIO")
    assert outputs.squeezelite_options("sndrpihifiberry", dsd=True) == outputs.SQUEEZELITE_RESAMPLE, "no DSD on a board that takes none"


def test_with_dsd_squeezelites_chain_skips_the_widening_and_the_others_keep_it():
    out = outputs.Output(card="AUDIO", label="SMSL USB DAC", control=None)
    conf = outputs.render(out, False, widen=True, dsd=True)
    head = conf[conf.index("pcm.output {"):conf.index("pcm.output_wait")]
    wait = conf[conf.index("pcm.output_wait {"):conf.index("ctl.output")]
    assert "type linear" in head, "Bluetooth and Spotify still get 32 bits"
    assert "type linear" not in wait and "{ type hw card AUDIO nonblock 0 }" in wait
    assert "type meter" in wait, "the meter stays: peppyalsa draws nothing from DSD"


def test_write_turns_dsd_on_only_when_fixed(monkeypatch, tmp_path):
    _asked(monkeypatch, {"AUDIO": SMSL_DUMP})
    seen = {}
    monkeypatch.setattr(outputs, "write_squeezelite_env", lambda card, path=None, dsd=False: seen.update(dsd=dsd))
    monkeypatch.setattr(outputs, "CONF_PATH", tmp_path / "output.conf")
    out = outputs.Output(card="AUDIO", label="SMSL USB DAC", control=None)
    outputs.write(out, tmp_path / "output.conf", fixed=True)
    assert seen == {"dsd": True}
    outputs.write(out, tmp_path / "output.conf", fixed=False)
    assert seen == {"dsd": False}
    outputs.write(outputs.with_software_volume(out), tmp_path / "output.conf", fixed=True)
    assert seen == {"dsd": False}, "never through the software stage"


# --- ADR-0141 D5: the jack stands in for an HDMI output with nothing on it ----

def _outs(hdmi2_connected):
    return [outputs.Output(card="vc4hdmi0", label="HDMI 1", control=None),
            outputs.Output(card="vc4hdmi1", label="HDMI 2", control=None, connected=hdmi2_connected),
            outputs.Output(card="Headphones", label="Headphones (3.5 mm)", control="PCM")]


def test_an_hdmi_output_with_nothing_connected_is_played_through_the_jack():
    out, standing = outputs.in_force("HDMI 2", _outs(False))
    assert out.card == "Headphones" and standing is True


def test_the_hdmi_output_plays_again_once_connected_and_others_are_untouched():
    out, standing = outputs.in_force("HDMI 2", _outs(True))
    assert out.card == "vc4hdmi1" and standing is False
    out, standing = outputs.in_force("Headphones (3.5 mm)", _outs(False))
    assert out.card == "Headphones" and standing is False


# --- What is on an HDMI port, for sound (George, 2026-10-13) ----------------

ELD_TV = """monitor_name\t\tLG TV
connection_type\t\tHDMI
sad_count\t\t3
sad0_coding_type\t[0x1] LPCM
sad0_channels\t\t8
sad0_rates\t\t[0x1ee0] 32000 44100 48000 88200 96000 176400 192000
sad0_bits\t\t[0xe] 16 20 24
sad1_coding_type\t[0x2] AC-3
sad1_channels\t\t6
sad1_rates\t\t[0xe0] 32000 44100 48000
sad2_coding_type\t[0x9] DSD (One Bit Audio)
sad2_channels\t\t6
sad2_rates\t\t[0x40] 44100
"""
ELD_SCREEN = """monitor_name\t\tWaveShare
connection_type\t\tHDMI
sad_count\t\t1
sad0_coding_type\t[0x1] LPCM
sad0_channels\t\t2
sad0_rates\t\t[0xe0] 32000 44100 48000
sad0_bits\t\t[0xe] 16 20 24
"""


def _eld(tmp_path, card, text):
    d = tmp_path / card
    d.mkdir(parents=True, exist_ok=True)
    (d / "eld#0.0").write_text(text)
    return tmp_path


def test_an_hdmi_port_says_what_is_on_it_and_the_pcm_it_takes(tmp_path):
    """Read on sofapi: an LG TV on HDMI 2, the WaveShare screen on HDMI 1.
    Only PCM: the TV's AC-3 and one-bit DSD are not what the Pi sends."""
    from gexis_core.outputs import hdmi_sound

    proc = _eld(tmp_path, "vc4hdmi1", ELD_TV)
    assert hdmi_sound("vc4hdmi1", proc) == ("LG TV", "up to 192 kHz / 24-bit")
    proc = _eld(tmp_path, "vc4hdmi0", ELD_SCREEN)
    assert hdmi_sound("vc4hdmi0", proc) == ("WaveShare", "up to 48 kHz / 24-bit")


def test_a_device_without_sound_says_so(tmp_path):
    from gexis_core.outputs import hdmi_sound

    proc = _eld(tmp_path, "vc4hdmi0", "monitor_name\t\tDELL U2415\nsad_count\t\t0\n")
    assert hdmi_sound("vc4hdmi0", proc) == ("DELL U2415", "takes no sound")


def test_nothing_connected_or_not_hdmi_has_no_line(tmp_path):
    from gexis_core.outputs import hdmi_sound

    assert hdmi_sound("vc4hdmi0", tmp_path) is None, "no ELD file"
    proc = _eld(tmp_path, "vc4hdmi1", "monitor_present\t\t0\neld_valid\t\t0\n")
    assert hdmi_sound("vc4hdmi1", proc) is None
    proc = _eld(tmp_path, "Headphones", ELD_TV)
    assert hdmi_sound("Headphones", proc) is None


def test_a_missing_output_is_reported_once_until_it_comes_back(caplog, monkeypatch):
    """With the stand-in watcher working (it runs `resolve` every 3 s), a USB
    DAC left unplugged was reported every 3 s - sofapi, 2026-10-15, 20 a
    minute. Once while it is away; again after it has been seen back."""
    monkeypatch.setattr(outputs, "_said_missing", set())
    dac = Output(card="DAC", label="SMSL USB DAC", control="PCM")
    caplog.set_level("WARNING", logger="gexis_core.outputs")

    def said() -> int:
        return sum("is not here any more" in r.getMessage() for r in caplog.records)

    for _ in range(5):
        assert outputs.resolve("SMSL USB DAC", [JACK], current="Headphones") is JACK
    assert said() == 1
    assert outputs.resolve("SMSL USB DAC", [JACK, dac], current="Headphones") is dac
    outputs.resolve("SMSL USB DAC", [JACK], current="Headphones")
    assert said() == 2
