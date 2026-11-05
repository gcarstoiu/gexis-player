"""The measurement microphone (ADR-0175 item 9): the UMIK-1 found by its USB
identity, whatever ALSA calls it, and the level it reads as dB SPL."""
from gexis_core import room_correction as rc
from gexis_core import room_mic
from gexis_core.room_mic import Microphone


def card(proc, sound, n, usbid, cid, product, capture=True, playback=False):
    d = proc / f"card{n}"
    d.mkdir(parents=True)
    if usbid:
        (d / "usbid").write_text(usbid + "\n")
    (d / "id").write_text(cid + "\n")
    if capture:
        (d / "pcm0c").mkdir()
    if playback:
        (d / "pcm0p").mkdir()
    # sysfs: the card's device is the USB interface; the device above it
    # says what it is.
    usb = sound.parent / "usb" / f"1-1.{n}"
    (usb / f"1-1.{n}:1.0").mkdir(parents=True)
    (usb / "product").write_text(product + "\n")
    sound.mkdir(exist_ok=True)
    (sound / f"card{n}").mkdir()
    (sound / f"card{n}" / "device").symlink_to(usb / f"1-1.{n}:1.0")


def test_a_usb_c_umik_is_found_by_its_identity(tmp_path):
    proc, sound = tmp_path / "proc", tmp_path / "sys" / "sound"
    card(proc, sound, 0, None, "sndrpihifiberry", "", capture=False, playback=True)
    card(proc, sound, 10, "2752:0007", "UMIK1", "UMIK-1")
    assert room_mic.find(proc, sound) == ("found", Microphone("UMIK1", None))
    assert Microphone("UMIK1", None).device == "plughw:CARD=UMIK1,DEV=0"


def test_an_older_one_says_its_gain(tmp_path):
    proc, sound = tmp_path / "proc", tmp_path / "sys" / "sound"
    card(proc, sound, 3, "2752:0007", "U18dB", "Umik-1  Gain: 18dB  ")
    assert room_mic.find(proc, sound) == ("found", Microphone("U18dB", 18.0))


def test_another_microphone_is_not_supported_yet(tmp_path):
    proc, sound = tmp_path / "proc", tmp_path / "sys" / "sound"
    card(proc, sound, 2, "0d8c:0014", "Device", "USB Audio Device")
    card(proc, sound, 4, "1234:5678", "DAC", "USB DAC", capture=False, playback=True)
    assert room_mic.find(proc, sound) == ("other", None)


def test_nothing_plugged_in(tmp_path):
    proc, sound = tmp_path / "proc", tmp_path / "sys" / "sound"
    card(proc, sound, 4, "1234:5678", "DAC", "USB DAC", capture=True, playback=True)
    assert room_mic.find(proc, sound) == ("absent", None)
    assert room_mic.find(tmp_path / "nowhere", sound) == ("absent", None)


def test_the_level_in_db_spl_as_rew_reads_the_sensitivity():
    cal = rc.Calibration("7071234", -0.667, ((10.0, 0.0), (20000.0, 0.0)), "2026-11-05", gain_db=18.0)
    assert room_mic.spl_offset(cal) == 94.667
    assert room_mic.spl_offset(cal, Microphone("U18dB", 18.0)) == 94.667
    assert room_mic.spl_offset(cal, Microphone("U12dB", 12.0)) == 100.667, "its switches set 6 dB less"
    assert room_mic.spl_offset(cal, Microphone("UMIK1", None)) == 94.667


async def test_a_cancelled_signal_stops_its_sound(monkeypatch):
    """The player and the recorder are both stopped when a run is cancelled
    mid-sweep (George, 2026-11-05: Cancel should be instant)."""
    import asyncio

    import pytest
    np = pytest.importorskip("numpy")
    procs = []

    class Proc:
        def __init__(self, name):
            self.name, self.returncode, self.killed = name, None, False
            self.stdout = self

        async def read(self):
            await asyncio.sleep(60)
            return b""

        async def communicate(self, data=None):
            await asyncio.sleep(60)
            return b"", b""

        async def wait(self):
            return 0

        def kill(self):
            self.killed, self.returncode = True, -9

    async def exec_(*args, **_kwargs):
        p = Proc(args[0])
        procs.append(p)
        return p

    cal = rc.Calibration("7071234", -0.7, ((10.0, 0.0), (20000.0, 0.0)), "2026-11-05")
    audio = room_mic.Audio(Microphone("UMIK1", None), cal, exec_=exec_)
    task = asyncio.create_task(audio.play(np.zeros(48000), channel=0))
    await asyncio.sleep(room_mic.LEAD_S + 0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert [p.name for p in procs] == ["arecord", "aplay"] and all(p.killed for p in procs)
