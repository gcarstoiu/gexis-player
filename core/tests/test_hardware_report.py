"""ADR-0126: what a hardware report carries, and never carries."""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from gexis_core import hardware_report as hr

DEVICES = """\
I: Bus=001e Vendor=0000 Product=0000 Version=0001
N: Name="vc4-hdmi-0"
H: Handlers=kbd event0

I: Bus=0003 Vendor=222a Product=0001 Version=0110
N: Name="ILITEK ILITEK-TP"
U: Uniq=SN-0042-SECRET
H: Handlers=mouse0 event4
"""


def test_the_touch_controller_by_name_and_id_never_its_serial(tmp_path, monkeypatch):
    devices = tmp_path / "devices"
    devices.write_text(DEVICES)
    monkeypatch.setattr(hr, "INPUT_DEVICES", devices)
    assert hr._touch() == ["ILITEK ILITEK-TP (222a:0001)"]


def facts():
    return hr.Facts(pi="Raspberry Pi 4 Model B Rev 1.5", memory_mb=3795, version="0.9.4", kernel="6.18",
                    card="IQaudIODAC", board="IQaudIO Pi-DAC PRO", state="Tested",
                    eeprom_vendor="IQaudIO Limited", eeprom_product="Pi-DAC PRO", eeprom_id="0x0008",
                    controls=["Digital", "Analogue"], formats="S16_LE S32_LE", rates="[8000 384000]",
                    screen_connected=True, edid_maker="RTK", edid_name="RTK FHD", preferred="1920x1080",
                    screen_chosen='Waveshare 13.3" HDMI LCD (H)', touch=["ILITEK ILITEK-TP (222a:0001)"])


def test_the_issue_is_prefilled_with_the_answers_and_the_facts():
    url = hr.issue_url(facts(), {"sound": "Yes", "volume": "No", "bogus": "x"}, "Clicks at 96 kHz.")
    q = parse_qs(urlsplit(url).query)
    assert q["template"] == ["hardware-report.yml"]
    assert q["title"] == ['[Hardware] IQaudIO Pi-DAC PRO · Waveshare 13.3" HDMI LCD (H)']
    assert q["sound"] == ["Yes"] and q["volume"] == ["No"] and "bogus" not in q, "only the form's own fields"
    assert q["notes"] == ["Clicks at 96 kHz."]
    assert "Pi-DAC PRO / 0x0008" in q["details"][0] and "S16_LE S32_LE" in q["details"][0]


def test_a_long_report_is_cut_to_what_github_accepts():
    f = facts()
    f.controls = [f"Control number {n}" for n in range(800)]
    url = hr.issue_url(f, {"sound": "Yes"}, "")
    assert len(url) <= hr.URL_MAX
    assert parse_qs(urlsplit(url).query)["details"][0].endswith("[cut]")


def test_no_sound_card_still_makes_a_report():
    f = hr.Facts(pi="Raspberry Pi 4", memory_mb=1844, version="0.9.4", kernel="6.18")
    q = parse_qs(urlsplit(hr.issue_url(f, {}, "")).query)
    assert q["board"] == ["no sound card"] and q["screen"] == ["none"]
    assert "card: none" in q["details"][0]


def test_a_tone_is_the_rate_and_format_music_comes_in_at_minus_20_dbfs(tmp_path):
    import math, struct, wave
    for rate, width in ((44100, 2), (96000, 4), (192000, 4)):
        path = tmp_path / f"t{rate}.wav"
        hr._tone(path, rate)
        with wave.open(str(path)) as w:
            assert (w.getframerate(), w.getsampwidth(), w.getnchannels()) == (rate, width, 2)
            data = w.readframes(w.getnframes())
        fmt = "<h" if width == 2 else "<i"
        peak = max(abs(struct.unpack_from(fmt, data, i)[0]) for i in range(0, len(data), width))
        dbfs = 20 * math.log10(peak / (2 ** (8 * width - 1) - 1))
        assert -20.1 < dbfs <= -19.9, (rate, dbfs)
        if width == 4:
            assert all(data[i] == 0 for i in range(0, len(data), 4)), "24 bits in a 32-bit container"


def test_nothing_is_played_over_music(tmp_path, monkeypatch):
    status = tmp_path / "card5" / "pcm0p" / "sub0"
    status.mkdir(parents=True)
    (status / "status").write_text("state: RUNNING\n")
    monkeypatch.setattr(hr, "Path", lambda p: tmp_path if p == "/proc/asound" else __import__("pathlib").Path(p))
    assert hr.playing() is True
    (status / "status").write_text("closed\n")
    assert hr.playing() is False


def test_the_tones_reach_the_report():
    url = hr.issue_url(facts(), {"sound": "Yes"}, "", ["44.1 kHz: played, the card at 44.1 kHz S16_LE"])
    assert "Test tones\n- 44.1 kHz: played" in parse_qs(urlsplit(url).query)["details"][0]
